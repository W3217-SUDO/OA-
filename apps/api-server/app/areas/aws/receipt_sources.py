"""按上传来源列出官文收文与案件内收文。"""

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_identity, get_db, settings
from app.core.permissions import _permission_payload_for_identity, _require_record_module_menu
from app.core.person_names import person_name
from app.core.query_batches import _scalars_in_batches
from app.core.storage import _attachment_dict
from app.core.system import _record_dict
from app.models import BusinessRecord, FileAttachment


router = APIRouter()
CHINA = timezone(timedelta(hours=8))

# 按文件名识别案件里的法院收文；“裁定书”和旧系统一致（501385，范文玲 11-04 确认；调解书、决定书等不计入）。
RECEIPT_KEYWORDS = ("缴费单", "判决书", "裁定书", "通知书", "传票", "告知书")
RECEIPT_MENU = {
    "official": "documents-official",
    "mine": "documents-my",
    "company": "documents-company",
}


def _is_actual_admin(identity: dict) -> bool:
    roles = identity.get("_actual_role_ids") or identity.get("role_ids") or [identity.get("role")]
    return "admin" in roles


async def is_official_receipt(record: BusinessRecord, db: AsyncSession) -> bool:
    if record.module != "document" or (record.data or {}).get("direction") != "收文":
        return False
    attachment_id = (record.data or {}).get("attachment_id")
    if not str(attachment_id or "").isdigit():
        return False
    attachment = await db.get(FileAttachment, int(attachment_id))
    if not attachment or attachment.category != "官方收文" or not attachment.record_id:
        return False
    case = await db.get(BusinessRecord, attachment.record_id)
    if not case or case.module != "case":
        return False
    return True


async def _require_receipt_menu(scope: str, identity: dict, db: AsyncSession) -> None:
    await _require_record_module_menu("document", identity, db, action="查看")
    if _is_actual_admin(identity):
        return
    permission = await _permission_payload_for_identity(identity, db)
    if RECEIPT_MENU[scope] not in set(permission.get("menu_keys") or []):
        raise HTTPException(status_code=403, detail="当前账号没有该收文窗口的查看权限")


async def can_read_receipt_attachment(attachment: FileAttachment, identity: dict, db: AsyncSession) -> bool:
    if not attachment.record_id:
        return False
    if _is_actual_admin(identity):
        return True
    permission = await _permission_payload_for_identity(identity, db)
    keys = set(permission.get("menu_keys") or [])
    if attachment.category == "官方收文":
        documents = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "document"))).all()
        linked = next((record for record in documents if
            (record.data or {}).get("direction") == "收文"
            and str((record.data or {}).get("attachment_id") or "") == str(attachment.id)
        ), None)
        if linked and await is_official_receipt(linked, db):
            return bool(keys & {"documents-official", "documents-company"})
    if not any(keyword in attachment.original_name for keyword in RECEIPT_KEYWORDS):
        return False
    if "documents-company" not in keys and not ("documents-my" in keys and attachment.uploader == identity["username"]):
        return False
    record = await db.get(BusinessRecord, attachment.record_id)
    return bool(record and record.module == "case")


def _case_attachment_row(attachment: FileAttachment, case: BusinessRecord) -> dict:
    case_data = case.data or {}
    # 按北京时间算日期：UTC 前 10 位会把 8 点前上传的算到前一天，默认当日就漏了。
    created = attachment.created_at
    if created is not None and created.tzinfo is not None:
        created = created.astimezone(CHINA)
    created_at = created.isoformat() if created else ""
    return {
        "id": -attachment.id,
        "serial_no": case.serial_no,
        "title": attachment.original_name,
        "customer": case.customer,
        "status": "已签收",
        "owner": attachment.uploader,
        "owner_display_name": person_name(attachment.uploader),
        "description": attachment.remark,
        "data": {
            "receipt_source": "case_attachment",
            "uploader_display_name": person_name(attachment.uploader),
            "attachment_id": attachment.id,
            "case_id": case.id,
            "case_no": case.serial_no,
            "plaintiff": case_data.get("plaintiff") or case.customer,
            "defendant": case_data.get("opponent") or "",
            "court_no": case_data.get("court_case_no") or case_data.get("first_court_case_no") or "",
            "court_name": case_data.get("court") or case_data.get("first_court_name") or "",
            "document_date": created_at[:10],
            "uploaded_at": created_at[:10],
            "uploader": attachment.uploader,
            "import_status": "已导入",
            "business_process_status": "未处理",
            "hearing_lawyer": case_data.get("hearing_lawyer") or "",
            "assistant": case_data.get("assistant") or "",
            "case_manager": case_data.get("case_manager") or "",
            "handling_lawyer": case_data.get("handling_lawyer") or "",
        },
    }


