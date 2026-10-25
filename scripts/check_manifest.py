#!/usr/bin/env python3
# Copyright (c) 2026 The HPM Zephyr Module Contributors
# SPDX-License-Identifier: Apache-2.0

"""Validate manifest placeholders and immutable vendor/module pins."""

from pathlib import Path
import sys
import re

ROOT = Path(__file__).resolve().parents[1]
manifest = (ROOT / "west.yml").read_text(encoding="utf-8")

if "YOUR_GITHUB_ORG" in manifest:
    print("error: replace YOUR_GITHUB_ORG in west.yml", file=sys.stderr)
    raise SystemExit(1)


def project_revision(name: str) -> str | None:
    """Return the revision belonging to the named west project."""
    match = re.search(
        rf"^    - name: {re.escape(name)}\n(?:.*\n)*?      revision: ([^\n]+)$",
        manifest,
        re.MULTILINE,
    )
    return match.group(1) if match else None


hpm_sdk_revision = project_revision("hpm_sdk")
if hpm_sdk_revision is None:
    print("error: hpm_sdk project is missing from west.yml", file=sys.stderr)
    raise SystemExit(1)
if not re.fullmatch(r"[0-9a-f]{40}", hpm_sdk_revision):
    print(
        "error: hpm_sdk must be pinned to a full 40-character commit SHA",
        file=sys.stderr,
    )
    raise SystemExit(1)

hpm_zephyr_revision = project_revision("hpm-zephyr")
if hpm_zephyr_revision is None:
    print("error: hpm-zephyr project is missing from west.yml", file=sys.stderr)
    raise SystemExit(1)
if not re.fullmatch(r"[0-9a-f]{40}", hpm_zephyr_revision):
    print(
        "error: hpm-zephyr must be pinned to a full 40-character commit SHA",
        file=sys.stderr,
    )
    raise SystemExit(1)

print("west manifest immutable pins: OK")
