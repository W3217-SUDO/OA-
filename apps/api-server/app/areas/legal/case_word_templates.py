"""按固定模板生成文书（陶国南 11-03 15:56）。

管理员上传 Word 模板，模板里用 {法院}{原告}{被告}{案由}{法院案号}{开庭律师}{生成日期} 等占位字段。
生成时字段由系统按固定规则从案件信息取，案件里没有的（如撤诉理由）由人选常用项或手填；
正文不经过智能体改写，只替换字段，保留原件字体和段落。确认后存进案件空间文档，和“生成案件文书”同一种存法。
模板清单存在系统配置 case_word_templates 里；内置模板随代码发布，上传的模板文件按普通附件保存；删除只做逻辑删除。
"""
from __future__ import annotations

from contextvars import ContextVar

import re
from copy import deepcopy
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from lxml import etree
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.areas.legal.template_documents import WORD_NS, _replace_slots
from app.config import settings
from app.core.case_cause import case_cause
from app.core.constants import UPLOAD_ROOT
from app.database import get_db
from app.models import BusinessRecord, FileAttachment, SystemConfig, User, WorkflowEvent
from app.security import current_identity

router = APIRouter(prefix=settings.api_prefix)
CONFIG_KEY = "case_word_templates"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TEMPLATE_CATEGORY = "案件文书模板"
PLACEHOLDER = re.compile(r"\{([一-龥A-Za-z0-9_（）()]{1,20})\}")
MAX_TEMPLATE_BYTES = 10 * 1024 * 1024
SPLIT = re.compile(r"[,，、;；\n]+")
CAUSE_NUMBER = re.compile(r"^\s*(?:[一二三四五六七八九十百]+|\d+)[、.．]\s*")

BUILTIN_TEMPLATES = [{
    "id": "withdrawal-application", "name": "撤诉申请书", "file": "WITHDRAWAL_APPLICATION_DOCX",
    "options": {"撤诉理由": ["原被告之间已达成和解并履行", "原被告之间已达成和解", "被告已停止侵权并赔偿损失", "原告决定不再追究"]},
}, {
    # 陶国南 11-04：调解员、付款期限可以留空，打印后手写。
    # 陶国南 11-05 13:28：改名“调解协议书（诉前调解）”，和“调解协议（诉讼中，请法院确认）”区分。
    "id": "mediation-agreement", "name": "调解协议书（诉前调解）", "file": "MEDIATION_AGREEMENT_DOCX",
    "options": {}, "optional": ["调解员", "付款期限"],
}, {
    # 陶国南 11-05 给的三份申请书：申请人=原告（本所委托人），被申请人=被告；法定代表人、职务、送达地址系统里没有，留空手写。
    "id": "property-preservation", "name": "财产保全申请书", "file": "PROPERTY_PRESERVATION_DOCX",
    "options": {}, "optional": ["财产线索"],
}, {
    "id": "change-claims", "name": "变更诉讼请求申请书", "file": "CHANGE_CLAIMS_DOCX",
    "options": {}, "optional": [],
}, {
    "id": "non-public-hearing", "name": "不公开审理申请书", "file": "NON_PUBLIC_HEARING_DOCX",
    "options": {}, "optional": [],
}, {
    # 陶国南 11-05：办案小结（诉讼）。案情概况、办案体会、保管期限由律师填，可以留空手写；事务所审查意见、承办律师签名留给手写。
    "id": "case-summary", "name": "办案小结（诉讼）", "file": "CASE_SUMMARY_DOCX",
    # 陶国南 11-05 11:25：保管期限按案件类型自动带（民事、行政 20 年，刑事长期），其他类型留空可选。
    "options": {"保管期限": ["20年", "长期"]}, "optional": ["简要案情工作概况", "办案体会", "保管期限", "处理结果", "开庭日期", "起诉日期", "结案日期"],
}, {
    # 陶国南 11-05 12:15：当事人“胜诉退费”银行账号确认书。当事人=本所委托人；银行账号取客户档案的开户行、账号（多数没填，留空手写）。
    "id": "court-refund-account", "name": "胜诉退费银行账号确认书", "file": "COURT_REFUND_ACCOUNT_DOCX",
    "options": {}, "optional": ["委托人联系方式", "退费开户行", "退费户名", "退费账号"],
}, {
    # 陶国南 11-05 12:15：调解协议（诉讼中，请法院确认）——和“调解协议书”（诉前调解，调解员主持、线上签署、不司法确认）是两种格式。
    "id": "mediation-agreement-litigation", "name": "调解协议（诉讼中，请法院确认）", "file": "MEDIATION_LITIGATION_DOCX",
    "options": {"诉讼费承担方": ["原告", "被告", "原、被告各半"]},
    "optional": ["涉案产品", "回收负责人", "回收联系电话", "收款联行号", "付款期限"],
}, {
    # 陶国南 11-05 12:16：送达地址确认书。当事人=本所委托人；送达地址默认沪知所地址（系统参数）加经办律师姓名和手机，短信送达号码用经办律师手机。
    "id": "delivery-address", "name": "送达地址确认书", "file": "DELIVERY_ADDRESS_DOCX",
    "options": {}, "optional": ["送达联系方式", "送达邮编", "短信送达号码"],
}, {
    # 陶国南 11-05 12:19：庭审纪要，表头从案件带出，其余格子庭审时填写；表头各项都可以留空。
    "id": "hearing-memo", "name": "庭审纪要", "file": "HEARING_MEMO_DOCX",
    "options": {}, "optional": ["法院案号", "开庭时间", "原告联系方式", "被告联系方式", "主审法官", "法官联系方式", "书记员", "书记员联系方式"],
}, {
    # 陶国南 11-05 12:19：法院统一格式的要素式起诉状。当事人几块按当事人类型（自然人/单位）复制填写，诉请和事实由律师填。
    "id": "element-complaint-unfair-competition", "name": "民事起诉状（要素式·不正当竞争纠纷）", "file": "ELEMENT_COMPLAINT_UNFAIR_COMPETITION_DOCX",
    "options": {}, "optional": [], "form": "element_complaint",
}, {
    # 陶国南 11-05 12:20：商标侵权版是法院“实例”，改成空白表（示例值清空、勾选改回□），生成逻辑同不正当竞争版。
    "id": "element-complaint-trademark", "name": "民事起诉状（要素式·侵害商标权纠纷）", "file": "ELEMENT_COMPLAINT_TRADEMARK_DOCX",
    "options": {}, "optional": [], "form": "element_complaint",
}]
# 系统自动取值的字段；模板里出现其他占位字段时，按“需要人工填写”处理。
AUTO_FIELDS = ("法院", "法院案号", "原告", "被告", "第三人", "案由", "开庭律师", "经办律师", "律师助理", "客户名称", "案件编号", "生成日期",
               "原告信息", "被告信息", "委托诉讼代理人", "代理律所", "赔偿金额", "赔偿金额大写", "收款户名", "收款开户行", "收款账号",
               "付款期限", "签署日期", "申请人信息", "被申请人信息", "落款日期", "保全金额",
               "收案日期", "起诉日期", "结案日期", "开庭日期", "处理结果", "归档日期", "保管期限",
               "调解原告信息", "调解被告信息", "付款被告", "收款联行号", "委托人名称", "委托人联系方式", "退费开户行", "退费户名", "退费账号",
               "送达地址", "送达联系方式", "送达邮编", "短信送达号码", "侵权行为表述",
               "开庭时间", "原告联系方式", "被告联系方式", "主审法官", "法官联系方式", "书记员", "书记员联系方式")
# 陶国南 11-04 14:28：日期都要生成。案件里没有约定付款日期时，付款期限默认生成日起 7 天（样本是起草后约 3 天），可以改。
DEFAULT_PAYMENT_DAYS = 7
PAYMENT_DATE_KEYS = ("agreed_payment_date", "payment_deadline", "settlement_payment_date", "promised_payment_date", "mediation_payment_date")
# 多个当事人逐行列出（每人一段，段落前面的“原告：”“被告：”跟着重复）。
MULTILINE_FIELDS = {"原告信息", "被告信息", "申请人信息", "被申请人信息", "事实和理由", "财产线索", "变更后诉讼请求", "调解原告信息", "调解被告信息",
                    "简要案情工作概况", "办案体会", "处理结果"}
