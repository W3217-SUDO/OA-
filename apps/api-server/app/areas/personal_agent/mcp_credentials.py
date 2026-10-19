"""在保存聊天或请求模型前阻止MCP配置及凭据进入消息链。"""
import re
from urllib.parse import parse_qsl, urlsplit

from fastapi import HTTPException

_CONTEXT = re.compile(r'\bmcp\b|mcpServers|mcp\.json', re.I)
_CONFIG = re.compile(r'["\'](?:mcpServers|mcp\.json)["\']\s*:', re.I)
_HEADERS = re.compile(r'["\'](?:headers|env)["\']\s*:', re.I)
_JSON_CREDENTIAL = re.compile(r'["\'](?:authorization|x-api-key|api[-_]?key|access[_-]?token|client_secret)["\']\s*:\s*["\'][^"\']+', re.I)
_CREDENTIAL = re.compile(r'Bearer\s+\S+|(?:api[-_ ]?key|token|secret|密钥|密码)\s*[:=：]\s*\S+', re.I)
_QUERY_KEY = re.compile(r'^(?:key|(?:api|access|secret|private|client|x[-_]?api)[_-]?key(?:[_-]?id)?|credentials?|signature|(?:(?:access|refresh|id|auth)[_-]?)?token|secret|client[_-]?secret|password|authorization|passwd|sig|auth|ossaccesskeyid|x[-_]amz[-_](?:signature|credential|security[-_]token))$', re.I)


def reject_mcp_chat_credentials(content):
    blocked = bool(_CONFIG.search(content) or _JSON_CREDENTIAL.search(content))
    if _CONTEXT.search(content) and (_CREDENTIAL.search(content) or (_CONFIG.search(content) and _HEADERS.search(content))):
        blocked = True
    for url in re.findall(r'https?://[^\s<>"\']+', content):
        try:
            parsed = urlsplit(url)
            if parsed.username is not None or parsed.password is not None or any(_QUERY_KEY.search(key) for key, _ in parse_qsl(parsed.query)):
                blocked = True
        except ValueError:
            # 不回显解析异常中的原地址。
            if _CONTEXT.search(content):
                blocked = True
    if blocked:
        raise HTTPException(422, 'MCP配置或凭据不能发送到聊天记录或模型，请在聊天内的个人MCP连接卡片中提交；地址密钥请改用请求头')
