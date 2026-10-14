"""生成私有试用目录；只处理声明文本，连接器不复制凭据或执行命令。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import yaml
import sys

from markdown_it import MarkdownIt
from workbuddy_package_format import CATEGORIES, REPOSITORY, license_kind, localized, markdown
from workbuddy_connector_config import sanitized_config

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api-server"))
from app.areas.capability_market.catalog import definition
from app.user_agent_skills import normalize_custom_skill


def read_index(root):
    tokens = MarkdownIt("commonmark").enable("table").parse((root / "CATALOG.md").read_text(encoding="utf-8"))
    rows, cells, result, category = [], [], {}, ""
    for token in tokens:
        if token.type == "heading_open" and token.tag == "h3":
            category = ""
        elif token.type == "inline" and not cells and not rows and token.level == 1:
            category = token.content
        elif token.type == "tr_open":
            rows = []
        elif token.type == "td_open":
            cells = [True]
        elif token.type == "inline" and cells:
            plain = "".join(child.content for child in (token.children or []) if child.type in {"text", "code_inline"})
            links = [child.attrGet("href") for child in (token.children or []) if child.type == "link_open"]
            rows.append((plain, links))
        elif token.type == "td_close":
            cells = []
        elif token.type == "tr_close":
            if len(rows) in {3, 4}:
                links = rows[0][1]
                if links:
                    path = links[0].removeprefix("./").strip("/")
                    if len(path.split("/")) == 2:
                        result[path] = {"name": rows[1][0] if len(rows) == 4 else rows[0][0],
                                        "description": rows[2][0] if len(rows) == 4 else rows[1][0],
                                        "requirements": rows[-1][0], "category": re.sub(r"（\d+）$", "", category)}
            rows = []
    return result


def package(root, archive, commit, index, assets):
    relative = root.relative_to(archive).as_posix()
    info = index[relative]
    kind = {"skills": "skill", "experts": "expert", "connectors": "connector"}[relative.split("/")[0]]
    identifier = hashlib.sha256(relative.encode()).hexdigest()[:24]
    item = {"id": identifier, "kind": kind, **info, "source_path": relative,
            "source": f"{REPOSITORY}/tree/{commit}/{relative}", "author": "", "version": "", "tags": [],
            "members": [], "avatar": "", "instruction": "", "resources": {}, "dependencies": [],
            "license": "未声明", "unavailable_reason": "", "license_documents": {},
            "connection_configs": {}, "required_credentials": [], "excluded_resources": []}
    for file in root.rglob("*"):
        if file.is_file() and (file.name.upper().startswith(("LICENSE", "NOTICE")) or file.name.upper().endswith(".LICENSE")):
            text = file.read_text(encoding="utf-8-sig")
            item["license_documents"][file.relative_to(root).as_posix()] = text
            if file.parent == root and license_kind(text):
                item["license"] = license_kind(text)
    try:
        if kind == "skill":
            metadata, item["instruction"] = markdown(root / "SKILL.md")
            item["description"] = localized(metadata.get("description_zh")) or localized(metadata.get("description"))
            item["version"] = str(metadata.get("version", ""))
            item["author"] = localized(metadata.get("author"))
            item["quick_prompts"] = metadata.get("quick_prompts", [])
            if "Bash" in str(metadata.get("allowed-tools", "")) or "bash" in str(metadata.get("allowed-tools", "")):
                item["unavailable_reason"] = "原技能声明需要 Bash，当前 OA 不执行第三方命令。"
        elif kind == "expert":
            metadata = json.loads((root / ".codebuddy-plugin/plugin.json").read_text(encoding="utf-8-sig"))
            if metadata.get("expertType") not in {"agent", "team"}:
                raise ValueError("专家类型缺失或未支持")
            item["kind"] = "team" if metadata["expertType"] == "team" else "expert"
            item["name"] = localized(metadata.get("profession")) or localized(metadata.get("displayName"))
            item["description"] = localized(metadata.get("displayDescription")) or localized(metadata.get("description"))
            item["category"] = CATEGORIES.get(metadata.get("categoryId"), info["category"])
            item["version"] = str(metadata.get("version", ""))
            item["author"] = localized(metadata.get("author", {}).get("name"))
            item["tags"] = [localized(value) for value in metadata.get("tags", [])]
            item["quick_prompts"] = [localized(value) for value in metadata.get("quickPrompts", [])]
            primary = (root / "agents" / (metadata["agentName"] + ".md")).resolve()
            if not primary.is_relative_to(root):
                raise ValueError("主专家路径越过能力包边界")
            _, item["instruction"] = markdown(primary)
            for agent in metadata["agents"]:
                path = (root / agent).resolve()
                if not path.is_relative_to(root):
                    raise ValueError("成员路径越过能力包边界")
                member_definition, _ = markdown(path)
                item["members"].append({"id": path.stem, "name": localized(member_definition.get("displayName")) or path.stem,
                                        "profession": localized(member_definition.get("profession"))})
            dependencies = metadata.get("dependencies", {}).get("connectors", [])
            if not isinstance(dependencies, list) or any(not isinstance(value, str) for value in dependencies):
                raise ValueError("未支持的连接器依赖格式")
            item["dependencies"] = dependencies
            if metadata.get("avatar"):
                image = (root / metadata["avatar"]).resolve()
                if not image.is_relative_to(root) or image.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                    raise ValueError("头像路径或格式无效")
                content = image.read_bytes()
                if len(content) > 1024 * 1024 or not (content.startswith(b"\x89PNG\r\n\x1a\n") or content.startswith(b"\xff\xd8\xff")):
                    raise ValueError("头像不是允许的 PNG/JPEG 图片")
                filename = identifier + image.suffix.lower()
                (assets / filename).write_bytes(content)
                item["avatar_file"] = filename
                item["avatar_sha256"] = hashlib.sha256(content).hexdigest()
        else:
            files = [file for file in (root / "mcp.json", root / "cli.json") if file.is_file()]
            if not files:
                raise ValueError("未找到 MCP 或 CLI 连接配置")
            for file in files:
                config = json.loads(file.read_text(encoding="utf-8-sig"))
                sanitized, required = sanitized_config(config)
                item["connection_configs"][file.name] = sanitized
                item["required_credentials"].extend(file.name + "." + path for path in required)
            config = json.loads(files[0].read_text(encoding="utf-8-sig"))
            protocol = "MCP" if files[0].name == "mcp.json" else "CLI"
            item["tags"] = [protocol]
            item["instruction"] = f"{info['name']}\n{info['description']}\n接入方式：{protocol}\n前置条件：{info['requirements']}"
            if protocol == "MCP":
                servers = config.get("mcpServers", {})
                if not isinstance(servers, dict) or not servers:
                    raise ValueError("MCP 服务配置不完整")
                item["dependencies"] = list(servers)
            item["unavailable_reason"] = "配置已收录，需接入对应运行时并完成服务账号授权；当前未连接。"
        if not item["name"] or not item["description"] or not item["instruction"]:
            raise ValueError("名称、说明或指令缺失")
        for file in sorted(root.rglob("*.md")):
            parts = file.relative_to(root).parts
            if any(part in {"scripts", "tests", "test", "fixtures", "node_modules", ".git"} for part in parts):
                item["excluded_resources"].append(file.relative_to(root).as_posix())
                continue
            text = file.read_text(encoding="utf-8-sig")
            item["resources"][file.relative_to(root).as_posix()] = text
        body = item["instruction"]
        if not item["unavailable_reason"]:
            if item["kind"] == "team":
                item["unavailable_reason"] = "需要独立的专家团调度运行时，当前不能执行团队协作。"
            elif item["dependencies"]:
                item["unavailable_reason"] = "需要完成原包声明的外部连接器授权：" + ", ".join(item["dependencies"])
            elif re.search(r"(?:scripts/|\bdws\s|\bBash\b|\bnpm install\b|\bTeamCreate\b|\bAgentTool\b)", body):
                item["unavailable_reason"] = "需要脚本、CLI 或多智能体运行环境，当前未接入。"
            elif not 10 <= len(body) <= 60000:
                item["unavailable_reason"] = "指令长度不满足当前助手限制，未截断原文。"
    except (ValueError, KeyError, OSError, StopIteration, yaml.YAMLError) as exc:
        item["name"], item["description"] = info["name"], info["description"]
        item["unavailable_reason"] = "包格式需要适配，未安装：" + type(exc).__name__
    item["sha256"] = hashlib.sha256(item["instruction"].encode()).hexdigest()
    if not item["unavailable_reason"]:
        try:
            normalize_custom_skill(definition(item), source=item["source"])
        except ValueError as exc:
            item["unavailable_reason"] = "原包字段超过当前助手格式限制：" + str(exc)
    return item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root, output = args.archive.resolve(), args.output.resolve()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    index = read_index(root)
    assets = output.parent / "avatars"
    assets.mkdir(parents=True, exist_ok=True)
    items = [package(path, root, commit, index, assets) for group in ("skills", "experts", "connectors")
             for path in sorted((root / group).iterdir()) if path.is_dir()]
    expected = {group: len([path for path in (root / group).iterdir() if path.is_dir()]) for group in ("skills", "experts", "connectors")}
    if len(items) != sum(expected.values()):
        raise RuntimeError("归档数量不一致，禁止生成不完整目录")
    definitions = output.parent / "items"
    definitions.mkdir(parents=True, exist_ok=True)
    summaries = []
    for item in items:
        content = json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        (definitions / (item["id"] + ".json")).write_bytes(content)
        summaries.append({**{key: value for key, value in item.items() if key not in {"instruction", "resources", "license_documents", "connection_configs", "excluded_resources"}},
                          "excluded_resource_count": len(item["excluded_resources"]),
                          "detail_sha256": hashlib.sha256(content).hexdigest()})
    value = {"schema_version": 1, "repository": REPOSITORY, "source_commit": commit,
             "items": summaries, "archive_counts": expected}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"counts": expected, "items": len(items), "available": sum(not item["unavailable_reason"] for item in items),
                      "bytes": output.stat().st_size, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