# 由别的字段算出来的，不单独填：赔偿金额大写跟着赔偿金额走。
DERIVED_FIELDS = {"赔偿金额大写": "赔偿金额"}
# 陶国南 11-04 14:19：律所用系统所在的上海沪知律师事务所，收款账户用沪知所的账户——
# 取系统参数“付款单位”里的上海沪知律师事务所（户名/开户行/账号），那里改了这里跟着变。
FIRM_NAME = "上海沪知律师事务所"
# 陶国南 11-05 09:54：申请书的送达地址固定写沪知所地址。取系统参数“付款单位”里上海沪知律师事务所的 address（参数里改了这里跟着变），
# 参数里还没填时用这个地址。
FIRM_ADDRESS = "上海市静安区江场路1228弄20号五牛控股大厦603室"
# 留空的字段在文书里留几个全角空格，方便打印后手写。
BLANK = "\u3000" * 4


class TemplateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=60)
    is_active: bool | None = None
    options: dict[str, list[str]] | None = None
    mapping: dict[str, dict[str, str]] | None = None  # 下划线序号 → {"source": "case", "field": 法院} 或 {"source": "manual", "label": 撤诉理由}


class GenerateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: dict[str, str] = Field(default_factory=dict)  # 人工填写或修正的字段


# ---------- 模板清单 ----------

def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _require_template_admin(identity: dict) -> None:
    from app.core.permissions import _require_admin
    try:
        _require_admin(identity)
    except HTTPException as exc:
        raise HTTPException(403, "文书模板只有管理员可以上传和修改") from exc


async def _config(db: AsyncSession, *, lock: bool = False) -> tuple[SystemConfig | None, dict]:
    statement = select(SystemConfig).where(SystemConfig.key == CONFIG_KEY)
    record = await db.scalar(statement.with_for_update() if lock else statement)
    # 深拷贝：就地改了原值的话，ORM 比较新旧相同就不会写库。
    return record, deepcopy(record.value or {}) if record else {"items": []}


def _merged(value: dict) -> list[dict]:
    """内置模板 + 配置里的修改（改名、停用、换文件、常用选项）+ 上传的模板；已删除的不返回。"""
    overrides = {item["id"]: item for item in value.get("items", [])}
    items = []
    for builtin in BUILTIN_TEMPLATES:
        items.append({"builtin": True, "is_active": True, "attachment_id": None, **builtin, **overrides.get(builtin["id"], {})})
    items.extend({"builtin": False, **item} for item in value.get("items", []) if item["id"] not in {b["id"] for b in BUILTIN_TEMPLATES})
    return [item for item in items if not item.get("deleted_at")]


async def _template(db: AsyncSession, template_id: str) -> dict:
    _, value = await _config(db)
    item = next((item for item in _merged(value) if item["id"] == template_id), None)
    if item is None:
        raise HTTPException(404, "文书模板不存在或已删除")
    return item


async def _template_bytes(item: dict, db: AsyncSession) -> bytes:
    if item.get("attachment_id"):
        from app.core.storage import ensure_attachment_local
        attachment = await db.get(FileAttachment, int(item["attachment_id"]))
        path = await ensure_attachment_local(attachment) if attachment else None
        if not path:
            raise HTTPException(409, "模板文件找不到了，请管理员重新上传")
        return await run_in_threadpool(Path(path).read_bytes)
    import base64
    from app.areas.legal import builtin_word_templates
    return base64.b64decode(getattr(builtin_word_templates, item["file"]))


W = "{%s}" % WORD_NS["w"]
NOTE = re.compile(r"[（(][^（）()]*[）)]\s*")
# 按说明文字猜对应案件里的哪一项；猜不到的设成“生成时手填”，管理员可以在模板页改。
FIELD_HINTS = (
    (("调解原告信息",), "调解原告信息"), (("调解被告信息",), "调解被告信息"), (("付款被告",), "付款被告"), (("收款联行号",), "收款联行号"),
    (("委托人名称",), "委托人名称"), (("委托人联系方式",), "委托人联系方式"), (("退费开户行",), "退费开户行"), (("退费户名",), "退费户名"),
    (("退费账号",), "退费账号"), (("送达地址",), "送达地址"), (("送达联系方式",), "送达联系方式"), (("送达邮编",), "送达邮编"),
    (("短信送达号码",), "短信送达号码"), (("侵权行为表述",), "侵权行为表述"),
    (("原告联系方式",), "原告联系方式"), (("被告联系方式",), "被告联系方式"), (("法官联系方式",), "法官联系方式"),
    (("书记员联系方式",), "书记员联系方式"), (("书记员",), "书记员"), (("主审法官",), "主审法官"), (("开庭时间",), "开庭时间"),
    (("收案日期",), "收案日期"), (("起诉日期",), "起诉日期"), (("结案日期",), "结案日期"), (("开庭日期",), "开庭日期"),
    (("处理结果",), "处理结果"), (("归档日期",), "归档日期"), (("保管期限",), "保管期限"),
    (("被申请人信息",), "被申请人信息"), (("申请人信息",), "申请人信息"), (("落款日期",), "落款日期"), (("保全金额",), "保全金额"),
    (("原告信息",), "原告信息"), (("被告信息",), "被告信息"), (("原告名称",), "原告"), (("被告名称",), "被告"),
    (("委托诉讼代理人",), "委托诉讼代理人"), (("代理律所",), "代理律所"), (("赔偿金额大写",), "赔偿金额大写"), (("赔偿金额",), "赔偿金额"),
    (("收款户名",), "收款户名"), (("收款开户行",), "收款开户行"), (("收款账号",), "收款账号"),
    (("付款期限",), "付款期限"), (("签署日期",), "签署日期"),
    (("法院案号", "案号"), "法院案号"), (("开庭律师", "出庭律师", "代理律师", "代理人"), "开庭律师"), (("经办律师", "承办律师"), "经办律师"),
    (("律师助理", "助理"), "律师助理"), (("第三人",), "第三人"), (("原告",), "原告"), (("被告",), "被告"), (("案由",), "案由"),
    (("法院",), "法院"), (("客户",), "客户名称"), (("案件编号",), "案件编号"), (("生成当日", "当日", "今天", "日期"), "生成日期"),
)


def suggest_field(note: str, sample: str) -> str | None:
    text = note or sample
    return next((field for keys, field in FIELD_HINTS if any(key in text for key in keys)), None)


def _run_text(run) -> str:
    return "".join(node.text or "" for node in run.findall(W + "t"))


def _underlined(run) -> bool:
    mark = run.find(f"{W}rPr/{W}u")
    return mark is not None and mark.get(W + "val") != "none"


def _segments(paragraph) -> list[list]:
    """连续带下划线的文字是一段要替换的内容（Word 常把一段拆成好几截）。"""
    segments, current = [], []
    for run in paragraph.iter(W + "r"):
        text = _run_text(run)
        if not text:
            continue  # 书签、换行之类不打断
        if _underlined(run):
            current.append(run)
        elif current:
            segments.append(current)
            current = []
    if current:
        segments.append(current)
    return segments


def _split_segment(text: str) -> list[tuple[str, str]]:
    """一段下划线文字拆成若干（示例文字, 括号说明）；例如“甲公司（原告名称）侵权纠纷（案由）”。
    括号里只有数字的（如案号里的“（2022）”）是示例本身；几个括号连在一起时只有最后一个是说明
    （如“某商贸中心（个体工商户）（被告名称）”）。"""
    matches = list(NOTE.finditer(text))
    slots, last = [], 0
    for position, match in enumerate(matches):
        inner = match.group(0).strip()[1:-1].strip()
        followed = position + 1 < len(matches) and matches[position + 1].start() == match.end()
        if not re.search(r"[^\d\s]", inner) or followed:
            continue
        slots.append((text[last:match.start()], inner))
        last = match.end()
    if text[last:].strip():
        slots.append((text[last:], ""))
    return slots


def _xml_parts(source: ZipFile) -> list[str]:
    return sorted(name for name in source.namelist() if name.startswith("word/") and name.endswith(".xml"))


