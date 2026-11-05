"""任务页面与智能体共用的撤回、手动完成规则。"""

from fastapi import HTTPException

from app.core.case_automation import requires_phase_completion
from app.models import BusinessRecord


def validate_task_lifecycle(task: BusinessRecord, identity: dict, action: str, comment: str) -> None:
    actor = identity["username"]
    if action == "withdraw":
        if (task.data or {}).get("initiator") != actor:
            raise HTTPException(403, f"任务 {task.serial_no} 仅发起人可撤回")
        if task.status not in {"待接收", "待处理", "处理中", "进行中", "已逾期"}:
            raise HTTPException(409, f"任务 {task.serial_no} 当前状态不能撤回")
        if not comment.strip():
            raise HTTPException(422, "撤回任务必须填写撤回原因")
    elif action == "complete":
        if identity.get("role") != "admin" and task.owner != actor:
            raise HTTPException(403, f"任务 {task.serial_no} 仅负责人可提交完成")
        if requires_phase_completion(task):
            raise HTTPException(409, f"任务 {task.serial_no} 只能由案件阶段变化自动完成，不能手动完成")
        if task.status not in {"待接收", "待处理", "处理中", "进行中", "已逾期"}:
            raise HTTPException(409, f"任务 {task.serial_no} 当前状态不能提交完成")
    else:
        raise ValueError(f"Unsupported task lifecycle validation: {action}")


COMPANY_TASK_MENU = "task-company-accepted"


async def task_actor_identity(identity: dict, db) -> dict:
    """代办别人任务的身份（501580 tgn 11-05 选 A）：真管理员，或角色/个人权限里有“公司接受的任务”页面且勾了“批量修改任务”的人，
    可以代别人完成、转交任务（按管理员处理负责人校验）；其他人只能办自己的任务。
    不看页面临时提升出来的 admin（current_identity 按访问页面给的），只看真实角色和权限。"""
    from app.core.permissions import _permission_payload_for_identity
    actual_roles = identity.get("_actual_role_ids") or identity.get("role_ids") or [identity.get("role")]
    actual = {**identity, "role": identity.get("_actual_role") or identity.get("role"), "role_ids": actual_roles,
              "_page_menu_capability": False}
    if "admin" in actual_roles:
        return {**actual, "role": "admin"}
    permission = await _permission_payload_for_identity(actual, db)
    actions = set(permission.get("action_keys") or [])
    if COMPANY_TASK_MENU in set(permission.get("menu_keys") or []) and ("*" in actions or "task.batch.update" in actions):
        return {**actual, "role": "admin", "_task_proxy": True}
    return {**actual, "role": "user" if actual.get("role") == "admin" else actual.get("role")}


def proxy_note(task: BusinessRecord, identity: dict) -> str:
    """代办时写进操作记录：谁代谁办的。"""
    return f"（{identity['username']} 代 {task.owner} 办理）" if task.owner != identity["username"] else ""
