"""首页分端待办：律师端、财务行政端、调查端各放哪些待办，角色默认看哪个端（系统参数“首页分端待办”）。

系统管理员固定看三个端，不单独配置；其他角色按勾选显示。有多个端时用页签切换，一次只显示一个端
（用户 2026-10-26：三个端分开，一次只看一个端）；每个端的项数不限，首页一页显示 8 项，多了前端自动分页切换。待办数字口径不变：首页数字 = 点进去那个列表的总数；
已在“我的待办”和“案件与费用提醒”里统计的项直接复用那两组数字，其余项在这里按列表接口计数。
"""
from fastapi import HTTPException

CONFIG_KEY = "dashboard_portals"
# 旧的“管理端（全部待办）”勾选项，2026-10-26 起不再提供；旧配置里勾了它的角色按三个端都勾处理。
MANAGE_PORTAL = "manage"
ADMIN_ROLE_NAMES = {"系统管理员", "SYSTEM-ADMIN"}

# 待办目录：key、名称、点进去的页面、数字来源（todo=我的待办，metric=提醒指标，extra=本模块计数）、口径说明。
PORTAL_ITEMS = (
    ("task", "待处理任务", "task-my-accepted", "todo:待处理任务", "我负责、待接收或待处理的任务"),
    # BUG20261028002/003：改名“待缴官费”，点进去是请款单审批，数量同请款单审批列表。
    # BUG20261028003（2026-10-29）：只算请款单审批里待审批的官方费用，点进去同样只看官方费用。
    ("fee-unpaid", "待缴官费", "dashboard-queue-official-fee-audit", "todo:待审批官方费用", "请款单审批里待审批的官方费用"),
    ("internal-fee-audit", "待审批内部费用", "finance-internal-fee-audit", "todo:待审批内部费用", "内部费用待审核列表总数"),
    # BUG20261028004/005：改名“待审内部提成费用”，点进去只看内部提成-待审核和内部提成(退费)-待审核，数量同该列表。
    ("fee-audit", "待审内部提成费用", "dashboard-queue-internal-commission-audit", "extra", "内部提成-待审核和内部提成(退费)-待审核合计"),
    ("settlement-audit", "待审批结算费用", "finance-settlement-audit", "todo:待审批结算费用", "结算待审核列表总数"),
    ("archive-fee", "待审批归档费用", "finance-archive-fee-pending", "todo:待归档费用", "归档费结算待归档列表总数"),
    ("seal-stamping", "待用印", "seal-admin-pending", "extra", "行政用印里已批准、等待盖章的申请"),
    ("appeal", "待上诉", "dashboard-queue-appeal-pending", "metric:appeal-pending", "我的案件里处于待上诉的"),
    ("evidence", "补充证据", "dashboard-queue-evidence-supplement", "metric:evidence-supplement", "我的案件里需要补充证据的"),
    ("opinion", "补充意见", "dashboard-queue-opinion-supplement", "metric:opinion-supplement", "我的案件里需要补充意见的"),
    ("receipts-pending", "待分配回款", "finance-receipts-pending", "extra", "回款管理里待分配的回款（需要财务中心权限）"),
    ("receivable", "应收回款", "contract-receivable-mine", "extra", "我的应收款列表里的合同"),
    ("archive-closing", "待归档结案", "case-archive-refused", "extra", "归档被退回、需要重新提交的案件"),
    ("clue-audit", "待审批线索", "clue-audit-pending", "todo:待审批线索", "调查线索待审批"),
    ("notary-review", "待审核公证书", "notary", "extra", "公证管理里状态为待审核的公证记录"),
    ("contract-audit", "待审批合同", "contract-audit-pending", "todo:待审批合同", "合同审批轮到我的"),
    ("seal-audit", "待审批用印", "seal-audit-pending", "todo:待审批用印", "有用印审批权限时，待我审批的用印"),
    ("archive-review", "待审核归档", "case-archive-pending", "todo:待审核归档", "有归档审核权限时，待审核的归档"),
    ("loss-review", "待审核预损费用", "case-archive-loss-internal", "todo:待审核预损费用", "归档里亏损内审的案件"),
    ("execution", "待执行", "dashboard-queue-execution-pending", "metric:execution-pending", "我的案件里待执行的"),
    ("urgent", "紧急案件", "dashboard-queue-urgent-cases", "metric:urgent-cases", "我的紧急案件"),
    ("refund", "待退费", "dashboard-queue-refund-pending", "metric:refund-pending", "我的案件里待退费的"),
    ("fee-unreceived", "未到官费金额", "dashboard-queue-official-fee-unreceived", "metric:official-fee-unreceived", "未到账官费，按金额显示"),
)
ITEM_KEYS = tuple(key for key, *_ in PORTAL_ITEMS)

