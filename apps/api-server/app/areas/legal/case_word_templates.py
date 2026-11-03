"""按固定模板生成文书（陶国南 11-03 15:56）。

管理员上传 Word 模板，模板里用 {法院}{原告}{被告}{案由}{法院案号}{开庭律师}{生成日期} 等占位字段。
生成时字段由系统按固定规则从案件信息取，案件里没有的（如撤诉理由）由人选常用项或手填；
正文不经过智能体改写，只替换字段，保留原件字体和段落。确认后存进案件空间文档，和“生成案件文书”同一种存法。
模板清单存在系统配置 case_word_templates 里；内置模板随代码发布，上传的模板文件按普通附件保存；删除只做逻辑删除。
"""
from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime
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

from app.areas.legal.template_documents import TEMPLATE_ROOT, WORD_NS, _replace_slots
from app.config import settings
from app.core.constants import UPLOAD_ROOT
from app.database import get_db
from app.models import BusinessRecord, FileAttachment, SystemConfig, User, WorkflowEvent
from app.security import current_identity

router = APIRouter(prefix=settings.api_prefix)
CONFIG_KEY = "case_word_templates"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TEMPLATE_CATEGORY = "案件文书模板"
GENERATED_CATEGORY = "案件生成文书"
PLACEHOLDER = re.compile(r"\{([一-龥A-Za-z0-9_（）()]{1,20})\}")
MAX_TEMPLATE_BYTES = 10 * 1024 * 1024
SPLIT = re.compile(r"[,，、;；\n]+")
CAUSE_NUMBER = re.compile(r"^\s*(?:[一二三四五六七八九十百]+|\d+)[、.．]\s*")

BUILTIN_TEMPLATES = [{
    "id": "withdrawal-application", "name": "撤诉申请书", "file": "withdrawal-application.docx",
    "options": {"撤诉理由": ["原被告之间已达成和解并履行", "原被告之间已达成和解", "被告已停止侵权并赔偿损失", "原告决定不再追究"]},
}]
# 系统自动取值的字段；模板里出现其他占位字段时，按“需要人工填写”处理。
AUTO_FIELDS = ("法院", "法院案号", "原告", "被告", "第三人", "案由", "开庭律师", "经办律师", "律师助理", "客户名称", "案件编号", "生成日期")


class TemplateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=60)
    is_active: bool | None = None
    options: dict[str, list[str]] | None = None


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
    return await run_in_threadpool((TEMPLATE_ROOT / item["file"]).read_bytes)


def placeholders(content: bytes) -> list[str]:
    """按出现顺序列出模板里的占位字段（同一段文字被 Word 拆开也能识别）。"""
    found: list[str] = []
    try:
        with ZipFile(BytesIO(content)) as source:
            for name in source.namelist():
                if name.startswith("word/") and name.endswith(".xml"):
                    root = etree.fromstring(source.read(name))
                    for paragraph in root.xpath("//w:p", namespaces=WORD_NS):
                        text = "".join(node.text or "" for node in paragraph.xpath(".//w:t", namespaces=WORD_NS))
                        found.extend(match.group(1) for match in PLACEHOLDER.finditer(text))
    except (BadZipFile, KeyError, etree.XMLSyntaxError) as exc:
        raise HTTPException(422, "不是有效的 Word 文件（.docx）") from exc
    return list(dict.fromkeys(found))


def fill(content: bytes, values: dict) -> bytes:
    """只替换占位字段，其余内容、字体、段落原样保留。"""
    output = BytesIO()
    with ZipFile(BytesIO(content)) as source, ZipFile(output, "w", ZIP_DEFLATED) as target:
        for item in source.infolist():
            payload = source.read(item.filename)
            if item.filename.startswith("word/") and item.filename.endswith(".xml") and b"{" in payload:
                root = etree.fromstring(payload)
                for paragraph in root.xpath("//w:p", namespaces=WORD_NS):
                    _replace_slots(paragraph, values, PLACEHOLDER)
                payload = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            target.writestr(item, payload)
    return output.getvalue()


