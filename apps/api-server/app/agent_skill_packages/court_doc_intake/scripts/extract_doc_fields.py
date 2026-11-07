"""从法院文书正文识别收文要素：文书类型、案号、法院、案由、当事人、开庭、缴费、承办法官与书记员、落款日期。

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
    # 名称里的括号要保留：“某某（上海）有限公司”“××百货店（个体工商户）”；“（以下简称…）”这类注释去掉。
    for match in re.finditer(role + r"(?:人)?(?:（[^）]{0,8}）)?[:：]\s*((?:[^，,。；;\s：:（()）]|[（(][^，,。；;\s：:（()）]{1,12}[）)]){2,60})", text):
        name = re.sub(r"[（(](?:以下简称|下称|简称)[^）)]*[）)]$", "", match.group(1).strip())
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


_STAFF_LABELS = ("承办法官", "主审法官", "承办人", "审判长", "代理审判员", "审判员", "人民陪审员", "法官助理", "书记员")
_STAFF_STOP = (r"(?=[，,；;。、（(:：]|联系|电话|手机|担任|组成|主持|独任|适用|审理|与|和|为|" + "|".join(_STAFF_LABELS)
               + r"|[0-9〇○零一二三四五六七八九]{4}年|本件|$)")


def _staff_names(compact: str, label: str) -> list[str]:
    names = []
    # “代理审判员”“审判员”互不吞并：审判员前不能紧跟“代理”。
    prefix = r"(?<!代理)" if label == "审判员" else ""
    for match in re.finditer(prefix + label + r"[:：]?([\u4e00-\u9fff·]{2,5}?)" + _STAFF_STOP, compact):
        name = match.group(1)
        if name not in names:
            names.append(name)
    return names


def court_staff(compact: str) -> dict:
    """承办法官、书记员、法官电话。承办法官：文书写明“承办法官/主审法官/承办人”的优先；
    否则独任审判（只有一位审判员、没有审判长）取该审判员；合议庭没写明承办人时取审判长并标注。"""
    found = {label: _staff_names(compact, label) for label in _STAFF_LABELS}
    # 传票常见写法“承办法官/法官助理：徐某/（法官助理）”：斜杠前是法官，后面是助理，括号里的是没填的占位字。
    paired = re.search(r"承办法官/法官助理[:：]([^/（(]{0,6})/([^/（(:：]{0,6})", compact)
    if paired:
        for label, value in (("承办法官", paired.group(1)), ("法官助理", paired.group(2))):
            name = re.sub(r"(书记员|联系).*$", "", value)
            if 2 <= len(name) <= 5 and name not in found[label]:
                found[label].insert(0, name)
    judge, basis = "", ""
    for label in ("承办法官", "主审法官", "承办人"):
        if found[label]:
            judge, basis = found[label][0], label
            break
    judges = found["审判员"] + found["代理审判员"]
    if not judge and len(judges) == 1 and not found["审判长"]:
        judge, basis = judges[0], "独任审判员"
    if not judge and found["审判长"]:
        judge, basis = found["审判长"][0], "审判长（合议庭未写明承办人）"
    phone = ""
    for anchor in re.finditer(r"承办|法官|书记员|联系电话|联系人", compact):
        match = re.search(r"(?:电话|手机|联系方式)[:：]?(1[3-9]\d{9}|(?:\d{3,4}-)?\d{7,8}(?:-\d{1,6})?)", compact[anchor.start():anchor.start() + 60])
        if match:
            phone = match.group(1)
            break
    panel = [*found["审判长"], *judges, *found["人民陪审员"]]
    return {"承办法官": judge, "承办法官依据": basis, "审判人员": list(dict.fromkeys(panel)),
            "法官助理": found["法官助理"][0] if found["法官助理"] else "",
            "书记员": found["书记员"][0] if found["书记员"] else "", "法官电话": phone}


def signing_date(text: str) -> str:
    """落款日期：取正文最后一个完整日期（文书落款一般在末尾）。"""
    dates = [value for value in (to_date(match) for match in _DATE.finditer(text[-600:])) if value]
    return dates[-1] if dates else ""


# 单位名称：取到最后一个单位后缀为止（贪婪），“广州逸达酒店有限公司”不截成“广州逸达酒店”，
# “××有限公司霞美分公司”不截成总公司；“（个体工商户）”算名称的一部分。
_SUFFIX = r"(?:公司|商行|经营部|店|厂)(?:[（(](?:个体工商户|个人独资|普通合伙|有限合伙)[）)])?"
_PARTY = r"([^，,。；;：:\s]{2,60}" + _SUFFIX + r")"
# 被告后面紧跟案由（“……纠纷”）或标点，案由里出现“店”“厂”时也不会把案由吞进名称。
_AFTER_DEFENDANT = r"(?=[\u4e00-\u9fff、]{0,20}?纠纷|[，,。；;）)]|$)"


def _sued_parties(compact: str) -> tuple[list[str], list[str]]:
    """“原告甲诉被告乙……纠纷”“甲与乙……纠纷”这类无冒号写法；只认以单位后缀结尾的名称。"""
    # 被告名称后面不是案由或标点时（“正品建材店0738”），退回不看后文，至少取到原告；这种句式取到的名称都不用来直接存。
    match = re.search(r"原告" + _PARTY + r"诉被告" + _PARTY + _AFTER_DEFENDANT, compact) \
        or re.search(r"原告" + _PARTY + r"诉被告" + _PARTY, compact) \
        or re.search(_PARTY + r"(?:与|诉)" + _PARTY + r"[\u4e00-\u9fff、]{0,20}?纠纷", compact)
    return ([match.group(1)], [match.group(2)]) if match else ([], [])


# 识别出的名称在原文里后面紧跟着单位名称的剩余部分（“有限公司”“限公司”（断行）“××分公司”“（个体工商户）”），
# 说明可能被截短了。宁可多判：多判只是请律师确认，少判可能存错案件。
_TRUNCATED_TAIL = r"(?:[^，,。；;：:\s（()）诉与被原告]{0,8}(?:公司|商行|经营部|店|厂)|[（(](?:个体工商户|个人独资|普通合伙|有限合伙)[）)])"


def truncated_parties(compact: str, names: list[str]) -> list[str]:
    """名称可能识别不全的当事人。只用来判断能否直接存：有就请律师确认。"""
    return [name for name in names if re.search(re.escape(name) + _TRUNCATED_TAIL, compact)]


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
        "原告": _parties(text, "原告") or _parties(text, "上诉人") or _parties(text, "申请人"),
        "被告": _parties(text, "被告") or _parties(text, "被上诉人") or _parties(text, "被申请人"),
        "落款日期": signing_date(compact),
        **court_staff(compact),
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
    # “原告甲诉被告乙……纠纷”句式分不清名称在哪结束（“××有限公司实力供应商”“××宾馆”），
    # 从这种句式取到的名称一律算可能不全：照常显示，但不用来直接存（生产 6,309 件实测，句式取错 52 件、冒号写法 14 件）。
    sentence = [name for role, found in (("原告", sued_plaintiffs), ("被告", sued_defendants)) if not result[role] for name in found]
    result["原告"] = result["原告"] or sued_plaintiffs
    result["被告"] = result["被告"] or sued_defendants
    result["当事人可能截短"] = list(dict.fromkeys([*truncated_parties(compact, [*result["原告"], *result["被告"]]), *sentence]))
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
