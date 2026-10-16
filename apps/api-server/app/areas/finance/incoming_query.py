"""回款列表的全集筛选、两套汇总及可选分页读取。"""

import json
import math
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select

from app.core.contracts import _contract_person_values
from app.core.finance import _incoming_payment_legacy_summary, _round_fee_amount
from app.core.formatters import _person_reference_display
from app.models import BusinessRecord, IncomingPayment
from app.core.finance_centers import INCOMING_CENTER, LEGACY_INCOMING_SOURCE
from app.core.incoming_legacy_amounts import ASSIGNED_FIELDS, LEGACY_ASSIGNED_AMOUNTS


BANK_VIEWS = {f"finance-receipts-{bank}" for bank in ("icbc", "citic", "boc", "cmb")}
RECEIPT_VIEWS = {f"finance-receipts-{kind}" for kind in ("manage", "claim", "pending", "allocated")}
QUERY_VIEW = "finance-receipts-query"
VIEW_STATUSES = {
    "finance-receipts-claim": {"待认领"},
    "finance-receipts-pending": {"待分配", "部分分配"},
    "finance-receipts-allocated": {"已分配"},
}
TOTAL_FIELDS = {
    "回款金额": "amount", "金额": "amount", "到账金额": "amount",
    "已分金额": "allocated_amount", "未分金额": "remaining_amount",
    "已分官费": "assigned_official_fee", "已分代理费": "assigned_agency_fee",
    "已分其他费用": "assigned_other_fee",
}
JS_WHITESPACE = " \t\n\v\f\r\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"


def parse_incoming_filters(view: str, filters: str) -> dict:
    if view and view not in BANK_VIEWS | RECEIPT_VIEWS | {QUERY_VIEW}:
        raise HTTPException(422, "回款查询页面无效")
    if not filters:
        return {}
    if not view:
        raise HTTPException(422, "回款筛选必须指定查询页面")
    try:
        values = json.loads(filters)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, "回款筛选条件必须为有效 JSON 对象") from exc
    if not isinstance(values, dict):
        raise HTTPException(422, "回款筛选条件必须为 JSON 对象")
    count = 4 if view in BANK_VIEWS else 6 if view in RECEIPT_VIEWS else 12
    date_index = 2 if view in BANK_VIEWS else 0 if view in RECEIPT_VIEWS else 9
    enums = {3: {"请选择", "未导入", "已导入"}} if view in BANK_VIEWS else {
        8: {"全部", "官费", "代理费", "其他费用", "第三方费用"},
        11: {"全部", "已分配", "未分配"},
    } if view == QUERY_VIEW else {}
    for key, value in values.items():
        if key not in {f"routeField{index}" for index in range(count)}:
            raise HTTPException(422, "回款筛选字段无效")
        index = int(key.removeprefix("routeField"))
        if value is None or value == "" or (isinstance(value, str) and value in ("请选择", "全部")):
            continue
        if index == date_index:
            if not isinstance(value, list) or len(value) != 2:
                raise HTTPException(422, "回款日期筛选必须为两个日期的数组")
            for day in value:
                if day is None or day == "":
                    continue
                try:
                    if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
                        raise ValueError
                except ValueError as exc:
                    raise HTTPException(422, "回款日期必须为 YYYY-MM-DD") from exc
        elif index in enums:
            if not isinstance(value, str) or value not in enums[index] | {"请选择", "全部"}:
                raise HTTPException(422, "回款筛选选项无效")
        elif view == QUERY_VIEW and index == 10 and isinstance(value, list):
            if any(not isinstance(part, str) for part in value):
                raise HTTPException(422, "费用类型筛选必须为文字或文字数组")
        elif not isinstance(value, str):
            raise HTTPException(422, "回款文字筛选条件无效")
    return values


def incoming_customer_fields(item, customers_by_title: dict, users_by_username: dict) -> dict:
    customer = customers_by_title.get(item.claimed_customer.strip())
    if not customer:
        return {"customer_manager": "", "customer_manager_display_name": ""}
    managers = _contract_person_values((customer.data or {}).get("customer_managers") or [customer.owner])
    return {
        "customer_manager": "、".join(managers),
        "customer_manager_display_name": "、".join(
            _person_reference_display(value, users_by_username)[0] for value in managers
        ),
    }


async def incoming_customers(items, db) -> dict:
    titles = {item.claimed_customer.strip() for item in items if item.claimed_customer.strip()}
    if not titles:
        return {}
    rows = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "customer", BusinessRecord.title.in_(titles),
    ))).all()
    return {row.title.strip(): row for row in rows}


def matches_incoming_filters(item, view: str, filters: dict, customers: dict, users: dict) -> bool:
    # 回款响应没有 data；不能把缺失的前端筛选字段擅自改为顶层同名字段。
    if view in BANK_VIEWS:
        raw_values = [item.payer_name, None, None, item.status]
        date_index, enum_indexes = 2, {3}
    elif view in RECEIPT_VIEWS:
        raw_values = [item.received_date, item.bank_reference, item.claimed_customer,
                      item.payer_name, None, _incoming_payment_legacy_summary(item)["contract_no"]]
        date_index, enum_indexes = 0, set()
    else:
        manager = incoming_customer_fields(item, customers, users)["customer_manager_display_name"] or "—"
        raw_values = [None, "—", "—", "—", manager, "—", item.claimed_customer,
                      item.payer_name, None, item.received_date, None, None]
        date_index, enum_indexes = 9, {8, 11}
    for key, value in filters.items():
        if value is None or value == "" or value in ("请选择", "全部"):
            continue
        index = int(key.removeprefix("routeField"))
        raw = raw_values[index]
        if index == date_index:
            start, end = value
            if not start and not end:
                continue
            if raw is None or (start and raw < date.fromisoformat(start)) or (end and raw > date.fromisoformat(end)):
                return False
        elif view == QUERY_VIEW and index == 10:
            selected = value if isinstance(value, list) else value.split(",")
            if isinstance(value, list) and ",".join(value) in ("", "请选择", "全部"):
                continue
            if selected:
                return False
        elif raw is None:
            return False
        elif index in enum_indexes:
            if str(raw) != value:
                return False
        elif value.strip(JS_WHITESPACE).lower() not in str(raw).lower():
            return False
    return True


