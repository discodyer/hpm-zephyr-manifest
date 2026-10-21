#!/usr/bin/env python3
# Copyright (c) 2026 The HPM Zephyr Module Contributors
# SPDX-License-Identifier: Apache-2.0

"""Validate that the manifest has no unresolved repository placeholders."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
manifest = (ROOT / "west.yml").read_text(encoding="utf-8")

if "YOUR_GITHUB_ORG" in manifest:
    print("error: replace YOUR_GITHUB_ORG in west.yml", file=sys.stderr)
    raise SystemExit(1)

print("west manifest placeholders: OK")
