"""提取用户主动粘贴的连接声明，凭据仅在当前请求内使用。"""
from dataclasses import dataclass, field
import json
import re
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import SecretStr

from .mcp_connection_setup import ConnectionPlan, read_plan

_URL = re.compile(r'https?://[^\s<>"\'，；。,;]+', re.I)
_SECRET = re.compile(
    r'(?:Bearer\s+|(?:api[-_ ]?key|token|secret|密钥|秘钥)\s*[:=：]\s*)'
    r'["\']?([^\s"\'，；。,;]+)', re.I)


@dataclass(frozen=True)
class ChatConnection:
    plan: ConnectionPlan
    credential: SecretStr = field(repr=False)

    def message(self):
        plan = self.plan
        return (f'请连接 MCP「{plan.name}」。地址：{plan.server_url}；'
                f'传输：{plan.transport}；认证：{plan.authentication}。'
                + ('凭据已提交并隐藏。' if self.credential.get_secret_value() else '无需凭据。'))


IGNORED_FIELDS = {'description', 'timeout', 'disabled', 'enabled', 'autoApprove', 'alwaysAllow', 'note', 'notes',
                  'title', 'icon', 'category', 'tags', 'readTimeout', 'connectTimeout', 'sse_read_timeout'}
LOCAL_SKIPPED = '服务器不支持本机命令型 MCP，已跳过'
MAX_BATCH_SERVERS = 20  # 北大法宝整份 mcp.json 有 14 个服务（陶国南 11-01）
# 每个服务握手和工具目录验证最多 25 秒，批量时本轮时限按服务数放宽，逐个配好逐个返回结果。
BATCH_SECONDS_PER_SERVER = 30


def chat_connection_timeout(submission, default=180):
    if isinstance(submission, ChatConnectionBatch):
        return max(default, 60 + BATCH_SECONDS_PER_SERVER * len(submission.items))
    return default


@dataclass(frozen=True)
class ChatConnectionBatch:
    """一次粘贴的多个服务（陶国南、陶威 11-01：自动拆开逐个配置）；解析不通过的单个服务带着原因，不影响其他服务。"""
    items: tuple = field(repr=False)  # (名称, ChatConnection 或 None, 失败原因)

    def message(self):
        return f'请连接 {len(self.items)} 个 MCP 服务：' + '、'.join(f'「{name}」' for name, _, _ in self.items) + '。凭据已提交并隐藏。'


def _batch(servers):
    if len(servers) > MAX_BATCH_SERVERS:
        raise HTTPException(422, f'一次最多配置 {MAX_BATCH_SERVERS} 个 MCP 服务，这次粘贴了 {len(servers)} 个，请分几条消息发送。')
    items = []
    for name, value in servers.items():
        if isinstance(value, dict) and value.keys() & {'command', 'args', 'env'} and 'url' not in value:
            items.append((str(name), None, LOCAL_SKIPPED))
            continue
        try:
            items.append((str(name), _declaration({'mcpServers': {name: value}}), ''))
        except HTTPException as exc:
            items.append((str(name), None, str(exc.detail)))
    return ChatConnectionBatch(tuple(items))


def _declaration(value):
    if not isinstance(value, dict):
        raise HTTPException(422, '请提供一个完整的远程 MCP JSON 对象')
    if 'mcp.json' in value:
        value = value['mcp.json']
    name = ''
    if isinstance(value, dict) and 'mcpServers' in value:
        servers = value['mcpServers']
        if not isinstance(servers, dict) or not servers:
            raise HTTPException(422, '没有找到要配置的 MCP 服务，请粘贴完整配置')
        if len(servers) > 1:
            return _batch(servers)
        name, value = next(iter(servers.items()))
    if isinstance(value, dict) and value.keys() & {'command', 'args', 'env'}:
        raise HTTPException(422, '这是本机启动方式（command）的配置，系统不能在服务器上运行它；请改用服务方提供的远程地址（https 开头）和 Key')
    if isinstance(value, dict):
        # 各家配置示例常带说明、超时、开关等字段（如华语元典），与连接无关，忽略即可（陶国南 11-01）。
        value = {key: item for key, item in value.items() if key not in IGNORED_FIELDS}
    if not isinstance(value, dict) or set(value) - {
        'name', 'url', 'server_url', 'type', 'transport', 'headers',
        'auth_type', 'credential', 'api_key_header',
    }:
        raise HTTPException(422, '仅支持远程 MCP 的地址、名称、传输及认证字段')
    url = value.get('server_url', value.get('url'))
    if not isinstance(url, str):
        raise HTTPException(422, '缺少 MCP 服务地址')
    auth, credential, header = value.get('auth_type'), value.get('credential', ''), value.get('api_key_header', 'X-API-Key')
    if 'headers' in value:
        headers = value['headers']
        if auth is not None or 'credential' in value or not isinstance(headers, dict) or len(headers) > 1:
            raise HTTPException(422, '请选择一种认证声明，每个连接支持一个认证请求头')
        auth = 'none'
        for key, secret in headers.items():
            if not isinstance(secret, str):
                raise HTTPException(422, '认证请求头必须为文本')
            if key.lower() == 'authorization':
                match = re.fullmatch(r'Bearer\s+(\S+)', secret, re.I)
                if not match:
                    raise HTTPException(422, 'Authorization 仅支持 Bearer Token')
                auth, credential = 'bearer', match[1]
            else:
                auth, credential, header = 'api_key', secret, key
    elif auth is None:
        if credential:
            raise HTTPException(422, '请注明密钥使用 Bearer 还是 API Key 认证')
        auth = 'none'
    transport = value.get('transport', value.get('type', 'streamable_http'))
    if transport in ('http', 'streamableHttp', 'streamable-http'):
        transport = 'streamable_http'
    return _connection(name=value.get('name', name) or urlsplit(url).hostname,
                       server_url=url, transport=transport, authentication=auth,
                       header_name=header, credential=credential)


