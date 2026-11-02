"""执行聊天中明确提交的连接配置，复用既有凭据存储及 MCP 握手。"""
from datetime import datetime, timezone
import os
import re
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import HTTPException

from app.agent_mcp.auth import authenticated_identity, get_auth_context
from app.config import settings
from .mcp_chat_input import LOCAL_SKIPPED, ChatConnectionBatch
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


MAX_GROUP_SERVICES = 12
_PROVIDERS = ((re.compile(r'(^|\.)qcc\.com$'), '企查查'), (re.compile(r'(^|\.)tianyancha\.com$'), '天眼查'),
              (re.compile(r'(^|\.)pkulaw\.(com|cn)$'), '北大法宝'), (re.compile(r'(^|\.)baidu\.com$'), '百度'))


def group_name(names, urls):
    """分组名：已知服务商名称，其次服务名共同前缀，最后域名主体（与连接 MCP 面板一致）。"""
    hosts = {(urlsplit(url).hostname or '').lower() for url in urls}
    for pattern, label in _PROVIDERS:
        if all(pattern.search(host) for host in hosts):
            return label
    prefix = re.sub(r'[\s._\-/:]+$', '', os.path.commonprefix(list(names)))
    if len(prefix) >= 2:
        return prefix[:80]
    domains = {host.split('.')[-2] if host.count('.') else host for host in hosts}
    return next(iter(domains))[:80] if len(domains) == 1 else 'MCP 分组'


def _shared_key(submission):
    plan = submission.plan
    return plan.authentication, plan.header_name if plan.authentication == 'api_key' else '', submission.credential.get_secret_value()


async def configure_chat_group(batch, valid, identity, db, state, on_delta, on_progress, *, persist, case_id=None):
    """多个服务共用一个 Key 时合成一个 MCP 分组：一条连接、一份加密 Key，整组检测、改 Key、启停、删除（陶威 11-02）。"""
    from app.areas.capability_market.connector_store import save_configuration, save_verification
    from app.areas.capability_market.mcp_access import default_connection_scope
    from app.areas.capability_market.personal_mcp import item_for, normalize_configuration, redact_verification
    from app.areas.capability_market.remote_session import verify_personal_configuration

    context = get_auth_context()
    expected = (f'/case-spaces/{case_id}/agent/messages' if case_id is not None else '/personal-agent/messages')
    if context.scope.get('method') != 'POST' or context.scope.get('path') != settings.api_prefix + expected:
        raise HTTPException(403, '聊天连接配置必须由当前登录人的消息入口发起')
    actual = await authenticated_identity(db)
    if actual['username'] != identity['username']:
        raise HTTPException(403, '连接配置身份与实际登录人不一致')
    names = [name for name, _ in valid]
    name = group_name(names, [submission.plan.server_url for _, submission in valid])
    credential = valid[0][1].credential.get_secret_value()
    servers = {service: submission.plan.configuration(credential)['mcp.json']['mcpServers']['default'] for service, submission in valid}
    configuration = normalize_configuration({'mcp.json': {'mcpServers': servers}})
    scope = default_connection_scope(actual)
    item = item_for('personal-mcp-' + uuid4().hex, name)
    now = datetime.now(timezone.utc).isoformat()
    message = {'role': 'user', 'content': batch.message(), 'created_at': now, 'operator': identity['username'],
               'mcp_connection': {'id': item['id'], 'scope': scope, 'status': 'executing'}}
    state['messages'].append(message)
    state['updated_at'] = now
    await persist(identity['username'], state)
    if on_progress:
        await on_progress(f'正在保存 MCP 分组「{name}」并检测 {len(valid)} 个服务…')
    try:
        record = await save_configuration(item, scope, actual, db, configuration, [], '')
        revision = record.value['revision']
        await db.rollback()
        result = redact_verification(await verify_personal_configuration(configuration), configuration)
        record = await save_verification(item, scope, actual, db, revision, result)
    except BaseException:
        message['mcp_connection']['status'] = 'incomplete'
        await persist(identity['username'], state)
        raise
    status = record.value['status']
    message['mcp_connection']['status'] = status
    checked = {server.get('name'): server for server in result.get('servers', [])}
    tool_count = sum(server.get('tool_count', 0) for server in checked.values())
    scope_label = '全局共享' if scope == 'global' else '个人专用'
    lines = [f'已把 {len(valid)} 个服务合成一个 MCP 分组「{name}」（{scope_label}，共用一个 Key，只加密保存一份）：']
    for index, service in enumerate(names, 1):
        server = checked.get(service) or {}
        if server.get('error'):
            lines.append(f'{index}. 「{service}」检测未通过：{server["error"]}')
        elif server:
            lines.append(f'{index}. 「{service}」已连接，{server.get("tool_count", 0)} 个工具。')
        else:
            lines.append(f'{index}. 「{service}」检测未完成。')
    for skipped, submission, error in batch.items:
        if submission is None:
            lines.append(f'「{skipped}」：{LOCAL_SKIPPED}。' if error == LOCAL_SKIPPED else f'「{skipped}」未加入分组：{error}')
    lines.append('分组整体验证通过，共 %d 个工具；调用外部工具时仍会请你确认。' % tool_count if status == 'verified'
                 else '分组已保存但有服务没连上，可在“MCP 连接”里整组重新检测或修改 Key，不用重新粘贴。')
    response = '\n'.join(lines)
    await on_delta(response)
    connection_result = {'id': item['id'], 'name': name, 'scope': scope, 'status': status, 'tool_count': tool_count,
                         'error_code': ('upstream_auth_failed' if any(code in result.get('error', '') for code in ('HTTP401', 'HTTP403'))
                                        else 'upstream_unreachable') if status == 'failed' else '',
                         'services': names}
    now = datetime.now(timezone.utc).isoformat()
    state['messages'].append({'role': 'assistant', 'content': response, 'created_at': now,
                              'source': 'mcp_connection', 'connection_result': connection_result})
    state['updated_at'] = now
    state['last_response'] = response
    state['last_operator'] = identity['username']
    await persist(identity['username'], state)
    return {'response': response, 'state': state, 'context': {}}


