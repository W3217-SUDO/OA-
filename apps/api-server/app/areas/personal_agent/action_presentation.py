"""本人操作卡的持久化收起，不决定请求或改写业务审计。"""

from fastapi import HTTPException
from sqlalchemy import select

from app.areas.personal_agent import conversations
from app.areas.personal_agent.project_workspaces import require_state_access
from app.areas.personal_agent.confirmation_history import PERSONAL_ACTION_MODULE, project_personal_actions
from app.agent_mcp.service import ACTION_MODULE
from app.models import BusinessRecord


async def dismiss_personal_actions(directory, conversation_id, action_ids, identity, db):
    if (not action_ids or len(action_ids) > 30 or any(not isinstance(item, str) or not item for item in action_ids)
            or len(set(action_ids)) != len(action_ids)):
        raise HTTPException(422, "收起操作需要1至30个不重复的真实操作编号")
    async with conversations.conversation_operation(directory, conversation_id) as state:
        await require_state_access(state, identity, db)
        actions = {item.get("id"): item for item in state["pending_actions"] if isinstance(item, dict)}
        if not set(action_ids).issubset(actions):
            raise HTTPException(404, "操作卡不存在或已从原会话处理")
        serials = []
        for action_id in action_ids:
            action = actions[action_id]
            if action.get("requested_by") != identity["username"]:
                raise HTTPException(403, "只能收起本人会话中的操作卡")
            if action.get("type") == "mcp.call":
                request_id = (action.get("payload") or {}).get("request_id")
                if not isinstance(request_id, str) or not request_id:
                    raise HTTPException(422, "工具请求缺少有效编号")
                serials.append("MCP-" + request_id)
            elif action.get("type") in {"create_task", "approve_contract", "personal_mcp.call", "personal_mcp.connect"}:
                serials.append("PA-" + action_id)
            else:
                raise HTTPException(422, "操作卡类型无效")
        records = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module.in_((ACTION_MODULE, PERSONAL_ACTION_MODULE)), BusinessRecord.serial_no.in_(serials),
        ))).all()
        if any(record.owner != identity["username"] for record in records):
            raise HTTPException(403, "确认请求不属于当前账号")
        # 先校验真实存档归属和状态，绝不把他人的存档当成升级前旧请求。
        await project_personal_actions(state, identity, db)
        saved = await conversations.save_action_dismissals(directory, state["conversation_id"], action_ids)
        return {"state": await project_personal_actions(saved, identity, db)}
