"""按法院短信里的送达链接列出并下载文书（人民法院在线服务 zxfw.court.gov.cn）。

只用标准库，可在技能沙箱（仅准公网 HTTP/HTTPS）里直接运行：
    python fetch_court_docs.py "<短信完整链接>" [--list-only]
沙箱不保留文件，也拿不到 OA 凭据：要把文书存进 OA，请改用 OA 工具“下载法院送达文书”
（POST /documents/court-service/fetch），它在服务器上下载并保存为附件。本脚本用于预览和核对。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlsplit
import urllib.request

API = "https://zxfw.court.gov.cn/yzw/yzw-zxfw-sdfw/api/v1/sdfw/getWsListBySdbhNew"
REFERER = "https://zxfw.court.gov.cn/zxfw/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SERVICE_HOSTS = {"zxfw.court.gov.cn"}
_TOKEN = re.compile(r"[A-Za-z0-9]{8,128}")
MAX_FILE = 20 * 1024 * 1024


def parse_service_link(link: str) -> dict:
    """从送达链接（参数可能在 # 之后）取出 qdbh / sdbh / sdsin。"""
    text = str(link or "").strip()
    match = re.search(r"https?://[^\s，,。；;]+", text)
    if not match:
        raise ValueError("没有找到送达链接，请粘贴短信里完整的 https://zxfw.court.gov.cn/... 链接")
    url = urlsplit(match.group(0))
    if url.scheme != "https" or (url.hostname or "").lower() not in SERVICE_HOSTS:
        raise ValueError("只支持人民法院在线服务 zxfw.court.gov.cn 的送达链接")
    query = url.query + "&" + (url.fragment.split("?", 1)[1] if "?" in url.fragment else "")
    values = {key: items[0] for key, items in parse_qs(query).items() if items}
    result = {}
    for key in ("qdbh", "sdbh", "sdsin"):
        value = values.get(key, "")
        if not _TOKEN.fullmatch(value):
            raise ValueError(f"送达链接缺少有效的 {key} 参数，请确认链接完整")
        result[key] = value
    return result


def request_body(params: dict) -> bytes:
    return json.dumps({"sdbh": params["sdbh"], "qdbh": params["qdbh"], "sdsin": params["sdsin"]}).encode()


def headers() -> dict:
    return {"Content-Type": "application/json;charset=UTF-8", "User-Agent": USER_AGENT, "Referer": REFERER,
            "Origin": "https://zxfw.court.gov.cn", "Accept": "application/json, text/plain, */*"}


def documents_from_response(payload: dict) -> list[dict]:
    """把接口返回整理成统一清单；接口报错时抛出原始提示。"""
    if not isinstance(payload, dict):
        raise ValueError("法院接口返回格式无法识别")
    if payload.get("code") not in (200, "200") or payload.get("success") is False:
        raise ValueError("法院接口拒绝：" + str(payload.get("msg") or payload.get("code")))
    items = payload.get("data") or []
    if isinstance(items, dict):
        items = items.get("list") or items.get("records") or []
    result = []
    for item in items:
        if not isinstance(item, dict) or not item.get("wjlj"):
            continue
        extension = str(item.get("c_wjgs") or "pdf").lower().lstrip(".")
        name = re.sub(r'[\\/:*?"<>|\s]+', "_", str(item.get("c_wsmc") or "法院文书")).strip("_") or "法院文书"
        name = re.sub(r"(?i)\.(pdf|ofd|docx?|jpe?g|png)$", "", name) or "法院文书"
        result.append({"name": name, "extension": extension, "url": str(item["wjlj"]),
                       "document_no": str(item.get("c_wsbh") or ""), "court": str(item.get("c_fymc") or ""),
                       "court_code": str(item.get("c_fybh") or "")})
    return result


def _open(request, limit):
    with urllib.request.urlopen(request, timeout=25) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("文件超过 20MB 上限")
    return data


def main(arguments: list[str]) -> int:
    if not arguments:
        print("用法：fetch_court_docs.py <送达链接> [--list-only]", file=sys.stderr)
        return 2
    params = parse_service_link(arguments[0])
    payload = json.loads(_open(urllib.request.Request(API, data=request_body(params), headers=headers()), 2 * 1024 * 1024))
    documents = documents_from_response(payload)
    output = Path("/work/court-docs") if Path("/work").is_dir() else Path.cwd() / "court-docs"
    if "--list-only" not in arguments:
        output.mkdir(parents=True, exist_ok=True)
        for item in documents:
            data = _open(urllib.request.Request(item.pop("url"), headers={"User-Agent": USER_AGENT, "Referer": REFERER}), MAX_FILE)
            path = output / f"{item['name']}.{item['extension']}"
            path.write_bytes(data)
            item.update({"size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                         "is_pdf": data.startswith(b"%PDF"), "saved_to": str(path)})
    else:
        for item in documents:
            item.pop("url")
    print(json.dumps({"court": documents[0]["court"] if documents else "", "count": len(documents),
                      "documents": documents, "files_persisted": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
