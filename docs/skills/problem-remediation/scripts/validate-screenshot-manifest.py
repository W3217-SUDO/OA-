#!/usr/bin/env python3
"""Validate the screenshot manifest before an OA batch enters implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path


REQUIRED = {
    "image_id",
    "sheet_id",
    "sheet_name",
    "row",
    "col",
    "header",
    "filename",
    "sha256",
    "evidence_type",
    "mapping_status",
}
ALLOWED_EVIDENCE = {"new", "old", "rework", "unknown"}


def verify_file(item: dict, base: Path, errors: list[str], label: str) -> Path | None:
    filename = item.get("filename")
    if not isinstance(filename, str) or not filename.strip():
        errors.append(f"{label}: filename is required")
        return None
    path = Path(filename)
    if not path.is_absolute():
        path = base / path
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        errors.append(f"{label}: cannot read file: {exc}")
        return None
    if digest != str(item.get("sha256", "")).lower():
        errors.append(f"{label}: SHA256 mismatch")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--require-old-new", action="store_true")
    parser.add_argument("--require-rework", action="store_true")
    parser.add_argument("--source-evidence", type=Path,
                        help="Explicit reviewed source evidence for missing old/new screenshots")
    args = parser.parse_args()

    payload = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    images = payload.get("images", payload) if isinstance(payload, dict) else payload
    if not isinstance(images, list) or not images:
        raise ValueError("manifest must be a non-empty list or an object with an images list")

    errors: list[str] = []
    ids: set[str] = set()
    hashes: dict[str, set[tuple[str, int]]] = defaultdict(set)
    by_row: dict[tuple[str, int], set[str]] = defaultdict(set)
    occurrences: set[tuple[str, int, str, str]] = set()
    for index, item in enumerate(images, start=1):
        if not isinstance(item, dict):
            errors.append(f"images[{index}] is not an object")
            continue
        missing = REQUIRED - item.keys()
        if missing:
            errors.append(f"images[{index}] missing: {', '.join(sorted(missing))}")
        image_id = str(item.get("image_id", ""))
        if not image_id.strip():
            errors.append(f"images[{index}]: image_id is required")
        if image_id in ids:
            errors.append(f"duplicate image_id: {image_id}")
        ids.add(image_id)
        status = str(item.get("mapping_status", ""))
        if status != "confirmed":
            errors.append(f"{image_id or index}: mapping_status must be confirmed")
        evidence = str(item.get("evidence_type", ""))
        if evidence not in ALLOWED_EVIDENCE:
            errors.append(f"{image_id or index}: invalid evidence_type {evidence!r}")
        if evidence == "unknown":
            errors.append(f"{image_id or index}: evidence_type cannot be unknown")
        try:
            row = int(item["row"])
            if row < 1 or isinstance(item["row"], bool):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            errors.append(f"{image_id or index}: row must be an integer")
            continue
        col = str(item.get("col", ""))
        sheet_id = str(item.get("sheet_id", "")).strip()
        if not sheet_id or not str(item.get("sheet_name", "")).strip() or not col.strip():
            errors.append(f"{image_id}: sheet identity and column are required")
        if not str(item.get("visual_identity", "")).strip():
            errors.append(f"{image_id}: visual_identity is required")
        verify_file(item, args.manifest.parent, errors, image_id)
        # A cell may contain several independent images. Detect duplicate image
        # content within that cell, not duplicate cell coordinates.
        digest = str(item.get("sha256", "")).lower()
        occurrence = (sheet_id, row, col, digest)
        if occurrence in occurrences:
            errors.append(f"{image_id}: duplicate image in the same cell")
        occurrences.add(occurrence)
        row_key = (sheet_id, row)
        if digest:
            hashes[digest].add(row_key)
        by_row[row_key].add(evidence)

    supplements: dict[tuple[str, int], set[str]] = defaultdict(set)
    if args.source_evidence:
        sources = json.loads(args.source_evidence.read_text(encoding="utf-8-sig"))
        if not isinstance(sources, list):
            raise ValueError("source evidence must be a list")
        for index, item in enumerate(sources, 1):
            label = f"source[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{label}: must be an object")
                continue
            before = len(errors)
            try:
                key = (str(item["sheet_id"]), int(item["row"]))
            except (KeyError, TypeError, ValueError):
                errors.append(f"{label}: sheet_id and row are required")
                continue
            if key not in by_row:
                errors.append(f"{label}: no matching screenshot row")
            role = item.get("evidence_type")
            if role not in {"old", "new"}:
                errors.append(f"{label}: only old/new source evidence is supported")
            for field in ("missing_screenshot_reason", "entry", "finding", "reviewed_by", "reviewed_at"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    errors.append(f"{label}: {field} is required")
            if item.get("mapping_status") != "confirmed":
                errors.append(f"{label}: mapping_status must be confirmed")
            path = verify_file(item, args.source_evidence.parent, errors, label)
            try:
                start, end = item["line_start"], item["line_end"]
                if type(start) is not int or type(end) is not int or not 1 <= start <= end:
                    raise ValueError()
                if path and end > len(path.read_text(encoding="utf-8-sig").splitlines()):
                    raise ValueError()
            except (KeyError, TypeError, ValueError, OSError):
                errors.append(f"{label}: invalid source line range")
            if len(errors) == before:
                supplements[key].add(role)

    for digest, rows in hashes.items():
        if len(rows) > 1:
            errors.append(f"same image sha256 assigned to multiple rows: {digest}")
    for row, evidence in sorted(by_row.items()):
        if args.require_old_new and not {"old", "new"}.issubset(evidence | supplements[row]):
            errors.append(f"row {row}: requires both old and new evidence")
        if args.require_rework and "rework" not in evidence:
            errors.append(f"row {row}: requires rework evidence")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"screenshot manifest valid: {len(images)} images, {len(by_row)} rows; "
          f"{sum(len(v) for v in supplements.values())} reviewed source supplements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
