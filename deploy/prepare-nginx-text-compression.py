"""为已有 OA HTTPS 站点准备压缩 include 补丁，不安装、不重载 Nginx。

解析依赖 crossplane==0.5.8，仅安装到部署工具环境，不加入 API 依赖。
输出目录必须在仓库外；审核 diff 后，由发布锁内流程校验原配置哈希、
安装片段并应用补丁。nginx -t 或应用包激活失败时撤销本轮补丁和片段。
"""

import argparse
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import crossplane


def digest(content):
    return hashlib.sha256(content).hexdigest()


def parse_config(path):
    payload = crossplane.parse(str(path), single=True, check_ctx=False)
    if payload["status"] != "ok":
        raise ValueError(f"Nginx 配置解析失败：{payload['errors']}")
    return payload["config"][0]["parsed"]


def comparable(nodes):
    return [
        {"directive": node["directive"], "args": node["args"],
         **({"block": comparable(node["block"])} if "block" in node else {})}
        for node in nodes
    ]


def target_server(nodes, server_name):
    matches = [
        node for node in nodes if node["directive"] == "server"
        and any(child["directive"] == "server_name" and server_name in child["args"]
                for child in node["block"])
        and any(child["directive"] == "listen" and "ssl" in child["args"]
                for child in node["block"])
    ]
    if len(matches) != 1:
        raise ValueError("必须唯一定位指定域名的已有 HTTPS server")
    return matches[0]


def target_locations(server):
    result = []
    for route in ("/api/", "/"):
        matches = [node for node in server["block"]
                   if node["directive"] == "location" and node["args"] == [route]]
        if len(matches) != 1:
            raise ValueError(f"必须唯一定位已有 location {route}")
        if any(node["directive"].startswith("gzip") for node in matches[0]["block"]):
            raise ValueError(f"location {route} 已有压缩策略，必须先人工核对")
        result.append(matches[0])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-config", type=Path, required=True)
    parser.add_argument("--server-name", required=True)
    parser.add_argument("--installed-fragment", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    fragment_path = PurePosixPath(args.installed_fragment)
    if not fragment_path.is_absolute() or ".." in fragment_path.parts or not re.fullmatch(
        r"/[A-Za-z0-9_./-]+", args.installed_fragment
    ):
        raise ValueError("片段安装路径必须是无变量、无通配符的 Linux 绝对路径")
    output = args.output_dir.resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("补丁和原配置备份不得写入源码仓库")
    original = args.site_config.read_bytes()
    lines = original.decode("utf-8").splitlines(keepends=True)
    before = parse_config(args.site_config)
    locations = target_locations(target_server(before, args.server_name))
    if args.installed_fragment in original.decode("utf-8"):
        raise ValueError("配置已引用此安装路径，不得重复安装或覆盖已有片段")
    # 解析器确定块归属；仅支持独立的单行块头，复杂格式明确阻断而非猜测。
    for location in sorted(locations, key=lambda node: node["line"], reverse=True):
        index = location["line"] - 1
        header = lines[index]
        if not re.fullmatch(r"[ \t]*location[ \t]+[^{}\r\n]+\{[ \t]*(?:#[^\r\n]*)?\r?\n", header):
            raise ValueError("目标 location 块头格式需人工处理，不自动改写配置")
        indent = re.match(r"[ \t]*", header).group() + "    "
        newline = "\r\n" if header.endswith("\r\n") else "\n"
        lines.insert(index + 1, f'{indent}include "{args.installed_fragment}";{newline}')
    candidate = "".join(lines).encode("utf-8")
    output.mkdir(parents=True, exist_ok=False)
    (output / "site.before.conf").write_bytes(original)
    candidate_path = output / "site.after.conf"
    candidate_path.write_bytes(candidate)
    after = parse_config(candidate_path)
    for location in target_locations(target_server(after, args.server_name)):
        inserted = [node for node in location["block"] if node["directive"] == "include"
                    and node["args"] == [args.installed_fragment]]
        if len(inserted) != 1:
            raise ValueError("补丁必须仅向两个已有块各插入一次 include")
        location["block"].remove(inserted[0])
    if comparable(before) != comparable(after):
        raise ValueError("补丁改变了 include 之外的路由或指令，禁止安装")
    snippet = Path(__file__).with_name("nginx-oa-text-compression.location.conf").read_bytes()
    (output / "compression.location.conf").write_bytes(snippet)
    diff = "".join(difflib.unified_diff(
        original.decode("utf-8").splitlines(keepends=True), lines,
        fromfile="site.before.conf", tofile="site.after.conf",
    ))
    (output / "site.patch").write_bytes(diff.encode("utf-8"))
    rollback = "".join(difflib.unified_diff(
        lines, original.decode("utf-8").splitlines(keepends=True),
        fromfile="site.after.conf", tofile="site.before.conf",
    ))
    (output / "site.rollback.patch").write_bytes(rollback.encode("utf-8"))
    receipt = {"status": "prepared_not_installed", "server_name": args.server_name,
               "installed_fragment": args.installed_fragment, "added_locations": ["/api/", "/"],
               "before_sha256": digest(original), "after_sha256": digest(candidate),
               "fragment_sha256": digest(snippet), "patch_sha256": digest(diff.encode("utf-8")),
               "rollback_patch_sha256": digest(rollback.encode("utf-8")),
               "other_directives_unchanged": True, "nginx_validation": "not_performed",
               "runtime_acceptance": "not_performed"}
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
