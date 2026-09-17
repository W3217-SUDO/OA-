"""按案件实际到账分配明细生成清单，不改变回款或结算状态。"""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IncomingPayment, LegacyFinanceAllocation, LegacyFinanceRecord


RECEIPT_HEADERS = [
    "系统案号", "案件名称", "客户", "合同编号", "到账日期", "到账单号",
    "付款人", "银行流水号", "回款银行", "本案到账金额", "案件阶段", "分配日期", "备注",
]


async def case_receipt_export_rows(ids: str, identity: dict, db: AsyncSession) -> list[list]:
    from app.core.permissions import _require_record_module_menu, _scoped_export_records
    from app.core.system import _export_ids

    await _require_record_module_menu("case", identity, db, action="导出")
    selected_ids = _export_ids(ids)
    if not selected_ids:
        raise HTTPException(status_code=422, detail="请选择需要导出到账清单的案件")
    records = await _scoped_export_records("case", ids, identity, db)
    if len(records) != len(selected_ids):
        raise HTTPException(status_code=404, detail="存在案件记录不存在或当前账号无权导出")
    cases = {record.id: record for record in records}
    cases_by_no = {record.serial_no: record for record in records}
    rows = []
    payments = (await db.scalars(select(IncomingPayment).order_by(IncomingPayment.received_date, IncomingPayment.id))).all()
    for payment in payments:
        for allocation in payment.allocations or []:
            # 新分配以案件主键为准；历史分配没有主键时使用明确记录的案号。
            case_id = allocation.get("case_id")
            case = cases.get(int(case_id)) if case_id is not None else cases_by_no.get(allocation.get("case_no"))
            if case is None:
                continue
            amount = Decimal(str(allocation["amount"]))
            if not amount:
                continue
            rows.append([
                case.serial_no, case.title, case.customer, allocation.get("contract_no", ""),
                payment.received_date.isoformat(), payment.receipt_no, payment.payer_name,
                payment.bank_reference or "", payment.bank_source, format(amount, ".2f"),
                allocation.get("phase", ""), allocation.get("allocated_at", ""), payment.remark,
            ])

    # 历史财务台账独立保存源明细，不能用表头金额代替案件分配金额。
    legacy_rows = (await db.execute(
        select(LegacyFinanceAllocation, LegacyFinanceRecord)
        .join(LegacyFinanceRecord, LegacyFinanceAllocation.legacy_finance_record_id == LegacyFinanceRecord.id)
        .where(
            LegacyFinanceAllocation.source_table == "FAM_AR_Payment_Object",
            LegacyFinanceRecord.source_table == "FAM_AR_Payment",
            LegacyFinanceAllocation.case_record_id.in_(selected_ids),
            LegacyFinanceAllocation.is_active.is_(True),
            LegacyFinanceRecord.is_active.is_(True),
        )
        .order_by(LegacyFinanceRecord.id, LegacyFinanceAllocation.id)
    )).all()
    for allocation, payment in legacy_rows:
        if not allocation.amount:
            continue
        case = cases[allocation.case_record_id]
        header = payment.source_payload or {}
        detail = allocation.source_payload or {}
        rows.append([
            case.serial_no, case.title, case.customer, payment.legacy_contract_no,
            header.get("CashedDate") or "", payment.legacy_id, header.get("PayerName") or "",
            header.get("SequenceNo") or "", header.get("PaymentModeName") or "",
            format(allocation.amount, ".2f"), "", detail.get("CreateTime") or "", detail.get("Remark") or "",
        ])
    if not rows:
        raise HTTPException(status_code=422, detail="所选案件没有已分配的到账明细")
    return rows
