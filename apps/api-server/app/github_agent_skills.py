"""Import declarative SKILL.md instructions, never repository executables."""
from __future__ import annotations

import asyncio
import hashlib
import re
from urllib.parse import quote, unquote, urlsplit

import httpx
import yaml
from fastapi import HTTPException

from app.user_agent_skills import normalize_custom_skill

DOWNLOAD_LIMIT = 128 * 1024
DOWNLOAD_TIMEOUT = 20


def github_skill_location(url: str) -> dict[str, str]:
    parsed = urlsplit(url.strip())
    if (parsed.scheme != "https" or parsed.netloc not in {"github.com", "raw.githubusercontent.com"}
            or parsed.query or parsed.fragment):
        raise ValueError("只支持无查询参数的 GitHub HTTPS 技能链接")
    segments = [unquote(part) for part in parsed.path.strip("/").split("/")]
    if any(not part or part in {".", ".."} or re.search(r"[\\/\x00-\x20\x7f]", part) for part in segments):
        raise ValueError("GitHub 路径不合法")
    if len(segments) < 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in segments[:2]):
        raise ValueError("GitHub 仓库名称不合法")
    owner, repo = segments[:2]
    if parsed.netloc == "raw.githubusercontent.com":
        if len(segments) < 4:
            raise ValueError("请提供完整 SKILL.md 文件链接")
        ref, path = segments[2], segments[3:]
    elif len(segments) == 2:
        ref, path = "main", ["SKILL.md"]
    elif len(segments) >= 4 and segments[2] in {"blob", "tree"}:
        ref, path = segments[3], segments[4:]
        if segments[2] == "tree" and (not path or path[-1] != "SKILL.md"):
            path.append("SKILL.md")
    else:
        raise ValueError("请提供仓库、tree 目录或 blob/SKILL.md 链接；分支名含斜线时请使用提交 SHA")
    if not path or path[-1] != "SKILL.md":
        raise ValueError("仅支持 SKILL.md 技能文件")
    encoded_path = "/".join(quote(part, safe="") for part in path)
    source = f"https://github.com/{quote(owner, safe='')}/{quote(repo, safe='')}/blob/{quote(ref, safe='')}/" + "/".join(quote(part, safe="") for part in path)
    return {"url": source, "source": source, "owner": owner, "repo": repo, "ref": ref,
            "path": "/".join(path),
            "contents_url": f"https://api.github.com/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/contents/{encoded_path}"}


def parse_github_skill(content: bytes, location: dict[str, str]) -> dict:
    if len(content) > DOWNLOAD_LIMIT:
        raise ValueError("技能文件超过 128 KiB")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("SKILL.md 必须是 UTF-8 文本") from exc
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md 缺少包含 name 和 description 的 YAML 元数据")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ValueError("SKILL.md 元数据未闭合")
    try:
        metadata = yaml.safe_load("".join(lines[1:end]))
    except yaml.YAMLError as exc:
        raise ValueError("SKILL.md YAML 元数据格式不正确") from exc
    if not isinstance(metadata, dict) or not all(isinstance(metadata.get(key), str) for key in ("name", "description")):
        raise ValueError("SKILL.md 的 name 和 description 必须是文本")
    instruction = "".join(lines[end + 1:]).strip()
    if len(instruction) > 6000:
        raise ValueError("技能正文超过当前 6000 字符上限，未截断或安装")
    try:
        record = normalize_custom_skill({"name": metadata["name"], "description": metadata["description"],
                                        "category": "GitHub", "instruction": instruction}, source=location["source"])
    except ValueError as exc:
        raise ValueError(f"技能字段不满足当前格式限制：{exc}") from exc
    return {**{key: value for key, value in location.items() if key != "contents_url"},
            "name": record["name"], "description": record["description"], "instruction": record["instruction"],
            "sha256": hashlib.sha256(content).hexdigest()}


async def preview_github_skill(url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> dict:
    try:
        location = github_skill_location(url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        async with asyncio.timeout(DOWNLOAD_TIMEOUT), httpx.AsyncClient(timeout=httpx.Timeout(15, connect=5), follow_redirects=False,
                                     trust_env=False, transport=transport) as client:
            async with client.stream("GET", location["contents_url"], params={"ref": location["ref"]},
                                     headers={"Accept": "application/vnd.github.raw+json", "Accept-Encoding": "identity"}) as response:
                if response.status_code != 200:
                    raise HTTPException(status_code=422, detail=f"GitHub 文件读取失败（HTTP {response.status_code}）；请核对分支和 SKILL.md 路径，仓库根链接默认 main")
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > DOWNLOAD_LIMIT:
                        raise HTTPException(status_code=422, detail="技能文件超过 128 KiB")
        return parse_github_skill(bytes(content), location)
    except (httpx.HTTPError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail="GitHub 暂时无法连接，请稍后重试") from exc
    except (ValueError, RecursionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
