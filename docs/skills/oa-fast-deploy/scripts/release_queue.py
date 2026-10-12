#!/usr/bin/env python3
"""在生产版本锁内维护既有发布队列，不依赖服务器 Git 仓库或联网。"""

import argparse
import csv
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from github_release_refs import load_snapshot


VERSION = re.compile(r"1\.1\.(\d+)")
COMMIT = re.compile(r"[0-9a-f]{40}")
PENDING = {"assigned", "activating"}


def required(name):
    value = os.environ.get(name, "")
    if not value:
        raise ValueError(f"缺少明确发布配置: {name}")
    return value


def checked_field(value):
    if not value or any(character in value for character in "\r\n\t"):
        raise ValueError("发布参数不能为空或包含 TSV 控制符")
    return value


def read_queue(path):
    states = {}
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if row and VERSION.fullmatch(row[0]):
                if len(row) != 6 or not COMMIT.fullmatch(row[2]) or not row[3]:
                    raise ValueError(f"既有发布记录不完整: {row[0]}")
                states[row[0]] = row
    if not any(row[1] == "released" for row in states.values()):
        raise ValueError("生产队列缺少已激活基线，必须先完成元数据接管")
    return states


def validate_target(target, snapshot, states):
    if not COMMIT.fullmatch(target) or target != snapshot["refs"]["refs/heads/dev"]:
        raise ValueError("目标不是当前已发布的 GitHub dev")
    released = max((number for number, row in states.items() if row[1] == "released"),
                   key=lambda number: int(VERSION.fullmatch(number)[1]))
    tags = {ref[len("refs/tags/v"):]: commit for ref, commit in snapshot["refs"].items()
            if ref.startswith("refs/tags/v") and not ref.endswith("^{}")}
    missing = {number for number in tags if int(VERSION.fullmatch(number)[1]) > int(VERSION.fullmatch(released)[1]) and number not in states}
    if missing:
        raise ValueError(f"GitHub 已占用版本缺少生产队列接管记录: {sorted(missing)}")
    active_tag = f"refs/tags/v{released}"
    if snapshot["refs"].get(active_tag + "^{}", tags.get(released)) != states[released][2]:
        raise ValueError("生产已发布基线与 GitHub 标签不一致")
    return tags


def reservation(target, owner, scope, snapshot, states, consolidation):
    tags = validate_target(target, snapshot, states)
    for number in consolidation:
        if number not in states or states[number][1] != "assigned" or number not in tags:
            raise ValueError(f"待合并版本不是已接管且未激活的正式候选: {number}")
    pending = {number for number, row in states.items() if row[1] in PENDING}
    if pending - consolidation:
        raise ValueError(f"在先发布仍未完成: {sorted(pending - consolidation)}")
    highest = max(int(VERSION.fullmatch(number)[1]) for number in set(tags) | set(states))
    number = f"1.1.{highest + 1}"
    if consolidation:
        scope += ";consolidates=" + ",".join(sorted(consolidation))
    return number, [[number, "assigned", target, owner, scope, datetime.now(timezone.utc).isoformat()]]


def reassignment(number, old_target, new_target, owner, scope, snapshot, states):
    tags = validate_target(new_target, snapshot, states)
    if number in tags:
        raise ValueError(f"已有正式标签，不能改写该版本: {number}")
    row = states.get(number)
    if not row or row[1:4] != ["assigned", old_target, owner]:
        raise ValueError("当前有效领取记录的版本、提交或拥有者不匹配")
    if {value for value, current in states.items() if current[1] in PENDING} != {number}:
        raise ValueError("存在其他在先发布，不可单独重分配")
    timestamp = datetime.now(timezone.utc).isoformat()
    return number, [[number, "superseded", old_target, owner, row[4], timestamp],
                    [number, "assigned", new_target, owner, scope, timestamp]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    reserve = commands.add_parser("reserve")
    reserve.add_argument("target")
    reassign = commands.add_parser("reassign")
    reassign.add_argument("version")
    reassign.add_argument("old_target")
    reassign.add_argument("target")
    for command in (reserve, reassign):
        command.add_argument("owner")
        command.add_argument("scope")
    args = parser.parse_args()
    for value in vars(args).values():
        checked_field(value)
    if args.command == "reassign" and (not VERSION.fullmatch(args.version) or not COMMIT.fullmatch(args.old_target)):
        raise ValueError("原领取版本或提交无效")
    root = Path(os.environ.get("OA_RELEASE_ROOT", "/opt/sunhold-oa"))
    queue = root / "releases/queue.tsv"
    if not root.is_absolute() or not queue.is_file():
        raise ValueError("必须使用已接管的绝对部署根目录及既有生产队列")
    import fcntl

    lock_dir = root / "locks"
    lock_dir.mkdir(exist_ok=True)
    with (lock_dir / "version-allocation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        snapshot = load_snapshot(required("OA_RELEASE_REFS_FILE"), required("OA_RELEASE_REFS_SHA256"), required("OA_RELEASE_SOURCE_URL"))
        states = read_queue(queue)
        if args.command == "reserve":
            values = os.environ.get("OA_RELEASE_CONSOLIDATE_VERSIONS", "")
            consolidation = set(values.split(",")) if values else set()
            if any(not VERSION.fullmatch(value) for value in consolidation):
                raise ValueError("合并版本清单格式无效")
            number, rows = reservation(args.target, args.owner, args.scope, snapshot, states, consolidation)
        else:
            number, rows = reassignment(args.version, args.old_target, args.target, args.owner, args.scope, snapshot, states)
        with queue.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_NONE, quotechar=None).writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        print(number)


if __name__ == "__main__":
    main()