async def configure_chat_connections(batch, identity, db, state, on_delta, on_progress, *, save_state=None, case_id=None):
    """一次粘贴多个服务：共用同一个 Key 的合成一个 MCP 分组；各自 Key 不同时逐个配置，一个失败不影响其他。"""
    from .service import _save_state

    persist = save_state or _save_state
    valid = [(name, submission) for name, submission, _ in batch.items if submission is not None]
    if 2 <= len(valid) <= MAX_GROUP_SERVICES and len({_shared_key(submission) for _, submission in valid}) == 1:
        return await configure_chat_group(batch, valid, identity, db, state, on_delta, on_progress, persist=persist, case_id=case_id)

    async def quiet(_content):
        return None

    lines = []
    total = len(batch.items)
    header = f'这次粘贴了 {total} 个 MCP 服务，逐个配置，配好一个返回一个：\n'
    await on_delta(header)

    async def report(line):
        lines.append(line)
        await on_delta(line + '\n')

    for index, (name, submission, error) in enumerate(batch.items, 1):
        if submission is None:
            await report(f'{index}. 「{name}」未配置：{error}')
            continue
        if on_progress:
            await on_progress(f'正在配置第 {index}/{total} 个 MCP 服务「{name}」…')
        try:
            await configure_chat_connection(submission, identity, db, state, quiet, None, save_state=persist, case_id=case_id)
        except HTTPException as exc:
            await db.rollback()
            await report(f'{index}. 「{name}」未配置：{exc.detail}')
            continue
        except Exception:
            # 不把异常原文写进回复，避免带出请求里的凭据。
            await db.rollback()
            await report(f'{index}. 「{name}」配置没有完成，请稍后在“MCP 连接”里重试。')
            continue
        await report(_batch_line(index, name, state['messages'][-1].get('connection_result') or {}))
    footer = '没配好的可以在“MCP 连接”里修改或重试，不用重新粘贴已连接的服务。'
    await on_delta(footer)
    response = header + '\n'.join(lines) + '\n' + footer
    now = datetime.now(timezone.utc).isoformat()
    state['messages'].append({'role': 'assistant', 'content': response, 'created_at': now, 'source': 'mcp_connection'})
    state['updated_at'] = now
    state['last_response'] = response
    state['last_operator'] = identity['username']
    await persist(identity['username'], state)
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
