"""安装固定 GitHub 提交中的完整技能目录，资源仅经授权技能记录读取。"""

import asyncio
import hashlib
from io import BytesIO
import json
from pathlib import PurePosixPath
import re
import stat
from urllib.parse import quote
from zipfile import BadZipFile, ZipFile

import httpx
from fastapi import HTTPException
from .paths import filesystem_path


def storage_root():
    from app.areas.personal_agent.service import _storage_root
    from app.core.constants import UPLOAD_ROOT
    root = filesystem_path(_storage_root().parent / "private-skill-bundles")
    public = filesystem_path(UPLOAD_ROOT)
    if root == public or public in root.parents:
        raise HTTPException(503, "技能资源不能存放在公开附件目录中")
    return root


def bundle_directory(identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r"[a-f0-9]{64}", identifier):
        raise HTTPException(409, "技能资源摘要无效")
    return filesystem_path(storage_root() / identifier)


def _unpack(content, location, expected, source_text=None):
    relative = PurePosixPath(location["path"]).parent
    selected = {}
    try:
        with ZipFile(BytesIO(content)) as archive:
            roots = {item.filename.split("/", 1)[0] for item in archive.infolist()}
            if len(roots) != 1:
                raise ValueError("技能仓库归档目录无效")
            prefix = next(iter(roots)) + "/" + (str(relative) + "/" if str(relative) != "." else "")
            total = 0
            for item in archive.infolist():
                if not item.filename.startswith(prefix) or item.is_dir():
                    continue
                path = item.filename[len(prefix):]
                parts = PurePosixPath(path)
                if (not parts.parts or parts.is_absolute() or ".." in parts.parts or "\\" in path
                        or ":" in path or any(ord(char) < 32 for char in path)
                        or stat.S_ISLNK(item.external_attr >> 16)
                        or path.casefold() in {name.casefold() for name in selected}
                        or any(part.endswith((".", " ")) or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part)
                               for part in parts.parts)):
                    raise ValueError("技能包包含非法路径、链接或重复文件")
                total += item.file_size
                if item.file_size > 8 * 1024 * 1024 or total > 32 * 1024 * 1024 or len(selected) >= 512:
                    raise ValueError("技能目录超过文件大小或数量上限")
                selected[path] = archive.read(item)
    except (BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise HTTPException(422, "GitHub 技能归档损坏，未安装") from exc
    skill_content = selected.get("SKILL.md", b"")
    if source_text is not None:
        # 市场索引使用 UTF-8 文本及统一换行；包内原始字节仍按资源摘要保存。
        try:
            indexed_text = skill_content.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError as exc:
            raise HTTPException(409, "市场技能原文不是 UTF-8，未安装") from exc
        valid = indexed_text == source_text and hashlib.sha256(source_text.encode("utf-8")).hexdigest() == expected
    else:
        valid = hashlib.sha256(skill_content).hexdigest() == expected
    if "SKILL.md" not in selected or not valid:
        raise HTTPException(409, "技能内容在预览后发生变化，请重新预览安装")
    manifest = {path: hashlib.sha256(data).hexdigest() for path, data in sorted(selected.items())}
    identifier = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    directory = bundle_directory(identifier)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for path, data in selected.items():
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            with target.open("xb") as handle:
                handle.write(data)
        except FileExistsError:
            if target.is_symlink() or target.read_bytes() != data:
                raise HTTPException(409, "已安装技能资源与摘要不符，未覆盖原文件")
    return {"id": identifier, "files": manifest}


async def install_bundle(preview):
    """只在用户确认安装时下载；密钥及 OA 登录信息不传向 GitHub。"""
    from app.github_agent_skills import github_skill_location
    from .bundle_download import download_directory
    location = github_skill_location(preview["source"])
    repository = "/".join(quote(location[key], safe="") for key in ("owner", "repo"))
    try:
        async with asyncio.timeout(60), httpx.AsyncClient(timeout=30, trust_env=False, follow_redirects=False) as client:
            response = await client.get("https://api.github.com/repos/" + repository + "/commits/" + quote(location["ref"], safe=""))
            if response.status_code != 200:
                raise HTTPException(422, "无法确认 GitHub 技能的固定提交，未安装")
            commit = response.json().get("sha")
            if not isinstance(commit, str) or not re.fullmatch(r"[a-f0-9]{40}", commit):
                raise HTTPException(422, "GitHub 返回的技能提交无效")
            if re.fullmatch(r"[a-f0-9]{40}", location["ref"]) and commit != location["ref"]:
                raise HTTPException(409, "GitHub 返回的提交与市场固定来源不同，未安装")
            data = await download_directory(client, repository, commit, location)
        result = await asyncio.to_thread(_unpack, data, location, preview["sha256"], preview.get("source_text"))
        return {**result, "commit": commit}
    except (httpx.HTTPError, TimeoutError) as exc:
        raise HTTPException(502, "完整技能目录下载失败，未安装") from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc


def read_resource(bundle, path):
    files = bundle.get("files", {})
    if not isinstance(files, dict) or path not in files:
        raise HTTPException(404, "技能包不包含该资源")
    directory = bundle_directory(bundle.get("id"))
    relative = PurePosixPath(path)
    if relative.is_absolute() or ".." in relative.parts or "\\" in path or ":" in path:
        raise HTTPException(422, "技能资源路径无效")
    target = directory / path
    if target.is_symlink() or directory.resolve() not in target.resolve().parents:
        raise HTTPException(409, "技能资源不能指向包外文件")
    try:
        data = target.read_bytes()
    except FileNotFoundError as exc:
        raise HTTPException(409, "技能资源文件缺失，请重新安装此技能包") from exc
    if hashlib.sha256(data).hexdigest() != files[path]:
        raise HTTPException(409, "技能资源摘要不符，已阻止读取")
    return data
