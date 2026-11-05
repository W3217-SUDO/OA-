"""知识产权中心“专利转文”“商标转文”（280146 / 501616，照老系统恒达知识产权系统 CasePatentOfficeFile / CaseTrademarkOfficeFile）。

中间一栏的次级菜单照老系统：每项对应几种官文类型（文件类型编号同老系统），后面的数量是这些官文里还没转达的份数，
点一项右边出官文列表（筛选：案件编号或申请号、客户/申请人；列同老系统）。
勾选官文后：生成转文（按老系统转达函模板生成 Word，表里列勾选的案件，一次只能同一客户）、上传转文（把发出的转达函挂到案件上，
勾选的官文标成已转）、标记已转。沪知老知识产权系统（2018 年停用）留下的旧官文不列（数据不动）。
"""
import io
from datetime import date, datetime
from urllib.parse import quote

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.constants import UPLOAD_ROOT, WORD_DOCUMENT_CONTENT_TYPE
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, Document, File, FileAttachment, Form, HTTPException, Path, Query, Response,
    UploadFile, WorkflowEvent, current_identity, get_db, select, settings, uuid4,
)

router = APIRouter()

# 沪知老知识产权系统迁来的案件（2018 年停用，旧官文当年多半没标已转）不进转文列表。
LEGACY_SH_SOURCE = "hz_crm_20260930"
BLANK = "　" * 4