def scan(content: bytes) -> list[dict]:
    """识别模板里要替换的地方：带下划线的文字（后面括号是说明），以及 {字段} 写法。"""
    slots: list[dict] = []
    try:
        with ZipFile(BytesIO(content)) as source:
            for name in _xml_parts(source):
                payload = source.read(name)
                if b"<w:p" not in payload:
                    continue
                for paragraph in etree.fromstring(payload).iter(W + "p"):
                    for segment in _segments(paragraph):
                        for sample, note in _split_segment("".join(_run_text(run) for run in segment)):
                            slots.append({"index": len([x for x in slots if x["kind"] == "underline"]), "kind": "underline",
                                          "sample": sample.strip(), "note": note, "suggest": suggest_field(note, sample)})
                    text = "".join(node.text or "" for node in paragraph.iter(W + "t"))
                    for match in PLACEHOLDER.finditer(text):
                        key = match.group(1)
                        slots.append({"index": None, "kind": "placeholder", "sample": match.group(0), "note": key,
                                      "suggest": key if key in AUTO_FIELDS else None})
    except (BadZipFile, KeyError, etree.XMLSyntaxError) as exc:
        raise HTTPException(422, "不是有效的 Word 文件（.docx）") from exc
    return slots


def resolve_slots(slots: list[dict], mapping: dict | None) -> list[dict]:
    """每个识别到的地方对应案件里哪一项（或生成时手填）；管理员改过的以改过的为准。"""
    mapping = mapping or {}
    result = []
    for slot in slots:
        chosen = mapping.get(str(slot["index"])) if slot["kind"] == "underline" else None
        if chosen and chosen.get("source") == "case" and chosen.get("field") in AUTO_FIELDS:
            source, key = "case", chosen["field"]
        elif chosen and chosen.get("source") == "manual" and str(chosen.get("label") or "").strip():
            source, key = "manual", str(chosen["label"]).strip()
        elif slot["suggest"]:
            source, key = "case", slot["suggest"]
        else:
            source, key = "manual", slot["note"] or slot["sample"] or "待填写"
        result.append({**slot, "source": source, "key": key})
    return result


