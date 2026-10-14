"""连接声明校验、凭据字段与可打开的外部链接。"""
from copy import deepcopy
import json
import re
from urllib.parse import parse_qsl, urlsplit

from fastapi import HTTPException

_HEADER = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_SENSITIVE = re.compile(r"token|secret|password|api[-_]?key|authorization", re.I)


def connector_item(item):
    if item['kind'] != 'connector':
        raise HTTPException(422, '此能力包不是连接器')
    if not item.get('connection_configs'):
        raise HTTPException(422, '原包没有可配置的连接声明')
    return item


def validate_configuration(value, item):
    if not isinstance(value, dict) or set(value) != set(item['connection_configs']):
        raise HTTPException(422, '配置文件名称必须与此连接器原包一致')
    if len(json.dumps(value, ensure_ascii=False).encode()) > 65536:
        raise HTTPException(422, '连接配置超过64KB限制')
    for filename, config in value.items():
        if not isinstance(config, dict):
            raise HTTPException(422, '连接声明必须为JSON对象')
        if filename == 'mcp.json':
            servers = config.get('mcpServers')
            if not isinstance(servers, dict) or not 1 <= len(servers) <= 12:
                raise HTTPException(422, '请配置1至12个MCP服务')
            for name, server in servers.items():
                if not isinstance(name, str) or not name.strip() or not isinstance(server, dict):
                    raise HTTPException(422, 'MCP服务名称或配置无效')
                for key in ('headers', 'env'):
                    fields = server.get(key, {})
                    if not isinstance(fields, dict) or len(fields) > 32:
                        raise HTTPException(422, '请求头或环境变量配置无效')
                    if any(not isinstance(k, str) or not _HEADER.fullmatch(k) or not isinstance(v, str) or len(v) > 8192 or any(c in v for c in '\r\n\0') for k, v in fields.items()):
                        raise HTTPException(422, '请求头或环境变量包含无效名称、换行或过长内容')
                    if key == 'headers' and any(k.lower() in {'host', 'content-length', 'connection', 'proxy-authorization'} for k in fields):
                        raise HTTPException(422, '不能覆盖Host或传输控制请求头')
                if 'url' in server and not isinstance(server['url'], str):
                    raise HTTPException(422, '服务地址必须是字符串')
                if isinstance(server.get('url'), str):
                    try:
                        parsed = urlsplit(server['url'])
                    except ValueError as exc:
                        raise HTTPException(422, '服务地址格式无效') from exc
                    if '${' not in server['url'] and any(_SENSITIVE.search(key) for key, _ in parse_qsl(parsed.query)):
                        raise HTTPException(422, '请通过请求头填写凭据，不要把密钥保存在服务地址中')
    return deepcopy(value)


def secret_paths(configuration):
    paths = []
    for filename, config in configuration.items():
        if filename == 'mcp.json':
            for name, server in config.get('mcpServers', {}).items():
                for group in ('headers', 'env'):
                    for key in server.get(group, {}):
                        paths.append([filename, 'mcpServers', name, group, key])
    return paths


def path_value(configuration, path):
    current = configuration
    for part in path:
        current = current[part]
    return current


def set_path(configuration, path, value):
    current = configuration
    for part in path[:-1]:
        current = current[part]
    current[path[-1]] = value


def configured_secret(value):
    return bool(value.strip()) and '${' not in value and value != '<需自行配置>'


def public_configuration(configuration):
    result = deepcopy(configuration)
    fields = []
    for path in secret_paths(configuration):
        value = path_value(configuration, path)
        fields.append({'path': path, 'label': path[2] + ' · ' + path[-1], 'configured': configured_secret(value), 'template': value if not configured_secret(value) else ''})
        set_path(result, path, '')
    return result, fields


def public_link(value):
    if not isinstance(value, str) or len(value) > 2048 or any(char in value for char in '\r\n\0'):
        return None
    try:
        url = urlsplit(value)
    except ValueError:
        return None
    if url.scheme not in {'https', 'http'} or not url.hostname or url.username or url.password or '${' in value:
        return None
    if any(_SENSITIVE.search(key) for key, _ in parse_qsl(url.query)):
        return None
    return value


def configuration_links(configuration):
    result = []
    for filename, config in configuration.items():
        if filename == 'mcp.json':
            for name, server in config.get('mcpServers', {}).items():
                url = public_link(server.get('url'))
                if url:
                    result.append({'label': name + ' · 服务地址', 'url': url})
        if filename == 'cli.json' and isinstance(config.get('authUrlDomain'), str):
            domain = config['authUrlDomain']
            url = public_link(domain if '://' in domain else 'https://' + domain)
            if url:
                result.append({'label': '服务账号授权', 'url': url})
    return result


def reference_links(item):
    result, seen = [], set()
    for path, text in item.get('resources', {}).items():
        if path.rsplit('/', 1)[-1].lower() != 'readme.md':
            continue
        for value in re.findall(r'https?://[^\s<>\[\]()"`]+', text):
            url = public_link(value.rstrip('.,;'))
            if url and url not in seen:
                seen.add(url)
                result.append({'label': '参考链接 · ' + urlsplit(url).hostname, 'url': url})
            if len(result) >= 8:
                return result
    return result


def remote_servers(configuration):
    servers = configuration.get('mcp.json', {}).get('mcpServers', {})
    return [(name, server) for name, server in servers.items() if server.get('url') and server.get('type') in {'streamableHttp', 'streamable-http', 'http', 'sse'}]
