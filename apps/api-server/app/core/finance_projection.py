"""现代财务记录与旧 FAM 财务记录的只读展示投影。

该模块只负责查询层归并。旧记录保持在 ``legacy_finance_*`` 表中，绝不
转换为 ``FinanceTransaction``，也不参与现代费用审批、付款或退费状态机。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BusinessRecord,
    FileAttachment,
    FinanceTransaction,
    LegacyFinanceAllocation,
    LegacyFinanceRecord,
)


def _number(value: object) -> float | None:
    try:
        return round(float(value), 2) if value is not None else None
    except (TypeError, ValueError):
        return None


def _iso(value: object) -> str | None:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    text = str(value or "").strip()
    return text or None


def _legacy_payload_date(payload: object, *keys: str) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = payload.get(key)
        if value:
            return _iso(value)
    return None


def _legacy_fee_item(item: LegacyFinanceRecord, *, show_amount: bool) -> dict[str, Any]:
    amount = _number(item.primary_amount) if show_amount else None
    payload = item.source_payload or {}
    kind_labels = {
        "case_fee": "历史案件费用",
        "internal_fee": "历史内部费用",
        "ap_payment": "历史付款申请",
        "ar_payment": "历史回款",
        "invoice": "历史发票",
        "internal_payment": "历史内部请款",
    }
    label = kind_labels.get(item.record_kind, "历史财务记录")
    data = {
        "fee_type": label,
        "amount": amount,
        "case_no": item.legacy_case_no,
        "contract_no": item.legacy_contract_no,
        "customer_no": item.legacy_customer_no,
        "source_table": item.source_table,
        "legacy_id": item.legacy_id,
        "payee": str(payload.get("PaymentObject") or ""),
    }
    return {
        # 使用前缀，避免历史 ID 被误传给接收 BusinessRecord ID 的现代写接口。
        "id": f"legacy-fee:{item.id}",
        "record_id": item.id,
        "source": "legacy",
        "read_only": True,
        "can_edit": False,
        "can_delete": False,
        "can_submit": False,
        "can_pay": False,
        "can_refund": False,
        "module": "finance",
        "record_kind": item.record_kind,
        "source_table": item.source_table,
        "legacy_id": item.legacy_id,
        "serial_no": item.legacy_id,
        "finance_no": item.legacy_id,
        "title": label,
        "status": item.status_label or item.status_code,
        "status_code": item.status_code,
        "status_label": item.status_label,
        "fee_type": label,
        "customer": item.legacy_customer_no,
        "contract_no": item.legacy_contract_no,
        "case_no": item.legacy_case_no,
        "amount": amount,
        "primary_amount": amount,
        "currency": item.currency,
        "mapping_status": item.mapping_status,
        "contract_record_id": item.contract_record_id,
        "case_record_id": item.case_record_id,
        "customer_record_id": item.customer_record_id,
        "owner": str(payload.get("RequestUser") or payload.get("CreateUser") or ""),
        "description": str(payload.get("Remark") or ""),
        "data": data,
        "updated_at": _iso(item.updated_at),
        "created_at": _iso(item.imported_at),
    }


def _modern_fee_item(item: BusinessRecord, *, show_amount: bool, allowed_fields: set[str]) -> dict[str, Any]:
    from app.core.system import _record_dict

    visible_record = _record_dict(item, allowed_fields)
    data = visible_record["data"]
    amount = _number(data.get("amount")) if show_amount else None
    return {
        **visible_record,
        "id": f"modern-fee:{item.id}",
        "record_id": item.id,
        "source": "modern",
        "read_only": False,
        "can_edit": True,
        "can_delete": True,
        "can_submit": True,
        "can_pay": True,
        "can_refund": True,
        "module": item.module,
        "record_kind": "finance",
        "source_table": "business_records",
        "legacy_id": None,
        "serial_no": item.serial_no,
        "finance_no": item.serial_no,
        "title": item.title,
        "status": item.status,
        "status_code": item.status,
        "status_label": item.status,
        "fee_type": str(data.get("fee_type") or data.get("fee_type_name") or ""),
        "customer": item.customer,
        "contract_no": str(data.get("contract_no") or ""),
        "case_no": str(data.get("case_no") or ""),
        "amount": amount,
        "primary_amount": amount,
        "currency": str(data.get("currency") or "CNY"),
        "mapping_status": "modern",
        "contract_record_id": data.get("contract_id") or data.get("contract_record_id"),
        "case_record_id": data.get("case_id") or data.get("case_record_id"),
        "customer_record_id": data.get("customer_id") or data.get("customer_record_id"),
        "updated_at": _iso(item.updated_at),
        "created_at": _iso(item.created_at),
    }


def _legacy_transaction_item(
    item: LegacyFinanceAllocation,
    parent: LegacyFinanceRecord | None,
    *,
    show_amount: bool,
) -> dict[str, Any]:
    payload = item.source_payload or {}
    transaction_date = _legacy_payload_date(
        payload,
        "PaymentDate", "CashedDate", "InvoiceDate", "PaidDate", "CreateTime", "ChangeTime",
    ) or _iso(parent.updated_at if parent else item.updated_at)
    return {
        "id": f"legacy-allocation:{item.id}",
        "transaction_id": item.id,
        "finance_record_id": None,
        "finance_no": parent.legacy_id if parent else item.parent_legacy_id,
        "finance_title": parent.record_kind if parent else item.allocation_kind,
        "legacy_finance_record_id": item.legacy_finance_record_id,
        "source": "legacy",
        "read_only": True,
        "can_edit": False,
        "can_delete": False,
        "can_cancel": False,
        "transaction_type": item.allocation_kind,
        "amount": _number(item.amount) if show_amount else None,
        "transaction_date": transaction_date,
        "voucher_no": item.legacy_key,
        "counterparty": "",
        "operator": "",
        "voucher_count": 0,
        "voucher_categories": [],
        "vouchers": [],
        "remark": f"历史财务明细：{item.source_table}",
        "record_kind": parent.record_kind if parent else "",
        "legacy_id": parent.legacy_id if parent else item.parent_legacy_id,
        "legacy_case_no": item.legacy_case_no,
        "case_no": item.legacy_case_no,
        "contract_no": parent.legacy_contract_no if parent else "",
        "customer": parent.legacy_customer_no if parent else "",
        "allocation_kind": item.allocation_kind,
        "is_refund": bool(item.is_refund),
        "mapping_status": item.mapping_status,
        "updated_at": _iso(item.updated_at),
        "created_at": _iso(item.imported_at),
    }


def _modern_transaction_item(
    item: FinanceTransaction,
    record: BusinessRecord | None,
    vouchers: list[FileAttachment],
    *,
    show_amount: bool,
    users_by_username: dict,
) -> dict[str, Any]:
    from app.core.finance import _finance_transaction_dict

    modern = _finance_transaction_dict(
        item, record, vouchers, show_amount=show_amount, users_by_username=users_by_username,
    )
    data = record.data if record else {}
    return {
        **modern,
        "id": f"modern-transaction:{item.id}",
        "transaction_id": item.id,
        "finance_record_id": item.finance_record_id,
        "legacy_finance_record_id": None,
        "source": "modern",
        "read_only": False,
        "can_edit": False,
        "can_delete": True,
        "can_cancel": True,
        "transaction_type": item.transaction_type,
        "amount": _number(item.amount) if show_amount else None,
        "transaction_date": _iso(item.transaction_date),
        "voucher_no": item.voucher_no,
        "counterparty": item.counterparty,
        "record_kind": "finance",
        "legacy_id": None,
        "legacy_case_no": "",
        "case_no": str(data.get("case_no") or ""),
        "contract_no": str(data.get("contract_no") or ""),
        "customer": record.customer if record else "",
        "mapping_status": "modern",
        "updated_at": _iso(item.created_at),
        "created_at": _iso(item.created_at),
    }


async def read_unified_finance_projection(
    identity: dict,
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    keyword: str = "",
    source: str = "all",
    include_inactive: bool = False,
    status: str = "",
    fee_type: str = "",
) -> dict:
    """将现代费用与旧 FAM 费用表头合并为只读投影。"""
    from app.core.permissions import _record_scope_conditions
    from app.core.system import _allowed_field_keys

    if source not in {"all", "modern", "legacy"}:
        raise ValueError("source must be all, modern or legacy")
    allowed_fields = await _allowed_field_keys(identity, db)
    show_amount = "finance.amount" in allowed_fields
    modern: list[dict[str, Any]] = []
    legacy: list[dict[str, Any]] = []
    required = page * page_size
    if source in {"all", "modern"}:
        modern_conditions = [BusinessRecord.module == "finance", *await _record_scope_conditions(identity, db)]
        if not include_inactive:
            modern_conditions.append(BusinessRecord.status != "已删除")
        if status.strip():
            modern_conditions.append(BusinessRecord.status.ilike(f"%{status.strip()}%"))
        if fee_type.strip():
            modern_conditions.append(or_(
                BusinessRecord.data["fee_type"].as_string().ilike(f"%{fee_type.strip()}%"),
                BusinessRecord.data["fee_type_name"].as_string().ilike(f"%{fee_type.strip()}%"),
            ))
        if keyword.strip():
            needle = f"%{keyword.strip()}%"
            modern_conditions.append(or_(
                BusinessRecord.serial_no.ilike(needle),
                BusinessRecord.title.ilike(needle),
                BusinessRecord.customer.ilike(needle),
                BusinessRecord.data["case_no"].as_string().ilike(needle),
                BusinessRecord.data["contract_no"].as_string().ilike(needle),
                BusinessRecord.data["fee_type"].as_string().ilike(needle),
            ))
        modern_total = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(*modern_conditions)) or 0)
        modern_rows = list((await db.scalars(
            select(BusinessRecord).where(*modern_conditions).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc())
            .limit(required)
        )).all())
        modern = [_modern_fee_item(item, show_amount=show_amount, allowed_fields=allowed_fields) for item in modern_rows]
    else:
        modern_total = 0
    if source in {"all", "legacy"}:
        from app.core.legacy_sync import _legacy_finance_scope_conditions

        legacy_conditions = await _legacy_finance_scope_conditions(identity, db)
        # 旧案件费用已导入 BusinessRecord；本页仅补充未进入现代费用表的内部费用。
        legacy_conditions.append(LegacyFinanceRecord.record_kind == "internal_fee")
        if not include_inactive:
            legacy_conditions.append(LegacyFinanceRecord.is_active.is_(True))
        if status.strip():
            legacy_conditions.append(or_(
                LegacyFinanceRecord.status_code.ilike(f"%{status.strip()}%"),
                LegacyFinanceRecord.status_label.ilike(f"%{status.strip()}%"),
            ))
        if fee_type.strip():
            legacy_conditions.append(LegacyFinanceRecord.record_kind.ilike(f"%{fee_type.strip()}%"))
        if keyword.strip():
            needle = f"%{keyword.strip()}%"
            legacy_conditions.append(or_(
                LegacyFinanceRecord.legacy_id.ilike(needle),
                LegacyFinanceRecord.legacy_contract_no.ilike(needle),
                LegacyFinanceRecord.legacy_case_no.ilike(needle),
                LegacyFinanceRecord.legacy_customer_no.ilike(needle),
                LegacyFinanceRecord.record_kind.ilike(needle),
            ))
        legacy_total = int(await db.scalar(select(func.count()).select_from(LegacyFinanceRecord).where(*legacy_conditions)) or 0)
        legacy_rows = list((await db.scalars(
            select(LegacyFinanceRecord).where(*legacy_conditions).order_by(LegacyFinanceRecord.updated_at.desc(), LegacyFinanceRecord.id.desc())
            .limit(required)
        )).all())
        legacy = [_legacy_fee_item(item, show_amount=show_amount) for item in legacy_rows]
    else:
        legacy_total = 0
    rows = sorted(modern + legacy, key=lambda row: (str(row.get("updated_at") or ""), str(row.get("id") or "")), reverse=True)
    total = modern_total + legacy_total
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": total, "page": page, "page_size": page_size, "amount_visible": show_amount, "read_only": True}


async def read_unified_finance_transactions(
    identity: dict,
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    keyword: str = "",
    source: str = "all",
) -> dict:
    """将现代流水与历史分配明细合并返回，整个过程不产生写入。"""
    from app.core.permissions import _record_scope_conditions
    from app.core.system import _allowed_field_keys

    if source not in {"all", "modern", "legacy"}:
        raise ValueError("source must be all, modern or legacy")
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    modern: list[dict[str, Any]] = []
    legacy: list[dict[str, Any]] = []
    if source in {"all", "modern"}:
        scope_conditions = await _record_scope_conditions(identity, db)
        visible_ids = select(BusinessRecord.id).where(BusinessRecord.module == "finance", *scope_conditions)
        if identity.get("role") == "admin":
            modern_conditions: list[Any] = []
        else:
            modern_conditions = [or_(
                FinanceTransaction.finance_record_id.in_(visible_ids),
                and_(FinanceTransaction.finance_record_id.is_(None), FinanceTransaction.operator == identity.get("username", "")),
            )]
        if keyword.strip():
            needle = f"%{keyword.strip()}%"
            modern_conditions.append(or_(
                FinanceTransaction.transaction_type.ilike(needle),
                FinanceTransaction.voucher_no.ilike(needle),
                FinanceTransaction.counterparty.ilike(needle),
                FinanceTransaction.remark.ilike(needle),
            ))
        modern_total = int(await db.scalar(select(func.count()).select_from(FinanceTransaction).where(*modern_conditions)) or 0)
        modern_rows = list((await db.scalars(
            select(FinanceTransaction).where(*modern_conditions).order_by(FinanceTransaction.created_at.desc(), FinanceTransaction.id.desc())
            .limit(page * page_size)
        )).all())
        record_ids = {int(row.finance_record_id) for row in modern_rows if row.finance_record_id}
        records = {row.id: row for row in (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(record_ids)))).all()} if record_ids else {}
        transaction_ids = {row.id for row in modern_rows}
        voucher_rows = list((await db.scalars(select(FileAttachment).where(
            FileAttachment.finance_transaction_id.in_(transaction_ids)
        ).order_by(FileAttachment.created_at.desc()))).all()) if transaction_ids else []
        vouchers: dict[int, list[FileAttachment]] = {}
        for voucher in voucher_rows:
            vouchers.setdefault(int(voucher.finance_transaction_id or 0), []).append(voucher)
        from app.core.formatters import _user_display_map
        users_by_username = await _user_display_map({row.operator for row in modern_rows}, db)
        modern = [_modern_transaction_item(
            item, records.get(item.finance_record_id), vouchers.get(item.id, []),
            show_amount=show_amount, users_by_username=users_by_username,
        ) for item in modern_rows]
    else:
        modern_total = 0
    if source in {"all", "legacy"}:
        from app.core.legacy_sync import _legacy_finance_scope_conditions

        legacy_conditions = await _legacy_finance_scope_conditions(identity, db)
        parent_query = select(LegacyFinanceRecord.id).where(*legacy_conditions)
        allocation_conditions = [LegacyFinanceAllocation.legacy_finance_record_id.in_(parent_query), LegacyFinanceAllocation.is_active.is_(True)]
        if keyword.strip():
            needle = f"%{keyword.strip()}%"
            allocation_conditions.append(or_(
                LegacyFinanceAllocation.source_table.ilike(needle),
                LegacyFinanceAllocation.legacy_key.ilike(needle),
                LegacyFinanceAllocation.legacy_case_no.ilike(needle),
                LegacyFinanceAllocation.allocation_kind.ilike(needle),
            ))
        legacy_total = int(await db.scalar(select(func.count()).select_from(LegacyFinanceAllocation).where(*allocation_conditions)) or 0)
        allocation_rows = list((await db.scalars(
            select(LegacyFinanceAllocation).where(*allocation_conditions).order_by(LegacyFinanceAllocation.updated_at.desc(), LegacyFinanceAllocation.id.desc())
            .limit(page * page_size)
        )).all())
        parent_ids = {int(row.legacy_finance_record_id) for row in allocation_rows if row.legacy_finance_record_id}
        parents = {row.id: row for row in (await db.scalars(select(LegacyFinanceRecord).where(LegacyFinanceRecord.id.in_(parent_ids)))).all()} if parent_ids else {}
        legacy = [_legacy_transaction_item(item, parents.get(item.legacy_finance_record_id), show_amount=show_amount) for item in allocation_rows]
    else:
        legacy_total = 0
    rows = sorted(modern + legacy, key=lambda row: (str(row.get("updated_at") or ""), str(row.get("id") or "")), reverse=True)
    total = modern_total + legacy_total
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": total, "page": page, "page_size": page_size, "amount_visible": show_amount, "read_only": True}
