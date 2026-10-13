"""先核对任务规则和费用主数据，再生成待确认操作；不执行业务写入。"""

from copy import deepcopy

from fastapi import HTTPException
from sqlalchemy import select

from app.api_schemas.finance import FinanceFeeInput
from app.core.task_lifecycle_policy import validate_task_lifecycle
from app.models import BusinessRecord, SystemParameter


async def _resolve_fee_arguments(arguments, params, identity, db):
    from app.areas.finance.fee_draft_preparation import prepare_finance_fee_draft
    from app.core.finance import _fee_type_catalog, _finance_linked_case, _resolve_case_fee_type_master
    from app.core.permissions import _ensure_record_visible

    body = dict(params["body"])
    case = await _finance_linked_case(body.get("case_no", ""), identity, db)
    if body.get("case_record_id"):
        selected_case = await _ensure_record_visible(body["case_record_id"], identity, db)
        if selected_case.module != "case":
            raise HTTPException(422, "关联记录不是案件")
        if case and selected_case.id != case.id:
            raise HTTPException(409, "案件编号与案件记录不一致")
        case = selected_case
    items = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "fee_type",
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all())
    catalog = _fee_type_catalog(items)
    name = str(body.get("expense_subtype") or body["fee_type"]).strip()
    fee_id = body.get("fee_type_id")
    if not fee_id:
        candidates = [row for row in catalog if row["selectable"] and name in {
            row["name"], row["code"], row["path"], *row["historical_names"],
        } and (not body.get("expense_scope") or body["expense_scope"] in row["expense_scopes"])]
        if case:
            case_type = str((case.data or {}).get("case_type_code") or (case.data or {}).get("case_type_id") or "")
            by_id = {item.id: item for item in items}
            candidates = [row for row in candidates if not (by_id[row["id"]].extra or {}).get("case_type_code")
                          or str(by_id[row["id"]].extra["case_type_code"]) == case_type]
            specific = [row for row in candidates if case_type and
                        str((by_id[row["id"]].extra or {}).get("case_type_code") or "") == case_type]
            if specific:
                candidates = specific
        if not candidates:
            raise HTTPException(422, f"系统费用目录中没有可用的末级类型：{name}")
        if len(candidates) != 1:
            raise HTTPException(422, {"detail": "费用类型名称存在多个有效分类，请明确类型或归属后再确认",
                                      "options": [{"id": row["id"], "path": row["path"]} for row in candidates]})
        fee_id = candidates[0]["id"]
    item, option = await _resolve_case_fee_type_master(fee_id, body.get("expense_scope"), db)
    accepted_names = {item.name, item.code, option["path"], option["base_fee_type"], *option.get("historical_names", [])}
    if name not in accepted_names:
        raise HTTPException(422, "费用类型名称与选择的系统分类不一致")
    body.update(fee_type_id=item.id, fee_type=option["base_fee_type"], expense_subtype=item.name)
    prepared = FinanceFeeInput.model_validate(body)
    await prepare_finance_fee_draft(prepared, identity, db)
    return {**deepcopy(arguments), "body": body}


async def prepare_business_arguments(spec, arguments, params, identity, db):
    endpoint = spec._route.endpoint
    if endpoint.__module__ == "app.areas.finance.router" and endpoint.__name__ == "create_finance_fee":
        return await _resolve_fee_arguments(arguments, params, identity, db)
    if endpoint.__module__ != "app.areas.tp.router":
        return arguments
    name = endpoint.__name__
    if name in {"withdraw_task", "complete_task"}:
        action = "withdraw" if name == "withdraw_task" else "complete"
        task_ids = [params["path"]["task_id"]]
    elif name == "batch_lifecycle_tasks" and params["body"]["action"] in {"withdraw", "complete"}:
        action = params["body"]["action"]
        task_ids = list(dict.fromkeys(params["body"]["task_ids"]))
    else:
        return arguments
    tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task", BusinessRecord.id.in_(task_ids),
    ))).all())
    if len(tasks) != len(task_ids):
        raise HTTPException(404, "部分任务不存在")
    by_id = {task.id: task for task in tasks}
    for task_id in task_ids:
        validate_task_lifecycle(by_id[task_id], identity, action, params["body"].get("comment", ""))
    return arguments
