"""执行聊天中明确提交的连接配置，复用既有凭据存储及 MCP 握手。"""
from datetime import datetime, timezone

from fastapi import HTTPException

from app.agent_mcp.auth import authenticated_identity, get_auth_context
from app.config import settings
from .mcp_chat_input import ChatConnectionBatch
from .mcp_connection_setup import completion_message, connect, prepare_connection


async def configure_chat_submission(submission, identity, db, state, on_delta, on_progress, *, save_state=None, case_id=None):
    if isinstance(submission, ChatConnectionBatch):
        return await configure_chat_connections(submission, identity, db, state, on_delta, on_progress,
                                                save_state=save_state, case_id=case_id)
    return await configure_chat_connection(submission, identity, db, state, on_delta, on_progress,
                                           save_state=save_state, case_id=case_id)


def _batch_line(index, name, result):
    if result.get('status') == 'verified':
        return f'{index}. 「{name}」已连接，共发现 {result.get("tool_count", 0)} 个工具。'
    reason = ('服务拒绝了认证，请核对 Token 和认证方式' if result.get('error_code') == 'upstream_auth_failed'
              else '握手或工具目录读取未通过，请核对地址和服务状态')
    return f'{index}. 「{name}」配置已保存，但还没连上：{reason}。'


async def configure_chat_connections(batch, identity, db, state, on_delta, on_progress, *, save_state=None, case_id=None):
    """逐个配置一次粘贴的多个服务：每个服务各建一个连接、各自校验，一个失败不影响其他。"""
    from .service import _save_state

    persist = save_state or _save_state

    async def quiet(_content):
        return None

    lines = []
    total = len(batch.items)
    for index, (name, submission, error) in enumerate(batch.items, 1):
        if submission is None:
            lines.append(f'{index}. 「{name}」未配置：{error}')
            continue
        if on_progress:
            await on_progress(f'正在配置第 {index}/{total} 个 MCP 服务「{name}」…')
        try:
            await configure_chat_connection(submission, identity, db, state, quiet, None, save_state=persist, case_id=case_id)
        except HTTPException as exc:
            await db.rollback()
            lines.append(f'{index}. 「{name}」未配置：{exc.detail}')
            continue
        except Exception:
            # 不把异常原文写进回复，避免带出请求里的凭据。
            await db.rollback()
            lines.append(f'{index}. 「{name}」配置没有完成，请稍后在“管理连接”里重试。')
            continue
        lines.append(_batch_line(index, name, state['messages'][-1].get('connection_result') or {}))
    response = (f'这次粘贴了 {total} 个 MCP 服务，已逐个配置：\n' + '\n'.join(lines)
                + '\n没配好的可以在“管理连接”里修改或重试，不用重新粘贴已连接的服务。')
    now = datetime.now(timezone.utc).isoformat()
    state['messages'].append({'role': 'assistant', 'content': response, 'created_at': now, 'source': 'mcp_connection'})
    state['updated_at'] = now
    state['last_response'] = response
    state['last_operator'] = identity['username']
    await persist(identity['username'], state)
    await on_delta(response)
    return {'response': response, 'state': state, 'context': {}}


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
