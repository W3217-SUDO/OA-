"""接口等价性快照比较工具。

用法：
    python -B scripts/perf/compare_snapshots.py before/ after/

逐文件比较规范化 JSON；发现差异时打印第一个差异路径并以非 0 退出码结束。
不提供"忽略字段"开关：只有 baseline 连续两次运行就不同的字段才允许写进
--ignore-file，且每一条都必须有书面理由。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def compare(before, after, path: str = "") -> str | None:
    """返回第一个差异的描述；完全一致返回 None。"""
    if type(before) is not type(after):
        return f"{path or '<root>'}: 类型不同 {type(before).__name__} != {type(after).__name__}"
    if isinstance(before, dict):
        missing = sorted(set(before) - set(after))
        extra = sorted(set(after) - set(before))
        if missing:
            return f"{path or '<root>'}: 改后缺少键 {missing[:8]}"
        if extra:
            return f"{path or '<root>'}: 改后多出键 {extra[:8]}"
        for key in before:
            difference = compare(before[key], after[key], f"{path}.{key}" if path else key)
            if difference:
                return difference
        return None
    if isinstance(before, list):
        if len(before) != len(after):
            return f"{path or '<root>'}: 长度不同 {len(before)} != {len(after)}"
        for index, (left, right) in enumerate(zip(before, after)):
            difference = compare(left, right, f"{path}[{index}]")
            if difference:
                return difference
        return None
    if before != after:
        return f"{path or '<root>'}: 值不同 {before!r} != {after!r}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="比较两份接口快照")
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--ignore-file", type=Path, default=None,
                        help="每行一个用例 ID 的点分字段路径；仅用于改前两次运行本身就不稳定的字段")
    parser.add_argument("--max-report", type=int, default=50)
    args = parser.parse_args()

    ignored: set[str] = set()
    if args.ignore_file and args.ignore_file.exists():
        ignored = {line.strip() for line in args.ignore_file.read_text(encoding="utf-8").splitlines()
                   if line.strip() and not line.startswith("#")}

    before_files = {path.stem: path for path in args.before.glob("*.json") if not path.name.startswith("_")}
    after_files = {path.stem: path for path in args.after.glob("*.json") if not path.name.startswith("_")}
    missing = sorted(set(before_files) - set(after_files))
    extra = sorted(set(after_files) - set(before_files))
    if missing:
        print(f"改后缺少用例：{missing}")
    if extra:
        print(f"改后多出用例：{extra}")

    mismatches = 0
    compared = 0
    for case_id in sorted(set(before_files) & set(after_files)):
        try:
            before = load(before_files[case_id])
            after = load(after_files[case_id])
        except json.JSONDecodeError as error:
            print(f"FAIL {case_id}: JSON 解析失败 {error}")
            mismatches += 1
            continue
        compared += 1
        difference = compare(before, after, case_id)
        if difference and not any(difference.startswith(prefix) or f".{prefix}" in difference for prefix in ignored):
            mismatches += 1
            if mismatches <= args.max_report:
                print(f"DIFF {difference}")
    print(f"\n比较 {compared} 个用例，差异 {mismatches} 个")
    return 1 if mismatches or missing else 0


if __name__ == "__main__":
    sys.exit(main())
