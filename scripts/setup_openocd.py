#!/usr/bin/env python3
# Copyright (c) 2026 The HPM Zephyr Module Contributors
# Copyright (c) 2026 Cody Gu <gujiaqi@iscas.ac.cn>
# SPDX-License-Identifier: Apache-2.0

"""Build the pinned OpenOCD backport and configure west to use it."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Sequence

PROJECT = "openocd-zephyr"
DEFAULT_PREFIX = Path(".tools/openocd-hpm")
DEFAULT_BUILD_DIR = Path(".tools/build/openocd-hpm")
CONFIGURE_FLAGS = (
    "--disable-werror",
    "--enable-ftdi",
    "--disable-jlink",
    "--enable-internal-jimtcl",
    "--disable-internal-libjaylink",
)
CMAKE_OPENOCD = "-DOPENOCD="
CMAKE_OPENOCD_SCRIPTS = "-DOPENOCD_DEFAULT_PATH="


class SetupError(RuntimeError):
    """A recoverable OpenOCD setup error."""


def run(
    command: Sequence[str],
    *,
    cwd: Path,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a command and convert process errors into SetupError."""
    if not capture_output:
        print(f"+ {shlex.join(command)}", flush=True)

    try:
        return subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError as error:
        raise SetupError(f"required program not found: {command[0]}") from error
    except subprocess.CalledProcessError as error:
        detail = ""
        if capture_output:
            detail = (error.stderr or error.stdout or "").strip()
        if detail:
            raise SetupError(
                f"command failed: {shlex.join(command)}\n{detail}"
            ) from error
        raise SetupError(
            f"command failed with exit code {error.returncode}: {shlex.join(command)}"
        ) from error


def ensure_command(name: str) -> None:
    """Fail with a useful message when a host build tool is unavailable."""
    if shutil.which(name) is None:
        raise SetupError(
            f"required host build tool not found: {name}. "
            "Install the OpenOCD build prerequisites and retry."
        )


def find_workspace(value: str | None) -> Path:
    """Return the workspace root from an argument or the current directory."""
    if value:
        workspace = Path(value).resolve()
    else:
        result = run(
            ["west", "topdir"],
            cwd=Path.cwd(),
            capture_output=True,
        )
        workspace = Path(result.stdout.strip()).resolve()

    if not (workspace / ".west").exists():
        raise SetupError(f"not a west workspace: {workspace}")
    return workspace


def workspace_path(workspace: Path, value: str | Path) -> Path:
    """Resolve a path and keep generated setup data inside the workspace."""
    path = Path(value)
    if not path.is_absolute():
        path = workspace / path
    path = path.resolve()
    if path != workspace and workspace not in path.parents:
        raise SetupError(f"setup path must be inside workspace {workspace}: {path}")
    return path


def openocd_source(workspace: Path) -> Path:
    """Locate the OpenOCD project from the resolved west manifest."""
    result = run(
        ["west", "list", PROJECT, "-f", "{abspath}"],
        cwd=workspace,
        capture_output=True,
    )
    source = Path(result.stdout.strip()).resolve()
    if not (source / ".git").exists():
        raise SetupError(
            f"{PROJECT} is not cloned at {source}; run: west update {PROJECT}"
        )
    return source


def source_fingerprint(source: Path) -> str:
    """Return the checked-out commit and dirty state used for rebuild detection."""
    head = run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        cwd=source,
        capture_output=True,
    ).stdout.strip()
    dirty = bool(
        run(
            ["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"],
            cwd=source,
            capture_output=True,
        ).stdout.strip()
    )
    return f"{head}-dirty" if dirty else head


def binary_version(binary: Path) -> str:
    """Return the first line reported by the installed OpenOCD binary."""
    result = run([str(binary), "--version"], cwd=binary.parent, capture_output=True)
    lines = (result.stdout + result.stderr).splitlines()
    if not lines:
        raise SetupError(f"{binary} did not report a version")
    return lines[0]


def installation_matches(binary: Path, stamp: Path, fingerprint: str) -> bool:
    """Check that the installed binary and source commit stamp are current."""
    if fingerprint.endswith("-dirty"):
        return False
    if not binary.is_file() or not stamp.is_file():
        return False
    if stamp.read_text(encoding="utf-8").strip() != fingerprint:
        return False
    return fingerprint[:8] in binary_version(binary)


def prepare_jimtcl(source: Path) -> None:
    """Ensure the Jim Tcl submodule needed by OpenOCD is available."""
    run(
        [
            "git",
            "-C",
            str(source),
            "submodule",
            "update",
            "--init",
            "--recursive",
            "jimtcl",
        ],
        cwd=source,
    )


def prepare_configure(source: Path) -> Path:
    """Generate the autotools configure script when it is absent."""
    configure = source / "configure"
    if configure.is_file():
        return configure

    for command in ("autoconf", "automake", "libtoolize", "make", "cc"):
        ensure_command(command)
    run(["./bootstrap"], cwd=source)
    if not configure.is_file():
        raise SetupError(f"bootstrap did not generate {configure}")
    return configure


