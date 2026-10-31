"""控制台待办统计，任务生命周期与原任务中心保持一致。"""
from app.core.dependencies import BusinessRecord, ContractApprovalStep, select, func, or_
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
    # 旧系统“待审批线索”= 线索审批列表（PageId 1401004001）里待审批的条数，按线索审批范围（客户管理人/协作人/线索审批岗）计。
    from app.core.clue_audit_scope import clue_audit_condition
    pending_clue_reviews = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
        BusinessRecord.status == "待审批", await clue_audit_condition(identity, db),
    )) or 0) if "clue" in modules else 0
    labels = [("待处理任务", "待审批官方费用"), ("待审批线索", "待审批内部费用"),
              ("待审批合同", "待审批结算费用"), ("待审批用印", "待归档费用"),
              ("待审核归档", "待审核预损费用")]
    # 控制台数字口径（用户 2026-10-23 确认）：右列五张卡片 = 点进去那个列表的总数，
    # 复用列表查询函数计数（dashboard_list_counts），不再按费用类型文字统计本人名下费用。
    from app.core import dashboard_list_counts as list_counts
    archive_action_allowed = await _case_action_granted(identity, db, "case.archive.review")
    # 各卡片计数互不依赖，独立只读会话并行计算（性能：原先串行约 5–8 秒）。
    list_totals = await list_counts.gather_counts(db, {
        "待审批官方费用": lambda session: list_counts.payment_audit_official_total(identity, session),
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
    rejected = await legacy_rejected_counts(identity, db)
    todos = [[left, 0, rejected.get(left, 0), right, right_counts[right], rejected.get(right, 0)] for left, right in labels]
    # 旧系统每行两列：蓝色是待我审批，橙色是被驳回；橙色的范围见 REJECTED_COUNT_SCOPE。
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
        "待审批合同": (0, rejected["待审批合同"]),
        "待审批线索": (
            pending_clue_reviews,
            clue_counts.get("已驳回", 0) + clue_counts.get("已拒绝", 0),
        ),
        "待审批用印": (0, rejected["待审批用印"]),
        "待审核归档": (0, rejected["待审核归档"]),
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
        rejected["待审批合同"],
    )

    seal_context = await _seal_authorization_context(identity, db)
    seal_approver = func.trim(func.coalesce(BusinessRecord.data["approver"].as_string(), ""))
    personal_todo_counts["待审批用印"] = (
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "seal",
            BusinessRecord.status == "待审批",
            or_(seal_approver == "", seal_approver == username),
        )) or 0) if seal_context["approve"] or seal_context["reject"] else 0,
        rejected["待审批用印"],
    )

    # 待审核归档 = 归档“待审核归档”标签总数（状态 待归档审核/归档审核；管理员看全部，其他人按审核人分配），
    # 与点进去的列表同一查询；亏损内审、亏损审核在各自标签，不计入本卡（Q1）。
    personal_todo_counts["待审核归档"] = (list_totals.get("待审核归档", 0), rejected["待审核归档"])
    for todo in todos:
        if todo[0] in personal_todo_counts:
            todo[1], todo[2] = personal_todo_counts[todo[0]]
    return {"todos": todos}


_table_ready: dict[tuple[int, str], bool] = {}


async def _has_table(db, name: str) -> bool:
    """只建了部分表的测试库没有旧数据表。"""
    from sqlalchemy import inspect
    key = (id(db.get_bind()), name)
    if key not in _table_ready:
        _table_ready[key] = await db.run_sync(lambda session: inspect(session.connection()).has_table(name))
    return _table_ready[key]


# 旧系统工作台橙色“被驳回”数字的范围。旧系统实际：合同按我的客户；用印、归档、亏损、结算没有按人过滤，是全公司数。
# 陶国南确认前先按本人算（"personal"）；改成 "company" 即与旧系统显示一致。
REJECTED_COUNT_SCOPE = "personal"
CIVIL_CASE_TYPES = ("民事争议", "民事案件")


