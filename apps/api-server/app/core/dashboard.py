"""控制台分区数据加载，权限范围由现有权限服务统一确定。"""
from app.core.dependencies import BusinessRecord, select
from app.core.permissions import _permission_payload_for_identity, _record_scope_conditions
from app.core.system import _record_module_menu_allowed


async def dashboard_scope(identity, db):
    scope = await _record_scope_conditions(identity, db)
    permission = await _permission_payload_for_identity(identity, db)
    modules = {module for module in {"case", "task", "finance", "refund", "contract", "clue", "seal"}
               if _record_module_menu_allowed(module, identity, permission)}
    return scope, modules


async def dashboard_records(db, scope, modules):
    return list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(modules), *scope,
    ))).all()) if modules else []