async def _fill_case_people(row_cases: list[tuple[dict, BusinessRecord]], db: AsyncSession) -> None:
    """收文列表的开庭律师、律师助理、品牌管理人显示姓名（陶威 11-07：这三列一直显示“姓名待维护”）。

    页面读 *_display_name，接口以前从没给过。开庭律师、律师助理按工作台同一套规则（账号→姓名，旧系统姓名兜底）；
    品牌管理人按案件导出：案件客户的客户管理人，旧系统 CoordinatorName 兜底。只给姓名，不带客户其他信息。
    """
    from app.core.system import _dashboard_people
    from app.models import User
    if not row_cases:
        return
    users_by_username = {user.username.lower(): user for user in (await db.scalars(select(User))).all()}
    cases = {case.id: case for _, case in row_cases}
    customer_ids = {int((case.data or {}).get("customer_id") or (case.data or {}).get("customer_record_id") or 0) for case in cases.values()} - {0}
    customers = {item.id: item for item in await _scalars_in_batches(
        db, customer_ids, lambda batch: select(BusinessRecord).where(BusinessRecord.id.in_(batch), BusinessRecord.module == "customer"))}
    people: dict[int, dict] = {}
    for case_id, case in cases.items():
        data = case.data or {}
        legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
        customer = customers.get(int(data.get("customer_id") or data.get("customer_record_id") or 0))
        customer_data = (customer.data or {}) if customer else {}
        customer_legacy = customer_data.get("legacy_record") if isinstance(customer_data.get("legacy_record"), dict) else {}
        people[case_id] = {
            "hearing_lawyer_display_name": _dashboard_people(
                users_by_username, data.get("hearing_lawyer_usernames"), data.get("hearing_lawyer_username"), data.get("hearing_lawyers"),
                data.get("hearing_lawyer"), data.get("hearing_lawyer_display_names"), data.get("hearing_lawyer_display_name"),
                legacy.get("CourtLawyerName")),
            "assistant_display_name": _dashboard_people(
                users_by_username, data.get("assistant_usernames"), data.get("assistant_username"), data.get("assistants"),
                data.get("assistant"), data.get("assistant_display_names"), data.get("assistant_display_name"),
                legacy.get("CaseAssistantName")),
            "brand_manager_display_name": _dashboard_people(
                users_by_username, customer_data.get("customer_managers"), customer_legacy.get("CoordinatorName")),
        }
    for row, case in row_cases:
        row["data"] = {**(row.get("data") or {}), **people[case.id]}