async def legacy_rejected_counts(identity, db, *, scope: str | None = None) -> dict[str, int]:
    """待办表橙色列：各类被驳回的数量（旧系统 Views/Dashboard/Index.cshtml 各项的驳回列表条件）。"""
    import json
    from app.core.json_relation_query import scalar_in_values
    from app.core.permissions import _case_mine_scope_condition, _coordinated_case_condition
    from app.models import LegacyFinanceRecord

    company = (scope or REJECTED_COUNT_SCOPE) == "company"
    username = identity["username"]
    data = BusinessRecord.data

    async def count(*conditions) -> int:
        return int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions)) or 0)

    token = json.dumps(username, ensure_ascii=False)
    my_customers = (await db.execute(select(BusinessRecord.id, BusinessRecord.serial_no).where(
        BusinessRecord.module == "customer", or_(
            BusinessRecord.owner == username,
            data["customer_managers"].as_string().contains(token, autoescape=True),
            data["coordinators"].as_string().contains(token, autoescape=True),
        )))).all()
    customer_ids = {str(row.id) for row in my_customers}
    customer_nos = {str(row.serial_no) for row in my_customers if row.serial_no}
    # 合同驳回：旧系统 ContractStatus = 4，且客户协作人有我或客户 BusinessOwner 是我（这一项旧系统就是按人）。
    contract = await count(
        BusinessRecord.module == "contract", BusinessRecord.status.in_(["已拒绝", "已驳回"]),
        or_(scalar_in_values(data["customer_record_id"].as_string(), customer_ids or {""}),
            scalar_in_values(data["customer_record_id"].as_integer(), {int(value) for value in customer_ids} or {0}),
            scalar_in_values(data["customer_no"].as_string(), customer_nos or {""})),
    )
    # 用印驳回：旧用印记录迁在公文发文（official_outgoing），新系统用印在 seal。
    seal = await count(
        BusinessRecord.module.in_(["official_outgoing", "seal"]), BusinessRecord.status == "已拒绝",
        *([] if company else [or_(BusinessRecord.owner == username, data["business_owner"].as_string() == username)]),
    )
    # 归档驳回 / 亏损驳回：民事案件阶段“归档拒绝”（x06014）/“亏损拒绝”（x06019）。
    async def rejected_cases(status: str) -> int:
        conditions = [BusinessRecord.module == "case", BusinessRecord.status == status,
                      data["case_type"].as_string().in_(CIVIL_CASE_TYPES)]
        total = await count(*conditions)
        if company or not total:
            return total
        return await count(*conditions, or_(await _case_mine_scope_condition(identity, db),
                                            _coordinated_case_condition(username, db.get_bind().dialect.name)))

    archive = await rejected_cases("归档拒绝")
    loss = await rejected_cases("亏损拒绝")
    # 结算驳回：旧到账单 SettlementStatus = 30（迁在 legacy_finance_records），加新系统被驳回的结算申请。
    payload = LegacyFinanceRecord.source_payload
    legacy_settlement = int(await db.scalar(select(func.count()).select_from(LegacyFinanceRecord).where(
        LegacyFinanceRecord.source_table == "FAM_AR_Payment",
        payload["SettlementStatus"].as_string() == "30", payload["IsActived"].as_string() == "T",
        *([] if company else [payload["CreateUser"].as_string() == username]),
    )) or 0) if await _has_table(db, LegacyFinanceRecord.__tablename__) else 0
    settlement = legacy_settlement + await count(
        BusinessRecord.module == "finance_settlement", BusinessRecord.status.in_(["已拒绝", "已驳回", "已退回"]),
        *([] if company else [BusinessRecord.owner == username]),
    )
    # 官方费用请款单被驳回：旧系统按申请人（本人）。
    official = await count(BusinessRecord.module == "contract_payment", BusinessRecord.status == "已驳回",
                           BusinessRecord.owner == username)
    return {"待审批合同": contract, "待审批用印": seal, "待审核归档": archive, "待审核预损费用": loss,
            "待审批结算费用": settlement, "待审批官方费用": official}
