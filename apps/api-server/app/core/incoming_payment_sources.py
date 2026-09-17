"""按已核对的回款写入器标记来源；旧系统迁移编号保持来源未确认。"""
import re
from datetime import datetime
from sqlalchemy import select, update
from app.models import BusinessRecord, IncomingPayment


def historical_receipt_source(receipt_no: str, ipr_receipts: set[str]) -> str:
    if receipt_no in ipr_receipts or re.fullmatch(r"FNIHK\d{20}", receipt_no):
        return "system"
    if re.fullmatch(r"HKICBC[0-9a-f]+", receipt_no) or re.fullmatch(r"HK\d{21,}", receipt_no):
        return "bank_import"
    if re.fullmatch(r"HK\d{20}", receipt_no):
        try:
            datetime.strptime(receipt_no[2:], "%Y%m%d%H%M%S%f")
        except ValueError:
            return "unknown"
        # HK 加二十位时间戳只有手工登记和知识产权费用到账两个写入入口。
        return "manual"
    return "unknown"


def backfill_incoming_sources(connection):
    rows = connection.execute(select(IncomingPayment.id, IncomingPayment.receipt_no).where(IncomingPayment.source_kind == "unknown")).all()
    numbers = [row.receipt_no for row in rows]
    ipr_receipts = set(connection.scalars(select(BusinessRecord.data["arrival_receipt_no"].as_string()).where(
        BusinessRecord.data["arrival_receipt_no"].as_string().in_(numbers),
    )).all()) if numbers else set()
    for row in rows:
        source = historical_receipt_source(row.receipt_no, ipr_receipts)
        if source != "unknown":
            connection.execute(update(IncomingPayment).where(IncomingPayment.id == row.id).values(source_kind=source, updated_at=IncomingPayment.updated_at))
