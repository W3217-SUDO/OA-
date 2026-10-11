"""按原始案件费用 GUID 修复发票文件关联，默认只读预检。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select, text


def _key(value: object) -> str:
    return str(value or "").strip().lower()


async def link_files(*, apply: bool) -> dict[str, int]:
    from app.database import SessionLocal
    from app.models import BusinessRecord, FileAttachment, LegacyFinanceFile, LegacyFinanceRecord

    async with SessionLocal() as db:
        raw_files = (await db.execute(text(
            'SELECT "InvoiceId", "CaseFeeId", "InvoiceNo", "InvoiceFileName" FROM "FAM_Invoice_File"'
        ))).mappings().all()
        raw_fees = (await db.execute(text(
            'SELECT "CaseFeeId", "CaseFeeGuid" FROM "FAM_AR_CaseFee"'
        ))).mappings().all()
        raw_objects = (await db.execute(text(
            'SELECT "InvoiceId", "CaseFeeId" FROM "FAM_Invoice_Object"'
        ))).mappings().all()
        raw_invoices = (await db.execute(text(
            'SELECT "InvoiceId", "InvoiceNo" FROM "FAM_Invoice"'
        ))).mappings().all()
        ledger_files = (await db.scalars(select(LegacyFinanceFile).where(
            LegacyFinanceFile.source_table == "FAM_Invoice_File",
        ))).all()
        ledger_invoices = (await db.scalars(select(LegacyFinanceRecord).where(
            LegacyFinanceRecord.record_kind == "invoice",
            LegacyFinanceRecord.source_table == "FAM_Invoice",
        ))).all()
        modern_fees = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance",
            BusinessRecord.data["legacy_kind"].as_string() == "ar_case_fee",
        ))).all()
        modern_invoices = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "invoice",
        ))).all()
        attachments = (await db.scalars(select(FileAttachment).where(
            FileAttachment.category.in_(("案件票据文件", "案件发票文件")),
        ))).all()

        fee_sources_by_guid: dict[str, list[str]] = defaultdict(list)
        for row in raw_fees:
            fee_sources_by_guid[_key(row["CaseFeeGuid"])].append(str(row["CaseFeeId"]))
        fee_by_source = {str((row.data or {}).get("case_fee_id")): row for row in modern_fees}
        invoice_by_source = {str((row.data or {}).get("invoice_id")): row for row in modern_invoices}
        ledger_invoice_by_source = {row.legacy_id: row for row in ledger_invoices}
        ledger_file_by_source = {str((row.source_payload or {}).get("InvoiceId")): row for row in ledger_files}
        invoice_numbers = {str(row["InvoiceId"]): _key(row["InvoiceNo"]) for row in raw_invoices}
        applications_by_fee: dict[str, set[str]] = defaultdict(set)
        for row in raw_objects:
            applications_by_fee[str(row["CaseFeeId"])].add(str(row["InvoiceId"]))
        attachments_by_fee_name: dict[tuple[int, str], list[FileAttachment]] = defaultdict(list)
        for row in attachments:
            if row.record_id:
                attachments_by_fee_name[(row.record_id, row.original_name)].append(row)

        if len(raw_files) != len(ledger_file_by_source):
            raise RuntimeError("原始发票文件与导入账本的数量或编号不一致")
        if len(raw_invoices) != len(ledger_invoice_by_source) or len(raw_invoices) != len(invoice_by_source):
            raise RuntimeError("发票申请的原始记录、账本和业务记录未一一对应")

        application_links = 0
        attachment_links = 0
        file_updates = []
        attachment_updates: dict[int, tuple[FileAttachment, int]] = {}
        for source in raw_files:
            source_id = str(source["InvoiceId"])
            ledger = ledger_file_by_source[source_id]
            fee_source_ids = fee_sources_by_guid.get(_key(source["CaseFeeId"]), [])
            fees = [fee_by_source.get(fee_source_id) for fee_source_id in fee_source_ids]
            if not fee_source_ids or any(fee is None for fee in fees):
                raise RuntimeError(f"发票文件 {source_id} 的案件费用 GUID 无法完整映射")
            number = _key(source["InvoiceNo"])
            application_ids = set().union(*(applications_by_fee.get(fee_source_id, set())
                                            for fee_source_id in fee_source_ids))
            matches = [invoice_id for invoice_id in application_ids
                       if number and invoice_numbers.get(invoice_id) == number]
            invoice = invoice_by_source[matches[0]] if len(matches) == 1 else None
            ledger_invoice = ledger_invoice_by_source[matches[0]] if invoice else None
            if invoice:
                application_links += 1
            for fee in fees:
                linked = attachments_by_fee_name.get((fee.id, str(source["InvoiceFileName"] or "")), [])
                attachment = linked[0] if len(linked) == 1 else None
                if attachment and invoice:
                    if attachment.invoice_record_id not in (None, invoice.id):
                        raise RuntimeError(f"发票文件 {source_id} 的附件指向另一张发票")
                    previous = attachment_updates.get(attachment.id)
                    if previous and previous[1] != invoice.id:
                        raise RuntimeError(f"附件 {attachment.id} 被不同发票争用")
                    attachment_updates[attachment.id] = (attachment, invoice.id)
                    attachment_links += 1
            reason = "invoice_application_ambiguous" if len(matches) > 1 else ""
            file_updates.append((ledger, fee_source_ids, [fee.id for fee in fees],
                                 ledger_invoice.id if ledger_invoice else None,
                                 ledger_invoice.legacy_id if ledger_invoice else "", reason))

        report = {
            "source_files": len(raw_files),
            "case_fee_links": sum(len(item[1]) for item in file_updates),
            "multi_fee_files": sum(len(item[1]) > 1 for item in file_updates),
            "application_links": application_links,
            "attachment_links": attachment_links,
            "verified_physical_files": sum(bool(row.physical_file_verified) for row in ledger_files),
            "unmatched_applications": len(raw_files) - application_links,
        }
        if not apply:
            await db.rollback()
            return report
        for ledger, fee_source_ids, fee_record_ids, application_id, application_no, reason in file_updates:
            ledger.source_payload = {**(ledger.source_payload or {}),
                                     "linked_case_fee_ids": fee_source_ids,
                                     "linked_finance_record_ids": fee_record_ids}
            ledger.legacy_finance_record_id = application_id
            ledger.parent_legacy_id = application_no
            ledger.orphan_reason = reason
        for attachment, application_id in attachment_updates.values():
            attachment.invoice_record_id = application_id
        await db.commit()
        return {**report, "updated_file_links": len(file_updates),
                "updated_attachment_links": len(attachment_updates)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, help="数据库环境变量文件")
    parser.add_argument("--apply", action="store_true", help="完成预检后提交数据")
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=True)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    print(json.dumps(asyncio.run(link_files(apply=args.apply)), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