# (键, 名称, 官文类型编号, 转达函模板)。专利“转第一次审查意见通知书”老系统按发明/实用外观分两页，类型相同，这里合成一项，
# 生成时按案件类型选模板。
PATENT_ITEMS = [
    ("200101", "转专利申请受理通知书", ["200101"], "转专利申请受理通知书"),
    ("200021", "转费用减缓审批通知", ["200021"], "转费用减缓审批通知书"),
    ("3310362", "转受理通知书纸件", ["3310362"], "转受理通知书纸件及缴费通知"),
    ("210304", "转发明专利申请初步审查合格通知书", ["210304"], "转初审合格通知"),
    ("210305", "转发明专利申请公布通知书", ["210305"], "转发明公布通知书"),
    ("210307", "转发明专利申请进入实质审查阶段通知书", ["210307", "210308"], "转进入实质审查阶段通知"),
    ("210306", "转实质审查请求期限届满前通知", ["210306"], "转实质审查请求期限届满前通知书"),
    ("200028", "转手续合格通知书", ["200028"], "转手续合格通知书"),
    ("210302", "转补正通知", ["210302", "220302", "230301"], "转第N次补正通知书"),
    ("210401", "转第一次审查意见通知书", ["210401", "210402"], "转第一次审查意见通知书(发明)"),
    ("220301", "转第N次审查意见通知书", ["220301", "230302", "210403"], "转第N次审查意见通知书"),
    ("200029", "转办理手续补正通知书", ["200029"], "转办理手续补正通知书"),
    ("200305", "转驳回决定", ["200305", "210407", "210408"], "转驳回决定"),
    ("200026", "转恢复权利请求审批通知书", ["200026"], "转恢复权利请求审批通知书"),
    ("200032", "转办理恢复权利手续补正通知", ["200032"], "转办理恢复权利手续补正通知书"),
    ("200701", "转缴费通知书", ["200701"], "转官方缴费通知"),
    ("3310008", "转专利证书通知", ["3310008", "400001", "400002", "400003"], "转专利证书通知"),
    ("200022", "转视为撤回通知书", ["200022"], "转视为撤回通知书"),
    ("200601", "转视为放弃取得专利权通知书", ["200601"], "转视为放弃取得专利权通知书"),
    ("200302", "转视为未要求优先权通知", ["200302"], "转视为未要求优先权通知书"),
    ("200023", "转视为未提出通知", ["200023"], "转视为未提出通知"),
    ("200602", "转授权及缴纳授权费通知", ["200602"], "转授权通知书，通知缴纳授权费、手续费"),
    ("3310363", "转授权通知纸件", ["3310363"], "转授权通知书纸件及缴费通知"),
    ("200905", "转复审请求受理通知书", ["200905"], "转复审请求受理通知书"),
    ("200702", "转专利权终止", ["200702"], "转专利权终止通知书"),
]
PATENT_OTHER = ("other", "转其他官文", [], "转其他专利官文")
# 老系统“转其他官文”还排除了这两种（申请文件类）。
PATENT_OTHER_EXCLUDED = {"200103", "200105"}
TRADEMARK_ITEMS = [
    ("420008", "转商标注册证书", ["420008"], "转商标证书通知"),
    ("420001", "转商标注册申请受理通知书", ["420001"], "转商标受理通知"),
    ("420007", "转异议受理通知书", ["420007"], "转商标通知书"),
    ("420016", "转异议决定书", ["420016", "420017"], "转商标决定书"),
    ("420012", "转争议受理通知书", ["420012"], "转商标通知书"),
    ("420018", "转复审决定书", ["420018", "420019"], "转商标复审决定书"),
    ("4100005", "转商标续展注册证明", ["4100005"], "转商标通知书"),
    ("420013", "转不予受理通知书", ["420013"], "转商标通知书"),
    ("420011", "转商标驳回通知书", ["420011"], "转商标决定书"),
    ("420027", "转商标部分驳回通知书", ["420027"], "转商标决定书"),
    ("420015", "转商标评审申请受理通知书", ["420015", "420012", "420042", "420043"], "转商标复审受理通知"),
    ("4100010", "转商标核准转让证明", ["4100010"], "转商标通知书"),
    ("420039", "转商标注册申请初步审定公告通知书", ["420039"], "转商标通知书"),
    ("420002", "转商标注册申请补正通知书", ["420002"], "转商标补正通知书"),
    ("420022", "转许可备案通知书", ["420022"], "转商标通知书"),
    ("4100012", "转商标变更证明", ["4100012"], "转商标通知书"),
    ("420026", "转商标变更申请补正通知书", ["420026"], "转商标补正通知书"),
    ("420004", "转视为撤回通知书", ["420004"], "转商标通知书"),
    ("420023", "转异议答辩通知书", ["420023"], "转商标通知书"),
    ("renewal", "通知商标续展", ["420008"], "转商标通知书"),
    ("420409", "转商标转让受理通知书", ["420409"], "转商标通知书"),
    ("420414", "转商标转让申请补正通知书", ["420414"], "转商标补正通知书"),
    ("420032", "转撤销连续三年不使用注册商标受理通知书", ["420032"], "转商标通知书"),
    ("420031", "转注册商标连续三年不使用撤销申请的决定", ["420031"], "转商标决定书"),
    ("420416", "转关于提供注册商标使用证据的通知", ["420416"], "转商标通知书"),
    ("420411", "转商标评审案件答辩通知书", ["420411"], "转商标通知书"),
    ("420391", "转商标无效宣告请求裁定书", ["420391"], "转商标决定书"),
]
KINDS = {"patent": ("专利", PATENT_ITEMS, PATENT_OTHER), "trademark": ("商标", TRADEMARK_ITEMS, None)}
# 老系统模板里的旧收款账户，生成时换成 BUG20261030004 确认的账户（和专利年费 Word 一致）。
ACCOUNT_REPLACEMENTS = (("452075880439", "8110201012400029679"), ("中国银行上海市交大徐汇校区支行", "中信银行古北支行"))


class TransferMarkInput(BaseModel):
    attachment_ids: list[int] = Field(min_length=1, max_length=500)
    comment: str = Field(default="", max_length=500)


def _kind(kind: str):
    if kind not in KINDS:
        raise HTTPException(404, "转文类别不存在")
    return KINDS[kind]


def _patent_named_codes() -> set[str]:
    return {code for _, _, codes, _ in PATENT_ITEMS for code in codes} | PATENT_OTHER_EXCLUDED


def _item(kind: str, key: str):
    case_kind, items, other = _kind(kind)
    for item in items + ([other] if other else []):
        if item[0] == key:
            return item
    raise HTTPException(422, "转文项目无效，请刷新页面")


def _received(attachment: FileAttachment) -> date | None:
    if attachment.document_date:
        return attachment.document_date
    return attachment.created_at.date() if attachment.created_at else None


