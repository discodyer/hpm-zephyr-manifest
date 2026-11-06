#!/usr/bin/env python3
# Copyright (c) 2026 The HPM Zephyr Module Contributors
# Copyright (c) 2026 Cody Gu <gujiaqi@iscas.ac.cn>
# SPDX-License-Identifier: Apache-2.0

"""West frontend for the workspace OpenOCD setup helper."""

from pathlib import Path
import subprocess
import sys

from west.commands import WestCommand
from west.util import west_topdir

SETUP_SCRIPT = Path(__file__).with_name("setup_openocd.py")


class OpenOcdSetup(WestCommand):
    """Build the pinned OpenOCD backport and configure Zephyr runners."""

    def __init__(self):
        super().__init__(
            "openocd-setup",
            "build and configure the pinned HPM OpenOCD backport",
            description=(
                "Build the OpenOCD project pinned in west.yml, install it under "
                "<workspace>/.tools/openocd-hpm, and configure west build.cmake-args "
                "to use that installation."
            ),
        )

    def do_add_parser(self, parser_adder):
        parser = parser_adder.add_parser(
            self.name,
            help=self.help,
            description=self.description,
        )
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument(
            "--check",
            action="store_true",
            help="verify the installation and west configuration without rebuilding",
        )
        mode.add_argument(
            "--force",
            action="store_true",
            help="force a rebuild even if the installed commit matches",
        )
        parser.add_argument(
            "--prefix",
            help="installation prefix (default: <workspace>/.tools/openocd-hpm)",
        )
        parser.add_argument(
            "--build-dir",
            help="build directory (default: <workspace>/.tools/build/openocd-hpm)",
        )
        parser.add_argument(
            "--jobs",
            type=int,
            help="parallel build jobs (default: host CPU count)",
        )
        return parser

    def do_run(self, args, unknown_args):
        if unknown_args:
            self.die(f"unknown arguments: {' '.join(unknown_args)}")

        workspace = west_topdir()
        if workspace is None:
            self.die("not inside a west workspace")

        command = [sys.executable, str(SETUP_SCRIPT), "--workspace", workspace]
        if args.check:
            command.append("--check")
        if args.force:
            command.append("--force")
        if args.prefix:
            command.extend(["--prefix", args.prefix])
        if args.build_dir:
            command.extend(["--build-dir", args.build_dir])
        if args.jobs is not None:
            command.extend(["--jobs", str(args.jobs)])

        result = subprocess.run(command, check=False)
        if result.returncode:
            self.die(f"OpenOCD setup failed with exit code {result.returncode}")
