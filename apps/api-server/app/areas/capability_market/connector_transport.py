"""远程连接验证仅访问公网HTTPS，并固定本次解析的IP与TLS主机名。"""
import asyncio
import ipaddress
import socket
from urllib.parse import parse_qsl, urlsplit

from fastapi import HTTPException
import httpx2

from .connector_format import _SENSITIVE


def validate_endpoint(url):
    if not isinstance(url, str) or len(url) > 2048 or any(value in url for value in ('\r', '\n', '\0', '${')):
        raise HTTPException(422, '请完整填写公网HTTPS服务地址')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise HTTPException(422, '连接验证只允许不含用户名和密码的HTTPS服务地址')
    try:
        if parsed.port not in (None, 443):
            raise HTTPException(422, '连接验证只允许HTTPS默认端口443')
    except ValueError as exc:
        raise HTTPException(422, '服务端口格式无效') from exc
    if any(_SENSITIVE.search(key) for key, _ in parse_qsl(parsed.query)):
        raise HTTPException(422, '请通过请求头配置密钥，不要把凭据放入服务地址')


async def public_address(host):
    try:
        rows = await asyncio.to_thread(socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HTTPException(422, '服务域名解析失败') from exc
    addresses = list(dict.fromkeys(row[4][0] for row in rows))
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise HTTPException(422, '不能连接内网、回环或保留地址')
    return addresses[0]


class BoundedStream(httpx2.AsyncByteStream):
    def __init__(self, stream):
        self.stream = stream

    async def __aiter__(self):
        total = 0
        async for chunk in self.stream:
            total += len(chunk)
            if total > 2 * 1024 * 1024:
                raise HTTPException(502, '服务响应超过2MB验证限制')
            yield chunk

    async def aclose(self):
        await self.stream.aclose()


class PublicHttpsTransport(httpx2.AsyncBaseTransport):
    def __init__(self):
        self.inner = httpx2.AsyncHTTPTransport(trust_env=False, retries=0)
        self.failure = ''

    async def handle_async_request(self, request):
        try:
            validate_endpoint(str(request.url))
            host = request.url.host
            address = await public_address(host)
        except HTTPException as exc:
            self.failure = exc.detail
            raise
        # 固定连接IP，保留原始Host与SNI，防止二次解析切换到内网地址。
        pinned = httpx2.Request(request.method, request.url.copy_with(host=address), headers=request.headers,
                                stream=request.stream, extensions={**request.extensions, 'sni_hostname': host})
        response = await self.inner.handle_async_request(pinned)
        if response.status_code in (401, 403):
            self.failure = f'服务返回HTTP{response.status_code}，请先授权或核对请求头中的凭据'
        elif response.status_code >= 400:
            self.failure = f'服务返回HTTP{response.status_code}，请核对MCP地址和接入方式'
        response.stream = BoundedStream(response.stream)
        return response

    async def aclose(self):
        await self.inner.aclose()