def incoming_summary(items, show_amount: bool) -> dict:
    return {
        "total": len(items),
        "unclaimed": sum(1 for item in items if item.status == "待认领"),
        "unallocated": sum(1 for item in items if item.status in {"待分配", "部分分配"}),
        "completed": sum(1 for item in items if item.status == "已分配"),
        "amount": sum(item.amount for item in items) if show_amount else None,
        "remaining": sum(max(item.amount - item.allocated_amount, 0) for item in items) if show_amount else None,
    }


def incoming_totals(items, show_amount: bool) -> dict:
    if items and not show_amount:
        return dict.fromkeys(TOTAL_FIELDS, None)
    cents = dict.fromkeys(TOTAL_FIELDS, 0.0)
    for item in items:
        allocated = float(item.allocated_amount or 0)
        if allocated <= 0 and item.allocations:
            allocated = _round_fee_amount(sum(
                float(allocation.get("amount") or 0)
                for allocation in item.allocations if isinstance(allocation, dict)
            ))
        amounts = {
            "amount": float(item.amount), "allocated_amount": allocated,
            "remaining_amount": max(float(item.amount) - allocated, 0),
            **_incoming_payment_legacy_summary(item),
        }
        for header, field in TOTAL_FIELDS.items():
            if amounts[field] is None:
                cents[header] = None
                continue
            if cents[header] is None:
                continue
            number = float(amounts[field]) * 100
            whole = math.floor(number)
            # JavaScript Math.round 的半分向正无穷取整，不使用 Python 银行家舍入。
            cents[header] += whole + (number - whole >= 0.5)
    return {header: amount / 100 if amount is not None else None for header, amount in cents.items()}


async def read_incoming_query(statement, keyword: str, view: str, filters: dict,
                              page: int | None, page_size: int | None,
                              show_amount: bool, users: dict, db) -> dict:
    projection = statement.with_only_columns(
        IncomingPayment.id, IncomingPayment.received_date, IncomingPayment.receipt_no,
        IncomingPayment.amount, IncomingPayment.allocated_amount, IncomingPayment.status,
        IncomingPayment.payer_name, IncomingPayment.bank_reference, IncomingPayment.claimed_customer,
        IncomingPayment.contract_no, IncomingPayment.allocations, IncomingPayment.source_kind,
        IncomingPayment.remark, IncomingPayment.bank_source,
        IncomingPayment.contract_record_id, IncomingPayment.case_no,
        IncomingPayment.claimant, IncomingPayment.operator,
        IncomingPayment.created_at, IncomingPayment.updated_at,
        IncomingPayment.finance_scope,
        IncomingPayment.payment_method,
        IncomingPayment.local_allocation_summary,
        INCOMING_CENTER.label("resolved_finance_scope"),
        LEGACY_INCOMING_SOURCE.c.payment_method.label("legacy_payment_method"),
        LEGACY_INCOMING_SOURCE.c.settlement_status.label("legacy_settlement_status"),
        *(LEGACY_ASSIGNED_AMOUNTS.c[field].label("legacy_" + field) for field in ASSIGNED_FIELDS),
        LEGACY_ASSIGNED_AMOUNTS.c.baseline_allocations.label("legacy_baseline_allocations"),
        LEGACY_ASSIGNED_AMOUNTS.c.baseline_applied_amount.label("legacy_baseline_applied_amount"),
    ).order_by(IncomingPayment.received_date.desc(), IncomingPayment.id.desc())
    items = list((await db.execute(projection)).all())
    if keyword:
        key = keyword.casefold()
        items = [item for item in items if key in f"{item.receipt_no} {item.payer_name} {item.bank_reference} {item.claimed_customer}".casefold()]
    if view in BANK_VIEWS:
        bank = view.removeprefix("finance-receipts-")
        names = {"icbc": ("工行", "工商银行"), "citic": ("中信",),
                 "boc": ("中行", "中国银行"), "cmb": ("招商", "招行")}
        items = [item for item in items if (item.bank_source or "").strip(JS_WHITESPACE).lower() == bank
                 or any(name in (item.bank_source or "").strip(JS_WHITESPACE).lower() for name in names[bank])]
    if view in VIEW_STATUSES:
        items = [item for item in items if item.status in VIEW_STATUSES[view]]
    customers = await incoming_customers(items, db) if view == QUERY_VIEW and filters.get("routeField4") not in (None, "", "请选择", "全部") else {}
    if filters:
        items = [item for item in items if matches_incoming_filters(item, view, filters, customers, users)]
    result = {"total": len(items), "summary": incoming_summary(items, show_amount),
              "totals": incoming_totals(items, show_amount)}
    paginated = page is not None or page_size is not None
    if paginated:
        page = page if page is not None else 1
        page_size = page_size if page_size is not None else 20
        items = items[(page - 1) * page_size:page * page_size]
        result.update(page=page, page_size=page_size)
    # 明细与汇总来自同一次回款读取，避免分页后再次读取导致并发更新口径不一致。
    result["items"] = items
    result["customers"] = await incoming_customers(items, db)
    return result
