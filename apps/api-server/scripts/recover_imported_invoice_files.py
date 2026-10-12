"""核验原始附件实体并接入案件费用，默认只读预检。"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import mimetypes
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from dotenv import load_dotenv
import httpx
from sqlalchemy import select, text


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def _manifest(path: Path, source_dir: Path) -> list[dict]:
    from app.core.oss_attachments import oss_attachment_signed_url

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({row["key"] for row in rows}) != len(rows):
        raise RuntimeError("附件清单包含重复来源编号")
    local_rows = [row for row in rows if not row.get("object_key")]
    oss_rows = [row for row in rows if row.get("object_key")]
    for row in local_rows:
        local_name = row["local_name"]
        if Path(local_name).name != local_name:
            raise RuntimeError("附件清单包含非文件名路径")
        source = source_dir / local_name
        if not source.is_file() or source.stat().st_size != row["size"] or _digest(source) != row["sha256"]:
            raise RuntimeError(f"附件 {row['key']} 的实体文件或校验值不一致")
    semaphore = asyncio.Semaphore(8)
    async with httpx.AsyncClient(timeout=45, follow_redirects=False, trust_env=False) as client:
        async def verify_oss(row: dict) -> None:
            bucket = str(row.get("oss_bucket") or "")
            object_key = str(row["object_key"])
            if not bucket or not object_key or object_key.rsplit("/", 1)[-1] != row["filename"]:
                raise RuntimeError(f"附件 {row['key']} 的 OSS 对象身份不一致")
            location = f"oss://{bucket}/{object_key}"
            url = oss_attachment_signed_url(SimpleNamespace(path=location))
            async with semaphore:
                response = await client.get(url)
            if response.status_code != 200 or len(response.content) != row["size"] or \
                    hashlib.sha256(response.content).hexdigest() != row["sha256"]:
                raise RuntimeError(f"附件 {row['key']} 的 OSS 实体或校验值不一致")
        await asyncio.gather(*(verify_oss(row) for row in oss_rows))
    return rows


async def recover(*, manifest_path: Path, source_dir: Path, apply: bool) -> dict[str, int]:
    from app.areas.legal.case_fee_file_deletions import fee_file_was_deleted
    from app.core.constants import UPLOAD_ROOT
    from app.database import SessionLocal
    from app.models import BusinessRecord, FileAttachment, LegacyFinanceFile, LegacyFinanceRecord

    manifest = await _manifest(manifest_path, source_dir)
    keys = [row["key"] for row in manifest]
    async with SessionLocal() as db:
        ledger_rows = (await db.scalars(select(LegacyFinanceFile).where(
            LegacyFinanceFile.source_table == "FAM_Invoice_File",
            LegacyFinanceFile.legacy_key.in_(keys),
        ))).all()
        ledger_by_key = {row.legacy_key: row for row in ledger_rows}
        if len(ledger_rows) != len(keys) or len(ledger_by_key) != len(keys):
            raise RuntimeError("附件清单与来源文件账本未一一对应")

        fee_guids = {str(row.legacy_case_fee_id).strip().lower() for row in ledger_rows}
        raw_fees = (await db.execute(text(
            'SELECT "CaseFeeId", "CaseFeeGuid" FROM "FAM_AR_CaseFee"'
        ))).mappings().all()
        source_ids_by_guid: dict[str, list[str]] = defaultdict(list)
        for row in raw_fees:
            guid = str(row["CaseFeeGuid"] or "").strip().lower()
            if guid in fee_guids:
                source_ids_by_guid[guid].append(str(row["CaseFeeId"]))
        wanted_ids = {source_id for ids in source_ids_by_guid.values() for source_id in ids}
        modern_fees = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance",
            BusinessRecord.data["legacy_kind"].as_string() == "ar_case_fee",
            BusinessRecord.data["case_fee_id"].as_string().in_(wanted_ids),
        ))).all()
        fee_by_source = {str((row.data or {}).get("case_fee_id")): row for row in modern_fees}
        linked_invoice_ids = {row.legacy_finance_record_id for row in ledger_rows
                              if row.legacy_finance_record_id}
        invoice_sources = (await db.scalars(select(LegacyFinanceRecord).where(
            LegacyFinanceRecord.id.in_(linked_invoice_ids),
            LegacyFinanceRecord.record_kind == "invoice",
        ))).all()
        source_invoice_by_ledger = {row.id: row.legacy_id for row in invoice_sources}
        modern_invoices = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "invoice",
            BusinessRecord.data["invoice_id"].as_string().in_(source_invoice_by_ledger.values()),
        ))).all()
        invoice_by_source = {str((row.data or {}).get("invoice_id")): row.id
                             for row in modern_invoices}
        if len(source_invoice_by_ledger) != len(linked_invoice_ids) or \
                len(invoice_by_source) != len(set(source_invoice_by_ledger.values())):
            raise RuntimeError("附件关联的发票申请无法完整对应现行业务记录")
        existing = (await db.scalars(select(FileAttachment).where(
            FileAttachment.record_id.in_([row.id for row in modern_fees]),
            FileAttachment.category.in_(("案件票据文件", "案件发票文件")),
        ))).all()
        attachments_by_fee_name: dict[tuple[int, str], list[FileAttachment]] = defaultdict(list)
        for attachment in existing:
            attachments_by_fee_name[(attachment.record_id, attachment.original_name)].append(attachment)

        plans = []
        reused = 0
        deleted_links_skipped = 0
        for entry in manifest:
            ledger = ledger_by_key[entry["key"]]
            if not ledger.is_active or ledger.filename != entry["filename"] or ledger.size_bytes != entry["size"]:
                raise RuntimeError(f"来源附件 {entry['key']} 的状态、名称或大小不一致")
            guid = str(ledger.legacy_case_fee_id).strip().lower()
            source_ids = source_ids_by_guid.get(guid, [])
            if not source_ids or any(source_id not in fee_by_source for source_id in source_ids):
                raise RuntimeError(f"来源附件 {entry['key']} 的案件费用关联不完整")
            for source_id in source_ids:
                fee = fee_by_source[source_id]
                if fee_file_was_deleted(fee.data or {}, legacy_file_key=ledger.legacy_key):
                    deleted_links_skipped += 1
                    continue
                matches = attachments_by_fee_name[(fee.id, ledger.filename)]
                if entry.get("object_key"):
                    source_location = f"oss://{entry['oss_bucket']}/{entry['object_key']}"
                    verified = [row for row in matches if row.path == source_location
                                and row.size == entry["size"]]
                else:
                    verified = [row for row in matches if Path(row.path).is_file()
                                and row.size == entry["size"] and _digest(Path(row.path)) == entry["sha256"]]
                if verified:
                    reused += 1
                else:
                    plans.append((entry, ledger, fee))
        report = {"source_files": len(manifest),
                  "oss_objects": sum(bool(row.get("object_key")) for row in manifest),
                  "local_files": sum(not row.get("object_key") for row in manifest),
                  "existing_verified_links": reused,
                  "deleted_links_skipped": deleted_links_skipped,
                  "attachments_to_create": len(plans),
                  "ledger_files_to_verify": sum(not ledger_by_key[row["key"]].physical_file_verified
                                                for row in manifest)}
        if not apply:
            await db.rollback()
            return report

        created_paths = []
        try:
            for entry, ledger, fee in plans:
                stored_name = f"{uuid4().hex}{Path(ledger.filename).suffix.lower()}"
                if entry.get("object_key"):
                    attachment_path = f"oss://{entry['oss_bucket']}/{entry['object_key']}"
                else:
                    target = UPLOAD_ROOT / stored_name
                    shutil.copyfile(source_dir / entry["local_name"], target)
                    created_paths.append(target)
                    if target.stat().st_size != entry["size"] or _digest(target) != entry["sha256"]:
                        raise RuntimeError(f"附件 {entry['key']} 复制后校验失败")
                    attachment_path = str(target)
                db.add(FileAttachment(
                    record_id=fee.id,
                    invoice_record_id=(invoice_by_source[source_invoice_by_ledger[ledger.legacy_finance_record_id]]
                                       if ledger.legacy_finance_record_id else None),
                    category="案件发票文件", original_name=ledger.filename,
                    stored_name=stored_name,
                    content_type=mimetypes.guess_type(ledger.filename)[0] or "application/octet-stream",
                    size=entry["size"], path=attachment_path,
                    uploader=str((ledger.source_payload or {}).get("CreateUser") or "system")[:64],
                    remark=f"原始发票文件 {ledger.legacy_key}",
                    document_date=ledger.invoice_date.date() if ledger.invoice_date else None,
                ))
            for entry in manifest:
                ledger = ledger_by_key[entry["key"]]
                ledger.physical_file_verified = True
                ledger.source_payload = {**(ledger.source_payload or {}),
                                         "recovered_sha256": entry["sha256"],
                                         "recovery_provenance": entry.get("provenance") or "exact_legacy_path",
                                         "recovered_source_path": entry.get("source_path") or
                                         f"oss://{entry['oss_bucket']}/{entry['object_key']}"}
            await db.commit()
        except Exception:
            await db.rollback()
            for path in created_paths:
                path.unlink(missing_ok=True)
            raise
        return {**report, "created_attachments": len(plans)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=True)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    print(json.dumps(asyncio.run(recover(manifest_path=args.manifest, source_dir=args.source_dir,
                                         apply=args.apply)), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
