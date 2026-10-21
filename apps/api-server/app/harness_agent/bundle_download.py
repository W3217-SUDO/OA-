"""按固定 Git 提交仅下载所选技能目录，不下载整仓无关文件。"""
import asyncio
import hashlib
from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import quote
from zipfile import ZipFile

from fastapi import HTTPException


def _require_download_response(response, message):
    if response.status_code == 200:
        return
    if response.status_code == 429 or (response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0"):
        raise HTTPException(429, "GitHub 下载请求额度已用尽，请在额度恢复后重试，未安装")
    raise HTTPException(422, f"{message}（HTTP {response.status_code}）")


async def _tree(client, repository, sha, *, recursive=False):
    response = await client.get("https://api.github.com/repos/" + repository + "/git/trees/" + sha,
                                params={"recursive": "1"} if recursive else None)
    _require_download_response(response, "无法读取固定提交的技能资源目录")
    if len(response.content) > 8 * 1024 * 1024:
        raise HTTPException(413, "技能资源目录索引超过 8 MiB 上限")
    value = response.json()
    if value.get("truncated") or not isinstance(value.get("tree"), list):
        raise HTTPException(422, "GitHub 技能资源目录不完整，未安装")
    return value["tree"]


async def download_directory(client, repository, commit, location):
    relative = PurePosixPath(location["path"]).parent
    sha = commit
    for part in relative.parts:
        entries = await _tree(client, repository, sha)
        child = next((item for item in entries if item.get("path") == part and item.get("type") == "tree"), None)
        if child is None:
            raise HTTPException(422, "固定提交不包含所选技能目录")
        sha = child["sha"]
    entries = await _tree(client, repository, sha, recursive=True)
    files = [item for item in entries if item.get("type") != "tree"]
    if (len(files) > 512 or any(item.get("type") != "blob" or item.get("mode") not in {"100644", "100755"}
            or not isinstance(item.get("size"), int) or not 0 <= item["size"] <= 8 * 1024 * 1024 for item in files)
            or sum(item["size"] for item in files) > 32 * 1024 * 1024):
        raise HTTPException(413, "技能目录包含不支持的链接或超过资源上限")
    semaphore = asyncio.Semaphore(4)

    async def download(item):
        path = item["path"]
        parsed = PurePosixPath(path)
        if parsed.is_absolute() or ".." in parsed.parts or "\\" in path or ":" in path:
            raise HTTPException(422, "技能资源目录含非法路径")
        async with semaphore:
            data = bytearray()
            # 按目录中的固定对象摘要读取原始字节，预览和安装统一使用 GitHub API。
            async with client.stream("GET", "https://api.github.com/repos/" + repository + "/git/blobs/" + quote(item["sha"], safe=""),
                                     headers={"Accept": "application/vnd.github.raw+json", "Accept-Encoding": "identity"}) as response:
                _require_download_response(response, "无法下载固定提交的技能资源文件")
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > item["size"]:
                        raise HTTPException(409, "技能资源大小与固定目录不同，未安装")
            blob = b"blob " + str(len(data)).encode() + b"\0" + data
            if len(data) != item["size"] or hashlib.sha1(blob, usedforsecurity=False).hexdigest() != item["sha"]:
                raise HTTPException(409, "技能资源摘要与固定提交不同，未安装")
            return path, bytes(data)

    downloaded = await asyncio.gather(*(download(item) for item in files))
    result = BytesIO()
    prefix = "fixed/" + (str(relative) + "/" if str(relative) != "." else "")
    with ZipFile(result, "w") as archive:
        for path, data in downloaded:
            archive.writestr(prefix + path, data)
    return result.getvalue()
