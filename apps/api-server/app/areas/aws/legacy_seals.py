"""用印中心“旧系统用印记录”：只读列出旧系统用印申请（AWS_OfficialDocument，迁移时放在公文发文 official_outgoing），数据不挪。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import BusinessRecord
from app.security import current_identity

router = APIRouter()

LEGACY_SEAL_SOURCE = "AWS_OfficialDocument"


@router.get(f"{settings.api_prefix}/legacy-seal-records")
async def list_legacy_seal_records(
    status: str = "", official_no: str = "", applicant: str = "", customer: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.formatters import _user_display_map
    from app.core.permissions import _permission_payload_for_identity

    menus = set((await _permission_payload_for_identity(identity, db)).get("menu_keys") or [])
    if not any(key == "seal" or key.startswith("seal-") for key in menus):
        raise HTTPException(status_code=403, detail="没有用印中心权限")
    # 能审批或管理用印的人看全部旧记录，其他人只看自己申请的。
    see_all = any(key.startswith(("seal-audit", "seal-admin")) for key in menus) or identity.get("role") == "admin"
    data = BusinessRecord.data
    username = identity["username"]
    conditions = [
        BusinessRecord.module == "official_outgoing",
        data["source_table"].as_string() == LEGACY_SEAL_SOURCE,
    ]
    if not see_all:
        conditions.append(or_(BusinessRecord.owner == username, data["business_owner"].as_string() == username))
    if status.strip():
        conditions.append(BusinessRecord.status == status.strip())
    if official_no.strip():
        conditions.append(BusinessRecord.serial_no.ilike(f"%{official_no.strip()}%"))
    if customer.strip():
        conditions.append(or_(BusinessRecord.customer.ilike(f"%{customer.strip()}%"),
                              data["customer_no"].as_string().ilike(f"%{customer.strip()}%")))
    if applicant.strip():
        conditions.append(or_(BusinessRecord.owner.ilike(f"%{applicant.strip()}%"),
                              data["business_owner"].as_string().ilike(f"%{applicant.strip()}%")))
    total = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions)) or 0)
    records = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(
        BusinessRecord.created_at.desc(), BusinessRecord.id.desc(),
    ).offset((page - 1) * page_size).limit(page_size))).all()
    people = {str(value).strip() for item in records for value in (
        item.owner, (item.data or {}).get("business_owner"), (item.data or {}).get("auditor"),
    ) if str(value or "").strip()}
    users = await _user_display_map(people, db)

    def name(value) -> str:
        token = str(value or "").strip()
        user = users.get(token.lower()) or users.get(token)
        return getattr(user, "display_name", None) or token

    items = []
    for item in records:
        row = item.data or {}
        items.append({
            "id": item.id, "serial_no": item.serial_no, "status": item.status,
            "applicant": name(row.get("business_owner") or item.owner),
            "customer": item.customer or row.get("customer_no") or "",
            "contract_no": row.get("contract_no") or "", "case_no": row.get("case_no") or "",
            "document_name": row.get("official_document_name") or item.title or "",
            "seal_type": row.get("seal_type") or "", "print_quantity": row.get("print_quantity") or "",
            "application_date": str(row.get("application_date") or row.get("create_time") or "")[:19],
            "auditor": name(row.get("auditor")), "audit_time": str(row.get("audit_time") or "")[:19],
            "audit_remark": row.get("audit_remark") or row.get("review_comment") or "",
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}
