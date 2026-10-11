"""按费用、请款、明细、付款包的原始关系接入内部财务数据。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import insert, select, text


SOURCE = "hz_crm_20260930"
PARENT_STATUS = {"0": "草稿", "1": "待审批", "3": "已审批", "4": "已驳回", "5": "已作废"}
LINE_STATUS = {"1": "待审批", "2": "已审批", "3": "待核销", "4": "已付款", "5": "已作废"}
PACKAGE_STATUS = {"1": "待打包", "2": "待核销", "3": "已付款"}


def _number(value: object) -> float:
    return round(float(value or 0), 2)


def _date(value: object) -> date | None:
    raw = str(value or "").strip()
    return date.fromisoformat(raw[:10]) if raw else None


def _time(value: object) -> datetime | None:
    raw = str(value or "").strip()
    return datetime.fromisoformat(raw.replace("Z", "+00:00")) if raw else None


def _raw(row) -> dict:
    return {key: value.isoformat() if isinstance(value, (date, datetime)) else
            str(value) if isinstance(value, Decimal) else value
            for key, value in row.items()}


def _package_serial(row) -> str:
    return str(row["PackageNo"] or "").strip() or f"LIP-PKG-{row['PackingId']}"


async def _insert_batch(db, model, rows: list[dict]) -> dict[str, int]:
    created: dict[str, int] = {}
    for start in range(0, len(rows), 500):
        batch = rows[start:start + 500]
        result = await db.execute(insert(model).returning(model.id, model.serial_no), batch)
        created.update({serial: identifier for identifier, serial in result.all()})
    return created


async def promote(*, apply: bool) -> dict[str, int]:
    from app.database import SessionLocal
    from app.models import (BusinessRecord, FinanceTransaction, LegacyFinanceAllocation,
                            LegacyFinanceAudit, LegacyFinanceRecord, SystemParameter, WorkflowEvent)

    async with SessionLocal() as db:
        source_rows = (await db.scalars(select(LegacyFinanceRecord).where(
            LegacyFinanceRecord.record_kind.in_(("internal_fee", "internal_payment")),
        ).order_by(LegacyFinanceRecord.id))).all()
        fees = {row.legacy_id: row for row in source_rows if row.record_kind == "internal_fee"}
        requests = {row.legacy_id: row for row in source_rows if row.record_kind == "internal_payment"}
        lines = (await db.scalars(select(LegacyFinanceAllocation).where(
            LegacyFinanceAllocation.allocation_kind == "internal_payment",
        ).order_by(LegacyFinanceAllocation.id))).all()
        audits = (await db.scalars(select(LegacyFinanceAudit).where(
            LegacyFinanceAudit.audit_kind == "internal_payment",
        ))).all()
        packages = (await db.execute(text('SELECT * FROM "FAM_InternalFee_Payment_Packing" ORDER BY "PackingId"'))).mappings().all()
        package_numbers = Counter(str(row["PackageNo"] or "").strip() for row in packages)

        case_ids = {row.case_record_id for row in source_rows if row.case_record_id}
        case_ids.update(row.case_record_id for row in lines if row.case_record_id)
        cases = {row.id: row for row in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "case", BusinessRecord.id.in_(case_ids),
        ))).all()}
        fee_codes = {str((row.source_payload or {}).get("FeeTypeId") or "") for row in fees.values()}
        fee_types = {row.code: row for row in (await db.scalars(select(SystemParameter).where(
            SystemParameter.code.in_(fee_codes),
        ))).all()}
        source_fee_ids = {str((row.source_payload or {}).get("CaseFeeId") or "") for row in fees.values()}
        external_fees = {str((row.data or {}).get("case_fee_id")): row.id for row in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance",
            BusinessRecord.data["legacy_kind"].as_string() == "ar_case_fee",
            BusinessRecord.data["case_fee_id"].as_string().in_(source_fee_ids),
        ))).all()}

        fee_serials = {f"LIF-{row.legacy_id}" for row in fees.values()}
        request_serials = {f"LIP-{row.legacy_id}" for row in requests.values()}
        line_serials = {f"LIP-L-{row.legacy_key}" for row in lines}
        package_serials = {_package_serial(row) for row in packages}
        serials = fee_serials | request_serials | line_serials | package_serials
        existing = {}
        ordered_serials = sorted(serials)
        for start in range(0, len(ordered_serials), 5000):
            batch = ordered_serials[start:start + 5000]
            existing.update({row.serial_no: row for row in (await db.scalars(
                select(BusinessRecord).where(BusinessRecord.serial_no.in_(batch))
            )).all()})

        lines_by_fee = defaultdict(list)
        lines_by_request = defaultdict(list)
        lines_by_package = defaultdict(list)
        for row in lines:
            payload = row.source_payload or {}
            lines_by_fee[str(payload.get("InternalFeeId") or "")].append(row)
            lines_by_request[str(payload.get("PaymentId") or "")].append(row)
            package_no = str(payload.get("PackageNo") or "").strip()
            if package_no:
                lines_by_package[package_no].append(row)

        errors = []
        if len(fees) + len(requests) != len(source_rows) or len(line_serials) != len(lines) or len(package_serials) != len(packages):
            errors.append("来源编号不唯一")
        for row in existing.values():
            data = row.data or {}
            if row.serial_no in package_serials:
                valid = row.module == "finance_package" and data.get("legacy_kind") == "internal_packing"
                valid = valid and str(data.get("legacy_packing_id")) == str(next(
                    source["PackingId"] for source in packages if _package_serial(source) == row.serial_no
                ))
            elif row.serial_no.startswith("LIF-"):
                valid = row.module == "finance" and data.get("legacy_kind") == "internal_fee_source"
            elif row.serial_no.startswith("LIP-L-"):
                valid = row.module == "finance" and data.get("legacy_kind") == "internal_payment_line"
            else:
                valid = row.module == "finance_application" and data.get("legacy_kind") == "internal_payment"
            if not valid:
                errors.append(f"业务编号 {row.serial_no} 已被其他记录占用")
        for fee in fees.values():
            payload = fee.source_payload or {}
            code = str(payload.get("FeeTypeId") or "")
            if fee.case_record_id not in cases or code not in fee_types:
                errors.append(f"内部费用 {fee.legacy_id} 缺少案件或费用类别")
            external_id = str(payload.get("CaseFeeId") or "")
            if external_id and external_id not in external_fees:
                errors.append(f"内部费用 {fee.legacy_id} 的案件费用关联缺失")
        for request in requests.values():
            if request.case_record_id not in cases or str(request.status_code) not in PARENT_STATUS:
                errors.append(f"内部请款 {request.legacy_id} 缺少案件或状态")
        for row in lines:
            code = str((row.source_payload or {}).get("PaymentStatus") or "").strip()
            if code and code not in LINE_STATUS:
                errors.append(f"请款明细 {row.legacy_key} 状态未映射")
            if row.case_record_id not in cases:
                errors.append(f"请款明细 {row.legacy_key} 缺少案件")
            if row.is_active and code == "4" and not _date((row.source_payload or {}).get("PaymentDate")):
                errors.append(f"已付请款明细 {row.legacy_key} 缺少付款日期")
        for number, count in package_numbers.items():
            if number and count > 1 and lines_by_package.get(number):
                errors.append(f"付款包号 {number} 对应多个原始包，明细归属不明确")
        for serial in serials:
            if len(serial) > 64:
                errors.append(f"业务编号 {serial} 超过数据库长度")
        for package in packages:
            json.dumps(_raw(package))
        if errors:
            raise RuntimeError("内部财务接入预检失败：" + "；".join(errors[:20]))

        report = {
            "source_fees": len(fees), "source_requests": len(requests),
            "source_lines": len(lines), "source_packages": len(packages), "source_audits": len(audits),
            "already_promoted": len(existing), "to_promote": len(serials) - len(existing),
            "orphan_fee_lines": sum(1 for row in lines if str((row.source_payload or {}).get("InternalFeeId") or "") not in fees),
            "orphan_request_lines": sum(1 for row in lines if str((row.source_payload or {}).get("PaymentId") or "") not in requests),
            "packages_without_lines": sum(1 for row in packages if not lines_by_package.get(str(row["PackageNo"] or "").strip())),
            "duplicate_package_numbers": sum(1 for number, count in package_numbers.items() if number and count > 1),
        }
        if not apply:
            await db.rollback()
            return report

        base_records = []
        for source in fees.values():
            serial = f"LIF-{source.legacy_id}"
            if serial in existing:
                continue
            payload = source.source_payload or {}
            linked_case = cases[source.case_record_id]
            fee_type = fee_types[str(payload["FeeTypeId"])]
            related_lines = [row for row in lines_by_fee[source.legacy_id] if row.is_active]
            base_records.append({
                "module": "finance", "serial_no": serial,
                "title": f"{source.legacy_case_no} {fee_type.name}",
                "customer": linked_case.customer, "status": "已记录" if source.is_active else "已删除",
                "owner": str(payload.get("RequestUser") or payload.get("CreateUser") or "").strip(),
                "department": linked_case.department, "description": str(payload.get("Remark") or ""),
                "created_at": _time(payload.get("CreateTime")) or source.imported_at,
                "updated_at": _time(payload.get("ChangeTime")) or source.updated_at,
                "data": {
                    "legacy_kind": "internal_fee_source", "legacy_source": SOURCE,
                    "legacy_internal_fee_id": source.legacy_id, "legacy_record": payload,
                    "fee_type": "内部费用", "fee_type_name": fee_type.name,
                    "internal_fee_type": fee_type.name, "fee_type_id": payload.get("FeeTypeId"),
                    "expense_scope": "内部", "amount": _number(source.primary_amount),
                    "source_reported_paid_amount": _number(payload.get("PaidAmount")),
                    "paid_amount": round(sum(_number(row.amount) for row in related_lines
                                             if str((row.source_payload or {}).get("PaymentStatus") or "") == "4"), 2),
                    "payee": payload.get("PaymentObject") or "",
                    "case_id": linked_case.id, "case_no": source.legacy_case_no,
                    "case_record_id": linked_case.id,
                    "source_fee_id": external_fees.get(str(payload.get("CaseFeeId") or "")),
                    "source_fee_legacy_id": payload.get("CaseFeeId") or "",
                    "relation_status": "已关联" if related_lines else "尚无请款明细",
                },
            })
        new_base = await _insert_batch(db, BusinessRecord, base_records)
        base_ids = {**{serial: row.id for serial, row in existing.items() if serial in fee_serials}, **new_base}

        request_records = []
        for source in requests.values():
            serial = f"LIP-{source.legacy_id}"
            if serial in existing:
                continue
            payload = source.source_payload or {}
            linked_case = cases[source.case_record_id]
            status = PARENT_STATUS[str(source.status_code)] if source.is_active else "已删除"
            request_records.append({
                "module": "finance_application", "serial_no": serial,
                "title": f"内部请款 {payload.get('ApplicationNo') or source.legacy_id}",
                "customer": linked_case.customer, "status": status,
                "owner": str(payload.get("Applicant") or payload.get("CreateUser") or "").strip(),
                "department": linked_case.department, "description": str(payload.get("Remark") or ""),
                "created_at": _time(payload.get("ApplicationDate")) or source.imported_at,
                "updated_at": _time(payload.get("ChangeTime")) or source.updated_at,
                "data": {
                    "legacy_kind": "internal_payment", "legacy_source": SOURCE,
                    "legacy_internal_payment_id": source.legacy_id, "legacy_record": payload,
                    "application_no": payload.get("ApplicationNo") or "",
                    "application_date": payload.get("ApplicationDate") or "",
                    "amount": _number(source.primary_amount),
                    "case_id": linked_case.id, "case_no": source.legacy_case_no,
                    "case_record_id": linked_case.id,
                    "relation_status": "已关联" if lines_by_request[source.legacy_id] else "缺少请款明细",
                },
            })
        new_requests = await _insert_batch(db, BusinessRecord, request_records)
        request_ids = {**{serial: row.id for serial, row in existing.items() if serial in request_serials}, **new_requests}

        line_records = []
        paid_transactions = []
        for source in lines:
            serial = f"LIP-L-{source.legacy_key}"
            if serial in existing:
                continue
            payload = source.source_payload or {}
            fee_id = str(payload.get("InternalFeeId") or "")
            parent_id = str(payload.get("PaymentId") or "")
            fee = fees.get(fee_id)
            parent = requests.get(parent_id)
            linked_case = cases[source.case_record_id]
            fee_payload = fee.source_payload or {} if fee else {}
            parent_payload = parent.source_payload or {} if parent else {}
            fee_type = fee_types.get(str(fee_payload.get("FeeTypeId") or ""))
            code = str(payload.get("PaymentStatus") or "").strip()
            parent_status = str(parent.status_code or "") if parent else ""
            status = ("已删除" if not source.is_active else LINE_STATUS.get(code)
                      or PARENT_STATUS.get(parent_status, "待核对关联"))
            if not fee or not parent:
                status = "待核对关联" if source.is_active else "已删除"
            type_name = fee_type.name if fee_type else ""
            amount = _number(source.amount)
            line_records.append({
                "module": "finance", "serial_no": serial,
                "title": f"{source.legacy_case_no} {type_name or '内部请款'}",
                "customer": linked_case.customer, "status": status,
                "owner": str(parent_payload.get("Applicant") or payload.get("CreateUser") or "").strip(),
                "department": linked_case.department, "description": str(payload.get("Remark") or ""),
                "created_at": _time(payload.get("CreateTime")) or source.imported_at,
                "updated_at": _time(payload.get("ChangeTime")) or source.updated_at,
                "data": {
                    "legacy_kind": "internal_payment_line", "legacy_source": SOURCE,
                    "legacy_line_key": source.legacy_key, "legacy_record": payload,
                    "legacy_internal_payment_id": parent_id,
                    "legacy_internal_fee_id": fee_id,
                    "internal_application_id": request_ids.get(f"LIP-{parent_id}"),
                    "internal_fee_record_id": base_ids.get(f"LIF-{fee_id}"),
                    "payment_application_no": parent_payload.get("ApplicationNo") or "",
                    "application_date": parent_payload.get("ApplicationDate") or "",
                    "applicant": parent_payload.get("Applicant") or "",
                    "fee_type": "内部费用", "fee_type_name": type_name,
                    "internal_fee_type": type_name, "expense_scope": "内部",
                    "commission_type": type_name if "提成" in type_name else "",
                    "is_refund": "退费" in type_name,
                    "amount": amount, "paid_amount": amount if code == "4" else 0,
                    "payee": fee_payload.get("PaymentObject") or "",
                    "payment_status": status,
                    "payment_date": payload.get("PaymentDate") or "",
                    "payment_package_no": payload.get("PackageNo") or "",
                    "writeoff_status": "已核销" if code == "4" else "待核销" if code == "3" else "",
                    "case_id": linked_case.id, "case_no": source.legacy_case_no,
                    "case_record_id": linked_case.id,
                    "source_fee_id": external_fees.get(str(fee_payload.get("CaseFeeId") or "")),
                    "relation_status": "已关联" if fee and parent else "来源费用或请款单缺失",
                },
            })
            if source.is_active and code == "4":
                paid_date = _date(payload.get("PaymentDate"))
                if not paid_date:
                    raise RuntimeError(f"已付请款明细 {source.legacy_key} 缺少付款日期")
                paid_transactions.append((serial, base_ids.get(f"LIF-{fee_id}"), amount,
                                          paid_date, parent_payload.get("Applicant") or "", payload.get("PackageNo") or ""))
        new_lines = await _insert_batch(db, BusinessRecord, line_records)
        line_ids = {**{serial: row.id for serial, row in existing.items() if serial in line_serials}, **new_lines}

        package_records = []
        for source in packages:
            serial = _package_serial(source)
            if serial in existing:
                continue
            number = str(source["PackageNo"] or "").strip()
            members = lines_by_package.get(number, []) if number else []
            member_ids = [line_ids[f"LIP-L-{row.legacy_key}"] for row in members]
            status = PACKAGE_STATUS.get(str(source["PackingStatus"] or ""), "待核对关联")
            if source["IsActived"] != "T":
                status = "已删除"
            if not members and status != "已付款":
                status = "已删除" if status == "已删除" else "待核对关联"
            package_records.append({
                "module": "finance_package", "serial_no": serial,
                "title": f"内部付款包 {number or source['PackingId']}",
                "customer": cases[members[0].case_record_id].customer if members else "",
                "status": status, "owner": str(source["CreateUser"] or "").strip(),
                "department": cases[members[0].case_record_id].department if members else "",
                "description": str(source["Remark"] or ""),
                "created_at": source["CreateTime"] or datetime.now(),
                "updated_at": source["ChangeTime"] or source["CreateTime"] or datetime.now(),
                "data": {
                    "legacy_kind": "internal_packing", "legacy_source": SOURCE,
                    "legacy_packing_id": source["PackingId"], "legacy_record": _raw(source),
                    "payment_package_no": number, "fee_type": "内部费用付款包",
                    "fee_ids": member_ids,
                    "items": [{"fee_id": line_ids[f"LIP-L-{row.legacy_key}"],
                               "request_no": f"LIP-L-{row.legacy_key}", "amount": _number(row.amount)} for row in members],
                    "amount": round(sum(_number(row.amount) for row in members), 2) if members else None,
                    "total_amount": round(sum(_number(row.amount) for row in members), 2) if members else None,
                    "payment_status": status,
                    "payment_date": str(_date(source["PaidDate"]) or ""),
                    "invoice_no": source["InvoiceNo"] or "",
                    "writeoff_status": "已核销" if status == "已付款" else "待核销" if status == "待核销" else "",
                    "relation_status": "已关联" if members else "缺少请款明细",
                },
            })
        new_packages = await _insert_batch(db, BusinessRecord, package_records)
        package_ids = {**{serial: row.id for serial, row in existing.items() if serial in package_serials},
                       **new_packages}
        linked_lines = [row for row in lines if str((row.source_payload or {}).get("PackageNo") or "").strip()
                        in package_ids]
        for start in range(0, len(linked_lines), 500):
            batch = linked_lines[start:start + 500]
            records = (await db.scalars(select(BusinessRecord).where(
                BusinessRecord.serial_no.in_([f"LIP-L-{row.legacy_key}" for row in batch]),
            ))).all()
            source_by_serial = {f"LIP-L-{row.legacy_key}": row for row in batch}
            for record in records:
                source = source_by_serial[record.serial_no]
                package_no = str((source.source_payload or {}).get("PackageNo") or "").strip()
                package_id = package_ids[package_no]
                if (record.data or {}).get("payment_package_id") != package_id:
                    record.data = {**(record.data or {}), "payment_package_id": package_id,
                                   "payment_package_no": package_no}

        transactions = []
        for line_serial, base_id, amount, paid_date, operator, package_no in paid_transactions:
            transactions.append({
                "finance_record_id": base_id or line_ids[line_serial],
                "transaction_type": "付款", "amount": amount,
                "transaction_date": paid_date, "voucher_no": str(package_no)[:64],
                "counterparty": "", "operator": str(operator or "system")[:64],
                "remark": f"内部请款明细 {line_serial}",
            })
        for start in range(0, len(transactions), 500):
            await db.execute(insert(FinanceTransaction), transactions[start:start + 500])

        events = []
        for source in audits:
            parent = requests.get(str(source.parent_legacy_id or ""))
            if not parent or f"LIP-{parent.legacy_id}" not in new_requests:
                continue
            events.append({
                "record_id": request_ids[f"LIP-{parent.legacy_id}"],
                "action": "原内部请款审批记录", "from_status": "",
                "to_status": PARENT_STATUS.get(str(source.audit_status_code or ""), ""),
                "operator": source.auditor or "system", "comment": source.audit_content or "",
                "created_at": source.audit_date or source.imported_at,
            })
        for start in range(0, len(events), 500):
            await db.execute(insert(WorkflowEvent), events[start:start + 500])

        await db.commit()
        return {**report, "promoted": len(base_records) + len(request_records) + len(line_records) + len(package_records),
                "transactions": len(transactions), "workflow_events": len(events),
                "packages_promoted": len(new_packages)}


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