def build_openocd(
    source: Path,
    prefix: Path,
    build_dir: Path,
    jobs: int,
) -> None:
    """Configure, build, and strip-install OpenOCD out of tree."""
    for command in ("git", "make", "cc", "pkg-config", "strip"):
        ensure_command(command)
    prepare_jimtcl(source)
    configure = prepare_configure(source)

    prefix.mkdir(parents=True, exist_ok=True)
    expected_config = "\n".join((str(prefix), *CONFIGURE_FLAGS))
    config_stamp = build_dir / ".configure-args"
    makefile = build_dir / "Makefile"
    needs_configure = not makefile.is_file()
    if not needs_configure:
        if not config_stamp.is_file():
            needs_configure = True
        else:
            current_config = config_stamp.read_text(encoding="utf-8").strip()
            needs_configure = current_config != expected_config

    if needs_configure:
        if build_dir.exists():
            shutil.rmtree(build_dir)
        build_dir.mkdir(parents=True)
        run(
            [str(configure), f"--prefix={prefix}", *CONFIGURE_FLAGS],
            cwd=build_dir,
        )
        config_stamp.write_text(f"{expected_config}\n", encoding="utf-8")

    run(["make", f"-j{jobs}"], cwd=build_dir)
    run(["make", "install-strip"], cwd=build_dir)


def west_config_get(workspace: Path, key: str) -> str | None:
    """Return a west configuration value, or None when it is unset."""
    result = subprocess.run(
        ["west", "config", key],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def desired_cmake_args(current: str | None, prefix: Path) -> str:
    """Replace OpenOCD options while preserving unrelated CMake arguments."""
    words = shlex.split(current) if current else []
    words = [
        word
        for word in words
        if not word.startswith(CMAKE_OPENOCD)
        and not word.startswith(CMAKE_OPENOCD_SCRIPTS)
    ]
    words.extend(
        (
            f"{CMAKE_OPENOCD}{prefix / 'bin' / 'openocd'}",
            f"{CMAKE_OPENOCD_SCRIPTS}{prefix / 'share' / 'openocd' / 'scripts'}",
        )
    )
    return shlex.join(words)


def configure_west(workspace: Path, prefix: Path) -> str:
    """Persist the OpenOCD paths in the workspace-local west configuration."""
    current = west_config_get(workspace, "build.cmake-args")
    expected = desired_cmake_args(current, prefix)
    if current != expected:
        run(
            ["west", "config", "build.cmake-args", "--", expected],
            cwd=workspace,
        )
    return expected


def validate_workspace_paths(
    workspace: Path,
    prefix: Path,
    build_dir: Path,
) -> None:
    """Reject generated paths that could destroy workspace or source content."""
    project = workspace / PROJECT
    for path in (prefix, build_dir):
        if path == workspace or path == project:
            raise SetupError(f"refusing unsafe generated directory: {path}")
        if project == path or project in path.parents:
            raise SetupError(f"generated directory must not contain {PROJECT}: {path}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse setup options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", help="west workspace root")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="verify the installation and west configuration without rebuilding",
    )
    mode.add_argument(
        "--force",
        action="store_true",
        help="rebuild even when the installed source commit matches",
    )
    parser.add_argument(
        "--prefix", help=f"installation prefix (default: {DEFAULT_PREFIX})"
    )
    parser.add_argument(
        "--build-dir", help=f"build directory (default: {DEFAULT_BUILD_DIR})"
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=os.cpu_count() or 1,
        help="parallel build jobs (default: host CPU count)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the OpenOCD setup workflow."""
    args = parse_args(argv)
    if args.jobs < 1:
        print("error: --jobs must be at least 1", file=sys.stderr)
        return 2

    try:
        workspace = find_workspace(args.workspace)
        source = openocd_source(workspace)
        prefix = workspace_path(workspace, args.prefix or DEFAULT_PREFIX)
        build_dir = workspace_path(workspace, args.build_dir or DEFAULT_BUILD_DIR)
        validate_workspace_paths(workspace, prefix, build_dir)

        fingerprint = source_fingerprint(source)
        binary = prefix / "bin" / "openocd"
        stamp = prefix / ".source-commit"
        installed = installation_matches(binary, stamp, fingerprint)

        if args.check:
            if not installed:
                raise SetupError(
                    f"OpenOCD installation is missing or stale: {binary}; "
                    "run: west openocd-setup"
                )
            current_args = west_config_get(workspace, "build.cmake-args")
            expected_args = desired_cmake_args(current_args, prefix)
            if current_args != expected_args:
                raise SetupError(
                    "west build.cmake-args is not configured for this installation; "
                    "run: west openocd-setup"
                )
            print(f"OpenOCD setup: OK ({binary_version(binary)})")
            print(f"Source commit: {fingerprint}")
            print(f"CMake arguments: {expected_args}")
            return 0

        if args.force or not installed:
            build_openocd(source, prefix, build_dir, args.jobs)
            if not binary.is_file():
                raise SetupError(f"install completed without producing {binary}")
            version = binary_version(binary)
            if fingerprint[:8] not in version:
                raise SetupError(
                    f"installed binary version does not match source commit {fingerprint}: "
                    f"{version}"
                )
            stamp.write_text(f"{fingerprint}\n", encoding="utf-8")
        else:
            print(f"Reusing installed OpenOCD at {binary}", flush=True)

        cmake_args = configure_west(workspace, prefix)
        print("\nOpenOCD setup complete", flush=True)
        print(f"  Binary: {binary}")
        print(f"  Scripts: {prefix / 'share' / 'openocd' / 'scripts'}")
        print(f"  Source: {fingerprint}")
        print(f"  west build.cmake-args: {cmake_args}")
        print("\nReconfigure existing build directories once:")
        print("  west build -d <build-dir> --cmake-only")
        print("Then use the normal command:")
        print("  west flash -d <build-dir> --verify")
        return 0
    except (OSError, SetupError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