def paragraphs(content: bytes) -> list[str]:
    """预览用：按段落给出正文文字。"""
    from docx import Document
    return [paragraph.text for paragraph in Document(BytesIO(content)).paragraphs]


def _public(item: dict, fields: list[str] | None = None) -> dict:
    result = {key: item.get(key) for key in ("id", "name", "builtin", "is_active", "options", "updated_by", "updated_at")}
    result["options"] = item.get("options") or {}
    if fields is not None:
        result["fields"] = fields
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
    return {
        "法院": court,
        "法院案号": _first(data, *case_no_keys),
        "原告": "、".join(_names(data.get("plaintiffs") or data.get("plaintiff") or data.get("appellant_names"))),
        "被告": "、".join(_names(data.get("defendants") or data.get("defendant") or data.get("appellee_names"))),
        "第三人": "、".join(_names(data.get("third_parties") or data.get("third_party") or data.get("the_third_names"))),
        # 案由树里的编号（如“十五、不正当竞争纠纷”）不进文书。
        "案由": CAUSE_NUMBER.sub("", _first(data, "cause_or_charge", "cause", "cause_of_action", "cause_name")),
        "开庭律师": people(hearing),
        "经办律师": people(handling),
        "律师助理": people(assistant),
        "客户名称": record.customer or "",
        "案件编号": record.serial_no,
        "生成日期": f"{today.year}年{today.month}月{today.day}日",
    }


async def _fields(record: BusinessRecord, item: dict, content: bytes, db: AsyncSession, overrides: dict[str, str]) -> list[dict]:
    auto = await case_field_values(record, db)
    result = []
    for key in placeholders(content):
        automatic = key in AUTO_FIELDS
        value = str(overrides.get(key, auto.get(key, "") if automatic else "")).strip()
        result.append({"key": key, "value": value, "source": "case" if automatic else "manual", "missing": not value,
                       "options": (item.get("options") or {}).get(key, [])})
    return result


async def _case(case_id: int, identity: dict, db: AsyncSession, *, write: bool) -> BusinessRecord:
    from app.core.permissions import _ensure_record_module, _require_case_document_write_access
    record = await _ensure_record_module(case_id, "case", identity, db)
    if write:
        await _require_case_document_write_access(record, identity, db)
    return record


async def _render(case_id: int, template_id: str, body: GenerateInput, identity: dict, db: AsyncSession, *, write: bool):
    record = await _case(case_id, identity, db, write=write)
    item = await _template(db, template_id)
    if not item.get("is_active", True):
        raise HTTPException(409, "这个文书模板已停用")
    content = await _template_bytes(item, db)
    fields = await _fields(record, item, content, db, body.values)
    missing = [field["key"] for field in fields if field["missing"]]
    return record, item, fields, missing, content


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
        items.append(_public(item, placeholders(await _template_bytes(item, db))))
    return {"items": items, "can_manage": admin, "auto_fields": list(AUTO_FIELDS)}


async def _store_template_file(upload: UploadFile, identity: dict, db: AsyncSession) -> tuple[FileAttachment, list[str]]:
    name = upload.filename or "模板.docx"
    if not name.lower().endswith(".docx"):
        raise HTTPException(422, "请上传 Word 文件（.docx）；.doc 请先另存为 .docx")
    content = await upload.read(MAX_TEMPLATE_BYTES + 1)
    if len(content) > MAX_TEMPLATE_BYTES:
        raise HTTPException(413, "模板文件不能超过 10MB")
    fields = placeholders(content)
    if not fields:
        raise HTTPException(422, "模板里没有找到占位字段，请用 {法院}{原告}{被告} 这样的写法标出要替换的地方")
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
    attachment, fields = await _store_template_file(file, identity, db)
    item = {"id": "t-" + uuid4().hex[:10], "name": name.strip(), "attachment_id": attachment.id, "is_active": True,
            "options": {}, "updated_by": identity["username"], "updated_at": _now()}
    await _save(db, record, {**value, "items": [*value.get("items", []), item]})
    return _public({"builtin": False, **item}, fields)


