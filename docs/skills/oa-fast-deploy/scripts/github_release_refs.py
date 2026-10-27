#!/usr/bin/env python3
"""读取真实 GitHub 引用，生成供生产发布锁内校验的短期快照。"""

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


def checked_source(source):
    url = urlsplit(source)
    if (url.scheme != "https" or url.netloc != "github.com" or url.query or
            url.fragment or not re.fullmatch(r"/[^/]+/[^/]+\.git", url.path)):
        raise ValueError("发布源必须是无内嵌凭据的 GitHub HTTPS 仓库地址")
    return source


def checked_refs(refs):
    if not isinstance(refs, dict) or "refs/heads/dev" not in refs:
        raise ValueError("引用快照缺少 GitHub dev")
    for ref, commit in refs.items():
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError(f"引用提交号无效: {ref}")
        if not re.fullmatch(r"refs/heads/(dev|main)|refs/tags/v1\.[12]\.\d+(\^\{\})?", ref):
            raise ValueError(f"快照包含非发布引用: {ref}")
        if ref.endswith("^{}") and ref[:-3] not in refs:
            raise ValueError(f"标签解引用缺少原标签: {ref}")
    return refs


def load_snapshot(path, checksum, source):
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise ValueError("必须提供独立核对的快照 SHA256")
    content = Path(path).read_bytes()
    if hashlib.sha256(content).hexdigest() != checksum:
        raise ValueError("GitHub 引用快照 SHA256 不一致")
    snapshot = json.loads(content)
    if snapshot.get("schema_version") != 1 or snapshot.get("source_url") != checked_source(source):
        raise ValueError("GitHub 引用快照的来源或协议不一致")
    captured = datetime.fromisoformat(snapshot["captured_at"])
    if captured.tzinfo is None:
        raise ValueError("引用快照时间必须含时区")
    age = (datetime.now(timezone.utc) - captured).total_seconds()
    if not -30 <= age <= 300:
        raise ValueError("GitHub 引用快照已过期或时钟不一致，请重新读取")
    checked_refs(snapshot["refs"])
    return snapshot


def capture(repository, remote, output):
    def git(*arguments):
        environment = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        return subprocess.check_output(
            ["git", "-C", str(repository), *arguments], text=True,
            encoding="utf-8", timeout=45, env=environment,
        ).strip()

    source = checked_source(git("remote", "get-url", "--all", remote))
    if git("remote", "get-url", "--push", "--all", remote) != source:
        raise ValueError("GitHub 读取和推送地址不一致")
    refs = {}
    for line in git("ls-remote", source, "refs/heads/dev", "refs/heads/main", "refs/tags/v1.*").splitlines():
        commit, ref = line.split("\t")
        # Git 通配符也返回历史安全标签；它们不是正式版本领取记录。
        if not re.fullmatch(r"refs/heads/(dev|main)|refs/tags/v1\.[12]\.\d+(\^\{\})?", ref):
            continue
        if ref in refs:
            raise ValueError(f"重复引用: {ref}")
        refs[ref] = commit
    checked_refs(refs)
    snapshot = {
        "schema_version": 1, "source_url": source,
        "captured_at": datetime.now(timezone.utc).isoformat(), "refs": refs,
    }
    content = (json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with Path(output).open("xb") as handle:
        handle.write(content)
    return {"path": str(output), "sha256": hashlib.sha256(content).hexdigest(),
            "dev_commit": refs["refs/heads/dev"], "captured_at": snapshot["captured_at"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("capture")
    create.add_argument("--repository", required=True, type=Path)
    create.add_argument("--remote", default="github")
    create.add_argument("--output", required=True, type=Path)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--file", required=True, type=Path)
    inspect.add_argument("--sha256", required=True)
    inspect.add_argument("--source-url", required=True)
    args = parser.parse_args()
    if args.command == "capture":
        result = capture(args.repository, args.remote, args.output)
    else:
        result = load_snapshot(args.file, args.sha256, args.source_url)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
