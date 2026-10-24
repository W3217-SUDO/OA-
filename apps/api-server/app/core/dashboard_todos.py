"""控制台待办统计，任务生命周期与原任务中心保持一致。"""
from app.core.dependencies import BusinessRecord, ContractApprovalStep, select, func, and_, or_
from app.core.record_json_text_query import projected_record_condition, record_json_text_projection
from app.core.cases import _case_action_granted
from app.core.documents import _seal_authorization_context
from app.core.investigation import _is_investigation_task
from app.core.tasks import _task_dict
from app.core.dashboard import dashboard_scope


async def dashboard_todos(identity, db, *, record_scope=None):
    scope, modules = await dashboard_scope(identity, db, record_scope=record_scope)
    username = identity["username"]
    pending_statuses = {"待审批", "审批中", "待审核"}
    tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task", *scope,
        or_(BusinessRecord.owner == username,
            func.trim(BusinessRecord.data["initiator"].as_string()) == username),
    ))).all()) if "task" in modules else []
    clue_counts = dict((await db.execute(select(BusinessRecord.status, func.count()).where(
        BusinessRecord.module.in_(modules & {"clue"}), *scope,
    ).group_by(BusinessRecord.status))).all())
    labels = [("待处理任务", "待审批官方费用"), ("待审批线索", "待审批内部费用"),
              ("待审批合同", "待审批结算费用"), ("待审批用印", "待归档费用"),
              ("待审核归档", "待审核预损费用")]
    # 控制台数字口径（用户 2026-10-23 确认）：右列五张卡片 = 点进去那个列表的总数，
    # 复用列表查询函数计数（dashboard_list_counts），不再按费用类型文字统计本人名下费用。
    from app.core import dashboard_list_counts as list_counts
    archive_action_allowed = await _case_action_granted(identity, db, "case.archive.review")
    # 各卡片计数互不依赖，独立只读会话并行计算（性能：原先串行约 5–8 秒）。
    list_totals = await list_counts.gather_counts(db, {
        "待审批官方费用": lambda session: list_counts.payment_audit_total(identity, session),
        "待审批内部费用": lambda session: list_counts.internal_review_total(identity, session, "other"),
        "待审批结算费用": lambda session: list_counts.settlement_audit_total(identity, session),
        "待归档费用": lambda session: list_counts.archive_fee_pending_total(identity, session),
        # Q2(a)：库里没有“预损”费用，对应归档里的“亏损内审”案件，点进去是“亏损内审”标签。
        "待审核预损费用": lambda session: list_counts.archive_queue_total(identity, session, "loss_internal"),
        **({"待审核归档": lambda session: list_counts.archive_queue_total(identity, session, "pending")}
           if archive_action_allowed else {}),
    })
    right_counts = {name: list_totals[name] for name in (
        "待审批官方费用", "待审批内部费用", "待审批结算费用", "待归档费用", "待审核预损费用")}
    todos = [[left, 0, 0, right, right_counts[right], right_counts[right]] for left, right in labels]
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
        # 未接收的任务不会被自动完成，计数使用任务中心相同的展示状态。
        return _task_dict(item)["status"] in {"待接收", "待处理"}
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
            clue_counts.get("待审批", 0),
            clue_counts.get("已驳回", 0) + clue_counts.get("已拒绝", 0),
        ),
        "待审批用印": (0, 0),
        "待审核归档": (0, 0),
    }
    # 待审批合同范围留在数据库内，避免先读取全部编号再展开计数参数。
    pending_contract_ids = select(ContractApprovalStep.contract_record_id).where(
        ContractApprovalStep.approver == username,
        ContractApprovalStep.status == "待审批",
    )
    personal_todo_counts["待审批合同"] = (
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "contract",
            BusinessRecord.id.in_(pending_contract_ids),
            BusinessRecord.status.in_(pending_statuses),
        )) or 0),
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

    # 本函数没有业务写入，归档计数沿用本次调用已读取的同账号权限范围。
    archive_scope = scope
    archive_projection, archive_data = record_json_text_projection(db, (
        "archive_submitter", "archive_reviewer", "archive_internal_reviewer", "archive_reject_reason",
    ))
    archive_submitter = func.trim(func.coalesce(archive_data["archive_submitter"], ""))
    # 待审核归档 = 归档“待审核归档”标签总数（状态 待归档审核/归档审核；管理员看全部，其他人按审核人分配），
    # 与点进去的列表同一查询；亏损内审、亏损审核在各自标签，不计入本卡（Q1）。
    personal_todo_counts["待审核归档"] = (
        list_totals.get("待审核归档", 0),
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "case",
            projected_record_condition(archive_projection, and_(
                archive_submitter == username,
                or_(
                    BusinessRecord.status == "亏损归档拒绝",
                    func.trim(func.coalesce(archive_data["archive_reject_reason"], "")) != "",
                ),
            )),
            *archive_scope,
        )) or 0),
    )
    for todo in todos:
        if todo[0] in personal_todo_counts:
            todo[1], todo[2] = personal_todo_counts[todo[0]]
    return {"todos": todos}
