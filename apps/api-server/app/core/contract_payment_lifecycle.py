"""Contract payment mutations share one transaction and one contract lock."""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import OperationalError

from app.models import BusinessRecord, ContractPaymentLine, FinanceTransaction, User, WorkflowEvent
from app.models_shared import ContractPaymentApplicationInput, ContractPaymentLineInput


EDITABLE_STATUSES = {"草稿", "待提交", "创建待提交", "已驳回", "已退回"}
ACTIVE_STATUSES = {"待审批", "待付款", "已付款", "已核销"}


async def lock_contract(contract_id, identity, db):
    from app.core.permissions import _ensure_record_module
    await _ensure_record_module(contract_id, "contract", identity, db)
    # A no-op UPDATE also serializes writers on SQLite, which ignores FOR UPDATE.
    try:
        await db.execute(update(BusinessRecord).where(
            BusinessRecord.id == contract_id, BusinessRecord.module == "contract",
        ).values(id=BusinessRecord.id, updated_at=BusinessRecord.updated_at).execution_options(synchronize_session=False))
    except OperationalError as exc:
        if "locked" in str(exc.orig).lower() or getattr(exc.orig, "sqlstate", None) in {"40001", "40P01"}:
            raise HTTPException(409, "合同付款正在被其他操作修改，请刷新后重试") from exc
        raise
    return await db.scalar(select(BusinessRecord).where(
        BusinessRecord.id == contract_id,
    ).execution_options(populate_existing=True).with_for_update())


async def locked_payment(payment_id, identity, db, *, lock=True):
    from app.core.permissions import _ensure_record_module
    payment = await _ensure_record_module(payment_id, "contract_payment", identity, db)
    data = payment.data or {}
    contract_id = data.get("contract_id") or data.get("contract_record_id")
    if not contract_id:
        contract_id = await db.scalar(select(BusinessRecord.id).where(
            BusinessRecord.module == "contract", BusinessRecord.serial_no == data.get("contract_no"),
        ))
    if not contract_id:
        raise HTTPException(409, "合同付款缺少有效合同关联")
    contract = await lock_contract(int(contract_id), identity, db) if lock else await _ensure_record_module(int(contract_id), "contract", identity, db)
    if lock:
        payment = await db.scalar(select(BusinessRecord).where(
            BusinessRecord.id == payment_id, BusinessRecord.module == "contract_payment",
        ).execution_options(populate_existing=True).with_for_update())
    if not payment:
        raise HTTPException(404, "合同付款不存在")
    from app.core.finance import _fee_matches_contract
    if not _fee_matches_contract(payment, contract):
        raise HTTPException(409, "付款合同关联已变化，请刷新后重试")
    return payment, contract


async def ensure_unsettled(payment, db):
    data = payment.data or {}
    if (payment.status in {"已付款", "已核销", "待核销"}
            or data.get("writeoff_status") == "已核销"
            or data.get("paid_date") or data.get("written_off_at")
            or float(data.get("paid_amount") or 0) > 0):
        raise HTTPException(409, "已有支付或核销的合同付款不能修改、撤销或回滚")
    transaction = await db.scalar(select(FinanceTransaction.id).where(
        FinanceTransaction.finance_record_id == payment.id,
        FinanceTransaction.transaction_type.in_(["合同付款", "付款", "核销"]),
    ).limit(1))
    if transaction:
        raise HTTPException(409, "合同付款已存在支付或核销流水，不能重复办理")


def ensure_editable(payment):
    if payment.status not in EDITABLE_STATUSES:
        raise HTTPException(409, "仅待提交或已驳回的合同付款可以编辑和重新提交")


def line_key(line):
    return ("case_fee", line.case_fee_id) if line.case_fee_id else ("contract_object", line.contract_object_id)


async def payment_candidates(contract, identity, db, payment=None):
    from app.core.finance import _contract_payment_candidate_rows, _round_fee_amount
    rows = await _contract_payment_candidate_rows(contract, identity, db)
    if not payment or payment.status not in ACTIVE_STATUSES:
        return rows
    own = {}
    for line in (payment.data or {}).get("lines", []):
        if line.get("case_fee_id"):
            key = ("case_fee", int(line["case_fee_id"]))
            own[key] = own.get(key, 0) + float(line.get("amount") or 0)
    for line in (await db.scalars(select(ContractPaymentLine).where(
        ContractPaymentLine.payment_record_id == payment.id,
    ))).all():
        key = ("contract_object", line.contract_object_id)
        own[key] = own.get(key, 0) + line.requested_amount
    for row in rows:
        key = ("case_fee", row["case_fee_id"]) if row.get("case_fee_id") else ("contract_object", row["contract_object_id"])
        reserved = max(_round_fee_amount(row["reserved_amount"] - own.get(key, 0)), 0)
        row.update(reserved_amount=reserved, remaining_amount=max(_round_fee_amount(row["contract_amount"] - reserved), 0))
    return rows