@router.put("/case-word-templates/{template_id}/file")
async def replace_template_file(template_id: str, file: UploadFile = File(...), identity: dict = Depends(current_identity),
                                db: AsyncSession = Depends(get_db)):
    """修改模板：上传新的 Word 替换（旧文件保留不删）。"""
    _require_template_admin(identity)
    await _template(db, template_id)
    record, value = await _config(db, lock=True)
    attachment, fields = await _store_template_file(file, identity, db)
    item = await _update(db, record, value, template_id, {"attachment_id": attachment.id}, identity)
    return _public(item, fields)


@router.patch("/case-word-templates/{template_id}")
async def update_template(template_id: str, body: TemplateUpdate, identity: dict = Depends(current_identity),
                          db: AsyncSession = Depends(get_db)):
    """改名、停用/启用、维护常用选项（如撤诉理由）。"""
    _require_template_admin(identity)
    await _template(db, template_id)
    record, value = await _config(db, lock=True)
    changes = body.model_dump(exclude_none=True)
    if "options" in changes:
        changes["options"] = {key: [text.strip() for text in items if text.strip()][:30] for key, items in changes["options"].items()}
    item = await _update(db, record, value, template_id, changes, identity)
    return _public(item, placeholders(await _template_bytes(item, db)))


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
    record, item, fields, missing, content = await _render(case_id, template_id, body, identity, db, write=False)
    filled = fill(content, {field["key"]: field["value"] or "【" + field["key"] + "待填写】" for field in fields})
    return {"template": _public(item), "fields": fields, "missing": missing, "paragraphs": paragraphs(filled),
            "filename": f"{record.serial_no}-{item['name']}.docx"}


@router.post("/cases/{case_id}/documents/word-templates/{template_id}/download")
async def download_preview(case_id: int, template_id: str, body: GenerateInput, identity: dict = Depends(current_identity),
                           db: AsyncSession = Depends(get_db)):
    """下载预览用的 Word，不保存到案件。"""
    record, item, fields, missing, content = await _render(case_id, template_id, body, identity, db, write=False)
    if missing:
        raise HTTPException(422, "还缺：" + "、".join(missing))
    return _docx_response(fill(content, {field["key"]: field["value"] for field in fields}), f"{record.serial_no}-{item['name']}.docx")


@router.post("/cases/{case_id}/documents/word-templates/{template_id}/generate", status_code=status.HTTP_201_CREATED)
async def generate_document(case_id: int, template_id: str, body: GenerateInput, identity: dict = Depends(current_identity),
                            db: AsyncSession = Depends(get_db)):
    """确认后生成 Word 存进案件空间文档（和“生成案件文书”同一种存法）。"""
    from app.core.storage import _attachment_dict
    record, item, fields, missing, content = await _render(case_id, template_id, body, identity, db, write=True)
    if missing:
        raise HTTPException(422, "还缺：" + "、".join(missing) + "，补齐后再生成")
    document = fill(content, {field["key"]: field["value"] for field in fields})
    stored_name = f"{uuid4().hex}.docx"
    path = UPLOAD_ROOT / stored_name
    await run_in_threadpool(path.write_bytes, document)
    name = f"{record.serial_no}-{item['name']}-{datetime.now():%Y%m%d%H%M%S}.docx"
    attachment = FileAttachment(record_id=record.id, category=GENERATED_CATEGORY, original_name=name, stored_name=stored_name,
                                content_type=DOCX_TYPE, size=len(document), path=str(path), uploader=identity["username"],
                                remark=f"按模板生成：{item['name']}")
    try:
        db.add(attachment)
        await db.flush()
        db.add(WorkflowEvent(record_id=record.id, action="按模板生成文书", from_status=record.status, to_status=record.status,
                             operator=identity["username"], comment=f"{item['name']}｜附件 {name}"))
        await db.commit()
        await db.refresh(attachment)
    except Exception:
        await db.rollback()
        await run_in_threadpool(path.unlink, missing_ok=True)
        raise
    return {"attachment": _attachment_dict(attachment, record), "fields": fields}
