"""案件当事人信息（501226，陶国南 11-03）：案件信息里的原告、被告、第三人可以点开查看。

- 系统资料：当事人库、客户里同名的记录，加上案件里登记的证件信息；
- 工商信息：查过的直接显示（企业档案，不过期），不再扣费；没查过的点“查询工商信息”调企查查 410（0.20 元/家），
  只有点“重新查询”才会再计费。个人当事人不查工商信息。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.areas.crm.company_lookup import business_rows, company_profile, lookup_company
from app.config import settings
from app.core.dependencies import current_identity, get_db
from app.models import BusinessRecord, PartyRecord

router = APIRouter()

ROLES = (
    ("原告", ("plaintiffs", "plaintiff"), "plaintiff_identities"),
    ("被告", ("defendants", "defendant", "opponent"), "defendant_identities"),
    ("第三人", ("third_parties", "third_party"), "third_party_identities"),
)


def _names(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if isinstance(item, str) and str(item).strip()]
    text = str(value or "").strip()
    return [part.strip() for part in text.replace("，", "、").replace(",", "、").split("、") if part.strip()] if text else []


def case_party(record: BusinessRecord, name: str) -> tuple[str, dict]:
    """名称在本案哪一方，以及案件里登记的证件信息；不是本案当事人就 404。"""
    data = record.data or {}
    name = name.strip()
    for role, keys, identity_key in ROLES:
        names = next((found for key in keys if (found := _names(data.get(key)))), [])
        if name in names:
            identity = next((item for item in data.get(identity_key) or [] if isinstance(item, dict) and str(item.get("name") or "").strip() == name), {})
            return role, identity
    raise HTTPException(404, "不是本案当事人")


def _first(data: dict, *keys: str) -> str:
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    for key in keys:
        value = data.get(key) if key in data else legacy.get(key)
        if value not in (None, "") and str(value).strip():
            return str(value).strip()
    return ""


async def _local(db: AsyncSession, name: str) -> list[dict]:
    """系统里同名的当事人、客户记录（只取查看用的几项，不带银行账号等）。"""
    items = []
    customer = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "customer", BusinessRecord.title == name).order_by(BusinessRecord.id).limit(1))
    if customer is not None:
        items.append({"kind": "客户", "id": customer.id, "serial_no": customer.serial_no, "data": customer.data or {}})
    party = await db.scalar(select(PartyRecord).where(PartyRecord.name == name).order_by(PartyRecord.id).limit(1))
    if party is not None and not (customer and party.party_no == customer.serial_no):
        items.append({"kind": "当事人", "id": party.id, "serial_no": party.party_no, "data": party.data or {}})
    result = []
    for item in items:
        data = item.pop("data")
        rows = [("统一社会信用代码", _first(data, "credit_code", "LicenseNo")), ("组织类型", _first(data, "organization_type")),
                ("法定代表人", _first(data, "legal_representative", "legal_person", "LegalAgent")),
                ("地址", _first(data, "registered_address", "address", "contact_address", "ContactAddress")),
                ("电话", _first(data, "phone", "contact_phone", "ContactPhone"))]
        result.append({**item, "rows": [{"label": label, "value": value} for label, value in rows if value]})
    return result


def _keywords(name: str, identity: dict) -> list[str]:
    code = str(identity.get("identity_no") or "").strip().upper() if identity.get("organization_type") != "个人" else ""
    return [name, *([code] if len(code) == 18 else [])]


async def party_info(record: BusinessRecord, name: str, db: AsyncSession) -> dict:
    role, identity = case_party(record, name)
    name = name.strip()
    person = identity.get("organization_type") == "个人"
    business = None if person else await company_profile(db, *_keywords(name, identity))
    return {
        "name": name, "role": role, "person": person,
        "identity": {"organization_type": identity.get("organization_type") or "", "identity_no": identity.get("identity_no") or ""},
        "local": await _local(db, name),
        "business": {"rows": business_rows(business), "queried_at": business.get("queried_at") or "",
                     "abnormal": bool(business.get("abnormal"))} if business else None,
    }


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/parties/info")
async def get_case_party_info(case_id: int, name: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """当事人信息窗口：系统资料 + 已查过的工商信息（不调企查查）。"""
    from app.core.permissions import _ensure_record_module
    record = await _ensure_record_module(case_id, "case", identity, db)
    return await party_info(record, name, db)


class PartyLookupInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    refresh: bool = False


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/parties/business-info")
async def query_case_party_business_info(case_id: int, body: PartyLookupInput,
                                         identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """查询（或重新查询）当事人的企查查工商信息：没查过或 refresh=True 才计费，结果存进企业档案。"""
    from app.core.permissions import _ensure_record_module
    record = await _ensure_record_module(case_id, "case", identity, db)
    _role, party_identity = case_party(record, body.name)
    if party_identity.get("organization_type") == "个人":
        raise HTTPException(422, "个人当事人没有工商信息")
    keywords = _keywords(body.name.strip(), party_identity)
    if not body.refresh and await company_profile(db, *keywords):
        return await party_info(record, body.name, db)
    # 有信用代码按信用代码查，避免同名企业查错。
    await lookup_company(keywords[-1], identity["username"], db, refresh=body.refresh, aliases=tuple(keywords))
    return await party_info(record, body.name, db)


# ---------- 被告基本信息文档、尽职调查报告（501226 第 3 条） ----------
# 只用已存的工商信息生成 Word，存到案件 AI 空间，不另外调接口。报告目前只有工商登记部分（方案 A），
# 涉诉、失信、被执行、股东、经营风险要另买企查查接口，报告里写明“未核查”。

DOCUMENT_KINDS = {"basic": "基本信息", "due_diligence": "尽职调查报告"}
NOT_COVERED = ["涉诉情况（裁判文书、开庭公告、立案信息）", "失信被执行人", "被执行人", "限制高消费", "股东及出资",
               "主要人员", "经营异常", "行政处罚", "股权冻结、出质", "破产重整"]


def _risks(detail: dict) -> list[str]:
    from datetime import date
    risks = []
    if detail.get("abnormal"):
        risks.append(f"登记状态为“{detail.get('status')}”，主体可能已不能正常经营或承担责任")
    if detail.get("cancel_date") or detail.get("cancel_reason"):
        risks.append(f"已注销：{'，'.join(part for part in (detail.get('cancel_date'), detail.get('cancel_reason')) if part)}")
    if detail.get("revoke_date") or detail.get("revoke_reason"):
        risks.append(f"已吊销：{'，'.join(part for part in (detail.get('revoke_date'), detail.get('revoke_reason')) if part)}")
    end = str(detail.get("term_end") or "")
    if end and end < date.today().isoformat():
        risks.append(f"营业期限已于 {end} 届满")
    if detail.get("former_names"):
        risks.append("有曾用名，起诉和查询时注意名称变更")
    return risks


def render_party_docx(record: BusinessRecord, name: str, role: str, kind: str, detail: dict) -> bytes:
    from io import BytesIO
    from docx import Document
    from docx.shared import Pt, RGBColor

    document = Document()
    document.styles["Normal"].font.size = Pt(10.5)
    title = f"{role}{DOCUMENT_KINDS[kind]}"
    document.add_heading(f"{title}：{name}", level=1)
    queried = str(detail.get("queried_at") or "")[:10]
    document.add_paragraph(f"案件：{record.serial_no} {record.title}")
    document.add_paragraph(f"数据来源：企查查企业工商信息{f'（{queried} 查询）' if queried else ''}。以国家企业信用信息公示系统为准。")

    def table(rows: list[dict]) -> None:
        grid = document.add_table(rows=0, cols=2)
        grid.style = "Table Grid"
        for row in rows:
            cells = grid.add_row().cells
            cells[0].text, cells[1].text = row["label"], row["value"]

    from app.areas.crm.company_lookup import business_rows
    rows = business_rows(detail)
    if kind == "basic":
        table(rows)
    else:
        risks = _risks(detail)
        document.add_heading("一、结论摘要", level=2)
        if risks:
            for risk in risks:
                run = document.add_paragraph(style="List Bullet").add_run(risk)
                run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
        else:
            document.add_paragraph("工商登记层面未发现注销、吊销、营业期限届满等异常。")
        document.add_heading("二、主体工商登记情况", level=2)
        table(rows)
        document.add_heading("三、本报告未核查的事项", level=2)
        document.add_paragraph("以下事项需另行开通企查查对应接口或人工核查，本报告未涉及：")
        for item in NOT_COVERED:
            document.add_paragraph(item, style="List Bullet")
        document.add_paragraph("本报告由系统按固定模板根据工商信息生成，仅供办案参考，请律师核对后使用。")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class PartyDocumentInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: str = Field(pattern="^(basic|due_diligence)$")


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/parties/documents")
async def save_case_party_document(case_id: int, body: PartyDocumentInput,
                                   identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """把当事人工商信息生成 Word 存到案件 AI 空间：基本信息或尽职调查报告；只用已存的工商信息，不调接口。"""
    from app.core.cases import _case_ai_draft_name
    from app.core.constants import WORD_DOCUMENT_CONTENT_TYPE
    from app.core.generated_file_storage import save_generated_file
    from app.core.permissions import _ensure_record_module, _require_case_attachment_upload_access
    from app.core.storage import _attachment_dict
    from app.models import WorkflowEvent

    record = await _ensure_record_module(case_id, "case", identity, db)
    role, party_identity = case_party(record, body.name)
    name = body.name.strip()
    if party_identity.get("organization_type") == "个人":
        raise HTTPException(422, "个人当事人没有工商信息")
    detail = await company_profile(db, *_keywords(name, party_identity))
    if not detail:
        raise HTTPException(409, "请先点“查询工商信息”，查到后再生成")
    await _require_case_attachment_upload_access(record, identity, db)
    label = f"{role}{DOCUMENT_KINDS[body.kind]}"
    safe = "".join(char for char in name if char not in '\\/:*?"<>|')[:60]
    filename = _case_ai_draft_name(f"{record.serial_no}_{label}_{safe}.docx")

    async def on_available(session, item):
        item.remark = f"{label}（企查查工商信息生成）"
        session.add(WorkflowEvent(record_id=record.id, action=f"生成{label}", from_status=record.status,
                                  to_status=record.status, operator=identity["username"], comment=filename))

    result = await save_generated_file(
        db, identity, name=filename, content=render_party_docx(record, name, role, body.kind, detail),
        content_type=WORD_DOCUMENT_CONTENT_TYPE, source_kind="case_draft", case_record=record, on_available=on_available,
    )
    return {"file": _attachment_dict(result["attachment"], record)}
