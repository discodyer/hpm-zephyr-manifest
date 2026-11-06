#!/usr/bin/env python3
# Copyright (c) 2026 The HPM Zephyr Module Contributors
# Copyright (c) 2026 Cody Gu <gujiaqi@iscas.ac.cn>
# SPDX-License-Identifier: Apache-2.0

"""Validate development and release manifest revisions."""

import argparse
from pathlib import Path
import re
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_REVISION = "refs/heads/main"
IMMUTABLE_PROJECTS = ("zephyr", "hpm_sdk", "openocd-zephyr")
COMMIT_SHA = re.compile(r"[0-9a-f]{40}")


def project_revision(manifest: str, name: str) -> str | None:
    """Return the revision belonging to the named west project."""
    match = re.search(
        rf"^    - name: {re.escape(name)}\n"
        r"(?:(?!    - name: |  self:).*\n)*?      revision: ([^\n]+)$",
        manifest,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def validate_project(
    manifest: str,
    project: str,
    *,
    immutable: bool,
) -> bool:
    """Validate one project revision, reporting the failure if any."""
    revision = project_revision(manifest, project)
    if revision is None:
        print(f"error: {project} project is missing from west.yml", file=sys.stderr)
        return False

    if immutable:
        if not COMMIT_SHA.fullmatch(revision):
            print(
                f"error: {project} must be pinned to a full 40-character commit SHA",
                file=sys.stderr,
            )
            return False
        return True

    if revision == DEVELOPMENT_REVISION or COMMIT_SHA.fullmatch(revision):
        return True

    print(
        f"error: {project} must use {DEVELOPMENT_REVISION} or a full commit SHA "
        "in the development manifest",
        file=sys.stderr,
    )
    return False


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release",
        action="store_true",
        help="require every direct project to use an immutable commit SHA",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Validate west.yml and return a process exit code."""
    args = parse_args(argv)
    manifest = (ROOT / "west.yml").read_text(encoding="utf-8")

    if "YOUR_GITHUB_ORG" in manifest:
        print("error: replace YOUR_GITHUB_ORG in west.yml", file=sys.stderr)
        return 1

    valid = True
    for project in IMMUTABLE_PROJECTS:
        valid &= validate_project(manifest, project, immutable=True)
    valid &= validate_project(manifest, "hpm-zephyr", immutable=args.release)

    if not valid:
        return 1

    if args.release:
        print("west manifest release pins: OK")
    else:
        print("west manifest development revisions: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