async def _base_query(kind: str, identity: dict, db: AsyncSession):
    from app.core.ipr import _ipr_case_list_conditions
    case_kind = _kind(kind)[0]
    conditions = await _ipr_case_list_conditions(identity, db, case_kind=case_kind)
    source = BusinessRecord.data["migration_source"].as_string()
    return select(FileAttachment, BusinessRecord).join(BusinessRecord, BusinessRecord.id == FileAttachment.record_id).where(
        *conditions, FileAttachment.deleted_at.is_(None), FileAttachment.file_type_code != "",
        (source.is_(None)) | (source != LEGACY_SH_SOURCE),
    )


def _matches(kind: str, item, code: str, official: set[str]) -> bool:
    if item[0] == "other":
        # 老系统“转其他官文”只算官文类型（IsOfficeFileType），不含委托资料、沟通记录、已生成的转达函等。
        return code in official and code not in _patent_named_codes()
    return code in item[2]


async def _official_codes(db: AsyncSession) -> set[str]:
    from app.models import SystemParameter
    rows = (await db.scalars(select(SystemParameter).where(SystemParameter.category == "ipr_case_file_type"))).all()
    return {row.code for row in rows if (row.extra or {}).get("is_official")}


async def _pending(kind: str, identity: dict, db: AsyncSession) -> list[tuple[FileAttachment, BusinessRecord]]:
    query = await _base_query(kind, identity, db)
    return list((await db.execute(query.where(FileAttachment.is_transmitted.is_(False)))).all())


