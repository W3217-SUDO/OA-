"""案件未提成与退费查询的权限内筛选、计数和有界分页。"""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import BusinessRecord, User
from app.security import current_identity

router = APIRouter()


@router.get(f"{settings.api_prefix}/cases/special-records")
async def query_special_case_records(
    kind: Literal["unclaimed", "refund", "schedule"],
    scope: Literal["mine", "department", "company"] = "company",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200),
    serial_no: str = "", customer: str = "", court_case_no: str = "", notary_no: str = "",
    hearing_lawyer: str = "", assistant: str = "", investigator: str = "", source_person: str = "",
    case_stage: str = Query("", alias="status"), court: str = "", payee: str = "",
    refund_status: str = "", refund_amount: str = "", fee_type: str = "",
    paid_from: date | None = None, paid_to: date | None = None,
    hearing_from: date | None = None, hearing_to: date | None = None,
    source_from: date | None = None, source_to: date | None = None,
    plaintiff: str = "", defendant: str = "", third_party: str = "", keyword: str = "", handling_lawyer: str = "",
    case_type: str = "", document_name: str = "", log_content: str = "",
    export_format: Literal["xls"] | None = None,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.contracts import _contract_customer_record_dicts
    from app.core.permissions import _record_scope_conditions, _require_record_module_menu
    from app.core.system import _allowed_field_keys

    if paid_from and paid_to and paid_from > paid_to:
        raise HTTPException(422, "付款开始日期不能晚于结束日期")
    await _require_record_module_menu("case", identity, db, action="导出" if export_format else "查看")
    if export_format and kind != "schedule":
        raise HTTPException(422, "此导出入口仅支持公司开庭排期")
    if kind == "schedule":
        if scope != "company":
            raise HTTPException(422, "公司开庭排期仅支持公司查询范围")
        from app.areas.legal.hearing_query import query_company_hearings
        from app.areas.legal.case_hearing_export import export_company_hearing_cases
        query = export_company_hearing_cases if export_format else query_company_hearings
        return await query(
            identity, db, page=page, page_size=page_size,
            hearing_from=hearing_from, hearing_to=hearing_to, source_from=source_from, source_to=source_to,
            filters={"serial_no": serial_no, "customer": customer, "notary_no": notary_no,
                     "hearing_lawyer": hearing_lawyer, "assistant": assistant, "investigator": investigator,
                     "handling_lawyer": handling_lawyer, "court": court, "plaintiff": plaintiff,
                     "defendant": defendant, "third_party": third_party, "keyword": keyword,
                     "case_type": case_type, "document_name": document_name, "log_content": log_content},
        )
    conditions = list(await _record_scope_conditions(identity, db))
    data = BusinessRecord.data

    def text(key):
        return func.coalesce(cast(data[key].as_string(), String), "")

    if kind == "unclaimed":
        # 保留原前端的非空真值判定；JSON字符串false不等于布尔false。
        applied = cast(data["commission_applied"], String)
        conditions.extend([
            BusinessRecord.module == "case", BusinessRecord.status != "已合并",
            or_(applied.is_(None), applied.in_(("null", "false", "0", '""'))),
        ])
        number, stage = BusinessRecord.serial_no, BusinessRecord.status
    else:
        # 原入口分别读取这两类记录，各自权限必须同时保留。
        for module in ("finance", "refund"):
            await _require_record_module_menu(module, identity, db, action="查看")
        conditions.extend([
            or_(and_(BusinessRecord.module == "finance", BusinessRecord.status != "已删除"),
                BusinessRecord.module == "refund"),
            func.coalesce(func.nullif(text("fee_type"), ""), BusinessRecord.title).contains("退费"),
        ])
        number = func.coalesce(func.nullif(text("case_no"), ""), BusinessRecord.serial_no)
        stage = func.coalesce(func.nullif(text("case_stage"), ""), BusinessRecord.status)

    if scope != "company":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if user is None:
            raise HTTPException(403, "当前账号不存在，不能确定案件范围")
        if scope == "mine":
            owners = [user.username] + ([user.display_name] if user.display_name else [])
            conditions.append(BusinessRecord.owner.in_(owners))
        else:
            conditions.append(BusinessRecord.department == user.department)

    fields = (
        (number, serial_no), (BusinessRecord.customer, customer), (stage, case_stage),
        (text("court_case_no"), court_case_no), (text("notary_no"), notary_no),
        (text("hearing_lawyer"), hearing_lawyer), (text("assistant"), assistant),
        (text("investigator"), investigator), (text("source_person"), source_person),
        (text("court"), court), (text("payee"), payee), (text("refund_status"), refund_status),
        (text("refund_amount"), refund_amount), (text("fee_type"), fee_type),
    )
    for column, value in fields:
        if value.strip():
            conditions.append(column.icontains(value.strip(), autoescape=True))
    if paid_from or paid_to:
        paid_date = func.substr(func.coalesce(
            func.nullif(text("paid_date"), ""), func.nullif(text("payment_date"), ""),
        ), 1, 10)
        if paid_from:
            conditions.append(paid_date >= paid_from.isoformat())
        if paid_to:
            conditions.append(paid_date <= paid_to.isoformat())

    total = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions)) or 0)
    ordering = [BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()]
    if kind == "refund":
        ordering.insert(0, case((BusinessRecord.module == "finance", 0), else_=1))
    rows = list((await db.scalars(select(BusinessRecord).where(*conditions)
        .order_by(*ordering).offset((page - 1) * page_size).limit(page_size))).all())
    fields = await _allowed_field_keys(identity, db)
    return {
        "items": await _contract_customer_record_dicts(rows, fields, db, identity),
        "total": total, "page": page, "page_size": page_size,
    }