@router.get(f"{settings.api_prefix}/documents/receipts")
async def list_receipts(
    scope: str = Query(..., pattern="^(official|mine|company)$"),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
    uploaded_from: date | None = Query(default=None, description="上传日期起（北京时间，含当天）；和 uploaded_to 一起给"),
    uploaded_to: date | None = Query(default=None, description="上传日期止（北京时间，含当天）"),
):
    await _require_receipt_menu(scope, identity, db)
    # 收文台默认只看当天：以前日期只在浏览器里筛，每次都把全所 1 万多份收文整包取回（陶威 11-07 公司收文一直加载）。
    if (uploaded_from is None) != (uploaded_to is None):
        raise HTTPException(status_code=422, detail="上传日期起止要一起填")
    if uploaded_from is not None and uploaded_to is not None and uploaded_from > uploaded_to:
        raise HTTPException(status_code=422, detail="上传日期起不能晚于止")
    day_from = uploaded_from.isoformat() if uploaded_from else ""
    day_to = uploaded_to.isoformat() if uploaded_to else ""

    def in_upload_range(row: dict) -> bool:
        # 和页面原来的筛选完全一样：上传日期字符串在起止之间（按字符串比较）。
        value = str((row.get("data") or {}).get("uploaded_at") or "")
        return not day_from or (day_from <= value <= day_to)
    official_records = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "document"))).all()
    eligible_records = [
        record for record in official_records
        if (record.data or {}).get("direction") == "收文"
        and str((record.data or {}).get("attachment_id") or "").isdigit()
        and int((record.data or {}).get("attachment_id") or 0) > 0
    ]
    official_candidates = {
        int((record.data or {}).get("attachment_id")): record
        for record in eligible_records
    }
    official_attachments = {
        item.id: item for item in await _scalars_in_batches(
            db, official_candidates,
            lambda batch: select(FileAttachment).where(FileAttachment.id.in_(batch)),
        )
    }
    official_case_ids = {attachment.record_id for attachment in official_attachments.values() if attachment.record_id}
    official_cases = {
        case.id: case for case in await _scalars_in_batches(
            db, official_case_ids,
            lambda batch: select(BusinessRecord).where(BusinessRecord.id.in_(batch), BusinessRecord.module == "case"),
        )
    }
    official_ids = {
        attachment_id for attachment_id, attachment in official_attachments.items()
        if attachment.category == "官方收文"
        and attachment.record_id in official_cases
    }
    rows: list[dict] = []
    files: dict[int, dict] = {}
    row_cases: list[tuple[dict, BusinessRecord]] = []
    if scope in {"official", "company"}:
        for attachment_id in official_ids:
            record = official_candidates[attachment_id]
            attachment = official_attachments[attachment_id]
            row = _record_dict(record)
            row["data"] = {**row["data"], "receipt_source": "official_upload",
                           "uploader_display_name": person_name(attachment.uploader or record.owner)}
            if not in_upload_range(row):
                continue
            rows.append(row)
            row_cases.append((row, official_cases[attachment.record_id]))
            files[attachment_id] = _attachment_dict(attachment)

    if scope in {"mine", "company"}:
        keyword_filter = or_(*(FileAttachment.original_name.contains(word) for word in RECEIPT_KEYWORDS))
        case_query = (select(FileAttachment, BusinessRecord)
                      .join(BusinessRecord, FileAttachment.record_id == BusinessRecord.id)
                      .where(BusinessRecord.module == "case", keyword_filter))
        if uploaded_from is not None and uploaded_to is not None:
            # 案件附件的上传日期就是北京时间的上传那天（_case_attachment_row），按北京时间零点切。
            case_query = case_query.where(
                FileAttachment.created_at >= datetime.combine(uploaded_from, time.min, CHINA),
                FileAttachment.created_at < datetime.combine(uploaded_to + timedelta(days=1), time.min, CHINA))
        case_files = (await db.execute(case_query)).all()
        # 501385：旧系统归档官方收文时会在案件文档里另存一份，同一案件已有同名官方收文的那份案件附件不再重复列。
        official_names = {(official_attachments[item].record_id, official_attachments[item].original_name) for item in official_ids}
        for attachment, case in case_files:
            if attachment.id in official_ids or (attachment.record_id, attachment.original_name) in official_names:
                continue
            if scope == "mine" and attachment.uploader != identity["username"]:
                continue
            row = _case_attachment_row(attachment, case)
            if not in_upload_range(row):
                continue
            rows.append(row)
            row_cases.append((row, case))
            files[attachment.id] = _attachment_dict(attachment, case)

    await _fill_case_people(row_cases, db)
    rows.sort(key=lambda row: (str((row.get("data") or {}).get("uploaded_at") or ""), abs(row["id"])), reverse=True)
    return {"items": rows, "attachments": list(files.values()), "total": len(rows)}
