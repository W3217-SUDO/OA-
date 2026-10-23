"""官方案号归一化：清洗空格与括号、拆分多案号、生成由精确到宽松的检索变体。

只用标准库，既可在技能沙箱里直接运行，也被 OA 后端导入复用：
    python normalize_case_no.py "（2025）渝 0 103民 初 40009 号"
"""

from __future__ import annotations

import json
import re
import sys

_YEAR = re.compile(r"（(\d{4})）")
_CASE = re.compile(r"（(\d{4})）([一-鿿]{1,2}\d{0,4})([一-鿿]{1,6}?)(\d+)号?")
_LEVELS = (("终", "二审"), ("申", "再审"), ("再", "再审"), ("执", "执行"), ("初", "一审"))


def clean(value: str) -> str:
    """去空白、统一全角括号，并补齐年份后缺失的右括号。"""
    text = re.sub(r"\s+", "", str(value or "")).replace("(", "（").replace(")", "）")
    text = re.sub(r"〔|\[", "（", text)
    text = re.sub(r"〕|\]", "）", text)
    return re.sub(r"（(\d{4})(?!\d|）)", r"（\1）", text)


def split_numbers(value: str) -> list[str]:
    """一个字段里塞了多个案号时，按“（YYYY）”边界拆开。"""
    text = clean(value)
    starts = [match.start() for match in _YEAR.finditer(text)]
    if len(starts) <= 1:
        return [text] if text else []
    return [text[start:end] for start, end in zip(starts, [*starts[1:], len(text)])]


def instance_level(case_type: str) -> str:
    for marker, level in _LEVELS:
        if marker in case_type:
            return level
    return ""


def parse(value: str) -> dict:
    """解析单个案号；不符合法院案号形态的（仲裁纯数字、诉前调字号等）原样作为检索词。"""
    text = clean(value)
    match = _CASE.search(text)
    if not match:
        return {"原文": value, "归一化": text, "年份": "", "受理机关代字": "", "类型": "", "序号": "",
                "审级": "", "检索变体": [text] if text else []}
    year, court, case_type, serial = match.groups()
    normalized = f"（{year}）{court}{case_type}{serial}号"
    variants = [normalized, f"{year}{court}{case_type}{serial}号", f"{court}{case_type}{serial}号",
                f"{court}{case_type}{serial}", serial]
    return {"原文": value, "归一化": normalized, "年份": year, "受理机关代字": court, "类型": case_type,
            "序号": serial, "审级": instance_level(case_type), "检索变体": list(dict.fromkeys(variants))}


def normalize(value: str) -> list[dict]:
    return [parse(item) for item in split_numbers(value)]


def find_case_numbers(text: str) -> list[str]:
    """从文书正文里找出所有法院案号（已归一化、去重、保持出现顺序）。"""
    found = []
    for match in _CASE.finditer(clean(text)):
        year, court, case_type, serial = match.groups()
        found.append(f"（{year}）{court}{case_type}{serial}号")
    return list(dict.fromkeys(found))


def main(arguments: list[str]) -> int:
    if not arguments:
        print("用法：normalize_case_no.py <案号> [<案号> ...]", file=sys.stderr)
        return 2
    results = []
    for argument in arguments:
        items = normalize(argument)
        if len(items) > 1:
            print(f"警告：{argument} 拆出 {len(items)} 个案号，可能是关联案或一审/二审，须分别检索确认", file=sys.stderr)
        results.extend(items)
    print(json.dumps(results if len(results) != 1 else results[0], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