# 默认分端（用户 2026-10-24 确认）。
DEFAULT_PORTALS = [
    {"key": "lawyer", "name": "律师端", "items": [
        "task", "fee-unpaid", "appeal", "evidence", "opinion", "receipts-pending", "receivable", "archive-closing",
    ]},
    {"key": "finance_admin", "name": "财务行政端", "items": [
        "task", "fee-unpaid", "internal-fee-audit", "fee-audit", "settlement-audit", "archive-fee", "seal-stamping",
    ]},
    {"key": "investigation", "name": "调查端", "items": [
        "task", "fee-unpaid", "clue-audit", "notary-review", "evidence",
    ]},
]
# 角色默认归属：按人事角色名称匹配；系统管理员固定看三个端，不在这里配置。
DEFAULT_ROLE_PORTALS = {
    "合伙人律师": ["lawyer"], "主办律师": ["lawyer"], "承办律师": ["lawyer"], "律师助理": ["lawyer"],
    "案件主管": ["lawyer"], "合同管理员": ["lawyer"], "业务专员": ["lawyer"], "客户主管": ["lawyer"],
    "财务主管": ["finance_admin"], "财务专员": ["finance_admin"], "财务人员": ["finance_admin"],
    "行政人员": ["finance_admin"], "档案管理员": ["finance_admin"],
    "调查主管": ["investigation"], "调查员": ["investigation"], "调查专员": ["investigation"], "公证员": ["investigation"],
}
DEFAULT_CONFIG = {"portals": DEFAULT_PORTALS, "role_portals": DEFAULT_ROLE_PORTALS}

# 管理端（用户 2026-10-27）：排在三个端之后的第四个页签，只有管理员（admin 角色，即管理者账号）能看到。
# 固定内容、不进分端配置，和 2026-10-26 去掉的旧“管理端（全部待办）”勾选项无关（旧勾选仍按三个端都勾处理）。
ADMIN_PORTAL_KEY = "admin"
ADMIN_PORTAL_ITEMS = (
    ("feedback-pending", "问题反馈", "feedback-center", "extra", "问题处理中心里待处理的问题"),
    ("feedback-verify", "问题处理中心", "feedback-center", "extra", "问题处理中心里待验证的问题"),
)
ADMIN_PORTAL = {"key": ADMIN_PORTAL_KEY, "name": "管理端", "items": [key for key, *_ in ADMIN_PORTAL_ITEMS]}
FEEDBACK_ITEM_STATUS = {"feedback-pending": "待处理", "feedback-verify": "待验证"}


def catalog() -> list[dict]:
    return [{"key": key, "label": label, "route": route, "source": source, "description": description}
            for key, label, route, source, description in PORTAL_ITEMS]