def _connection(*, credential, **declaration):
    plan = read_plan(declaration)
    if not isinstance(credential, str) or len(credential) > 8192:
        raise HTTPException(422, '密钥须为不超过 8192 字符的文本')
    if plan.authentication != 'none' and not credential:
        raise HTTPException(422, '请在同一条消息中提供此服务的真实 Key / Token')
    if plan.authentication == 'none' and credential:
        raise HTTPException(422, '已提供密钥，请注明正确的认证方式')
    if credential and (credential != credential.strip() or any(char in credential for char in '\r\n\0')
                       or '${' in credential or '{{' in credential or '***' in credential
                       or credential.startswith('<') or credential.lower().startswith('bearer ')):
        raise HTTPException(422, '请提供真实 Token 本体，不能使用占位符或重复 Bearer')
    if credential and credential in json.dumps(plan.model_dump(), ensure_ascii=False):
        raise HTTPException(422, '密钥只能放在认证字段，不能同时作为公开名称或地址的一部分')
    return ChatConnection(plan, SecretStr(credential))


_PLACEHOLDER = re.compile(r'(?:YOUR[_-]?)?(?:API[_-]?)?(?:KEY|TOKEN)|x{3,}|<[^>]*>|\.\.\.', re.I)
_NAME_TOKEN = re.compile(r'[A-Za-z][A-Za-z0-9_-]{2,60}')


def _text_server_name(text, url):
    """网页复制来的地址表里，地址前面通常就是服务名（如 yuandian-law）；找不到就用域名加路径。"""
    before = text[max(0, text.find(url) - 80):text.find(url)]
    tokens = [token for token in _NAME_TOKEN.findall(before)
              if token.lower() not in {'https', 'http', 'bearer', 'authorization', 'mcp', 'server', 'stream'}
              and ('-' in token or '_' in token)]
    if tokens:
        return tokens[-1]
    parts = urlsplit(url)
    segments = [part for part in parts.path.split('/') if part and part not in {'mcp', 'stream', 'sse'}]
    return '-'.join([parts.hostname.split('.')[-2] if parts.hostname.count('.') else parts.hostname, *segments[:2]])


def extract_chat_connection(text):
    stripped = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.I)
    is_json = stripped.startswith('{') and re.search(r'"(?:mcpServers|mcp\.json|server_url)"\s*:|https://[^"\s]+/mcp', stripped)
    if is_json:
        try:
            value = json.loads(stripped)
        except (ValueError, RecursionError):
            raise HTTPException(422, 'MCP JSON 不完整，请粘贴完整配置；密钥不会写入聊天记录') from None
        return _declaration(value)
    urls = _URL.findall(text)
    # 从服务方网页整段复制时会带上示例占位符（如 Bearer YOUR_API_KEY），不当作密钥。
    secrets = [match for match in _SECRET.finditer(text) if not _PLACEHOLDER.fullmatch(match[1])]
    intent = re.search(r'\bmcp\b|mcpServers|(?:连接|链接|配置|接入|connect|setup)', text, re.I)
    if not intent or not (secrets or re.search(r'无需认证|无需\s*token|无认证', text, re.I)):
        return None
    if not urls:
        raise HTTPException(422, '请在同一条消息中提供 HTTPS MCP 服务地址和认证方式')
    if len(secrets) > 1 and len({match[1] for match in secrets}) != 1:
        raise HTTPException(422, '检测到不同密钥，请每条消息只配置一个服务及其凭据')
    credential = secrets[0][1] if secrets else ''
    if re.search(r'Bearer', text, re.I):
        authentication, header = 'bearer', 'X-API-Key'
    elif re.search(r'api[-_ ]?key|X-API-Key', text, re.I):
        authentication, header = 'api_key', 'X-API-Key'
        named = re.search(r'(?:请求头|header)\s*[:=：]\s*([A-Za-z0-9_-]+)', text, re.I)
        if named:
            header = named[1]
    elif not credential:
        authentication, header = 'none', 'X-API-Key'
    else:
        raise HTTPException(422, '请注明此 Token 使用 Bearer 还是 API Key 认证；无需另填输入框')
    transport = 'sse' if re.search(r'\bsse\b', text, re.I) else 'streamable_http'
    unique = list(dict.fromkeys(urls))
    if len(unique) > 1:
        # 服务方网页上列了几个地址、共用一个 Key（如华语元典 5 个服务）：逐个配置。
        if len(unique) > MAX_BATCH_SERVERS:
            raise HTTPException(422, f'一次最多配置 {MAX_BATCH_SERVERS} 个 MCP 服务，请分几条消息发送。')
        items = []
        for url in unique:
            name = _text_server_name(text, url)
            try:
                items.append((name, _connection(name=name, server_url=url, transport=transport, authentication=authentication,
                                                header_name=header, credential=credential), ''))
            except HTTPException as exc:
                items.append((name, None, str(exc.detail)))
        return ChatConnectionBatch(tuple(items))
    named = re.search(r'(?:连接名称|服务名称|名称)\s*[:=：]\s*([^\s，；。,;]+)', text)
    return _connection(name=named[1] if named else urlsplit(urls[0]).hostname,
                       server_url=urls[0], transport=transport,
                       authentication=authentication, header_name=header, credential=credential)
