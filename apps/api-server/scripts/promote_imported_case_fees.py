"""将已导入且缺少现行业务记录的案件费用补齐；默认只读预检。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select


def _time(value: object) -> datetime | None:
    raw = str(value or "").strip()
    return datetime.fromisoformat(raw.replace("Z", "+00:00")) if raw else None


async def promote(*, apply: bool) -> dict[str, int]:
    from app.database import SessionLocal
    from app.models import BusinessRecord, LegacyFinanceRecord, SystemParameter

    async with SessionLocal() as db:
        sources = (await db.scalars(select(LegacyFinanceRecord).where(
            LegacyFinanceRecord.record_kind == "case_fee",
            LegacyFinanceRecord.source_table == "FAM_AR_CaseFee",
        ).order_by(LegacyFinanceRecord.id))).all()
        existing_rows = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance",
            BusinessRecord.data["legacy_kind"].as_string() == "ar_case_fee",
        ))).all()
        existing = {str((row.data or {}).get("case_fee_id")): row for row in existing_rows}
        missing = [source for source in sources if source.legacy_id not in existing]
        serials = {f"HZ-FEE-{source.legacy_id}" for source in missing}
        collisions = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.serial_no.in_(serials),
        ))).all()
        relations = {row.id: row for row in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.id.in_({identifier for source in missing for identifier in (
                source.case_record_id, source.contract_record_id, source.customer_record_id,
            ) if identifier}),
        ))).all()}
        type_codes = {str((source.source_payload or {}).get("CaseFeeTypeId")) for source in missing}
        fee_types = {row.code: row for row in (await db.scalars(select(SystemParameter).where(
            SystemParameter.category == "fee_type", SystemParameter.code.in_(type_codes),
        ))).all()}

        errors = []
        if len(sources) != len(existing) + len(missing):
            errors.append("现有案件费用来源编号重复或目标数量不一致")
        for row in collisions:
            errors.append(f"业务编号 {row.serial_no} 已被占用")
        for source in missing:
            payload = source.source_payload or {}
            case = relations.get(source.case_record_id)
            contract = relations.get(source.contract_record_id)
            customer = relations.get(source.customer_record_id)
            fee_type = fee_types.get(str(payload.get("CaseFeeTypeId")))
            if not source.is_active:
                errors.append(f"费用 {source.legacy_id} 已失效，不能作为现行业务费用补入")
            if not case or case.module != "case" or not contract or contract.module != "contract" or not customer or customer.module != "customer":
                errors.append(f"费用 {source.legacy_id} 的案件、合同或客户关联不完整")
            if not fee_type or str(payload.get("CaseFeeStatus")) != "1" or str(payload.get("CompanyId")) != "1":
                errors.append(f"费用 {source.legacy_id} 的费用类别或源状态尚未完成映射")
        if errors:
            raise RuntimeError("案件费用补入预检失败：" + "；".join(errors[:20]))

        report = {"source_records": len(sources), "already_promoted": len(existing), "to_promote": len(missing)}
        if not apply:
            await db.rollback()
            return report

        for source in missing:
            payload = source.source_payload or {}
            case = relations[source.case_record_id]
            contract = relations[source.contract_record_id]
            customer = relations[source.customer_record_id]
            fee_type = fee_types[str(payload["CaseFeeTypeId"])]
            detail = fee_type.extra or {}
            case_number = source.legacy_case_no
            record = BusinessRecord(
                module="finance",
                serial_no=f"HZ-FEE-{source.legacy_id}",
                title=f"{case_number} {fee_type.name}",
                customer=customer.title,
                status="已通知",
                owner=str(payload.get("RequestUser") or payload.get("CreateUser") or "").strip(),
                department=case.department,
                description=str(payload.get("Remark") or ""),
                data={
                    "legacy_kind": "ar_case_fee",
                    "legacy_source": "hz_crm_20260930",
                    "migration_source": "hz_crm_20260930",
                    "source_table": source.source_table,
                    "case_fee_id": int(source.legacy_id),
                    "legacy_case_fee_id": int(source.legacy_id),
                    "legacy_status_code": "1",
                    "source_active": True,
                    "legacy_record": payload,
                    "amount": float(payload["Amount"]) if payload.get("Amount") is not None else None,
                    "paid_amount": float(payload["PaidAmount"] or 0),
                    "cashed_amount": float(payload["CashedAmount"] or 0),
                    "invoiced_amount": float(payload["InvoicedAmount"] or 0),
                    "refunded_amount": float(payload["RefundedAmount"] or 0),
                    "fee_type": detail.get("base_fee_type") or fee_type.name,
                    "expense_subtype": fee_type.name,
                    "fee_type_code": fee_type.code,
                    "case_fee_type_id": payload.get("CaseFeeTypeId"),
                    "expense_scope": "律所",
                    "case_id": case.id,
                    "case_record_id": case.id,
                    "case_no": case_number,
                    "contract_id": contract.id,
                    "contract_record_id": contract.id,
                    "contract_no": source.legacy_contract_no,
                    "customer_id": customer.id,
                    "customer_record_id": customer.id,
                    "customer_no": source.legacy_customer_no,
                    "case_title": case.title,
                    "contract_title": contract.title,
                    "customer_title": customer.title,
                    "request_user": payload.get("RequestUser"),
                    "remark": payload.get("Remark"),
                },
                created_at=_time(payload.get("CreateTime")) or source.imported_at,
                updated_at=_time(payload.get("ChangeTime")) or source.updated_at,
            )
            db.add(record)
        await db.commit()
        return {**report, "promoted": len(missing)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, help="数据库环境变量文件")
    parser.add_argument("--apply", action="store_true", help="完成只读预检后提交数据")
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=True)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    print(json.dumps(asyncio.run(promote(apply=args.apply)), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
