"""历史普通结算承接（BUG20261028009）。

结算管理里“历史只读”的行来自原系统回款头（legacy-normal:回款头）。在新系统里审核、支付、回滚或重新申请时，
先在同一事务里把它按原状态和原分配快照转成现代结算申请，再走现代流程；历史投影见到同回款的现代申请后自动隐藏。
"""
import re
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.core.imported_settlement_projection import read_imported_settlement_page
from app.models import BusinessRecord, IncomingPayment, WorkflowEvent

PROJECTION_ID = re.compile(r"^legacy-normal:[1-9]\d*$")
ARCHIVE_PROJECTION_ID = re.compile(r"^legacy-archive:[1-9]\d*$")
ARCHIVE_DECISION_STATUS = {"paid": "已支付", "rejected": "已拒绝"}
LEGACY_STATUSES = {"待审批", "待付款", "已付款", "已拒绝"}
_DROPPED_FIELDS = {"status", "date_unknown"}


def is_adopted(record: BusinessRecord) -> bool:
    return bool((record.data or {}).get("legacy_projection_id"))


async def adopt_legacy_settlements(projection_ids: list[str], identity: dict, db) -> list[int]:
    ids = list(dict.fromkeys(str(item).strip() for item in projection_ids))
    if not ids:
        return []
    invalid = [item for item in ids if not PROJECTION_ID.match(item)]
    if invalid:
        raise HTTPException(422, "历史结算编号无效：" + "、".join(invalid))
    rows = (await read_imported_settlement_page(
        [], identity, db, mode="normal", statuses=LEGACY_STATUSES, projection_ids=ids,
    ))["items"]
    if any(not (row.get("data") or {}).get("amount_visible") for row in rows):
        raise HTTPException(403, "没有查看结算金额的权限，不能办理历史结算")
    receipt_ids = [int((row.get("data") or {}).get("receipt_id") or 0) for row in rows]
    if 0 in receipt_ids or len(set(receipt_ids)) != len(receipt_ids):
        raise HTTPException(409, "历史结算缺少唯一的来源回款，不能办理")
    locked = (await db.scalars(select(IncomingPayment.id).where(
        IncomingPayment.id.in_(receipt_ids)).with_for_update())).all()
    if len(locked) != len(receipt_ids):
        raise HTTPException(409, "历史结算的来源回款不存在，不能办理")
    taken = await db.scalar(select(BusinessRecord.serial_no).where(
        BusinessRecord.module == "finance_settlement", BusinessRecord.status != "已删除",
        BusinessRecord.data["receipt_id"].as_integer().in_(receipt_ids),
    ).limit(1))
    if taken:
        raise HTTPException(409, f"部分历史结算已在新系统办理（{taken}），请刷新后重试")
    now = datetime.now()
    now_key = now.strftime("%Y%m%d%H%M%S%f")
    adopted_ids: list[int] = []
    for index, row in enumerate(rows):
        data = {key: value for key, value in (row.get("data") or {}).items() if key not in _DROPPED_FIELDS}
        record = BusinessRecord(
            module="finance_settlement",
            serial_no=f"JS{now_key}{index:02d}",
            title=f"{row.get('customer') or data.get('payer_name') or ''}结算申请",
            customer=str(row.get("customer") or ""),
            status=row["status"],
            owner=identity["username"],
            department=str(identity.get("department") or "上海分所"),
            description="",
            data={
                **data,
                "legacy_projection_id": row["id"],
                "legacy_record_id": row.get("legacy_record_id"),
                "legacy_source_status": row.get("source_status"),
                "adopted_by": identity["username"],
                "adopted_at": now.isoformat(timespec="seconds"),
            },
        )
        db.add(record)
        await db.flush()
        db.add(WorkflowEvent(
            record_id=record.id, action="承接历史结算", to_status=record.status, operator=identity["username"],
            comment=f"原系统结算状态 {row.get('source_status') or '未提供'}，按原分配快照承接",
        ))
        adopted_ids.append(record.id)
    return adopted_ids


async def legacy_archive_rows(projection_ids: list[str], mode: str, identity: dict, db) -> list[dict]:
    """读取指定的历史归档费行（BUG20261028010）；不存在、已办理或状态已变化时 409。"""
    ids = list(dict.fromkeys(str(item).strip() for item in projection_ids))
    if not ids:
        return []
    invalid = [item for item in ids if not ARCHIVE_PROJECTION_ID.match(item)]
    if invalid:
        raise HTTPException(422, "历史归档费编号无效：" + "、".join(invalid))
    rows = (await read_imported_settlement_page([], identity, db, mode=mode, projection_ids=ids))["items"]
    if any((row.get("data") or {}).get("archive_fee_amount") is None for row in rows):
        raise HTTPException(403, "没有查看结算金额的权限，不能办理历史归档费")
    taken = await db.scalar(select(BusinessRecord.serial_no).where(
        BusinessRecord.module == "finance_archive_settlement", BusinessRecord.status.in_({"已支付", "已拒绝"}),
        BusinessRecord.data["source_row_id"].as_string().in_(ids),
    ).limit(1))
    if taken:
        raise HTTPException(409, f"部分历史归档费已在新系统办理（{taken}），请刷新后重试")
    return rows


def archive_decision_data(row: dict, identity: dict, decided_at: str) -> dict:
    data = {key: value for key, value in (row.get("data") or {}).items() if key not in _DROPPED_FIELDS}
    return {
        **data,
        "source_row_id": row["id"],
        "legacy_projection_id": row["id"],
        "legacy_source_status": row.get("source_status"),
        "archive_payment_submitted_by": data.get("applied_by") or row.get("owner") or identity["username"],
        "archive_payment_submitted_at": data.get("applied_at") or data.get("settlement_paid_at") or decided_at,
        "archive_payment_reviewer": data.get("reviewer") or "",
        "archive_payment_reviewed_at": data.get("reviewed_at") or data.get("paid_at") or "",
    }


async def adopt_legacy_archive_settlements(projection_ids: list[str], mode: str, identity: dict, db) -> list[int]:
    """已支付/已拒绝的历史归档费在新系统回滚或重新申请时，按原状态承接为归档费决定记录。"""
    rows = await legacy_archive_rows(projection_ids, mode, identity, db)
    status = ARCHIVE_DECISION_STATUS[mode]
    now = datetime.now().isoformat(timespec="seconds")
    adopted_ids: list[int] = []
    for row in rows:
        record = BusinessRecord(
            module="finance_archive_settlement", serial_no=f"ARCP-{row['id'].replace(':', '-')}",
            title=row.get("title") or "历史归档结算", customer=row.get("customer") or "", status=status,
            owner=identity["username"], department=str(identity.get("department") or "上海分所"),
            data={**archive_decision_data(row, identity, now), "adopted_by": identity["username"], "adopted_at": now},
        )
        db.add(record)
        await db.flush()
        db.add(WorkflowEvent(
            record_id=record.id, action="承接历史归档费", to_status=status, operator=identity["username"],
            comment=f"原系统归档费状态 {row.get('source_status') or '未提供'}，按原明细承接",
        ))
        adopted_ids.append(record.id)
    return adopted_ids
