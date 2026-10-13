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
