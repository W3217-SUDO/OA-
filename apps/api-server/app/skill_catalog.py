"""Discover public declarative skills from fixed catalogs, never run their code."""
from __future__ import annotations

import asyncio
import copy
import json
import re
import time
from collections import OrderedDict, deque
from typing import Literal
from urllib.parse import quote, urlsplit

import httpx
from fastapi import HTTPException

from app.github_agent_skills import github_skill_location, preview_github_skill

CatalogSource = Literal["skills-sh", "openai", "anthropic"]
JSON_LIMIT = 1024 * 1024
CACHE_TTL = 120
_cache: OrderedDict[str, tuple[float, object]] = OrderedDict()
_requests: OrderedDict[str, deque] = OrderedDict()
OFFICIAL_REPOS = {"openai": "openai/skills", "anthropic": "anthropics/skills"}
SEGMENT = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*")


def catalog_quota(username: str) -> None:
    """Bound per-worker public-catalog requests without touching business data."""
    now = time.monotonic()
    history = _requests.setdefault(username, deque())
    while history and now - history[0] >= 60:
        history.popleft()
    if len(history) >= 30:
        raise HTTPException(429, "技能目录请求过于频繁，请一分钟后重试")
    history.append(now)
    _requests.move_to_end(username)
    while len(_requests) > 2048:
        _requests.popitem(last=False)


def _segment(value: object) -> str:
    if not isinstance(value, str) or len(value) > 200 or not SEGMENT.fullmatch(value) or value in {".", ".."}:
        raise HTTPException(502, "技能来源返回了不合法的仓库或技能标识")
    return value


def _repo(value: object) -> str:
    if not isinstance(value, str) or len(value.split("/")) != 2:
        raise HTTPException(502, "技能来源返回了不合法的仓库")
    return "/".join(_segment(part) for part in value.split("/"))


