"""控制台待办统计，任务生命周期与原任务中心保持一致。"""
from app.core.dependencies import BusinessRecord, ContractApprovalStep, select, func, and_, or_, date
from sqlalchemy import case
from app.core.cases import _case_action_granted
from app.core.documents import _seal_authorization_context
from app.core.investigation import _is_investigation_task
from app.core.permissions import _record_scope_conditions
from app.core.tasks import _apply_task_auto_completion, _apply_task_overdue_performance, _task_dict
from app.core.dashboard import dashboard_scope, dashboard_records


async def dashboard_todos(identity, db):
    await _apply_task_auto_completion(db)
    await _apply_task_overdue_performance(db)
    scope, modules = await dashboard_scope(identity, db)
    username = identity["username"]
    pending_statuses = {"待审批", "审批中", "待审核"}
    tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task", *scope,
        or_(BusinessRecord.owner == username,
            func.trim(BusinessRecord.data["initiator"].as_string()) == username),
    ))).all()) if "task" in modules else []
    clues = await dashboard_records(db, scope, modules & {"clue"})
    fee_label = func.coalesce(func.nullif(BusinessRecord.data["fee_type"].as_string(), ""),
                              BusinessRecord.data["expense_scope"].as_string(), "")
    categories = [or_(*(fee_label.contains(word) for word in ("官方", "官费", "律所"))),
                  *(fee_label.contains(word) for word in ("内部", "结算", "归档", "预损"))]
    sums = []
    for condition in categories:
        sums.extend((func.sum(case((and_(condition, BusinessRecord.owner == username), 1), else_=0)),
                     func.sum(case((condition, 1), else_=0))))
    totals = (await db.execute(select(*sums).where(
        BusinessRecord.module.in_(modules & {"finance", "refund"}),
        BusinessRecord.status.in_(pending_statuses), *scope,
    ))).one()
    labels = [("待处理任务", "待审批官方费用"), ("待审批线索", "待审批内部费用"),
              ("待审批合同", "待审批结算费用"), ("待审批用印", "待审批归档费用"),
              ("待审核归档", "待审核预损费用")]
    todos = [[left, 0, 0, right, int(totals[i * 2] or 0), int(totals[i * 2 + 1] or 0)]
             for i, (left, right) in enumerate(labels)]
    # The legacy dashboard's blue number is the signed-in user's actionable
    # queue; the orange number is that user's rejected/returned queue.  Neither
    # number is a company-wide total, even for administrators.
    personal_tasks = [
        item for item in tasks
        if not _is_investigation_task(item)
        and (
            item.owner == username
            or str((item.data or {}).get("initiator") or "").strip() == username
        )
    ]
    def task_is_effectively_pending(item: BusinessRecord) -> bool:
        # The task centre presents an overdue task in the processing tab even
        # when the stored workflow state is still 待接收/待处理.
        if _task_dict(item)["status"] not in {"待接收", "待处理"}:
            return False
        data = item.data or {}
        if item.status != "待接收" or data.get("handoff_restarted"):
            return True
        auto_complete_at = str(data.get("handoff_auto_complete_at") or "").strip()
        if not auto_complete_at:
            return True
        try:
            return date.fromisoformat(auto_complete_at) > date.today()
        except ValueError:
            return True
    personal_todo_counts = {
        "待处理任务": (
            sum(item.owner == username and task_is_effectively_pending(item) for item in personal_tasks),
            sum(
                str((item.data or {}).get("initiator") or "").strip() == username
                and item.status == "已拒绝"
                for item in personal_tasks
            ),
        ),
        "待审批合同": (0, 0),
        "待审批线索": (
            sum(item.status == "待审批" for item in clues),
            sum(item.status in {"已驳回", "已拒绝"} for item in clues),
        ),
        "待审批用印": (0, 0),
        "待审核归档": (0, 0),
    }
    pending_contract_ids = set((await db.scalars(select(ContractApprovalStep.contract_record_id).where(
        ContractApprovalStep.approver == username,
        ContractApprovalStep.status == "待审批",
    ))).all())
    personal_todo_counts["待审批合同"] = (
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "contract",
            BusinessRecord.id.in_(pending_contract_ids),
            BusinessRecord.status.in_(pending_statuses),
        )) or 0) if pending_contract_ids else 0,
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "contract",
            BusinessRecord.owner == username,
            BusinessRecord.status.in_({"已拒绝", "已驳回"}),
        )) or 0),
    )

    seal_context = await _seal_authorization_context(identity, db)
    seal_approver = func.trim(func.coalesce(BusinessRecord.data["approver"].as_string(), ""))
    personal_todo_counts["待审批用印"] = (
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "seal",
            BusinessRecord.status == "待审批",
            or_(seal_approver == "", seal_approver == username),
        )) or 0) if seal_context["approve"] or seal_context["reject"] else 0,
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "seal",
            BusinessRecord.owner == username,
            BusinessRecord.status == "已拒绝",
        )) or 0),
    )

    archive_action_allowed = await _case_action_granted(identity, db, "case.archive.review")
    archive_scope = await _record_scope_conditions(identity, db)
    archive_submitter = func.trim(func.coalesce(BusinessRecord.data["archive_submitter"].as_string(), ""))
    archive_reviewer = func.trim(func.coalesce(BusinessRecord.data["archive_reviewer"].as_string(), ""))
    archive_internal_reviewer = func.trim(func.coalesce(BusinessRecord.data["archive_internal_reviewer"].as_string(), ""))
    archive_assigned_to_user = or_(
        archive_reviewer == username,
        archive_internal_reviewer == username,
        and_(archive_reviewer == "", archive_internal_reviewer == "", BusinessRecord.owner == username),
    )
    personal_todo_counts["待审核归档"] = (
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "case",
            BusinessRecord.status.in_({"待归档审核", "亏损内审", "亏损审核"}),
            archive_assigned_to_user,
            archive_submitter != username,
            *archive_scope,
        )) or 0) if archive_action_allowed else 0,
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "case",
            archive_submitter == username,
            or_(
                BusinessRecord.status == "亏损归档拒绝",
                func.trim(func.coalesce(BusinessRecord.data["archive_reject_reason"].as_string(), "")) != "",
            ),
            *archive_scope,
        )) or 0),
    )
    for todo in todos:
        if todo[0] in personal_todo_counts:
            todo[1], todo[2] = personal_todo_counts[todo[0]]
    return {"todos": todos}