def fill(content: bytes, slots: list[dict], values: dict) -> bytes:
    """下划线那段换成值并去掉下划线，括号说明删掉；{字段} 换成值；其余文字、字体、段落一律不动。"""
    keys = [slot["key"] for slot in slots if slot["kind"] == "underline"]
    placeholder_values = {slot["note"]: values.get(slot["key"], "") for slot in slots if slot["kind"] == "placeholder"}
    position = 0
    output = BytesIO()
    with ZipFile(BytesIO(content)) as source, ZipFile(output, "w", ZIP_DEFLATED) as target:
        parts = set(_xml_parts(source))
        for item in source.infolist():
            payload = source.read(item.filename)
            if item.filename in parts and b"<w:p" in payload:
                root = etree.fromstring(payload)
                for paragraph in root.iter(W + "p"):
                    segments = _segments(paragraph)
                    for segment in segments:
                        count = len(_split_segment("".join(_run_text(run) for run in segment)))
                        text = "".join(str(values.get(key, "")) for key in keys[position:position + count])
                        position += count
                        nodes = [node for run in segment for node in run.findall(W + "t")]
                        nodes[0].text = text.replace("\n", LINE_SEPARATOR)
                        nodes[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                        for node in nodes[1:]:
                            node.text = ""
                    if segments:
                        # 陶国南 16:42：定稿不留下划线。替换过的段落里，空白 run、段落标记上的下划线也一并去掉（字段以外的文字本来就没有下划线）。
                        for mark in paragraph.iter(W + "u"):
                            if mark.getparent().tag == W + "rPr":
                                mark.getparent().remove(mark)
                    _replace_slots(paragraph, placeholder_values, PLACEHOLDER)
                _split_lines(root)
                payload = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            target.writestr(item, payload)
    return output.getvalue()


# 字段值里的换行先换成这个不可见的分隔符（后面的 {字段} 替换会把普通换行变成段内换行），最后再按它拆段。
LINE_SEPARATOR = "\u2063"


def _split_lines(root) -> None:
    """字段值里有换行（多个当事人）时，整段复制成几段，每段放一行；段落里其他文字（如“被告：”）每段都保留。"""
    for paragraph in list(root.iter(W + "p")):
        node = next((t for t in paragraph.iter(W + "t") if LINE_SEPARATOR in (t.text or "")), None)
        if node is None:
            continue
        lines = node.text.split(LINE_SEPARATOR)
        node.text = lines[0]
        anchor = paragraph
        for line in lines[1:]:
            clone = deepcopy(paragraph)
            target = next(t for t in clone.iter(W + "t") if t.text == lines[0])
            target.text = line
            anchor.addnext(clone)
            anchor = clone


NUMERALS = "零壹贰叁肆伍陆柒捌玖"


def amount_upper(value: str) -> str:
    """人民币金额大写，如 4500 → 肆仟伍佰元整，1200.5 → 壹仟贰佰元伍角。"""
    from decimal import Decimal, InvalidOperation
    text = str(value or "").replace(",", "").replace("，", "").replace("元", "").strip()
    try:
        amount = Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        return ""
    if amount < 0 or amount >= Decimal("1000000000000"):
        return ""
    integer, cents = divmod(int(amount * 100), 100)
    units, sections = ["", "拾", "佰", "仟"], ["", "万", "亿"]
    words, digits, zero = "", str(integer), False
    for position, char in enumerate(digits):
        place = len(digits) - position - 1
        digit = int(char)
        if digit:
            if zero:
                words += "零"
            words += NUMERALS[digit] + units[place % 4]
            zero = False
        else:
            zero = True
        if place % 4 == 0 and place and words and not words.endswith(tuple(sections[1:])):
            if digits[max(0, position - 3):position + 1].strip("0"):
                words += sections[place // 4]
                zero = False
    words = words + "元" if words else ("" if cents else "零元")
    jiao, fen = divmod(cents, 10)
    if not cents:
        return words + "整"
    if jiao:
        words += NUMERALS[jiao] + "角"
    elif integer:
        words += "零"
    if fen:
        words += NUMERALS[fen] + "分"
    return words


def paragraphs(content: bytes) -> list[str]:
    """预览用：按正文顺序给出段落文字；表格每行一条，各格用“｜”隔开（庭审纪要、要素式起诉状等表格式文书）。"""
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    document = Document(BytesIO(content))
    lines: list[str] = []
    for child in document.element.body.iterchildren():
        if child.tag == W + "p":
            lines.append(Paragraph(child, document).text)
        elif child.tag == W + "tbl":
            for row in Table(child, document).rows:
                cells, seen = [], set()
                for cell in row.cells:
                    if id(cell._tc) in seen:
                        continue
                    seen.add(id(cell._tc))
                    cells.append(cell.text.strip())
                lines.append("｜".join(cells))
    return lines


def field_keys(slots: list[dict]) -> list[str]:
    return list(dict.fromkeys(slot["key"] for slot in slots))


def _public(item: dict, slots: list[dict] | None = None) -> dict:
    result = {key: item.get(key) for key in ("id", "name", "builtin", "is_active", "updated_by", "updated_at")}
    result["options"] = item.get("options") or {}
    if slots is not None:
        result["slots"] = slots
        result["fields"] = field_keys(slots)
    return result


# ---------- 字段取值 ----------

def _names(value) -> list[str]:
    values = value if isinstance(value, list) else [value]
    return list(dict.fromkeys(part.strip() for item in values for part in SPLIT.split(str(item or "")) if part.strip()))


def _first(data: dict, *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            value = "、".join(_names(value))
        if value not in (None, "") and str(value).strip():
            return str(value).strip()
    return ""


def _court_keys(status_text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """按案件阶段取法院和法院案号：执行 > 再审 > 二审 > 一审；该阶段没填时退回一审。"""
    first = (("first_court_name", "first_instance_court", "first_intance_court", "court"),
             ("first_court_case_no", "first_instance_case_no", "first_intance_case_no", "court_case_no"))
    if "执行" in status_text:
        return (("execution_court_name", "execution_court", "execution_instance_court", *first[0]),
                ("execution_court_case_no", "execution_instance_case_no", "execution_intance_case_no", *first[1]))
    if "再审" in status_text:
        return (("retrial_court_name", "last_court_name", *first[0]), ("retrial_court_case_no", "last_court_case_no", "last_instance_case_no", *first[1]))
    if "二审" in status_text:
        return (("second_court_name", "second_instance_court", *first[0]), ("second_court_case_no", "second_instance_case_no", "second_intance_case_no", *first[1]))
    return first


ADDRESS_KEYS = ("contact_address", "registered_address", "registration_address", "address", "business_address", "invoice_address")
PHONE_KEYS = ("contact_phone", "phone", "mobile", "invoice_phone")


# 陶国南 11-05 10:34：生成文书时单位当事人缺法定代表人、信用代码、地址的，先用企业信息库存档（不扣次数），没有再查企查查（每家扣一次），
# 查到的存进企业信息库，以后复用；个人当事人不查。预览只看存档、列出需要查企查查的单位；下载或生成 Word 时才真正去查。
ENTERPRISE_LOOKUP: ContextVar[dict | None] = ContextVar("case_word_enterprise_lookup", default=None)
ENTERPRISE_FIELDS = ("credit_code", "legal_representative", "registered_address")


def _wanted(*keys: str) -> bool:
    """这份模板用不用这些字段；没在生成模板时（state 为空）照常算。用不到的当事人信息不算，也就不会为它去查企查查。"""
    state = ENTERPRISE_LOOKUP.get()
    fields = state.get("fields") if state else None
    return fields is None or any(key in fields for key in keys)


def _is_organization_name(name: str, profile: dict) -> bool:
    if profile.get("organization_type"):
        return profile["organization_type"] != "个人"
    return any(word in name for word in ORGANIZATION_WORDS) and len(name) > 4


def _needs_enterprise_info(profile: dict) -> bool:
    credit = str(profile.get("credit_code") or "").strip()
    return not credit or _looks_like_id_card(credit) or not _first(profile, "legal_representative") or not _first(profile, *ADDRESS_KEYS)


def _merge_enterprise(profile: dict, detail: dict) -> dict:
    merged = dict(profile)
    credit = str(merged.get("credit_code") or "").strip()
    if detail.get("credit_code") and (not credit or _looks_like_id_card(credit)):
        merged["credit_code"] = detail["credit_code"]
    if detail.get("legal_representative") and not _first(merged, "legal_representative"):
        merged["legal_representative"] = detail["legal_representative"]
    if detail.get("registered_address") and not _first(merged, *ADDRESS_KEYS):
        merged["registered_address"] = detail["registered_address"]
    return merged


async def _complete_enterprise(name: str, profile: dict, db: AsyncSession) -> dict:
    lookup = ENTERPRISE_LOOKUP.get()
    if lookup is None or not name or not _is_organization_name(name, profile) or not _needs_enterprise_info(profile):
        return profile
    from app.areas.crm.company_lookup import company_profile, lookup_company
    seen = lookup.setdefault("details", {})
    if name not in seen:
        seen[name] = await company_profile(db, name) or None
        if seen[name] is None and lookup.get("charge"):
            try:
                detail = await lookup_company(name, lookup["username"], db, aliases=(name,))
                seen[name] = detail
                if not detail.get("cached"):
                    lookup.setdefault("charged", []).append(name)
            except HTTPException as exc:
                lookup.setdefault("failed", []).append(f"{name}：{exc.detail}")
        elif seen[name] is None and name not in lookup.setdefault("pending", []):
            lookup["pending"].append(name)
    return _merge_enterprise(profile, seen[name]) if seen[name] else profile


def enterprise_notice(lookup: dict | None) -> dict:
    lookup = lookup or {}
    notice = {key: list(lookup.get(key) or []) for key in ("pending", "charged", "failed")}
    if notice["pending"]:
        notice["message"] = ("企业信息库里没有这几家单位的存档，下载或生成 Word 时会查企查查补全法定代表人、统一社会信用代码和地址（每家扣一次企查查次数）："
                             + "、".join(notice["pending"]))
    elif notice["charged"]:
        notice["message"] = "已查企查查补全：" + "、".join(notice["charged"]) + "（每家扣一次，已存进企业信息库，以后不再扣）"
    if notice["failed"]:
        notice["message"] = (notice.get("message", "") + "；" if notice.get("message") else "") + "没查到，请手写：" + "；".join(notice["failed"])
    return notice


async def _party_profiles(names: list[str], db: AsyncSession) -> dict[str, dict]:
    """当事人档案（当事人表优先，没有再看客户表）里的地址、电话、证件号。"""
    from app.data_models.parties import PartyRecord
    if not names:
        return {}
    profiles: dict[str, dict] = {}
    for title, data in (await db.execute(select(BusinessRecord.title, BusinessRecord.data).where(
            BusinessRecord.module == "customer", BusinessRecord.title.in_(names), BusinessRecord.deleted_at.is_(None)))).all():
        profiles[title.strip()] = dict(data or {})
    for name, data in (await db.execute(select(PartyRecord.name, PartyRecord.data).where(PartyRecord.name.in_(names)))).all():
        profiles[name.strip()] = {**profiles.get(name.strip(), {}), **(data or {})}
    for name in names:
        key = str(name or "").strip()
        completed = await _complete_enterprise(key, profiles.get(key, {}), db)
        if completed:
            profiles[key] = completed
    return profiles


ORGANIZATION_WORDS = ("公司", "店", "厂", "中心", "部", "所", "行", "馆", "社", "院", "局", "会", "站", "场", "室", "户）", "合作社")


def _looks_like_id_card(value: str) -> bool:
    """18 位身份证号（第 7～14 位是出生日期）；旧系统常把个人身份证号存在“统一社会信用代码”里。"""
    value = str(value or "").strip().upper()
    if not re.fullmatch(r"\d{17}[\dX]", value):
        return False
    try:
        datetime.strptime(value[6:14], "%Y%m%d")
    except ValueError:
        return False
    return True


def _is_person(name: str, identity: dict, identity_no: str, profile: dict) -> bool:
    if identity.get("organization_type"):
        return identity["organization_type"] == "个人"
    if any(word in name for word in ORGANIZATION_WORDS):
        return False
    if profile.get("credit_code") and not _looks_like_id_card(profile["credit_code"]):
        return False
    return len(identity_no) == 18 and identity_no[:17].isdigit() or len(name) <= 4


def _party_line(name: str, identity: dict, profile: dict, *, defendant: bool) -> str:
    """一位当事人的一行，各项都列出（陶国南 11-04 14:28）：单位写地址、统一社会信用代码；个人写性别（按身份证第 17 位）、身份证号、地址；
    被告再写联系方式。系统里没有的项留空格，打印后手写。"""
    identity_no = str(identity.get("identity_no") or profile.get("identity_no") or profile.get("credit_code") or "").strip().upper()
    address, phone = _first(profile, *ADDRESS_KEYS), _first(profile, *PHONE_KEYS)
    parts = [name]
    if _is_person(name, identity, identity_no, profile):
        gender = ("男" if int(identity_no[16]) % 2 else "女") if len(identity_no) == 18 and identity_no[16].isdigit() else ""
        parts += [gender or f"性别：{BLANK}", f"身份证号码：{identity_no or BLANK}", f"地址：{address or BLANK}"]
    else:
        parts += [f"{'地址' if defendant else '联系地址'}：{address or BLANK}", f"统一社会信用代码：{identity_no or BLANK}"]
    if defendant:
        parts.append(f"联系方式：{phone or BLANK}")
    return "，".join(parts)


async def _party_lines(data: dict, names: list[str], identities_key: str, db: AsyncSession, *, defendant: bool) -> str:
    identities = {str(item.get("name") or "").strip(): item for item in data.get(identities_key) or [] if isinstance(item, dict)}
    profiles = await _party_profiles(names, db)
    return "\n".join(_party_line(name, identities.get(name, {}), profiles.get(name, {}), defendant=defendant) for name in names)


CN_ORDINALS = "一二三四五六七八九十"


def _applicant_block(name: str, label: str, identity: dict, profile: dict, *, applicant: bool) -> list[str]:
    """申请书里一位申请人/被申请人的几行（陶国南 11-05 样本格式）：单位写统一社会信用代码、法定代表人和职务、住所；
    个人写性别、身份证号码、住址。法定代表人取当事人档案（多数没填），职务系统里没有，没有的留空格打印后手写；送达地址写沪知所地址。"""
    identity_no = str(identity.get("identity_no") or profile.get("identity_no") or profile.get("credit_code") or "").strip().upper()
    address = _first(profile, *ADDRESS_KEYS)
    if address == name:
        address = ""  # 旧系统有把名称填进地址的，不当地址用
    representative = _first(profile, "legal_representative")
    place = "住所" if applicant else "地址"
    if _is_person(name, identity, identity_no, profile):
        gender = ("男" if int(identity_no[16]) % 2 else "女") if len(identity_no) == 18 and identity_no[16].isdigit() else ""
        return [f"{label}：{name}，{gender or f'性别：{BLANK}'}，身份证号码：{identity_no or BLANK}", f"{place}：{address or BLANK}"]
    return [f"{label}：{name}", f"统一社会信用代码：{identity_no or BLANK}", f"法定代表人：{representative or BLANK}  职务：{_first(profile, 'legal_agent_title', 'legal_representative_title') or BLANK}",
            f"{place}：{address or BLANK}"]


def _mediation_block(name: str, label: str, identity: dict, profile: dict, agent: str) -> list[str]:
    """调解协议（诉讼中）一位当事人的几行（陶国南 11-05 12:15 样本格式）：单位写住所地、统一社会信用代码、法定代表人和职务；
    个人写性别、身份证号码、住址；最后一行代理人（本所委托人一方写经办律师和本所，对方留空手写）。"""
    identity_no = str(identity.get("identity_no") or profile.get("identity_no") or profile.get("credit_code") or "").strip().upper()
    address = _first(profile, *ADDRESS_KEYS)
    if address == name:
        address = ""
    if _is_person(name, identity, identity_no, profile):
        gender = ("男" if int(identity_no[16]) % 2 else "女") if len(identity_no) == 18 and identity_no[16].isdigit() else ""
        lines = [f"{label}：{name}，{gender or f'性别：{BLANK}'}，身份证号码：{identity_no or BLANK}", f"住址：{address or BLANK}"]
    else:
        title = _first(profile, "legal_agent_title", "legal_representative_title")
        lines = [f"{label}：{name}", f"住所地：{address or BLANK}", f"统一社会信用代码：{identity_no or BLANK}",
                 f"法定代表人：{_first(profile, 'legal_representative') or BLANK}          职务：{title or BLANK}"]
    return [*lines, f"代理人：{agent or BLANK}"]


async def _mediation_lines(data: dict, names: list[str], identities_key: str, db: AsyncSession, *, label: str, agent: str) -> str:
    identities = {str(item.get("name") or "").strip(): item for item in data.get(identities_key) or [] if isinstance(item, dict)}
    profiles = await _party_profiles(names, db)
    lines: list[str] = []
    for name in names or [""]:
        if not name:
            lines.append(f"{label}：{BLANK}")
            continue
        lines += _mediation_block(name, label, identities.get(name, {}), profiles.get(name, {}), agent)
    return "\n".join(lines)


async def _client_contact(record: BusinessRecord, db: AsyncSession) -> dict[str, str]:
    """胜诉退费确认书：当事人=本所委托人；联系方式、开户行、户名、账号取客户档案，没填的留空手写。"""
    name = str(record.customer or "").strip()
    profile = (await _party_profiles([name], db)).get(name, {}) if name else {}
    account = _first(profile, "bank_account")
    return {"委托人名称": name, "委托人联系方式": _first(profile, *PHONE_KEYS), "退费开户行": _first(profile, "bank_name"),
            "退费户名": (_first(profile, "bank_account_name", "account_name") or name) if account else "", "退费账号": account}


async def _delivery_contacts(db: AsyncSession, lawyers: list[str]) -> dict[str, str]:
    """送达地址确认书：送达地址=沪知所地址（系统参数）+“经办律师姓名律师手机”；联系方式、短信送达号码用经办律师手机，没填的留空手写。"""
    address = await firm_address(db)
    rows = (await db.scalars(select(User).where(User.username.in_(lawyers)))).all() if lawyers else []
    by_name = {row.username.casefold(): row for row in rows}
    people = []
    for token in lawyers:
        user = by_name.get(str(token).casefold())
        mobile = str(((user.profile if user else None) or {}).get("mobile") or "").strip()
        people.append(((user.display_name if user else str(token)), mobile))
    mobiles = list(dict.fromkeys(mobile for _, mobile in people if mobile))
    first_name, first_mobile = people[0] if people else ("", "")
    contact = f"，{first_name}律师{first_mobile}" if first_name else ""
    return {"送达地址": address + contact, "送达联系方式": first_mobile, "送达邮编": "", "短信送达号码": "、".join(mobiles)}


async def _applicant_lines(data: dict, names: list[str], identities_key: str, db: AsyncSession, *, applicant: bool) -> str:
    identities = {str(item.get("name") or "").strip(): item for item in data.get(identities_key) or [] if isinstance(item, dict)}
    profiles = await _party_profiles(names, db)
    word = "申请人" if applicant else "被申请人"
    lines = []
    for position, name in enumerate(names or [""]):
        label = word if len(names) <= 1 else f"{word}{CN_ORDINALS[position] if position < 10 else position + 1}"
        if not name:
            lines.append(f"{label}：{BLANK}")
            continue
        lines += _applicant_block(name, label, identities.get(name, {}), profiles.get(name, {}), applicant=applicant)
    if applicant:
        lines.append(f"送达地址：{await firm_address(db)}")
    return "\n".join(lines)


CN_DIGITS = "〇一二三四五六七八九"


def chinese_date(value: datetime) -> str:
    """落款日期写成“二〇二六年十一月五日”。"""
    def small(number: int) -> str:
        tens, ones = divmod(number, 10)
        return ("" if tens <= 1 else CN_DIGITS[tens]) + ("十" if tens else "") + (CN_DIGITS[ones] if ones else "")
    return "".join(CN_DIGITS[int(digit)] for digit in str(value.year)) + f"年{small(value.month)}月{small(value.day)}日"


def _day(value) -> datetime | None:
    text = str(value or "").strip()[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d") if text else None
    except ValueError:
        return None


def _day_text(*values) -> str:
    day = next((day for day in map(_day, values) if day), None)
    return f"{day.year}年{day.month}月{day.day}日" if day else ""


HEARING_DATE_KEYS = ("first_court_hearing_date", "second_court_hearing_date", "last_court_hearing_date", "execution_court_hearing_date")
CLOSING_WORDS = ("判决结案", "和解结案", "调解结案", "撤诉结案", "执行结案", "执行终本")


def _hearing_days(data: dict) -> str:
    """开庭日期按样本写成“2024.5.14；2025.11.18”，一审、二审、再审、执行各次开庭都列出。"""
    days = sorted({day for day in (_day(data.get(key)) for key in HEARING_DATE_KEYS) if day})
    return "；".join(f"{day.year}.{day.month}.{day.day}" for day in days)


def _our_agent(record: BusinessRecord, names: list[str], lawyers: str) -> str:
    """委托人在这一方时，代理人写经办律师和本所；不在这一方（对方当事人）留空。"""
    client = str(record.customer or "").strip()
    if client and client in [str(name).strip() for name in names] and lawyers:
        return f"{lawyers}，{FIRM_NAME}"
    return ""


def infringement_wording(cause: str) -> str:
    """调解协议（诉讼中）第一条“立即停止实施……的行为”按案由换说法（陶国南 11-05 13:28）。"""
    if "商标" in cause:
        return "侵害原告注册商标专用权"
    if "著作权" in cause or "版权" in cause:
        return "侵害原告著作权"
    if "专利" in cause:
        return "侵害原告专利权"
    if "不正当竞争" in cause:
        return "不正当竞争"
    return "侵害原告合法权益"


def retention_period(record: BusinessRecord, data: dict) -> str:
    """陶国南 11-05 11:25：民事案件、行政案件 20 年，刑事案件长期；其他（仲裁、法律顾问等）留空可选。没填案件类型的按案号（MS/XZ/XS）判断。"""
    case_type = str(data.get("case_type") or "")
    serial = str(record.serial_no or "").upper()
    if "刑事" in case_type or (not case_type and "XS" in serial):
        return "长期"
    if "民事" in case_type or "行政" in case_type or (not case_type and ("MS" in serial or "XZ" in serial)):
        return "20年"
    return ""


def _handling_result(record: BusinessRecord, data: dict) -> str:
    """处理结果的初稿：结案方式 + 诉讼标的额 + 判决/和解金额，律师可以改写。"""
    status = record.status or ""
    claim, judged, settled = (_amount_text(data.get(key)) for key in ("litigation_amount", "judgment_amount", "settlement_amount"))
    # 已归档的案件阶段里看不出怎么结的：有判决金额写判决结案，有和解金额写和解结案。
    closing = next((word for word in CLOSING_WORDS if word in status), "") or ("判决结案" if judged else "和解结案" if settled else "")
    parts = [closing]
    if claim:
        parts.append(f"诉讼标的额{claim}元")
    # 旧数据里判决金额和和解金额常是同一个数，按结案方式只写一个。
    if judged and "和解" not in closing and "调解" not in closing:
        parts.append(f"判决金额{judged}元")
    elif settled or judged:
        parts.append(f"{'调解' if '调解' in closing else '和解'}金额{settled or judged}元")
    return "，".join(part for part in parts if part)


def _stage_prefixes(status_text: str) -> tuple[str, ...]:
    """按案件阶段取法官、书记员、开庭时间：执行 > 二审 > 一审；该阶段没填时退回一审。"""
    if "执行" in status_text:
        return ("execution", "first")
    if "二审" in status_text:
        return ("second", "first")
    return ("first",)


def _stage_person(data: dict, status_text: str, role: str) -> str:
    # 新系统存姓名（first_court_judge），旧系统导入的存法官编号（first_instance_judge），编号再查法官表。
    keys = [key for stage in _stage_prefixes(status_text)
            for key in (f"{stage}_court_{role}", f"{stage}_instance_{role}", f"{stage}_intance_{role}")]
    return _first(data, *keys, role)


async def _court_officer(value: str, db: AsyncSession) -> tuple[str, str]:
    """法官/书记员：旧系统编号换成姓名和电话（旧系统法官表 BAS_Court_Officer）；本来就是姓名的原样用。"""
    if not value or not value.isdigit():
        return value, ""
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError
    try:
        async with db.begin_nested():
            row = (await db.execute(text('SELECT "OfficerName", "Phone" FROM "BAS_Court_Officer" WHERE "OfficerNo" = :no LIMIT 1'),
                                    {"no": value})).first()
    except SQLAlchemyError:
        row = None
    if not row:
        return "", ""
    return str(row[0] or "").strip(), str(row[1] or "").strip()


def _hearing_time(data: dict, status_text: str) -> str:
    """开庭时间写成“2025年7月28日 09:30”，没有具体钟点的只写日期。"""
    stage = _stage_prefixes(status_text)[0]
    keys = {"execution": "execution_court_hearing_date", "second": "second_court_hearing_date"}
    raw = _first(data, keys.get(stage, "first_court_hearing_date"), "first_court_hearing_date")
    day = _day(raw)
    if not day:
        return ""
    clock = raw[11:16] if len(raw) >= 16 and raw[10] in "T " else ""
    return f"{day.year}年{day.month}月{day.day}日" + (f" {clock}" if clock and clock != "00:00" else "")


async def _party_phones(names: list[str], db: AsyncSession) -> str:
    # 电话只看当事人档案，不为它查企查查（企查查不给电话，查了白扣次数）。
    token = ENTERPRISE_LOOKUP.set(None)
    try:
        profiles = await _party_profiles(names, db)
    finally:
        ENTERPRISE_LOOKUP.reset(token)
    phones = [(name, _first(profiles.get(name, {}), *PHONE_KEYS)) for name in names]
    if len(phones) == 1:
        return phones[0][1]
    return "；".join(f"{name}：{phone}" for name, phone in phones if phone)


def _amount_text(value) -> str:
    text = str(value or "").replace(",", "").strip()
    try:
        number = float(text)
    except ValueError:
        return ""
    return f"{number:.2f}".rstrip("0").rstrip(".") if number else ""


async def firm_address(db: AsyncSession) -> str:
    from app.models import SystemParameter
    rows = (await db.scalars(select(SystemParameter).where(SystemParameter.category == "payment_type", SystemParameter.name == FIRM_NAME,
                                                          SystemParameter.is_active.is_(True)).order_by(SystemParameter.id))).all()
    return next((str((row.extra or {}).get("address") or "").strip() for row in rows if str((row.extra or {}).get("address") or "").strip()),
                FIRM_ADDRESS)


async def firm_account(db: AsyncSession) -> dict[str, str]:
    """系统参数“付款单位”里本所的收款账户；没有维护时留空，生成时提示补填。"""
    from app.models import SystemParameter
    rows = (await db.scalars(select(SystemParameter).where(SystemParameter.category == "payment_type", SystemParameter.name == FIRM_NAME,
                                                          SystemParameter.is_active.is_(True)).order_by(SystemParameter.id))).all()
    for row in rows:
        extra = row.extra or {}
        bank, account = str(extra.get("account_bank") or "").strip(), str(extra.get("account") or "").strip()
        if bank and account:
            return {"收款户名": str(extra.get("payee") or FIRM_NAME).strip(), "收款开户行": bank, "收款账号": account,
                    "收款联行号": str(extra.get("bank_code") or extra.get("union_bank_no") or "").strip()}
    return {"收款户名": FIRM_NAME, "收款开户行": "", "收款账号": "", "收款联行号": ""}


async def case_field_values(record: BusinessRecord, db: AsyncSession, today: datetime | None = None) -> dict[str, str]:
    from app.core.cases import _case_commission_person_tokens
    from app.core.court_display import court_names_by_code

    data = record.data or {}
    court_keys, case_no_keys = _court_keys(record.status or "")
    court = _first(data, *court_keys)
    court = (await court_names_by_code(db)).get(court.casefold()) or court
    handling = _case_commission_person_tokens(data, ("handling_lawyer_usernames", "handling_lawyer_username", "handling_lawyers"))
    # 开庭律师按案件详情页同一规则：没单独填时取第一位经办律师（与 501222 一致）。
    hearing = _case_commission_person_tokens(data, (
        "hearing_lawyer_usernames", "hearing_lawyer_username", "court_lawyer_username", "hearing_lawyers", "hearing_lawyer", "court_lawyer",
    )) or handling[:1]
    assistant = _case_commission_person_tokens(data, ("assistant_username", "assistant", "case_assistant"))
    tokens = {token for token in (*handling, *hearing, *assistant)}
    users = {user.username.casefold(): user.display_name for user in (await db.scalars(select(User).where(User.username.in_(tokens)))).all()} if tokens else {}

    def people(items: list[str]) -> str:
        return "、".join(dict.fromkeys(users.get(item.casefold(), item) for item in items))

    today = today or datetime.now()
    plaintiffs = _names(data.get("plaintiffs") or data.get("plaintiff") or data.get("appellant_names"))
    defendants = _names(data.get("defendants") or data.get("defendant") or data.get("appellee_names"))
    compensation = _amount_text(data.get("settlement_amount") or data.get("judgment_amount"))
    judge = await _court_officer(_stage_person(data, record.status or "", "judge"), db)
    clerk = await _court_officer(_stage_person(data, record.status or "", "clerk"), db)
    payment_date = _first(data, *PAYMENT_DATE_KEYS)[:10]
    try:
        due = datetime.strptime(payment_date, "%Y-%m-%d") if payment_date else today + timedelta(days=DEFAULT_PAYMENT_DAYS)
    except ValueError:
        due = today + timedelta(days=DEFAULT_PAYMENT_DAYS)
    return {
        "法院": court,
        "法院案号": _first(data, *case_no_keys),
        "原告": "、".join(_names(data.get("plaintiffs") or data.get("plaintiff") or data.get("appellant_names"))),
        "被告": "、".join(_names(data.get("defendants") or data.get("defendant") or data.get("appellee_names"))),
        "第三人": "、".join(_names(data.get("third_parties") or data.get("third_party") or data.get("the_third_names"))),
        # 案由树里的编号（如“十五、不正当竞争纠纷”）不进文书。
        # 陶国南 11-05 13:10：统一的取案由逻辑（app/core/case_cause.py）：案件 → 当前审级法院信息 → 旧系统 → 按权利类型推定。
        "案由": case_cause(data, record.status or ""),
        "侵权行为表述": infringement_wording(case_cause(data, record.status or "")),
        "开庭律师": people(hearing),
        "经办律师": people(handling),
        "律师助理": people(assistant),
        "客户名称": record.customer or "",
        "案件编号": record.serial_no,
        "生成日期": f"{today.year}年{today.month}月{today.day}日",
        "原告信息": await _party_lines(data, plaintiffs, "plaintiff_identities", db, defendant=False) if _wanted("原告信息") else "",
        "被告信息": await _party_lines(data, defendants, "defendant_identities", db, defendant=True) if _wanted("被告信息") else "",
        # 陶国南 11-04 14:19：委托诉讼代理人用案件的经办律师，律所用本所。
        "委托诉讼代理人": people(handling),
        "代理律所": FIRM_NAME,
        "赔偿金额": compensation,
        "付款期限": f"{due.year}年{due.month}月{due.day}日",
        "签署日期": f"{today.year}年{today.month}月{today.day}日",
        "赔偿金额大写": amount_upper(compensation) if compensation else "",
        # 陶国南 11-05 申请书：申请人=原告，被申请人=被告；保全金额默认取案件的诉讼标的额，可以改。
        "申请人信息": await _applicant_lines(data, plaintiffs, "plaintiff_identities", db, applicant=True) if _wanted("申请人信息") else "",
        "被申请人信息": await _applicant_lines(data, defendants, "defendant_identities", db, applicant=False) if _wanted("被申请人信息") else "",
        "落款日期": chinese_date(today),
        "保全金额": _amount_text(data.get("litigation_amount") or data.get("claim_amount")),
        # 陶国南 11-05 办案小结：收案=建案登记日，起诉=一审立案日，结案=结案时间，归档日期=归档时间（还没归档就写生成当天）。
        "收案日期": _day_text(data.get("case_register_date"), record.created_at.isoformat() if record.created_at else ""),
        "起诉日期": _day_text(data.get("first_court_filing_date"), data.get("filing_date"), data.get("filing_time")),
        "结案日期": _day_text(data.get("case_closed_at"), data.get("closing_time")),
        "开庭日期": _hearing_days(data),
        "处理结果": _handling_result(record, data),
        "归档日期": chinese_date(_day(data.get("archived_at")) or today),
        "保管期限": retention_period(record, data),
        # 陶国南 11-05 12:15 调解协议（诉讼中）：本所委托人一方的代理人写“经办律师，上海沪知律师事务所”，对方代理人留空手写。
        "调解原告信息": await _mediation_lines(data, plaintiffs, "plaintiff_identities", db, label="原告",
                                         agent=_our_agent(record, plaintiffs, people(handling))) if _wanted("调解原告信息") else "",
        "调解被告信息": await _mediation_lines(data, defendants, "defendant_identities", db, label="被告",
                                         agent=_our_agent(record, defendants, people(handling))) if _wanted("调解被告信息") else "",
        "付款被告": "、".join(defendants),
        **(await _delivery_contacts(db, handling) if _wanted("送达地址", "送达联系方式", "短信送达号码") else {}),
        **(await _client_contact(record, db) if _wanted("委托人名称", "委托人联系方式", "退费开户行", "退费户名", "退费账号") else {}),
        # 陶国南 11-05 12:19 庭审纪要：时间、法官、书记员按案件当前阶段取；联系方式取当事人档案，没有的留空。
        "开庭时间": _hearing_time(data, record.status or ""),
        "主审法官": judge[0],
        "书记员": clerk[0],
        "原告联系方式": await _party_phones(plaintiffs, db) if _wanted("原告联系方式") else "",
        "被告联系方式": await _party_phones(defendants, db) if _wanted("被告联系方式") else "",
        "法官联系方式": judge[1],
        "书记员联系方式": clerk[1],
        **(await firm_account(db)),
    }


async def element_parties(record: BusinessRecord, db: AsyncSession, today: datetime | None = None) -> dict:
    """要素式起诉状的当事人几块（element_complaint）：原告、被告、第三人逐位的类型和信息，委托诉讼代理人=经办律师。"""
    from app.areas.legal.element_complaint import party_entry
    data = record.data or {}
    today = today or datetime.now()
    result: dict = {"firm": FIRM_NAME, "date": f"{today.year}年{today.month}月{today.day}日"}
    for role, keys, identities_key in (("原告", ("plaintiffs", "plaintiff", "appellant_names"), "plaintiff_identities"),
                                       ("被告", ("defendants", "defendant", "appellee_names"), "defendant_identities"),
                                       ("第三人", ("third_parties", "third_party", "the_third_names"), "third_party_identities")):
        names = _names(next((data.get(key) for key in keys if data.get(key)), None))
        identities = {str(item.get("name") or "").strip(): item for item in data.get(identities_key) or [] if isinstance(item, dict)}
        profiles = await _party_profiles(names, db)
        result[role] = [party_entry(name, identities.get(name, {}), profiles.get(name, {}), is_person=_is_person, first=_first,
                                    address_keys=ADDRESS_KEYS, phone_keys=PHONE_KEYS, looks_like_id_card=_looks_like_id_card)
                        for name in names]
    result["agents"] = (await case_field_values(record, db, today))["经办律师"]
    return result


def finish_document(item: dict, document: bytes) -> bytes:
    """按模板替换完字段后，特殊格式的模板再做一步（要素式起诉状填当事人几块）。"""
    if item.get("form") == "element_complaint" and item.get("_parties"):
        from app.areas.legal.element_complaint import fill_element_complaint
        return fill_element_complaint(document, item["_parties"])
    return document


async def _fields(record: BusinessRecord, item: dict, content: bytes, db: AsyncSession, overrides: dict[str, str]) -> tuple[list[dict], list[dict]]:
    slots = resolve_slots(scan(content), item.get("mapping"))
    state = ENTERPRISE_LOOKUP.get()
    if state is not None:
        state["fields"] = {slot["key"] for slot in slots}
    auto = await case_field_values(record, db)
    sources = {slot["key"]: slot["source"] for slot in slots}
    optional = set(item.get("optional") or [])
    values = {}
    for key in field_keys(slots):
        if key in DERIVED_FIELDS:
            continue
        # 只去掉普通空白；留给手写的全角空格要保留。
        values[key] = str(overrides.get(key, auto.get(key, "") if sources[key] == "case" else "")).strip(" \t\r\n")
    for key, base in DERIVED_FIELDS.items():
        if key in sources:
            values[key] = amount_upper(values.get(base, auto.get(base, ""))) if values.get(base, auto.get(base, "")) else ""
    result = []
    for key in field_keys(slots):
        value = values[key]
        result.append({"key": key, "value": value, "source": sources[key], "missing": not value and key not in optional,
                       "optional": key in optional, "derived": key in DERIVED_FIELDS, "multiline": key in MULTILINE_FIELDS,
                       "options": (item.get("options") or {}).get(key, [])})
    return result, slots


async def _case(case_id: int, identity: dict, db: AsyncSession, *, write: bool) -> BusinessRecord:
    from app.core.permissions import _ensure_record_module, _require_case_document_write_access
    record = await _ensure_record_module(case_id, "case", identity, db)
    if write:
        await _require_case_document_write_access(record, identity, db)
    return record


async def _render(case_id: int, template_id: str, body: GenerateInput, identity: dict, db: AsyncSession, *, write: bool,
                  charge: bool = False, lookup: dict | None = None):
    """charge=True（下载、生成 Word）时，单位当事人存档里没有的才查企查查；预览只看存档。"""
    record = await _case(case_id, identity, db, write=write)
    item = await _template(db, template_id)
    if not item.get("is_active", True):
        raise HTTPException(409, "这个文书模板已停用")
    content = await _template_bytes(item, db)
    state = lookup if lookup is not None else {}
    state.update(charge=charge, username=identity["username"])
    token = ENTERPRISE_LOOKUP.set(state)
    try:
        fields, slots = await _fields(record, item, content, db, body.values)
        if item.get("form") == "element_complaint":
            item = {**item, "_parties": await element_parties(record, db)}
    finally:
        ENTERPRISE_LOOKUP.reset(token)
    missing = [field["key"] for field in fields if field["missing"]]
    return record, item, fields, missing, content, slots


# ---------- 接口：模板管理 ----------

@router.get("/case-word-templates")
async def list_templates(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """所有能看案件的人都能看到启用的模板；管理员还能看到已停用的。"""
    from app.core.permissions import _require_admin
    try:
        _require_admin(identity)
        admin = True
    except HTTPException:
        admin = False
    _, value = await _config(db)
    items = []
    for item in _merged(value):
        if not admin and not item.get("is_active", True):
            continue
        items.append(_public(item, resolve_slots(scan(await _template_bytes(item, db)), item.get("mapping"))))
    return {"items": items, "can_manage": admin, "auto_fields": list(AUTO_FIELDS)}


async def _store_template_file(upload: UploadFile, identity: dict, db: AsyncSession) -> tuple[FileAttachment, list[dict]]:
    name = upload.filename or "模板.docx"
    if not name.lower().endswith(".docx"):
        raise HTTPException(422, "请上传 Word 文件（.docx）；.doc 请先另存为 .docx")
    content = await upload.read(MAX_TEMPLATE_BYTES + 1)
    if len(content) > MAX_TEMPLATE_BYTES:
        raise HTTPException(413, "模板文件不能超过 10MB")
    fields = scan(content)
    if not fields:
        raise HTTPException(422, "模板里没有找到要替换的地方：请把要替换的文字加下划线，后面用括号写说明，例如“上海市浦东新区人民法院（哪个法院）”")
    stored_name = f"{uuid4().hex}.docx"
    path = UPLOAD_ROOT / stored_name
    await run_in_threadpool(path.write_bytes, content)
    attachment = FileAttachment(record_id=None, category=TEMPLATE_CATEGORY, original_name=name, stored_name=stored_name,
                                content_type=DOCX_TYPE, size=len(content), path=str(path), uploader=identity["username"], remark="案件文书模板")
    db.add(attachment)
    await db.flush()
    return attachment, fields


@router.post("/case-word-templates", status_code=status.HTTP_201_CREATED)
async def create_template(name: str = Form(..., min_length=1, max_length=60), file: UploadFile = File(...),
                          identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_template_admin(identity)
    record, value = await _config(db, lock=True)
    if any(item["name"] == name.strip() for item in _merged(value)):
        raise HTTPException(409, "已有同名模板")
    attachment, slots = await _store_template_file(file, identity, db)
    item = {"id": "t-" + uuid4().hex[:10], "name": name.strip(), "attachment_id": attachment.id, "is_active": True,
            "options": {}, "mapping": {}, "updated_by": identity["username"], "updated_at": _now()}
    await _save(db, record, {**value, "items": [*value.get("items", []), item]})
    return _public({"builtin": False, **item}, resolve_slots(slots, {}))


@router.put("/case-word-templates/{template_id}/file")
async def replace_template_file(template_id: str, file: UploadFile = File(...), identity: dict = Depends(current_identity),
                                db: AsyncSession = Depends(get_db)):
    """修改模板：上传新的 Word 替换（旧文件保留不删）。"""
    _require_template_admin(identity)
    await _template(db, template_id)
    record, value = await _config(db, lock=True)
    attachment, slots = await _store_template_file(file, identity, db)
    # 换了文件，字段位置可能变了：对应关系重新按说明识别，管理员再核对。
    item = await _update(db, record, value, template_id, {"attachment_id": attachment.id, "mapping": {}}, identity)
    return _public(item, resolve_slots(slots, {}))


@router.patch("/case-word-templates/{template_id}")
async def update_template(template_id: str, body: TemplateUpdate, identity: dict = Depends(current_identity),
                          db: AsyncSession = Depends(get_db)):
    """改名、停用/启用、维护常用选项（如撤诉理由）、改“识别到的字段 → 案件里哪一项”。"""
    _require_template_admin(identity)
    await _template(db, template_id)
    record, value = await _config(db, lock=True)
    changes = body.model_dump(exclude_none=True)
    if "options" in changes:
        changes["options"] = {key: [text.strip() for text in items if text.strip()][:30] for key, items in changes["options"].items()}
    if "mapping" in changes:
        for slot in changes["mapping"].values():
            if slot.get("source") == "case" and slot.get("field") not in AUTO_FIELDS:
                raise HTTPException(422, "对应的案件信息不在可选范围内")
            if slot.get("source") == "manual" and not str(slot.get("label") or "").strip():
                raise HTTPException(422, "生成时手填的字段要写一个名称")
    item = await _update(db, record, value, template_id, changes, identity)
    return _public(item, resolve_slots(scan(await _template_bytes(item, db)), item.get("mapping")))


@router.delete("/case-word-templates/{template_id}")
async def delete_template(template_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """逻辑删除；内置模板不能删，只能停用。"""
    _require_template_admin(identity)
    if template_id in {item["id"] for item in BUILTIN_TEMPLATES}:
        raise HTTPException(409, "内置模板不能删除，可以停用")
    await _template(db, template_id)
    record, value = await _config(db, lock=True)
    await _update(db, record, value, template_id, {"deleted_at": _now(), "deleted_by": identity["username"]}, identity)
    return {"ok": True}


@router.get("/case-word-templates/{template_id}/download")
async def download_template(template_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_template_admin(identity)
    item = await _template(db, template_id)
    content = await _template_bytes(item, db)
    return _docx_response(content, f"{item['name']}-模板.docx")


async def _update(db: AsyncSession, record, value: dict, template_id: str, changes: dict, identity: dict) -> dict:
    items = list(value.get("items", []))
    current = next((item for item in items if item["id"] == template_id), None)
    if current is None:  # 内置模板第一次修改时加一条覆盖记录
        current = {"id": template_id}
        items.append(current)
    current.update({**changes, "updated_by": identity["username"], "updated_at": _now()})
    await _save(db, record, {**value, "items": items})
    return next(item for item in _merged({**value, "items": items}) if item["id"] == template_id) if not changes.get("deleted_at") else current


async def _save(db: AsyncSession, record, value: dict) -> None:
    if record is None:
        record = SystemConfig(key=CONFIG_KEY, label="案件文书模板", group="业务配置",
                              description="按固定模板生成文书的模板清单；在案件空间“按模板生成文书”里使用", value={})
    record.value = value
    db.add(record)
    await db.commit()


def _docx_response(content: bytes, filename: str) -> Response:
    return Response(content=content, media_type=DOCX_TYPE,
                    headers={"Content-Disposition": f"attachment; filename=document.docx; filename*=UTF-8''{quote(filename)}"})


# ---------- 接口：在案件里生成 ----------

@router.post("/cases/{case_id}/documents/word-templates/{template_id}/preview")
async def preview_document(case_id: int, template_id: str, body: GenerateInput, identity: dict = Depends(current_identity),
                           db: AsyncSession = Depends(get_db)):
    """列出字段（系统取的值、缺哪些）和替换后的正文，不保存。"""
    lookup: dict = {}
    record, item, fields, missing, content, slots = await _render(case_id, template_id, body, identity, db, write=False, lookup=lookup)
    filled = finish_document(item, fill(content, slots, {field["key"]: field["value"] or (BLANK if field["optional"] else "【" + field["key"] + "待填写】") for field in fields}))
    return {"template": _public(item), "fields": fields, "missing": missing, "paragraphs": paragraphs(filled),
            "filename": f"{record.serial_no}-{item['name']}.docx", "enterprise_lookup": enterprise_notice(lookup)}


@router.post("/cases/{case_id}/documents/word-templates/{template_id}/download")
async def download_preview(case_id: int, template_id: str, body: GenerateInput, identity: dict = Depends(current_identity),
                           db: AsyncSession = Depends(get_db)):
    """下载预览用的 Word，不保存到案件。"""
    record, item, fields, missing, content, slots = await _render(case_id, template_id, body, identity, db, write=False, charge=True)
    if missing:
        raise HTTPException(422, "还缺：" + "、".join(missing))
    return _docx_response(finish_document(item, fill(content, slots, {field["key"]: field["value"] or (BLANK if field["optional"] else "") for field in fields})), f"{record.serial_no}-{item['name']}.docx")


@router.post("/cases/{case_id}/documents/word-templates/{template_id}/generate", status_code=status.HTTP_201_CREATED)
async def generate_document(case_id: int, template_id: str, body: GenerateInput, identity: dict = Depends(current_identity),
                            db: AsyncSession = Depends(get_db)):
    """确认后生成 Word 存进案件空间（和分支3 501226 同一种存法：统一存储写 OSS、回读校验后才建附件）。"""
    from app.core.cases import _case_ai_draft_name
    from app.core.generated_file_storage import save_generated_file
    from app.core.storage import _attachment_dict
    lookup: dict = {}
    record, item, fields, missing, content, slots = await _render(case_id, template_id, body, identity, db, write=True, charge=True, lookup=lookup)
    if missing:
        raise HTTPException(422, "还缺：" + "、".join(missing) + "，补齐后再生成")
    document = finish_document(item, fill(content, slots, {field["key"]: field["value"] or (BLANK if field["optional"] else "") for field in fields}))
    safe = "".join(char for char in item["name"] if char not in '\\/:*?"<>|')[:60]
    filename = _case_ai_draft_name(f"{record.serial_no}_{safe}_{datetime.now():%Y%m%d%H%M%S}.docx")

    async def on_available(session, attachment):
        attachment.remark = f"按模板生成：{item['name']}"
        session.add(WorkflowEvent(record_id=record.id, action="按模板生成文书", from_status=record.status, to_status=record.status,
                                  operator=identity["username"], comment=f"{item['name']}｜{filename}"))

    result = await save_generated_file(db, identity, name=filename, content=document, content_type=DOCX_TYPE,
                                       source_kind="case_word_template", case_record=record, on_available=on_available)
    return {"attachment": _attachment_dict(result["attachment"], record), "fields": fields, "enterprise_lookup": enterprise_notice(lookup)}
