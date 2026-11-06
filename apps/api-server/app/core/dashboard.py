"""控制台分区数据加载，权限范围由现有权限服务统一确定。"""
from app.core.permissions import _permission_payload_for_identity, _record_scope_conditions
from app.core.system import _record_module_menu_allowed


async def dashboard_scope(identity, db, *, record_scope=None, module=None):
    """module：调用方只查这一个模块时传，范围条件走索引。"""
    scope = await _record_scope_conditions(identity, db, module=module) if record_scope is None else record_scope
    permission = await _permission_payload_for_identity(identity, db)
    modules = {module for module in {"case", "task", "finance", "refund", "contract", "clue", "seal"}
               if _record_module_menu_allowed(module, identity, permission)}
    return scope, modules
