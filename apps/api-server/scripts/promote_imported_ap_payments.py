"""将已导入的原付款申请接入现行付款流程。默认只读预检。"""

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
from sqlalchemy import select, text as sql_text


STATUS_BY_SOURCE = {
    "0": "草稿",
    "1": "待审批",
    "2": "待审批",
    "3": "已审批",
    "4": "已驳回",
    "5": "已作废",
    "6": "待核销",
    "7": "已付款",
}
ACTIONABLE_STATUSES = {"1", "2", "3", "6"}


def _date(value: object) -> date | None:
    text = str(value or "").strip()
    return date.fromisoformat(text[:10]) if text else None


def _datetime(value: object) -> datetime | None:
    text = str(value or "").strip()
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def _money(value: object) -> float:
    return round(float(value or 0), 2)


def _serial(source, number_counts: Counter[str]) -> str:
    number = str((source.source_payload or {}).get("ApplicationNo") or "").strip()
    if not number:
        return f"LAP-{source.legacy_id}"
    return number if number_counts[number] == 1 else f"{number}-{source.legacy_id}"


def _package_serial(row, number_counts: Counter[str], payment_serials: set[str]) -> str:
    number = str(row["PackageNo"] or "").strip()
    if number and len(number) <= 64 and number_counts[number] == 1 and number not in payment_serials:
        return number
    return f"LAP-PKG-{row['PackingId']}"


