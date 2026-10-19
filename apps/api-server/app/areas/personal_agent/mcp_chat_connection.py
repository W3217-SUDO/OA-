"""执行聊天中明确提交的连接配置，复用既有凭据存储及 MCP 握手。"""
from datetime import datetime, timezone

from fastapi import HTTPException

from app.agent_mcp.auth import authenticated_identity, get_auth_context
from app.config import settings
from .mcp_connection_setup import completion_message, connect, prepare_connection


async def configure_chat_connection(submission, identity, db, state, on_delta, on_progress, *, save_state=None, case_id=None):
    from .service import _save_state

    persist = save_state or _save_state
    context = get_auth_context()
    expected = (f'/case-spaces/{case_id}/agent/messages' if case_id is not None else '/personal-agent/messages')
    if context.scope.get('method') != 'POST' or context.scope.get('path') != settings.api_prefix + expected:
        raise HTTPException(403, '聊天连接配置必须由当前登录人的消息入口发起')
    actual = await authenticated_identity(db)
    if actual['username'] != identity['username']:
        raise HTTPException(403, '连接配置身份与实际登录人不一致')
    action = prepare_connection(submission.plan.model_dump(), actual)
    now = datetime.now(timezone.utc).isoformat()
    message = {'role': 'user', 'content': submission.message(), 'created_at': now, 'operator': identity['username'],
               'mcp_connection': {'id': action['payload']['connection_id'],
                                  'scope': action['payload']['scope'], 'status': 'executing'}}
    state['messages'].append(message)
    state['updated_at'] = now
    await persist(identity['username'], state)
    if on_progress:
        await on_progress('正在保存配置并验证 MCP 握手和工具目录…')
    try:
        result = await connect(action, actual, db, submission.credential.get_secret_value())
    except BaseException:
        # 保存失败或验证被中止时保留唯一连接编号，不能把未完成报告为成功。
        message['mcp_connection']['status'] = 'incomplete'
        await persist(identity['username'], state)
        raise
    message['mcp_connection']['status'] = result['status']
    response = completion_message(result)
    state['messages'].append({'role': 'assistant', 'content': response,
                              'created_at': datetime.now(timezone.utc).isoformat(),
                              'source': 'mcp_connection', 'connection_result': result})
    state['updated_at'] = datetime.now(timezone.utc).isoformat()
    state['last_response'] = response
    state['last_operator'] = identity['username']
    await persist(identity['username'], state)
    await on_delta(response)
    return {'response': response, 'state': state, 'context': {}}
