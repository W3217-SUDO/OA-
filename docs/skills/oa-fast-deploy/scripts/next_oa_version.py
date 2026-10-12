#!/usr/bin/env python3
"""Return the next occupied-aware OA release version in the 1.1.x train."""

from __future__ import annotations

import argparse
import re
import sys


VERSION_RE = re.compile(r"(?:^|[^0-9])v?1\.1\.(\d+)(?:$|[^0-9])")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("versions", nargs="*", help="Occupied tags or ledger versions")
    args = parser.parse_args()

    values = list(args.versions)
    if not sys.stdin.isatty():
        values.extend(sys.stdin.read().split())

    patches = []
    for value in values:
        match = VERSION_RE.search(value)
        if match:
            patches.append(int(match.group(1)))

    next_patch = max(patches, default=0) + 1
    print(f"1.1.{next_patch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
