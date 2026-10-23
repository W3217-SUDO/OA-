"""从法院文书正文识别收文要素：文书类型、案号、法院、案由、当事人、开庭、缴费、落款日期。

只用标准库。识别不到的项留空并列入“需人工核对”，绝不臆造。
    python extract_doc_fields.py --text "<正文>" [--name "<文书名称>"]
    python extract_doc_fields.py <文本文件或目录>        # .txt；装了 pypdf 时也读 .pdf
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

try:
    from . import normalize_case_no
except ImportError:  # 作为脚本在沙箱里直接运行
    import normalize_case_no

# 按优先级排列：名称更具体的在前，避免“通知书”类互相吞并。
DOC_TYPES = (
    ("交纳诉讼费用通知书", ("交纳诉讼费用通知", "缴纳诉讼费用通知", "预交诉讼费", "交纳案件受理费", "缴费通知")),
    ("受理通知书", ("受理通知书", "受理案件通知书")),
    ("应诉通知书", ("应诉通知书",)),
    ("举证通知书", ("举证通知书",)),
    ("传票", ("传票",)),
    ("出庭通知书", ("出庭通知书",)),
    ("合议庭组成通知书", ("合议庭组成", "审判人员通知书")),
    ("保全裁定书", ("保全裁定", "财产保全", "诉前保全", "诉讼保全")),
    ("撤诉裁定书", ("准许撤诉", "撤诉裁定", "按撤诉处理")),
    ("民事调解书", ("调解书",)),
    ("二审判决书", ("二审判决",)),
    ("判决书", ("判决书",)),
    ("裁定书", ("裁定书",)),
    ("起诉状副本", ("起诉状", "上诉状")),
    ("送达地址确认书", ("送达地址确认",)),
)
_CN_DIGITS = {"〇": 0, "○": 0, "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}


def cn_number(value: str) -> int | None:
    """把“七”“十五”“三十”“二〇二六”等中文数字转成整数；本来就是阿拉伯数字的直接返回。"""
    value = value.strip()
    if value.isdigit():
        return int(value)
    if value and all(char in _CN_DIGITS for char in value):
        return int("".join(str(_CN_DIGITS[char]) for char in value))
    if "十" in value:
        tens, _, ones = value.partition("十")
        high = _CN_DIGITS.get(tens, 1) if tens else 1
        low = _CN_DIGITS.get(ones, 0) if ones else 0
        if (tens and tens not in _CN_DIGITS) or (ones and ones not in _CN_DIGITS):
            return None
        return high * 10 + low
    return None


_DATE = re.compile(r"([0-9〇○零一二三四五六七八九]{4})年([0-9一二三四五六七八九十]{1,3})月([0-9一二三四五六七八九十]{1,3})日")
_TIME = re.compile(r"(上午|下午|晚上)?\s*([0-9一二三四五六七八九十]{1,3})\s*[时点:：]\s*([0-9]{1,2}|[一二三四五六七八九十]{1,3})?\s*分?")


def to_date(match: re.Match) -> str:
    year, month, day = (cn_number(part) for part in match.groups())
    if not year or not month or not day or not (1 <= month <= 12 and 1 <= day <= 31):
        return ""
    return f"{year:04d}-{month:02d}-{day:02d}"


def _first(pattern: str, text: str, flags: int = 0) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else ""


def _parties(text: str, role: str) -> list[str]:
    names = []
    for match in re.finditer(role + r"(?:人)?(?:（[^）]{0,8}）)?[:：]\s*([^，,。；;\s：:（(]{2,40})", text):
        name = match.group(1).strip()
        if name and name not in names:
            names.append(name)
    return names[:6]


def doc_type(name: str, text: str) -> str:
    for source in (name, text[:300], text):
        for label, markers in DOC_TYPES:
            if any(marker in source for marker in markers):
                return label
    return ""


def hearing(text: str) -> dict:
    """传票“应到时间/开庭时间”与法庭。只认紧挨关键词的日期，取不到就留空。"""
    for keyword in ("应到时间", "开庭时间", "定于", "开庭"):
        for anchor in re.finditer(keyword, text):
            window = text[anchor.end():anchor.end() + 80]
            date_match = _DATE.search(window)
            if not date_match or not to_date(date_match):
                continue
            result = {"开庭日期": to_date(date_match), "开庭时刻": ""}
            time_match = _TIME.match(window[date_match.end():date_match.end() + 20].strip())
            if time_match and time_match.group(2):
                hour = cn_number(time_match.group(2)) or 0
                minute = cn_number(time_match.group(3) or "0") or 0
                if time_match.group(1) in {"下午", "晚上"} and hour < 12:
                    hour += 12
                if 0 <= hour < 24 and 0 <= minute < 60:
                    result["开庭时刻"] = f"{hour:02d}:{minute:02d}"
            nearby = text[anchor.start():anchor.end() + 200]
            room = (re.search(r"(?:应到处所|地点|在)[:：]?((?:本院)?[\u4e00-\u9fff0-9]{0,20}?(?:法庭|审判庭))", nearby)
                    or re.search(r"((?:本院)?第[0-9一二三四五六七八九十百]+(?:法庭|审判庭))", nearby))
            result["开庭法庭"] = room.group(1).removeprefix("本院") if room else ""
            return result
    return {"开庭日期": "", "开庭时刻": "", "开庭法庭": ""}


def fee(text: str) -> dict:
    amount = _first(r"(?:案件受理费|诉讼费|受理费|应预交|预交|交纳)[^。\n]{0,30}?([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*元", text)
    days = _first(r"(?:次日起|之日起)\s*([0-9一二三四五六七八九十]{1,3})\s*日内", text)
    account = {
        "户名": _first(r"(?:户\s*名|收款单位|收款人)[:：]\s*([^\s；;，,。]{2,60})", text),
        "账号": _first(r"(?:账\s*号|帐\s*号)[:：]\s*([0-9\s-]{6,40})", text).replace(" ", ""),
        "开户行": _first(r"(?:开户行|开户银行|收款银行)[:：]\s*([^\s；;，,。]{2,60})", text),
    }
    return {"缴费金额": amount.replace(",", ""), "预交天数": cn_number(days) if days else None,
            "收款账户": {key: value for key, value in account.items() if value}}


def signing_date(text: str) -> str:
    """落款日期：取正文最后一个完整日期（文书落款一般在末尾）。"""
    dates = [value for value in (to_date(match) for match in _DATE.finditer(text[-600:])) if value]
    return dates[-1] if dates else ""


_PARTY = r"([^，,。；;：:\s]{2,40}?(?:有限责任公司|股份有限公司|有限公司|公司|商行|经营部|店|厂))"


def _sued_parties(compact: str) -> tuple[list[str], list[str]]:
    """“原告甲诉被告乙……纠纷”“甲与乙……纠纷”这类无冒号写法；只认以单位后缀结尾的名称。"""
    match = re.search(r"原告" + _PARTY + r"诉被告" + _PARTY, compact) or re.search(_PARTY + r"(?:与|诉)" + _PARTY + r"[\u4e00-\u9fff、]{0,20}?纠纷", compact)
    return ([match.group(1)], [match.group(2)]) if match else ([], [])


def _cause(compact: str) -> str:
    labelled = _first(r"案由[:：]?([\u4e00-\u9fff、]{2,20}?纠纷)", compact)
    if labelled:
        return labelled
    # “甲公司与乙公司侵害商标权纠纷”：去掉最后一个当事人名称及之前的部分。
    segment = _first(r"([\u4e00-\u9fff、]{2,60}?纠纷)", compact)
    return re.sub(r"^.*(?:公司|商行|经营部|店|厂|与|诉)", "", segment)


def extract(text: str, name: str = "") -> dict:
    text = text or ""
    # PDF 抽出的文字常把数字、年月日拆开甚至断行（“2026 年 11 月 13\n日”），日期、时间和案由在去空白文本上识别。
    compact = re.sub(r"\s+", "", text)
    sued_plaintiffs, sued_defendants = _sued_parties(compact)
    numbers = normalize_case_no.find_case_numbers(name + "\n" + text)
    primary = normalize_case_no.parse(numbers[0]) if numbers else None
    result = {
        "文书名称": name,
        "文书类型": doc_type(name, text),
        "官方案号": numbers,
        "主案号解析": primary,
        "受理机关": _first(r"([\u4e00-\u9fff]{2,30}?(?:人民法院|仲裁委员会|人民检察院))", compact),
        "案由": _cause(compact),
        "原告": _parties(text, "原告") or _parties(text, "上诉人") or _parties(text, "申请人") or sued_plaintiffs,
        "被告": _parties(text, "被告") or _parties(text, "被上诉人") or _parties(text, "被申请人") or sued_defendants,
        "落款日期": signing_date(compact),
    }
    kind = result["文书类型"]
    if kind in {"传票", "出庭通知书"} or "开庭" in text:
        result.update(hearing(compact))
    if kind == "交纳诉讼费用通知书" or "预交" in text:
        fields = fee(text)
        compact_fields = fee(compact)
        fields["缴费金额"] = fields["缴费金额"] or compact_fields["缴费金额"]
        fields["预交天数"] = fields["预交天数"] or compact_fields["预交天数"]
        result.update(fields)
    review = [key for key in ("文书类型", "官方案号", "受理机关") if not result.get(key)]
    if kind in {"传票", "出庭通知书"} and not result.get("开庭日期"):
        review.append("开庭日期")
    if kind == "交纳诉讼费用通知书" and (not result.get("缴费金额") or not result.get("预交天数")):
        review.append("缴费金额/期限")
    if not text.strip():
        review = ["正文为空（扫描件需人工阅读或 OCR）"]
    result["需人工核对"] = review
    result["识别状态"] = "需人工核对" if review else "已识别"
    return result


def _read(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return ""
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return path.read_text(encoding="utf-8", errors="replace")


def main(arguments: list[str]) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="识别法院文书收文要素")
    parser.add_argument("path", nargs="?", help="文本/PDF 文件或目录")
    # 单个参数有长度上限，正文可拆成多段依次传入，按顺序拼接。
    parser.add_argument("--text", nargs="+", help="文书正文（可分多段）")
    parser.add_argument("--name", default="", help="文书名称")
    options = parser.parse_args(arguments)
    if options.text:
        print(json.dumps(extract("".join(options.text), options.name), ensure_ascii=False, indent=2))
        return 0
    if not options.path:
        parser.print_usage(sys.stderr)
        return 2
    target = Path(options.path)
    files = sorted(item for item in target.iterdir() if item.suffix.lower() in {".txt", ".pdf"}) if target.is_dir() else [target]
    results = [extract(_read(item), item.stem) for item in files]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