def validate_config(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != {"portals", "role_portals"}:
        raise HTTPException(status_code=422, detail="首页分端配置必须包含端口和角色归属")
    portals, role_portals = value["portals"], value["role_portals"]
    default_keys = [portal["key"] for portal in DEFAULT_PORTALS]
    if not isinstance(portals, list) or [item.get("key") if isinstance(item, dict) else None for item in portals] != default_keys:
        raise HTTPException(status_code=422, detail="端口固定为律师端、财务行政端、调查端，不能增删")
    cleaned_portals = []
    for portal in portals:
        name = portal.get("name")
        items = portal.get("items")
        if set(portal) != {"key", "name", "items"} or not isinstance(name, str) or not name.strip() or len(name.strip()) > 20:
            raise HTTPException(status_code=422, detail="端口名称必填，最多 20 个字")
        if not isinstance(items, list) or any(item not in ITEM_KEYS for item in items) or len(set(items)) != len(items):
            raise HTTPException(status_code=422, detail="端口里有无效或重复的待办项")
        cleaned_portals.append({"key": portal["key"], "name": name.strip(), "items": list(items)})
    allowed = {*default_keys, MANAGE_PORTAL}
    if not isinstance(role_portals, dict):
        raise HTTPException(status_code=422, detail="角色归属配置无效")
    cleaned_roles = {}
    for role, keys in role_portals.items():
        if not isinstance(role, str) or not role.strip() or not isinstance(keys, list) or any(key not in allowed for key in keys):
            raise HTTPException(status_code=422, detail="角色归属里有无效的角色或端口")
        # 系统管理员固定看三个端，这一行的勾选不再保存。
        if keys and role.strip() not in ADMIN_ROLE_NAMES:
            cleaned_roles[role.strip()] = [key for key in default_keys if key in keys or MANAGE_PORTAL in keys]
    return {"portals": cleaned_portals, "role_portals": cleaned_roles}


async def load_config(db) -> dict:
    from app.core.dependencies import SystemConfig, select

    item = await db.scalar(select(SystemConfig).where(SystemConfig.key == CONFIG_KEY))
    try:
        return validate_config(dict(item.value or {})) if item else DEFAULT_CONFIG
    except HTTPException:
        return DEFAULT_CONFIG


async def portal_keys_for_identity(identity, db, config) -> list[str]:
    """当前账号能看的端：系统管理员（admin 账号或人事角色为系统管理员）固定看三个端；
    其他角色按人事角色名称（或编码）匹配勾选，
    没勾任何端就不显示分端页签，首页回到原来的“我的待办”（用户 2026-10-25：没勾就不要显示）。
    """
    from app.core.dependencies import select
    from app.core.permissions import _configured_user_job_role_name, _identity_role_ids, _job_role_for_name
    from app.data_models.identity import User

    names = set(ADMIN_ROLE_NAMES) if "admin" in _identity_role_ids(identity) else set()
    user = await db.scalar(select(User).where(User.username == identity.get("username", "")))
    role_name = _configured_user_job_role_name(user) if user else str(identity.get("permission_role") or identity.get("staff_role") or "").strip()
    if role_name:
        names.add(role_name)
        job_role = await _job_role_for_name(role_name, db)
        if job_role:
            names |= {job_role.name, job_role.code}
    portal_keys = [portal["key"] for portal in config["portals"]]
    if names & ADMIN_ROLE_NAMES:
        return portal_keys
    keys = {key for name in names for key in config["role_portals"].get(name, [])}
    return [key for key in portal_keys if key in keys]


def _is_admin_account(identity) -> bool:
    """系统角色是管理员（admin）的账号；只挂人事角色“系统管理员”的不算。"""
    from app.core.permissions import _identity_role_ids

    return "admin" in _identity_role_ids(identity)


async def _feedback_count(status, db) -> int:
    """与问题处理中心状态页签的数字一致：全部未删除的问题，旧状态按新流程归类。"""
    from app.areas.system.feedback import _stored_statuses
    from app.core.dependencies import BusinessRecord, func, select

    return int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
        BusinessRecord.module == "bug_feedback", BusinessRecord.deleted_at.is_(None),
        BusinessRecord.status.in_(_stored_statuses(status)),
    )) or 0)


async def _extra_count(key, identity, db) -> int:
    from app.core import dashboard_list_counts as list_counts

    if key in FEEDBACK_ITEM_STATUS:
        return await _feedback_count(FEEDBACK_ITEM_STATUS[key], db) if _is_admin_account(identity) else 0

    if key == "fee-audit":
        return await list_counts.internal_review_total(identity, db, "commission_all")
    if key == "seal-stamping":
        from app.areas.legal.seals import list_seal_applications
        return await list_counts._list_total(list_seal_applications, view="all", record_status="待用印",
                                             page=1, page_size=1, identity=identity, db=db)
    if key == "receipts-pending":
        from app.areas.finance.incoming_payments import list_incoming_payments
        scoped = await list_counts._finance_center_identity(identity, db)
        if scoped is None:
            return 0
        return await list_counts._list_total(list_incoming_payments, view="finance-receipts-pending",
                                             page=1, page_size=1, identity=scoped, db=db)
    if key == "receivable":
        from app.areas.contract.template_exports import list_receivable_contracts
        return await list_counts._list_total(list_receivable_contracts, scope="mine", identity=identity, db=db)
    if key == "archive-closing":
        return await list_counts.archive_queue_total(identity, db, "refused")
    if key == "notary-review":
        from app.areas.legal.record_queries import list_records
        return await list_counts._list_total(list_records, module="notary", record_status="待审核",
                                             page=1, page_size=1, identity=identity, db=db)
    raise ValueError(f"未知的分端待办计数：{key}")


async def dashboard_portals(identity, db):
    """控制台 portals 分区：当前账号的端口、待办目录和本模块负责的计数。"""
    from app.core.dashboard_list_counts import gather_counts

    config = await load_config(db)
    keys = await portal_keys_for_identity(identity, db, config)
    portals = [portal for portal in config["portals"] if portal["key"] in keys]
    items = catalog()
    if _is_admin_account(identity):
        portals.append(ADMIN_PORTAL)
        items += [{"key": key, "label": label, "route": route, "source": source, "description": description}
                  for key, label, route, source, description in ADMIN_PORTAL_ITEMS]
    sources = {item["key"]: item["source"] for item in items}
    needed = {item for portal in portals for item in portal["items"] if sources[item] == "extra"}
    counts = await gather_counts(db, {
        key: (lambda session, key=key: _extra_count(key, identity, session)) for key in sorted(needed)
    }) if needed else {}
    return {"portals": portals, "portal_items": items, "portal_counts": counts}