async def normalized_payment(body, contract, identity, db, payment=None):
    from app.core.contracts import _contract_allows_finance_application
    from app.core.finance import _active_payment_type, _finance_payment_type_dict, _round_fee_amount
    if not _contract_allows_finance_application(contract):
        raise HTTPException(409, "归档或已终止合同不能发起合同付款")
    if any(line.case_fee_id and line.contract_object_id for line in body.lines):
        raise HTTPException(422, "每条付款明细只能选择案件费用或合同标的之一")
    if len({line_key(line) for line in body.lines}) != len(body.lines):
        raise HTTPException(422, "同一费用只能提交一次")
    # Fee writers also contend on these rows; always acquire them in ID order.
    fee_ids = sorted({line.case_fee_id for line in body.lines if line.case_fee_id})
    if fee_ids:
        await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(fee_ids)).order_by(
            BusinessRecord.id,
        ).with_for_update().execution_options(populate_existing=True))
    payment_type = await _active_payment_type(body.payment_type_id, db)
    type_data = _finance_payment_type_dict(payment_type)
    rows = await payment_candidates(contract, identity, db, payment)
    candidates = {
        ("case_fee", row["case_fee_id"]) if row.get("case_fee_id") else ("contract_object", row["contract_object_id"]): row
        for row in rows
    }
    snapshot = []
    for line in body.lines:
        candidate = candidates.get(line_key(line))
        if not candidate:
            raise HTTPException(404, "付款费用不存在、不属于该合同或无权访问")
        amount = _round_fee_amount(line.amount)
        if amount <= 0 or amount > candidate["remaining_amount"] + 0.0001:
            raise HTTPException(422, "本次支付金额不能超过扣除其他申请后的待付余额")
        case_record = await db.get(BusinessRecord, candidate["case_record_id"])
        snapshot.append({
            "contract_object_id": candidate.get("contract_object_id"),
            "case_fee_id": candidate.get("case_fee_id"), "case_id": candidate["case_record_id"],
            "case_no": candidate["case_no"], "fee_type": candidate["fee_type"],
            "amount": amount, "remark": line.remark.strip(),
            "case_stage": str((case_record.data or {}).get("case_stage") or (case_record.data or {}).get("stage") or ""),
        })
    return {
        "payment_type_id": payment_type.id, "payment_type_code": payment_type.code,
        "payment_type": payment_type.name, "payment_nature": type_data["nature"],
        "payee": type_data["payee"], "account_bank": type_data["account_bank"], "account": type_data["account"],
        "payer_name": body.payer_name.strip() or contract.customer,
        "application_date": body.application_date.isoformat(), "remark": body.remark.strip(),
        "amount": _round_fee_amount(sum(line["amount"] for line in snapshot)), "lines": snapshot,
    }


def payment_input(payment):
    data = payment.data or {}
    try:
        return ContractPaymentApplicationInput(
            payment_type_id=data.get("payment_type_id"), payer_name=data.get("payer_name") or "",
            application_date=data.get("application_date"), remark=payment.description or "",
            lines=[ContractPaymentLineInput(
                case_fee_id=line.get("case_fee_id"),
                contract_object_id=None if line.get("case_fee_id") else line.get("contract_object_id"),
                amount=line.get("amount"), remark=line.get("remark") or "",
            ) for line in data.get("lines", [])],
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, "原付款资料不完整，请编辑补全后重新提交") from exc


async def replace_payment_details(payment, normalized, db):
    existing = {line.contract_object_id: line for line in (await db.scalars(select(ContractPaymentLine).where(
        ContractPaymentLine.payment_record_id == payment.id,
    ))).all()}
    for line in normalized["lines"]:
        if not line.get("case_fee_id") and line.get("contract_object_id"):
            detail = existing.pop(line["contract_object_id"], None)
            if detail is None:
                detail = ContractPaymentLine(payment_record_id=payment.id, contract_object_id=line["contract_object_id"])
                db.add(detail)
            detail.case_record_id = line["case_id"]
            detail.fee_type = line["fee_type"]
            detail.requested_amount = line["amount"]
    for obsolete in existing.values():
        await db.delete(obsolete)
    payment.data = {**(payment.data or {}), **normalized}
    payment.description = normalized["remark"]


def payment_event(payment, action, previous, identity, comment="", before=None):
    import json
    detail = {"comment": comment, "serial_no": payment.serial_no, "contract_id": (payment.data or {}).get("contract_id"),
              "audit_round": (payment.data or {}).get("audit_round", 1), "after": payment.data or {}}
    if before is not None:
        detail["before"] = before
    return WorkflowEvent(record_id=payment.id, action=action, from_status=previous,
                         to_status=payment.status, operator=identity["username"],
                         comment=json.dumps(detail, ensure_ascii=False, default=str))


