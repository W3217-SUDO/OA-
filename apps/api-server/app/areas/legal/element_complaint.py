"""要素式民事起诉状（法院统一格式，陶国南 11-05 12:19 给的不正当竞争纠纷版）：当事人几块按当事人类型填写。

表格本身不改（法院要求不得改变要素内容、格式）。原告、被告、第三人各有“自然人”“法人、非法人组织”两块：
有几位就把对应那一块复制几份（表格说明允许多原告、多被告复制），逐份填进系统里有的信息；某一类一个都没有的，
那一块原样留空。委托诉讼代理人勾“有”，填经办律师、上海沪知律师事务所、律师；落款具状人和日期、证据清单提交人和时间也带出。
诉讼请求、事实与理由、证据等由律师填写。系统里没有的项留空，打印后手写。
"""
import re
from copy import deepcopy
from datetime import datetime
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
# （表格序号, [行号]）：表格按正文顺序数（不含嵌套表格）。
BLOCKS = {
    "原告": {"person": (0, [2]), "org": (0, [3, 4, 5])},
    "被告": {"person": (1, [1]), "org": (1, [2, 3, 4])},
    "第三人": {"person": (1, [5]), "org": (2, [0, 1, 2])},
}
AGENT_ROW = (1, 0)
CHECKED = "☑"


def _text(paragraph) -> str:
    return "".join(node.text or "" for node in paragraph.iter(W + "t"))


def _set_text(paragraph, text: str) -> None:
    nodes = list(paragraph.iter(W + "t"))
    if not nodes:
        return
    nodes[0].text = text
    nodes[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for node in nodes[1:]:
        node.text = ""


def _after(text: str, label: str, value: str) -> str:
    """在标签后面插入值；标签后原有的空格留着（表格对齐用）。"""
    if not value or label not in text:
        return text
    at = text.index(label) + len(label)
    return text[:at] + value + text[at:]


def _fill_person(text: str, party: dict) -> str:
    if text.startswith("姓名："):
        text = _after(text, "姓名：", party["name"])
    if party.get("gender") and "男□" in text and "女□" in text:
        text = text.replace(f"{party['gender']}□", f"{party['gender']}{CHECKED}", 1)
    birth = party.get("birth")
    if birth and text.startswith("出生日期："):
        text = re.sub(r"^出生日期：\s*年\s*月\s*日", f"出生日期：{birth.year}年{birth.month}月{birth.day}日", text)
    text = _after(text, "住所地（户籍所在地）：", party.get("address", ""))
    if party.get("id_no"):
        text = _after(text, "证件类型：", "居民身份证")
        text = _after(text, "证件号码：", party["id_no"])
    return _after(text, "联系电话：", party.get("phone", ""))


def _fill_org(text: str, party: dict) -> str:
    if text.startswith("名称："):
        text = _after(text, "名称：", party["name"])
    text = _after(text, "住所地（主要办事机构所在地）：", party.get("address", ""))
    text = _after(text, "法定代表人 / 负责人：", party.get("legal_representative", ""))
    text = _after(text, "统一社会信用代码：", party.get("credit_code", ""))
    return _after(text, "联系电话：", party.get("phone", ""))


def _fill_rows(rows, filler, party: dict) -> None:
    for row in rows:
        for paragraph in row.iter(W + "p"):
            text = _text(paragraph)
            new = filler(text, party)
            if new != text:
                _set_text(paragraph, new)


def _top_tables(body) -> list:
    return [child for child in body if child.tag == W + "tbl"]


def _rows(table) -> list:
    return [child for child in table if child.tag == W + "tr"]


def fill_element_complaint(content: bytes, parties: dict) -> bytes:
    """parties：{"原告": [...], "被告": [...], "第三人": [...], "agents": "张三、李四", "firm": ..., "date": "2026年11月5日"}。"""
    output = BytesIO()
    with ZipFile(BytesIO(content)) as source, ZipFile(output, "w", ZIP_DEFLATED) as target:
        for item in source.infolist():
            payload = source.read(item.filename)
            if item.filename == "word/document.xml":
                payload = _fill_document(payload, parties)
            target.writestr(item, payload)
    return output.getvalue()


def _fill_document(payload: bytes, parties: dict) -> bytes:
    root = etree.fromstring(payload)
    tables = _top_tables(root.find(W + "body"))
    # 同一张表里从下往上处理，复制出来的行不影响上面各块的行号。
    jobs = [(table, rows, role, kind) for role, kinds in BLOCKS.items() for kind, (table, rows) in kinds.items()]
    jobs.sort(key=lambda job: (job[0], -job[1][0]))
    agent_row = _rows(tables[AGENT_ROW[0]])[AGENT_ROW[1]]
    for table_index, row_numbers, role, kind in jobs:
        table_rows = _rows(tables[table_index])
        block = [table_rows[number] for number in row_numbers]
        members = [party for party in parties.get(role, []) if party["person"] == (kind == "person")]
        if not members:
            continue
        filler = _fill_person if kind == "person" else _fill_org
        anchor = block[-1]
        copies = [block] + [[deepcopy(row) for row in block] for _ in members[1:]]
        for rows in copies[1:]:
            for row in rows:
                anchor.addnext(row)
                anchor = row
        for rows, party in zip(copies, members):
            _fill_rows(rows, filler, party)
    agents = parties.get("agents", "")
    if agents:
        for paragraph in agent_row.iter(W + "p"):
            text = _text(paragraph)
            new = text
            if text.strip() == "有□":
                new = text.replace("有□", f"有{CHECKED}", 1)
            elif text.startswith("姓名："):
                new = _after(text, "姓名：", agents)
            elif text.startswith("单位："):
                new = _after(_after(text, "单位：", parties.get("firm", "")), "职务：", "律师")
            if new != text:
                _set_text(paragraph, new)
    plaintiffs = "、".join(party["name"] for party in parties.get("原告", []))
    for paragraph in root.iter(W + "p"):
        text = _text(paragraph)
        new = text
        if text.startswith("具状人（签字、盖章）："):
            new = _after(_after(text, "具状人（签字、盖章）：", plaintiffs), "日期：", parties.get("date", ""))
        elif text.strip() == "提交人：":
            new = _after(text, "提交人：", plaintiffs)
        elif text.strip() == "提交时间：":
            new = _after(text, "提交时间：", parties.get("date", ""))
        if new != text:
            _set_text(paragraph, new)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def party_entry(name: str, identity: dict, profile: dict, *, is_person, first, address_keys, phone_keys, looks_like_id_card) -> dict:
    identity_no = str(identity.get("identity_no") or profile.get("identity_no") or profile.get("credit_code") or "").strip().upper()
    address = first(profile, *address_keys)
    if address == name:
        address = ""
    entry = {"name": name, "address": address, "phone": first(profile, *phone_keys)}
    if is_person(name, identity, identity_no, profile):
        entry["person"] = True
        if len(identity_no) == 18 and looks_like_id_card(identity_no):
            entry.update(id_no=identity_no, gender="男" if int(identity_no[16]) % 2 else "女",
                         birth=datetime.strptime(identity_no[6:14], "%Y%m%d"))
        elif identity_no:
            entry["id_no"] = identity_no
        return entry
    entry.update(person=False, credit_code=identity_no if not looks_like_id_card(identity_no) else "",
                 legal_representative=first(profile, "legal_representative"))
    return entry