async def _json(url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> object:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc not in {"api.github.com", "skills.sh"}:
        raise HTTPException(422, "技能目录地址不合法")
    if transport is None and url in _cache:
        expires, cached = _cache[url]
        if time.monotonic() < expires:
            _cache.move_to_end(url)
            return copy.deepcopy(cached)
        del _cache[url]
    try:
        async with asyncio.timeout(20), httpx.AsyncClient(timeout=httpx.Timeout(15, connect=5),
                trust_env=False, follow_redirects=False, transport=transport) as client:
            async with client.stream("GET", url, headers={"Accept": "application/json", "Accept-Encoding": "identity"}) as response:
                if response.status_code != 200:
                    raise HTTPException(502, f"技能来源 {parsed.netloc} 请求失败（HTTP {response.status_code}），请稍后重试")
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > JSON_LIMIT:
                        raise HTTPException(502, "技能目录超过 1 MiB 安全限制")
        result = json.loads(content)
    except (httpx.HTTPError, TimeoutError) as exc:
        raise HTTPException(502, f"技能来源 {parsed.netloc} 暂时无法连接，请稍后重试") from exc
    except (ValueError, RecursionError) as exc:
        raise HTTPException(502, "技能来源返回了无效目录，请稍后重试") from exc
    if transport is None:
        _cache[url] = (time.monotonic() + CACHE_TTL, result)
        _cache.move_to_end(url)
        while len(_cache) > 64:
            _cache.popitem(last=False)
    return result


async def _tree(repo: str, transport=None) -> tuple[str, list[str], str]:
    repo = _repo(repo)
    base = f"https://api.github.com/repos/{repo}"
    metadata = await _json(base, transport=transport)
    if not isinstance(metadata, dict) or not isinstance(metadata.get("default_branch"), str):
        raise HTTPException(502, "GitHub 仓库缺少默认分支")
    branch = metadata["default_branch"]
    if not branch or len(branch) > 200:
        raise HTTPException(502, "GitHub 默认分支不合法")
    commit = await _json(f"{base}/commits/{quote(branch, safe='')}", transport=transport)
    sha = commit.get("sha") if isinstance(commit, dict) else None
    if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise HTTPException(502, "GitHub 默认分支提交不合法")
    tree = await _json(f"{base}/git/trees/{sha}?recursive=1", transport=transport)
    if not isinstance(tree, dict) or tree.get("truncated") is not False or not isinstance(tree.get("tree"), list):
        raise HTTPException(502, "GitHub 目录不完整，不能安全确定技能路径")
    paths = []
    for entry in tree["tree"]:
        if not isinstance(entry, dict) or entry.get("type") != "blob" or entry.get("mode") != "100644":
            continue
        path = entry.get("path")
        if isinstance(path, str) and path.split("/")[-1] == "SKILL.md":
            # Validate GitHub-provided paths with the same download whitelist.
            try:
                github_skill_location(f"https://github.com/{repo}/blob/{sha}/" + quote(path, safe="/"))
            except ValueError as exc:
                raise HTTPException(502, "GitHub 返回了不安全的技能路径") from exc
            paths.append(path)
    return sha, paths, branch


async def catalog(source: CatalogSource, q: str = "", *, transport=None) -> dict:
    if source not in {"skills-sh", *OFFICIAL_REPOS}:
        raise HTTPException(422, "不支持的技能来源")
    query = q.strip()
    if len(query) > 100 or any(ord(char) < 32 for char in query):
        raise HTTPException(422, "搜索词不合法")
    items = []
    note = "目录名称来自实际文件夹；选择后读取完整技能说明与指令。"
    if source == "skills-sh":
        effective = query or "skill"
        raw = await _json(f"https://skills.sh/api/search?q={quote(effective, safe='')}&limit=20", transport=transport)
        if not isinstance(raw, dict) or not isinstance(raw.get("skills"), list):
            raise HTTPException(502, "skills.sh 返回了无效搜索目录")
        for item in raw["skills"][:20]:
            if not isinstance(item, dict):
                raise HTTPException(502, "skills.sh 返回了无效技能条目")
            repo, slug = _repo(item.get("source")), _segment(item.get("skillId"))
            identity = f"{repo}/{slug}"
            if item.get("id") != identity or not isinstance(item.get("name"), str):
                raise HTTPException(502, "skills.sh 技能标识与来源不一致")
            record = {"id": identity, "name": item["name"][:200], "description": "", "source": source,
                      "market_url": f"https://www.skills.sh/{identity}", "repo": repo, "skill_slug": slug}
            if isinstance(item.get("installs"), int) and not isinstance(item["installs"], bool) and item["installs"] >= 0:
                record["installs"] = item["installs"]
            items.append(record)
        note = "安装量由 skills.sh 返回；选择后从 GitHub 读取完整指令。" if query else "当前展示推荐关键词 skill 的真实搜索结果，可输入关键词搜索。"
    else:
        repo = OFFICIAL_REPOS[source]
        sha, paths, _ = await _tree(repo, transport)
        for path in paths:
            parts = path.split("/")
            if source == "openai":
                valid = len(parts) == 4 and parts[0] == "skills" and parts[1] in {".curated", ".system"}
            else:
                valid = len(parts) == 3 and parts[0] == "skills"
            if not valid:
                continue
            slug = _segment(parts[-2])
            if query and query.casefold() not in slug.casefold():
                continue
            url = f"https://github.com/{repo}/blob/{sha}/{quote(path, safe='/')}"
            items.append({"id": f"{repo}/{path}", "name": slug, "description": "", "source": source,
                          "market_url": url, "repo": repo, "skill_slug": slug, "url": url})
        items.sort(key=lambda item: item["id"])
    return {"items": items, "source": source, "query": query, "note": note}


async def catalog_preview(source: CatalogSource, identity: str, q: str = "", *, transport=None) -> dict:
    listing = await catalog(source, q, transport=transport)
    matches = [item for item in listing["items"] if item["id"] == identity]
    if len(matches) != 1:
        raise HTTPException(409, "所选技能已不在当前目录中，请刷新搜索后重选")
    item = matches[0]
    url = item.get("url")
    sha, paths, branch = await _tree(item["repo"], transport)
    if not url:
        matches = [path for path in paths if path.split("/")[-2:-1] == [item["skill_slug"]]]
        if len(matches) != 1:
            raise HTTPException(422, "仓库没有唯一匹配的 SKILL.md，不能安全安装该技能")
        url = f"https://github.com/{item['repo']}/blob/{sha}/{quote(matches[0], safe='/')}"
    preview = await preview_github_skill(url, transport=transport)
    try:
        stable = github_skill_location(f"https://github.com/{item['repo']}/blob/{quote(branch, safe='')}/{quote(preview['path'], safe='/')}")
    except ValueError as exc:
        raise HTTPException(422, "此仓库默认分支名称暂不支持，请使用高级 GitHub 链接安装固定提交") from exc
    return {**preview, "url": stable["url"], "source": stable["source"], "ref": branch,
            "resolved_commit": preview["ref"]}