async def change_payment_state(payment_id, operation, comment, identity, db):
    from app.core.permissions import _record_dict_for_identity, _require_contract_action, _require_record_owner_or_manager
    await _require_contract_action(identity, db,
        "contract.payment.approve" if operation == "rollback" else "contract.payment.create", "办理合同付款")
    payment, contract = await locked_payment(payment_id, identity, db)
    if operation != "rollback":
        await _require_record_owner_or_manager(payment, identity, db)
    await ensure_unsettled(payment, db)
    previous = payment.status
    before = dict(payment.data or {})
    targets = {"submit": "待审批", "cancel": "已撤回", "rollback": "待提交"}
    if operation == "cancel" and not comment.strip():
        raise HTTPException(422, "请输入撤回原因")
    if previous == targets[operation]:
        return await _record_dict_for_identity(payment, identity, db)
    if operation == "submit":
        ensure_editable(payment)
        normalized = await normalized_payment(payment_input(payment), contract, identity, db, payment)
        await replace_payment_details(payment, normalized, db)
        payment.data = {**payment.data, "audit_round": int(before.get("audit_round") or 1) + 1,
                        "submitted_by": identity["username"], "submitted_at": datetime.now().isoformat()}
    elif operation == "cancel":
        if previous not in EDITABLE_STATUSES | {"待审批"}:
            raise HTTPException(409, "当前合同付款状态不能撤销，请使用回滚")
        payment.data = {**before, "cancel_reason": comment.strip(), "canceled_by": identity["username"],
                        "canceled_at": datetime.now().isoformat()}
    else:
        if previous not in {"待审批", "待付款"}:
            raise HTTPException(409, "仅待审批或待付款的合同付款可以回滚")
        payment.data = {**before, "rollback_comment": comment.strip(), "rolled_back_by": identity["username"],
                        "rolled_back_at": datetime.now().isoformat(), "package_no": ""}
    payment.status = targets[operation]
    payment.data = {**payment.data, "payment_status": "创建待提交" if operation == "rollback" else payment.status}
    db.add(payment_event(payment, {"submit": "重新提交合同付款申请", "cancel": "合同付款申请撤回", "rollback": "合同付款申请回滚"}[operation], previous, identity, comment.strip(), before))
    await db.commit()
    await db.refresh(payment)
    return await _record_dict_for_identity(payment, identity, db)


def payment_query_line_match(record, key, value, dialect):
    from sqlalchemy import JSON, case, cast, func, literal, type_coerce
    raw = record.data["lines"]
    if dialect == "postgresql":
        safe_array = case((func.json_typeof(raw) == "array", raw), else_=cast(literal("[]"), JSON))
        elements = func.json_array_elements(safe_array).table_valued("value").alias("payment_line")
    else:
        safe_array = case((func.json_type(raw) == "array", raw), else_=literal("[]"))
        elements = func.json_each(safe_array).table_valued("value").alias("payment_line")
    field = type_coerce(elements.c.value, JSON)[key].as_string()
    return select(1).select_from(elements).where(field.ilike(f"%{value}%")).correlate(record).exists()


def payment_query_amount(record, dialect):
    from sqlalchemy import Float, String, case, cast, func
    value = func.trim(cast(record.data["amount"].as_string(), String))
    if dialect == "postgresql":
        # Cast only validated decimal text: historical JSON can contain "" or non-numbers.
        value = case((value.op("~")(r"^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)$"), value), else_=None)
    return cast(func.nullif(value, ""), Float)