@router.get(f"{settings.api_prefix}/ipr/transfer-center/{{kind}}/summary")
async def ipr_transfer_summary(kind: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import _require_record_module_menu
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    case_kind, items, other = _kind(kind)
    rows = await _pending(kind, identity, db)
    official = await _official_codes(db)
    out = []
    for item in items + ([other] if other else []):
        out.append({"key": item[0], "label": item[1], "count": sum(1 for attachment, _ in rows if _matches(kind, item, attachment.file_type_code, official))})
    return {"items": out, "title": f"{case_kind}转文"}


def _row(attachment: FileAttachment, record: BusinessRecord) -> dict:
    data = record.data or {}
    received = _received(attachment)
    application_date = str(data.get("application_date") or "")[:10]
    return {
        "attachment_id": attachment.id, "case_id": record.id, "serial_no": record.serial_no,
        "status": "已转" if attachment.is_transmitted else "未转", "file_type": attachment.category or "",
        "file_type_code": attachment.file_type_code, "file_name": attachment.original_name,
        "received_date": str(received) if received else "", "application_no": data.get("application_no") or "",
        "application_date": "" if application_date.startswith("2000-01-01") else application_date,
        "customer": record.customer or "", "customer_record_id": data.get("customer_record_id") or data.get("primary_customer_id"),
        "case_name": data.get("case_name") or record.title or "", "case_type": data.get("case_type_name") or data.get("case_type") or "",
        "trademark_class": data.get("trademark_class") or data.get("trademark_ids") or "",
    }


@router.get(f"{settings.api_prefix}/ipr/transfer-center/{{kind}}/items")
async def list_ipr_transfer_items(
    kind: str, item: str = Query(min_length=1, max_length=32), case_no: str = Query(default="", max_length=100),
    customer: str = Query(default="", max_length=100), status: str = Query(default="未转", pattern="^(未转|已转|全部)$"),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import _require_record_module_menu
    from app.areas.ipr.annual_fee_monitor import _search_key
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    selected = _item(kind, item)
    query = await _base_query(kind, identity, db)
    if status != "全部":
        query = query.where(FileAttachment.is_transmitted.is_(status == "已转"))
    official = await _official_codes(db)
    rows = [_row(attachment, record) for attachment, record in (await db.execute(query)).all() if _matches(kind, selected, attachment.file_type_code, official)]
    word, name = _search_key(case_no), _search_key(customer)
    if word:
        rows = [row for row in rows if word in _search_key(row["serial_no"]) or word in _search_key(row["application_no"])]
    if name:
        rows = [row for row in rows if name in _search_key(row["customer"])]
    rows.sort(key=lambda row: (row["received_date"] or "9999", row["serial_no"]), reverse=False)
    return {"items": rows, "total": len(rows), "label": selected[1]}


async def _selected(attachment_ids: list[int], identity: dict, db: AsyncSession) -> list[tuple[FileAttachment, BusinessRecord]]:
    from app.core.permissions import _ensure_record_module
    ids = list(dict.fromkeys(attachment_ids))
    pairs = list((await db.execute(select(FileAttachment, BusinessRecord).join(BusinessRecord, BusinessRecord.id == FileAttachment.record_id).where(
        FileAttachment.id.in_(ids), FileAttachment.deleted_at.is_(None), BusinessRecord.module == "ipr_case"))).all())
    if len(pairs) != len(ids):
        raise HTTPException(404, "有官文不存在或已删除，请刷新后重新勾选")
    for record_id in {record.id for _, record in pairs}:
        await _ensure_record_module(record_id, "ipr_case", identity, db)
    return pairs


@router.post(f"{settings.api_prefix}/ipr/transfer-center/mark-transmitted")
async def mark_ipr_transfer_transmitted(body: TransferMarkInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """标记已转：老系统“标记已转”，不生成、不上传。"""
    from app.core.permissions import _require_role_action
    await _require_role_action(identity, db, "ipr.official.manage")
    pairs = await _selected(body.attachment_ids, identity, db)
    now = datetime.now()
    changed = 0
    for attachment, record in pairs:
        if attachment.is_transmitted:
            continue
        attachment.is_transmitted = True; attachment.transmitted_at = now; attachment.transmitted_by = identity["username"]
        db.add(WorkflowEvent(record_id=record.id, action="官文标记已转", from_status=record.status, to_status=record.status,
                             operator=identity["username"], comment=f"{attachment.category}｜{attachment.original_name}" + (f"｜{body.comment.strip()}" if body.comment.strip() else "")))
        changed += 1
    await db.commit()
    return {"updated": changed}


@router.post(f"{settings.api_prefix}/ipr/transfer-center/upload", status_code=201)
async def upload_ipr_transfer_letter(
    file: UploadFile = File(...), attachment_ids: str = Form(...), document_date: date = Form(...), remark: str = Form(""),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """上传转文：发出的转达函挂到勾选官文所在的每个案件（文件类型“知识产权待转文”同类的转文），勾选的官文标成已转。"""
    import json as _json
    from app.core.permissions import _require_role_action
    await _require_role_action(identity, db, "ipr.official.manage")
    try:
        ids = [int(value) for value in _json.loads(attachment_ids)]
    except (TypeError, ValueError, _json.JSONDecodeError):
        raise HTTPException(422, "请勾选要转达的官文")
    if not ids or len(ids) > 500:
        raise HTTPException(422, "请勾选 1~500 份官文")
    pairs = await _selected(ids, identity, db)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".zip", ".rar"}:
        raise HTTPException(422, "不支持的文件格式")
    content = await file.read()
    if not content:
        raise HTTPException(422, "文件不能为空")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "单个文件不能超过 20MB")
    now, name = datetime.now(), Path(file.filename or "转达函").name
    records = {record.id: record for _, record in pairs}
    paths = []
    try:
        for record in records.values():
            target = UPLOAD_ROOT / f"{uuid4().hex}{suffix}"
            target.write_bytes(content)
            paths.append(target)
            db.add(FileAttachment(record_id=record.id, category="转文", file_type_code="IPR-TRANSFER", original_name=name, stored_name=target.name,
                                  content_type=file.content_type or "application/octet-stream", size=len(content), path=str(target),
                                  uploader=identity["username"], remark=remark.strip(), document_date=document_date,
                                  requires_transmission=False, is_transmitted=True, transmitted_at=now, transmitted_by=identity["username"]))
        for attachment, record in pairs:
            if not attachment.is_transmitted:
                attachment.is_transmitted = True; attachment.transmitted_at = now; attachment.transmitted_by = identity["username"]
            db.add(WorkflowEvent(record_id=record.id, action="官文已转达", from_status=record.status, to_status=record.status,
                                 operator=identity["username"], comment=f"{attachment.category}｜{attachment.original_name}｜转达函 {name}"))
        await db.commit()
    except Exception:
        await db.rollback()
        for path in paths:
            path.unlink(missing_ok=True)
        raise
    return {"cases": len(records), "transmitted": len(pairs)}


def _fill_table(table, rows: list[dict]) -> None:
    header = [cell.text.strip() for cell in table.rows[0].cells]
    values = {
        "序号": lambda i, r: str(i), "案件编号": lambda i, r: r["serial_no"], "申请号": lambda i, r: r["application_no"],
        "申请日": lambda i, r: r["application_date"], "案件名称": lambda i, r: r["case_name"], "类别": lambda i, r: r["trademark_class"],
        "收文日期": lambda i, r: r["received_date"], "发文日期": lambda i, r: r["received_date"],
    }
    for index, row in enumerate(rows, start=1):
        cells = table.add_row().cells
        for cell, title in zip(cells, header):
            cell.text = values[title](index, row) if title in values else ""


@router.get(f"{settings.api_prefix}/ipr/transfer-center/{{kind}}/generate")
async def generate_ipr_transfer_letter(
    kind: str, item: str = Query(min_length=1, max_length=32), attachment_ids: str = Query(min_length=1, max_length=5000),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """生成转文：按老系统转达函模板生成 Word；一次只能同一客户（老系统“客户不一致,不允许转文”）。金额留空手写。"""
    from app.core.permissions import _require_record_module_menu
    from app.areas.ipr.annual_fee_monitor import _customer_letter_fields, _fill_placeholders
    from app.areas.ipr.transfer_templates import TEMPLATES
    import base64
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    selected = _item(kind, item)
    try:
        ids = [int(value) for value in attachment_ids.split(",") if value.strip()]
    except ValueError:
        raise HTTPException(422, "请勾选要转达的官文")
    pairs = await _selected(ids, identity, db)
    rows = [_row(attachment, record) for attachment, record in pairs]
    if len({(row["customer_record_id"], row["customer"]) for row in rows}) > 1:
        raise HTTPException(422, "客户不一致，不允许转文：一次只能勾选同一客户的官文")
    template = selected[3]
    if selected[0] == "210401" and all("发明" not in row["case_type"] for row in rows):
        template = "转第一次审查意见通知书(实用新型,外观)"
    document = Document(io.BytesIO(base64.b64decode(TEMPLATES[template])))
    today = date.today()
    values = await _customer_letter_fields(rows[0]["customer_record_id"], rows[0]["customer"], db)
    values.update({"$FWR": str(today), "$FileName": "、".join(dict.fromkeys(row["file_type"] for row in rows)),
                   "$NAME": identity.get("display_name") or identity["username"], "$YYYYMMDD": today.strftime("%Y%m%d"),
                   "$TZSFWR": min((row["received_date"] for row in rows if row["received_date"]), default=""), "$YEAR": ""})
    values.update({f"${n}": BLANK for n in range(1, 19)})
    for key in ("$CopywriterName", "$CopywriterEmail", "$CopywriterMobilePhone", "$CopywriterTelPhone"):
        values.setdefault(key, BLANK)
    paragraphs = list(document.paragraphs)
    for table in document.tables:
        for cells in table.rows:
            for cell in cells.cells:
                paragraphs.extend(cell.paragraphs)
    ordered = dict(sorted(values.items(), key=lambda pair: -len(pair[0])))
    for paragraph in paragraphs:
        for old, new in ACCOUNT_REPLACEMENTS:
            if old in paragraph.text:
                _fill_placeholders(paragraph, {old: new})
        if "$" in paragraph.text:
            _fill_placeholders(paragraph, ordered)
    if document.tables:
        _fill_table(document.tables[-1], rows)
    buffer = io.BytesIO()
    document.save(buffer)
    filename = f"{selected[1]}-{values.get('$CUSTOMERNAME') or rows[0]['customer']}-{today}.docx"
    return Response(content=buffer.getvalue(), media_type=WORD_DOCUMENT_CONTENT_TYPE,
                    headers={"Content-Disposition": f"attachment; filename=transfer-letter.docx; filename*=UTF-8''{quote(filename)}"})
