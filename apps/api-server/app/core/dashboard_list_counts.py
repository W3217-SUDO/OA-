"""控制台“我的待办”卡片计数：直接复用点进去那个列表的同一查询函数，只取总数。

控制台数字口径（2026-10-23 用户确认）：首页每个数字 = 当前账号按点进去页面默认条件查询得到的总条数。
不另写一套条件，列表的权限、数据范围、状态规则改动时首页自动跟随。
"""
import asyncio
import inspect

from fastapi import HTTPException
from fastapi.params import Depends as DependsParam, Param


def _endpoint_kwargs(fn, **values):
    """按接口签名补齐 Query 默认值；Depends 参数必须显式传入。"""
    kwargs = {}
    for name, parameter in inspect.signature(fn).parameters.items():
        if name in values:
            kwargs[name] = values[name]
            continue
        default = parameter.default
        if isinstance(default, DependsParam):
            raise TypeError(f"{fn.__name__} 缺少依赖参数 {name}")
        if isinstance(default, Param):
            default = default.default
        kwargs[name] = default
    return kwargs


async def _list_total(fn, **values) -> int:
    try:
        result = await fn(**_endpoint_kwargs(fn, **values))
    except HTTPException as error:
        if error.status_code in {403, 404}:
            return 0
        raise
    if isinstance(result, dict):
        return int(result.get("total") or 0)
    return len(result or [])


async def _finance_center_identity(identity, db, scope="firm"):
    """与 finance_center_identity 相同的菜单校验；没有该财务中心菜单时卡片计 0。"""
    from app.core.permissions import _permission_payload_for_identity

    if identity.get("role") != "admin":
        permission = await _permission_payload_for_identity(identity, db)
        prefix = "platform-finance" if scope == "platform" else "finance"
        if not any(key == prefix or key.startswith(prefix + "-") for key in permission.get("menu_keys") or []):
            return None
    return {**identity, "_finance_scope": scope}


async def archive_queue_total(identity, db, view):
    from app.core.case_archive import ArchiveSearchInput, search_archive_cases

    try:
        result = await search_archive_cases(ArchiveSearchInput(view=view, page=1, page_size=1), identity, db)
    except HTTPException as error:
        if error.status_code in {403, 404}:
            return 0
        raise
    return int(result.get("total") or 0)


async def payment_audit_total(identity, db):
    """请款单审批（finance-payment-audit）：外部费用“待审批” + 合同付款“待审批”。"""
    from app.areas.legal.record_queries import list_records

    fees = await _list_total(list_records, module="finance", finance_view="external", record_status="待审批",
                             page=1, page_size=1, identity=identity, db=db)
    contract_payments = await _list_total(list_records, module="contract_payment", record_status="待审批",
                                          page=1, page_size=1, identity=identity, db=db)
    return fees + contract_payments


async def payment_audit_official_total(identity, db):
    """BUG20261028003（范明明 2026-10-29）：“待缴官费”= 请款单审批里待审批的官方费用（不含代理费等和合同付款）。"""
    # 与请款单审批取数同一条件（请款费用行、待审批、本人数据范围），再限定费用类型。
    from sqlalchemy import select

    from app.core.contract_payment_lifecycle import payment_application_fee_condition
    from app.core.permissions import _record_scope_conditions, _require_record_module_menu
    from app.models import BusinessRecord

    from app.core.permissions import _permission_payload_for_identity

    # 点“待缴官费”进的是请款单审批页面，列表按该页面的数据范围取数（给页面=页面数据全有）；
    # 有这个页面的人计数也按同一范围，否则数据范围小的人（如范明明）计数为 0、列表却有数据（2026-10-29）。
    menus = set((await _permission_payload_for_identity(identity, db)).get("menu_keys") or [])
    if "finance-payment-audit" in menus and not identity.get("_page_menu_capability"):
        role_ids = list(identity.get("role_ids") or [])
        identity = {**identity, "role": "admin", "role_ids": role_ids if "admin" in role_ids else ["admin", *role_ids],
                    "action_keys": ["*"], "_page_menu_capability": True, "_request_page": "finance-payment-audit"}
    try:
        await _require_record_module_menu("finance", identity, db, action="查询请款")
    except HTTPException as error:
        if error.status_code in {403, 404}:
            return 0
        raise
    ids = (await db.scalars(select(BusinessRecord.id).where(
        payment_application_fee_condition(), BusinessRecord.status == "待审批",
        BusinessRecord.data["fee_type"].as_string() == "官方费用",
        *(await _record_scope_conditions(identity, db)),
    ))).all()
    # 工作台点进去是财务中心的请款单审批，只算律所（老系统 GroupId 10）的（陶威 2026-10-30）。
    from app.core.finance_centers import finance_centers_for_ids
    centers = await finance_centers_for_ids(db, ids)
    return sum(1 for record_id in ids if centers.get(record_id, "firm") == "firm")


async def internal_review_total(identity, db, kind="other"):
    """内部请款审批列表（/finance/internal-review-requests）的总数：同一权限判断、取数与筛选函数。"""
    from app.core.internal_finance_query import InternalApplicationFilters, filter_internal_rows
    from app.core.internal_requests import internal_review_rows

    if identity.get("role") not in {"admin", "manager", "auditor"}:
        return 0
    rows = await internal_review_rows(identity, db, kind)
    return len(filter_internal_rows(rows, case_no="", customer="", case_stages="", payee="", fee_types="",
                                    paid_from=None, paid_to=None, **InternalApplicationFilters().values()))


async def settlement_audit_total(identity, db):
    from app.areas.finance.settlements import list_general_settlement_applications

    scoped = await _finance_center_identity(identity, db)
    if scoped is None:
        return 0
    return await _list_total(list_general_settlement_applications, application_status="待审批",
                             page=1, page_size=1, identity=scoped, db=db)


async def archive_fee_pending_total(identity, db):
    from app.areas.finance.settlements import list_pending_archive_settlements

    scoped = await _finance_center_identity(identity, db)
    if scoped is None:
        return 0
    return await _list_total(list_pending_archive_settlements, page=1, page_size=1, identity=scoped, db=db)


# 同时计数的上限：每张卡片占用一个独立只读连接，限制并发避免多人同时打开控制台时耗尽连接池。
PARALLEL_COUNT_LIMIT = 4


async def gather_counts(db, jobs):
    """并行计算多张卡片（每张独立会话、只读）；非 PostgreSQL（测试用 SQLite）按顺序在当前会话计算。

    jobs: {卡片名: async 函数(db) -> int}。各计数互不依赖，结果与逐个计算相同。
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    bind = db.bind
    if bind is None or bind.dialect.name != "postgresql":
        return {name: await job(db) for name, job in jobs.items()}
    sessions = async_sessionmaker(bind, expire_on_commit=False, class_=AsyncSession)
    limit = asyncio.Semaphore(PARALLEL_COUNT_LIMIT)

    async def run(job):
        async with limit, sessions() as session:
            try:
                return await job(session)
            finally:
                await session.rollback()

    names = list(jobs)
    values = await asyncio.gather(*(run(jobs[name]) for name in names))
    return dict(zip(names, values))
