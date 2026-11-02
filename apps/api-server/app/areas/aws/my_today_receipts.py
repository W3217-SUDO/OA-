"""今日收文（501147，tgn 11-02 22:27）：只列与本人有关案件今天的官方收文，不看全公司。

“与本人有关”= 本人是案件负责人、经办律师、开庭律师或律师助理；管理员也只看自己的案件，不因管理员身份放宽。
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_identity, get_db, settings
from app.models import BusinessRecord

router = APIRouter()


def _values(value) -> set[str]:
    items = value if isinstance(value, list) else [value]
    return {str(item or "").strip().lower() for item in items if str(item or "").strip()}


def case_team_usernames(case: BusinessRecord) -> set[str]:
    data = case.data or {}
    names = _values(case.owner)
    for key in ("handling_lawyer_usernames", "assistant_username", "assistant_usernames", "case_team_usernames",
                "hearing_lawyer", "hearing_lawyers", "hearing_lawyer_usernames"):
        names |= _values(data.get(key))
    return names


def _receipt_day(data: dict) -> str:
    return str(data.get("uploaded_at") or data.get("received_at") or "")[:10]


@router.get(f"{settings.api_prefix}/documents/receipts/today-mine")
async def list_my_today_receipts(
    day: date | None = Query(None, description="日期 YYYY-MM-DD，默认今天"),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """今日收文：与我有关的案件（我是负责人、经办律师、开庭律师或律师助理）今天收到的法院文书，不含全公司其他案件。"""
    target = (day or date.today()).isoformat()
    username = str(identity.get("username") or "").strip().lower()
    receipts = [record for record in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "document",
        BusinessRecord.data["direction"].as_string() == "收文",
    ))).all() if _receipt_day(record.data or {}) == target]
    case_ids = {int(value) for record in receipts
                for value in [(record.data or {}).get("case_id"), *((record.data or {}).get("case_ids") or [])]
                if str(value or "").isdigit()}
    cases = {case.id: case for case in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(sorted(case_ids)), BusinessRecord.module == "case",
    ))).all()} if case_ids else {}
    mine = {case_id for case_id, case in cases.items() if username and username in case_team_usernames(case)}
    items = []
    for record in receipts:
        data = record.data or {}
        linked = [int(value) for value in [data.get("case_id"), *(data.get("case_ids") or [])] if str(value or "").isdigit()]
        case_id = next((value for value in linked if value in mine), None)
        if case_id is None:
            continue
        case = cases[case_id]
        items.append({
            "id": record.id, "serial_no": record.serial_no, "title": record.title, "document_type": record.description or "",
            "case_id": case.id, "case_no": case.serial_no, "case_title": case.title, "court_no": data.get("court_no") or "",
            "received_at": data.get("received_at") or "", "uploaded_at": data.get("uploaded_at") or "", "status": record.status,
        })
    items.sort(key=lambda item: (item["case_no"], item["serial_no"]))
    return {"date": target, "total": len(items), "items": items}