async def promote(*, apply: bool) -> dict[str, int]:
    from app.database import SessionLocal
    from app.models import (
        BusinessRecord, FinanceTransaction, LegacyFinanceAllocation,
        LegacyFinanceAudit, LegacyFinanceRecord, SystemParameter, WorkflowEvent,
    )

    async with SessionLocal() as db:
        if apply:
            await db.execute(select(LegacyFinanceRecord.id).where(
                LegacyFinanceRecord.record_kind == "ap_payment",
            ).with_for_update())
        records = (await db.scalars(select(LegacyFinanceRecord).where(
            LegacyFinanceRecord.record_kind == "ap_payment",
            LegacyFinanceRecord.source_table == "FAM_AP_Payment",
        ).order_by(LegacyFinanceRecord.id))).all()
        number_counts = Counter(str((row.source_payload or {}).get("ApplicationNo") or "").strip() for row in records)
        serials = {_serial(row, number_counts) for row in records}
        package_rows = (await db.execute(sql_text('SELECT * FROM "FAM_AP_Payment_Packing" ORDER BY "PackingId"'))).mappings().all()
        package_counts = Counter(str(row["PackageNo"] or "").strip() for row in package_rows)
        package_serials = {_package_serial(row, package_counts, serials) for row in package_rows}
        package_members = defaultdict(list)
        for row in records:
            package_no = str((row.source_payload or {}).get("PackageNo") or "").strip()
            if package_no:
                package_members[package_no].append(row)
        ambiguous_package_numbers = {number for number, count in package_counts.items()
                                     if number and count > 1 and package_members.get(number)}
        record_ids = [row.id for row in records]
        allocations = (await db.scalars(select(LegacyFinanceAllocation).where(
            LegacyFinanceAllocation.legacy_finance_record_id.in_(record_ids),
            LegacyFinanceAllocation.allocation_kind == "ap_payment",
            LegacyFinanceAllocation.is_active.is_(True),
        ).order_by(LegacyFinanceAllocation.id))).all()
        audits = (await db.scalars(select(LegacyFinanceAudit).where(
            LegacyFinanceAudit.legacy_finance_record_id.in_(record_ids),
            LegacyFinanceAudit.audit_kind == "ap_payment",
        ).order_by(LegacyFinanceAudit.id))).all()
        linked_ids = {
            row.contract_record_id for row in records if row.contract_record_id
        } | {
            row.customer_record_id for row in records if row.customer_record_id
        } | {
            row.case_record_id for row in allocations if row.case_record_id
        }
        relations = {row.id: row for row in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.id.in_(linked_ids),
        ))).all()}
        source_fee_ids = {str(row.legacy_case_fee_id).strip() for row in allocations}
        fees = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance",
            BusinessRecord.data["case_fee_id"].as_string().in_(source_fee_ids),
            BusinessRecord.data["legacy_kind"].as_string() == "ar_case_fee",
        ))).all()
        fees_by_source = defaultdict(list)
        for fee in fees:
            fees_by_source[str((fee.data or {}).get("case_fee_id"))].append(fee)
        parameters = {row.code: row for row in (await db.scalars(select(SystemParameter).where(
            SystemParameter.category == "payment_type",
        ))).all()}
        existing = {row.serial_no: row for row in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.serial_no.in_(serials),
        ))).all()}
        existing_packages = {row.serial_no: row for row in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.serial_no.in_(package_serials),
        ))).all()}
        allocation_by_record = defaultdict(list)
        audit_by_record = defaultdict(list)
        for row in allocations:
            allocation_by_record[row.legacy_finance_record_id].append(row)
        for row in audits:
            audit_by_record[row.legacy_finance_record_id].append(row)

        preflight_errors: list[str] = []
        pending = 0
        for source in records:
            payload = source.source_payload or {}
            code = str(source.status_code or "").strip()
            serial = _serial(source, number_counts)
            if code not in STATUS_BY_SOURCE:
                preflight_errors.append(f"{serial}: 未知源状态 {code}")
                continue
            previous = existing.get(serial)
            if previous and (
                previous.module != "contract_payment"
                or str((previous.data or {}).get("legacy_finance_record_id")) != str(source.id)
            ):
                preflight_errors.append(f"{serial}: 现行业务编号已被其他记录占用")
            if not source.is_active or code not in ACTIONABLE_STATUSES:
                continue
            pending += 1
            contract = relations.get(source.contract_record_id)
            customer = relations.get(source.customer_record_id)
            payment_type_id = payload.get("PaymentTypeId")
            parameter = parameters.get(f"LEGACY-PAYMENT-{payment_type_id}")
            account = (parameter.extra or {}) if parameter else {}
            lines = allocation_by_record[source.id]
            if not contract or contract.module != "contract" or not customer or customer.module != "customer":
                preflight_errors.append(f"{serial}: 合同或客户关联缺失")
            if not account.get("payee") or not account.get("account") or not account.get("account_bank"):
                preflight_errors.append(f"{serial}: 收款账户资料不完整")
            if not lines or abs(sum(_money(item.amount) for item in lines) - _money(source.primary_amount)) > 0.01:
                preflight_errors.append(f"{serial}: 费用明细与申请金额不一致")
            for line in lines:
                matches = fees_by_source.get(str(line.legacy_case_fee_id).strip(), [])
                if len(matches) != 1 or not line.case_record_id or not relations.get(line.case_record_id):
                    preflight_errors.append(f"{serial}: 案件费用或案件关联不唯一")
        if len(serials) != len(records) or len(package_serials) != len(package_rows) or serials & package_serials:
            preflight_errors.append("付款申请或付款包编号不唯一")
        if ambiguous_package_numbers:
            preflight_errors.append("付款包号重复且存在申请明细：" + "、".join(sorted(ambiguous_package_numbers)[:10]))
        for source in records:
            if len(_serial(source, number_counts)) > 64:
                preflight_errors.append(f"付款申请 {source.legacy_id} 编号超长")
        for package in package_rows:
            serial = _package_serial(package, package_counts, serials)
            json.dumps({key: value.isoformat() if isinstance(value, (datetime, date)) else
                        str(value) if isinstance(value, Decimal) else value
                        for key, value in package.items()})
            previous = existing_packages.get(serial)
            if previous and (previous.module != "finance_package"
                             or str((previous.data or {}).get("legacy_packing_id")) != str(package["PackingId"])):
                preflight_errors.append(f"付款包 {serial} 的业务编号已被占用")
        if preflight_errors:
            raise RuntimeError("付款申请接入预检失败：" + "；".join(preflight_errors[:20]))

        summary = {
            "source_records": len(records),
            "already_promoted": len(existing),
            "to_promote": len(records) - len(existing),
            "actionable": pending,
            "allocations": len(allocations),
            "audits": len(audits),
            "source_packages": len(package_rows),
            "packages_without_members": sum(1 for row in package_rows if not package_members.get(str(row["PackageNo"] or "").strip())),
            "duplicate_package_numbers": sum(1 for number, count in package_counts.items() if number and count > 1),
            "packages_to_promote": len(package_rows) - len(existing_packages),
        }
        if not apply:
            await db.rollback()
            return summary

        packages = {str(row["PackageNo"]): row for row in package_rows if row["PackageNo"]}
        promoted = 0
        package_promoted = 0
        transactions = 0
        events = 0
        payments_by_source = {str((row.data or {}).get("legacy_id")): row for row in existing.values()}
        for source in records:
            serial = _serial(source, number_counts)
            if serial in existing:
                continue
            payload = source.source_payload or {}
            code = str(source.status_code).strip()
            status = STATUS_BY_SOURCE[code] if source.is_active else "已删除"
            contract = relations.get(source.contract_record_id)
            customer = relations.get(source.customer_record_id)
            parameter = parameters.get(f"LEGACY-PAYMENT-{payload.get('PaymentTypeId')}")
            account = (parameter.extra or {}) if parameter else {}
            source_lines = allocation_by_record[source.id]
            source_lines_amount = round(sum(_money(line.amount) for line in source_lines), 2)
            source_amount = _money(source.primary_amount)
            relation_status = ("缺少费用明细" if not source_lines else
                               "申请金额与明细不一致" if abs(source_lines_amount - source_amount) > 0.01 else
                               "已关联")
            lines = []
            for line in source_lines:
                fee = fees_by_source.get(str(line.legacy_case_fee_id).strip(), [])
                lines.append({
                    "case_no": line.legacy_case_no,
                    "case_id": line.case_record_id,
                    "case_fee_id": fee[0].id if len(fee) == 1 else None,
                    "fee_record_id": fee[0].id if len(fee) == 1 else None,
                    "legacy_case_fee_id": line.legacy_case_fee_id,
                    "fee_type": (fee[0].data or {}).get("fee_type") if len(fee) == 1 else "",
                    "amount": _money(line.amount),
                    "requested_amount": _money(line.amount),
                    "prepaid_amount": _money(line.prepaid_amount),
                    "remark": (line.source_payload or {}).get("Remark") or "",
                })
            paid_date = _date(payload.get("PaymentDate"))
            package_no = str(payload.get("PackageNo") or "").strip()
            package = packages.get(package_no)
            row = BusinessRecord(
                module="contract_payment",
                serial_no=serial,
                title=f"付款申请 {payload.get('ApplicationNo') or source.legacy_id}",
                customer=customer.title if customer else "",
                status=status,
                owner=str(payload.get("Applicant") or payload.get("CreateUser") or "").strip(),
                department=contract.department if contract else "",
                description=str(payload.get("Remark") or ""),
                data={
                    "legacy_kind": "ap_payment",
                    "legacy_source": "hz_crm_20260930",
                    "legacy_finance_record_id": source.id,
                    "legacy_id": source.legacy_id,
                    "source_table": source.source_table,
                    "legacy_status_code": code,
                    "legacy_record": payload,
                    "application_no": payload.get("ApplicationNo") or "",
                    "application_date": payload.get("ApplicationDate") or "",
                    "applicant": payload.get("Applicant") or "",
                    "deadline": payload.get("DeadLine") or "",
                    "payment_date": str(paid_date) if paid_date else "",
                    "payment_package_no": package_no,
                    "payment_status": status,
                    "writeoff_status": "已核销" if code == "7" else "待核销" if code == "6" else "",
                    "fee_type": "付款申请",
                    "amount": _money(source.primary_amount),
                    "paid_amount": _money(source.primary_amount) if code == "7" else 0,
                    "payee": account.get("payee") or "",
                    "account": account.get("account") or "",
                    "account_bank": account.get("account_bank") or "",
                    "payment_type_id": parameter.id if parameter else None,
                    "payment_type_code": parameter.code if parameter else "",
                    "legacy_payment_type_id": payload.get("PaymentTypeId"),
                    "payer_name": payload.get("PayerName") or "",
                    "contract_id": source.contract_record_id,
                    "contract_no": source.legacy_contract_no,
                    "customer_id": source.customer_record_id,
                    "customer_no": source.legacy_customer_no,
                    "case_no": lines[0]["case_no"] if len(lines) == 1 else "",
                    "lines": lines,
                    "relation_status": relation_status,
                },
                created_at=_datetime(payload.get("ApplicationDate")) or source.imported_at,
                updated_at=_datetime(payload.get("ChangeTime")) or source.updated_at,
            )
            db.add(row)
            await db.flush()
            payments_by_source[str(source.legacy_id)] = row
            promoted += 1
            for audit in audit_by_record[source.id]:
                db.add(WorkflowEvent(
                    record_id=row.id,
                    action="原付款申请审批记录",
                    from_status="",
                    to_status=STATUS_BY_SOURCE.get(str(audit.audit_status_code), ""),
                    operator=audit.auditor or "system",
                    comment=audit.audit_content or "",
                    created_at=audit.audit_date or audit.imported_at,
                ))
                events += 1
            if code == "7" and source.is_active:
                db.add(FinanceTransaction(
                    finance_record_id=row.id,
                    transaction_type="付款",
                    amount=_money(source.primary_amount),
                    transaction_date=paid_date,
                    voucher_no=str(package["InvoiceNo"] or "") if package else "",
                    counterparty=str(account.get("payee") or ""),
                    operator=str(payload.get("ChangeUser") or payload.get("Applicant") or "system"),
                    remark=f"来源 {source.source_table} #{source.legacy_id}；付款包 {package_no}",
                    created_at=_datetime(payload.get("PaymentDate")) or source.imported_at,
                ))
                transactions += 1
        for source_package in package_rows:
            serial = _package_serial(source_package, package_counts, serials)
            if serial in existing_packages:
                package_record = existing_packages[serial]
            else:
                package_no = str(source_package["PackageNo"] or "").strip()
                members = [payments_by_source[str(item.legacy_id)] for item in package_members.get(package_no, [])]
                source_status = str(source_package["PackingStatus"] or "").strip()
                parameter = parameters.get(f"LEGACY-PAYMENT-{source_package['PaymentTypeId']}")
                account = (parameter.extra or {}) if parameter else {}
                amount = round(sum(_money((item.data or {}).get("amount")) for item in members), 2) if members else None
                status = ("已删除" if source_package["IsActived"] != "T" else
                          "已付款" if source_status == "3" else
                          "待核销" if members and source_status == "2" else
                          "待打包" if members and source_status == "1" else "待核对关联")
                payload = {key: value.isoformat() if isinstance(value, (datetime, date)) else
                           str(value) if isinstance(value, Decimal) else value
                           for key, value in source_package.items()}
                package_record = BusinessRecord(
                    module="finance_package", serial_no=serial,
                    title=f"付款包 {package_no or source_package['PackingId']}",
                    customer=members[0].customer if members else "",
                    status=status,
                    owner=str(source_package["CreateUser"] or "").strip(),
                    department=members[0].department if members else "",
                    description=str(source_package["Remark"] or ""),
                    data={
                        "legacy_kind": "ap_packing",
                        "legacy_source": "hz_crm_20260930",
                        "legacy_packing_id": source_package["PackingId"],
                        "legacy_record": payload,
                        "payment_package_no": package_no,
                        "fee_type": "普通付款包",
                        "fee_ids": [item.id for item in members],
                        "items": [{"id": item.id, "request_no": item.serial_no,
                                   "amount": _money((item.data or {}).get("amount"))} for item in members],
                        "amount": amount,
                        "total_amount": amount,
                        "payee": account.get("payee") or "",
                        "account": account.get("account") or "",
                        "account_bank": account.get("account_bank") or "",
                        "payment_status": status,
                        "writeoff_status": "已核销" if status == "已付款" else "待核销" if status == "待核销" else "",
                        "payment_date": str(_date(source_package["PaidDate"]) or ""),
                        "invoice_no": str(source_package["InvoiceNo"] or ""),
                        "relation_status": "已关联" if members else "缺少付款申请明细",
                    },
                    created_at=source_package["CreateTime"] or datetime.now(),
                    updated_at=source_package["ChangeTime"] or source_package["CreateTime"] or datetime.now(),
                )
                db.add(package_record)
                await db.flush()
                package_promoted += 1
            package_no = str(source_package["PackageNo"] or "").strip()
            for source_member in package_members.get(package_no, []):
                member = payments_by_source[str(source_member.legacy_id)]
                if (member.data or {}).get("payment_package_id") != package_record.id:
                    member.data = {**(member.data or {}), "payment_package_id": package_record.id}
        await db.commit()
        return {**summary, "promoted": promoted, "packages_promoted": package_promoted,
                "transactions": transactions, "workflow_events": events}


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
