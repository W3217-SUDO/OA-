"""Backfill historical seal applications that stored file names without file rows.

The migration is idempotent. It only copies a matching real attachment from the
application's related contract/case when the seal application has no application
file rows. Run without ``--apply`` for an audit-only report.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.main import UPLOAD_ROOT, _attachment_storage_path
from app.models import BusinessRecord, FileAttachment, WorkflowEvent


APPLICATION_CATEGORY = "用印文件"
COMPLETED_STATUSES = {"已用印", "已归档"}


def requested_names(record: BusinessRecord) -> list[str]:
    value = str((record.data or {}).get("document_names") or "")
    return list(dict.fromkeys(
        Path(item.strip()).name
        for item in re.split(r"[\n\r,;，；、|]+", value)
        if item.strip()
    ))


async def run(apply: bool) -> None:
    report = {"candidates": 0, "repaired_records": 0, "copied_files": 0, "missing_source": []}
    created_paths: list[Path] = []
    async with SessionLocal() as db:
        seals = list((await db.scalars(
            select(BusinessRecord)
            .where(BusinessRecord.module == "seal", ~BusinessRecord.status.in_(COMPLETED_STATUSES))
            .order_by(BusinessRecord.id)
        )).all())
        for seal in seals:
            names = requested_names(seal)
            if not names:
                continue
            existing = list((await db.scalars(select(FileAttachment).where(
                FileAttachment.record_id == seal.id,
                FileAttachment.category == APPLICATION_CATEGORY,
            ))).all())
            if existing:
                continue
            report["candidates"] += 1
            data = seal.data or {}
            module = "contract" if data.get("contract_no") else "case" if data.get("case_no") else ""
            serial_no = str(data.get("contract_no") or data.get("case_no") or "").strip()
            source_record = await db.scalar(select(BusinessRecord).where(
                BusinessRecord.module == module,
                BusinessRecord.serial_no == serial_no,
            )) if module and serial_no else None
            source_files = list((await db.scalars(select(FileAttachment).where(
                FileAttachment.record_id == source_record.id
            ).order_by(FileAttachment.created_at, FileAttachment.id))).all()) if source_record else []
            by_name: dict[str, list[FileAttachment]] = {}
            for source in source_files:
                by_name.setdefault(Path(source.original_name).name, []).append(source)
            matched = [by_name[name][0] for name in names if by_name.get(name)]
            if not matched and len(source_files) == 1 and len(names) == 1:
                matched = source_files
            if not matched:
                report["missing_source"].append({"seal_id": seal.id, "serial_no": seal.serial_no, "names": names})
                continue
            if not apply:
                report["repaired_records"] += 1
                report["copied_files"] += len(matched)
                continue
            try:
                for source in matched:
                    source_path = _attachment_storage_path(source)
                    if source_path is None:
                        raise FileNotFoundError(f"source file missing: {source.path}")
                    target = UPLOAD_ROOT / f"{uuid4().hex}{source_path.suffix.lower()}"
                    target.write_bytes(source_path.read_bytes())
                    created_paths.append(target)
                    db.add(FileAttachment(
                        record_id=seal.id,
                        category=APPLICATION_CATEGORY,
                        original_name=source.original_name,
                        stored_name=target.name,
                        content_type=source.content_type or "application/octet-stream",
                        size=target.stat().st_size,
                        path=str(target),
                        uploader=seal.owner or "legacy-file-backfill",
                        remark=f"backfilled from {source_record.serial_no}",
                        document_date=source.document_date,
                    ))
                db.add(WorkflowEvent(
                    record_id=seal.id,
                    action="补齐历史用印文件",
                    from_status=seal.status,
                    to_status=seal.status,
                    operator="legacy-file-backfill",
                    comment=f"从{source_record.serial_no}补齐真实文件：{'、'.join(item.original_name for item in matched)}",
                ))
                await db.flush()
                report["repaired_records"] += 1
                report["copied_files"] += len(matched)
            except Exception:
                await db.rollback()
                for path in created_paths:
                    path.unlink(missing_ok=True)
                raise
        if apply:
            await db.commit()
    print(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.apply))