async def query_payments(filters, identity, db):
    from sqlalchemy import String, and_, case, cast, func, or_
    from app.core.permissions import _record_scope_conditions, _require_record_module_menu
    from app.core.system import _allowed_field_keys
    from app.core.contracts import _contract_customer_record_dicts
    await _require_record_module_menu("finance", identity, db, action="查询请款")
    record = BusinessRecord
    data = record.data
    legacy_kind = func.coalesce(data["legacy_kind"].as_string(), "")
    conditions = [or_(record.module == "contract_payment", and_(
        record.module == "finance", legacy_kind.in_(["", "ap_payment"]),
    )), *(await _record_scope_conditions(identity, db))]
    scope = filters.get("scope", "all")
    applicant_value = func.coalesce(func.nullif(data["applicant"].as_string(), ""), record.owner)
    if scope == "mine":
        conditions.append(applicant_value == identity["username"])
    elif scope == "department":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if not user:
            raise HTTPException(401, "当前用户不存在")
        conditions.append(record.department == user.department)
    elif scope == "audit":
        conditions.append(record.status == "待审批")
    finance_scope = filters.get("finance_scope") or (scope if scope in {"firm", "platform"} else "")
    if finance_scope:
        computed_scope = func.coalesce(func.nullif(data["finance_scope"].as_string(), ""), case(
            (or_(data["accounting_center"].as_string() == "平台财务中心", data["contract_body"].as_string() == "平台"), "platform"),
            else_="firm",
        ))
        conditions.append(computed_scope == finance_scope)
    if filters.get("keyword"):
        conditions.append(record.serial_no.ilike(f"%{filters['keyword'].strip()}%"))
    display_status = func.coalesce(func.nullif(data["payment_status"].as_string(), ""), case(
        (data["writeoff_status"].as_string() == "待核销", "待核销"),
        (record.status.in_(["草稿", "待提交"]), "创建待提交"),
        (record.status.in_(["已审批", "部分付款"]), "待付款"),
        (record.status == "已退回", "已驳回"), else_=record.status,
    ))
    selected_statuses = [value.strip() for value in filters.get("statuses", "").split(",") if value.strip()]
    if filters.get("record_status"):
        selected_statuses.append(filters["record_status"].strip())
    if selected_statuses:
        conditions.append(or_(record.status.in_(selected_statuses), display_status.in_(selected_statuses)))
    tx_conditions = [FinanceTransaction.finance_record_id == record.id,
                     FinanceTransaction.transaction_type.in_(["付款", "合同付款"])]
    def latest_transaction(column):
        return select(column).where(*tx_conditions).order_by(
            FinanceTransaction.transaction_date.desc(), FinanceTransaction.id.desc(),
        ).limit(1).correlate(record).scalar_subquery()

    def line_matches(key, value):
        return payment_query_line_match(record, key, value, db.get_bind().dialect.name)

    for key, column in {
        "applicant": applicant_value, "contract_no": data["contract_no"].as_string(),
        "customer": record.customer, "title": record.title,
        "handler": func.coalesce(func.nullif(data["handler"].as_string(), ""), record.owner),
        "payee": func.coalesce(func.nullif(data["payee"].as_string(), ""), latest_transaction(FinanceTransaction.counterparty)),
    }.items():
        value = str(filters.get(key) or "").strip()
        if value:
            conditions.append(column.ilike(f"%{value}%"))
    for key, value in {"case_no": filters.get("case_no"), "fee_type": filters.get("fee_type"),
                       "case_stage": filters.get("case_stage") or filters.get("stage")}.items():
        if value and str(value).strip():
            value = str(value).strip()
            conditions.append(or_(data[key].as_string().ilike(f"%{value}%"),
                                  and_(record.module == "contract_payment", line_matches(key, value))))
    date_columns = {
        "application_date": func.coalesce(func.nullif(data["application_date"].as_string(), ""), cast(record.created_at, String)),
        "payment_date": latest_transaction(FinanceTransaction.transaction_date),
        "deadline": func.coalesce(func.nullif(data["deadline"].as_string(), ""), data["due_date"].as_string()),
        "audit_date": select(func.max(WorkflowEvent.created_at)).where(
            WorkflowEvent.record_id == record.id, WorkflowEvent.action.in_([
                "合同付款审批通过", "合同付款审批驳回", "费用审批通过", "费用审批驳回",
            ]),
        ).correlate(record).scalar_subquery(),
    }
    from datetime import date
    for key, column in date_columns.items():
        for suffix, lower in [("start", True), ("end", False)]:
            value = filters.get(f"{key}_{suffix}")
            if value:
                try:
                    day = date.fromisoformat(str(value)).isoformat()
                except ValueError as exc:
                    raise HTTPException(422, "日期筛选必须为 YYYY-MM-DD") from exc
                expression = func.substr(cast(column, String), 1, 10)
                conditions.append(expression >= day if lower else expression <= day)
    page, page_size = int(filters.get("page", 1)), int(filters.get("page_size", 20))
    if page < 1 or not 1 <= page_size <= 500:
        raise HTTPException(422, "分页参数超出有效范围")
    total = int(await db.scalar(select(func.count(record.id)).where(*conditions)) or 0)
    allowed = await _allowed_field_keys(identity, db)
    totals = {}
    if allowed is None or "finance.amount" in allowed:
        amount = await db.scalar(select(func.coalesce(func.sum(payment_query_amount(record, db.get_bind().dialect.name)), 0)).where(*conditions))
        totals = {"amount": round(float(amount or 0), 2)}
    rows = list((await db.scalars(select(record).where(*conditions).order_by(
        record.created_at.desc(), record.id.desc(),
    ).offset((page - 1) * page_size).limit(page_size))).all())
    return {"items": await _contract_customer_record_dicts(rows, allowed, db, identity=identity),
            "total": total, "page": page, "page_size": page_size, "totals": totals}
