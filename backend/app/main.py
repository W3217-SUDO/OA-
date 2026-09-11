from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .legacy_models import AwsOfficialDocument, HrRole, HrRolePermission, HrStaff, IprUser, IprUserRole, SysMenu
from .api.agent import router as agent_router

settings = get_settings()
app = FastAPI(title="Sunhold Legacy Parity API", version="0.1.0")
app.include_router(agent_router)

OFFICIAL_DOCUMENT_STATUS_NAMES = {
    10: "待审核",
    20: "已审待用印",
    30: "审核拒绝",
    40: "已撤回",
    60: "已用印",
}
OFFICIAL_DOCUMENT_TYPE_NAMES = {10: "合同用印", 20: "案件用印", 30: "行政用印"}
SEAL_TYPE_NAMES = {1: "合同章", 2: "公章", 4: "所函专用章", 8: "法人章", 16: "发票章", 32: "财务专用章", 64: "财务三排章"}


def _legacy_official_document(row: AwsOfficialDocument) -> dict[str, object]:
    return {
        "OfficialDocumentId": row.official_document_id,
        "OfficialDocumentNo": row.official_document_no,
        "OfficialDocumentGuid": row.official_document_guid,
        "CaseNo": row.case_no,
        "ContractNo": row.contract_no,
        "CustomerNo": row.customer_no,
        "CustomerName": None,
        "OfficialDocumentName": row.official_document_name,
        "BusinessOwner": row.business_owner,
        "BusinessOwnerName": row.business_owner,
        "OfficialDocumentType": row.official_document_type,
        "OfficialDocumentTypeName": OFFICIAL_DOCUMENT_TYPE_NAMES.get(row.official_document_type, ""),
        "SealType": row.seal_type,
        "SealTypeName": "、".join(name for value, name in SEAL_TYPE_NAMES.items() if (row.seal_type or 0) & value),
        "OfficialDocumentStatus": row.official_document_status,
        "OfficialDocumentStatusName": OFFICIAL_DOCUMENT_STATUS_NAMES.get(row.official_document_status, ""),
        "ApplicationDate": row.application_date,
        "Auditor": row.auditor,
        "AuditorName": row.auditor,
        "AuditTime": row.audit_time,
        "AuditRemark": row.audit_remark,
    }


@app.get(f"{settings.api_prefix}/legacy/official-documents")
def official_documents(
    page_no: int = Query(default=1, ge=1),
    page_size: int = Query(default=15, ge=1, le=100),
    official_document_no: str | None = None,
    business_owner: str | None = None,
    case_no: str | None = None,
    contract_no: str | None = None,
    customer_name: str | None = None,
    official_document_status: int | None = None,
    official_document_type: int | None = None,
    file_name: str | None = None,
    application_begin_date: datetime | None = None,
    application_end_date: datetime | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Read the legacy official-document list without changing the old database."""
    query = select(AwsOfficialDocument).where(AwsOfficialDocument.is_actived == "T")
    if official_document_no:
        query = query.where(AwsOfficialDocument.official_document_no.contains(official_document_no))
    if business_owner:
        query = query.where(AwsOfficialDocument.business_owner.contains(business_owner))
    if case_no:
        query = query.where(AwsOfficialDocument.case_no.contains(case_no))
    if contract_no:
        query = query.where(AwsOfficialDocument.contract_no.contains(contract_no))
    if official_document_status is not None:
        query = query.where(AwsOfficialDocument.official_document_status == official_document_status)
    if official_document_type is not None:
        query = query.where(AwsOfficialDocument.official_document_type == official_document_type)
    if application_begin_date:
        query = query.where(AwsOfficialDocument.application_date >= application_begin_date)
    if application_end_date:
        query = query.where(AwsOfficialDocument.application_date <= application_end_date)
    # Customer and file filters depend on legacy soft relationships; retain the
    # parameters for route parity until their source tables are mapped.
    _ = customer_name, file_name
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(AwsOfficialDocument.application_date.desc(), AwsOfficialDocument.official_document_id.desc()).offset((page_no - 1) * page_size).limit(page_size)).all()
    return {"IsSuccess": True, "Data": {"OfficialDocuments": [{"Basic": _legacy_official_document(row), "OfficialDocumentFileList": []} for row in rows], "TotalItemCount": total, "PageNo": page_no, "PageSize": page_size}}


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "legacy_read_only": settings.legacy_read_only}


@app.get(f"{settings.api_prefix}/legacy/authorization/summary")
def authorization_summary(db: Session = Depends(get_db)) -> dict[str, int]:
    return {
        "menus": db.scalar(select(func.count()).select_from(SysMenu)) or 0,
        "roles": db.scalar(select(func.count()).select_from(HrRole)) or 0,
        "role_permissions": db.scalar(select(func.count()).select_from(HrRolePermission)) or 0,
        "staff": db.scalar(select(func.count()).select_from(HrStaff)) or 0,
        "users": db.scalar(select(func.count()).select_from(IprUser)) or 0,
        "user_roles": db.scalar(select(func.count()).select_from(IprUserRole)) or 0,
    }


@app.get(f"{settings.api_prefix}/legacy/authorization/menus")
def legacy_menus(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = db.scalars(select(SysMenu).order_by(SysMenu.parent_menu_id, SysMenu.order_id, SysMenu.menu_id)).all()
    return [
        {
            "MenuId": row.menu_id,
            "MenuCode": row.menu_code,
            "MenuName": row.menu_name,
            "ParentMenuId": row.parent_menu_id,
            "OrderId": row.order_id,
            "ImageUrl": row.image_url,
            "LinkUrl": row.link_url,
            "MenuTypeId": row.menu_type_id,
            "IsActived": row.is_actived,
        }
        for row in rows
    ]


@app.get(f"{settings.api_prefix}/legacy/authorization/staff/{{staff_id}}/menu-tree")
def legacy_staff_menu_tree(staff_id: int, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    """Reproduce legacy MenuService permission lookup for one HR_Staff record."""
    staff = db.get(HrStaff, staff_id)
    if staff is None:
        raise HTTPException(status_code=404, detail="Legacy staff record not found")
    rows = db.scalars(select(SysMenu).where(SysMenu.is_actived == "T").order_by(
        SysMenu.order_id, SysMenu.menu_id
    )).all()
    authorized_codes = {
        str(code)
        for code in db.scalars(select(HrRolePermission.resource_code).where(
            HrRolePermission.role_id == staff.role_id,
            HrRolePermission.resource_type == "M",
        ))
    }
    all_by_code = {str(row.menu_code): row for row in rows}
    included_codes = set(authorized_codes)
    for code in tuple(authorized_codes):
        current = all_by_code.get(code)
        while current is not None and str(current.parent_menu_id) != "-1":
            parent_code = str(current.parent_menu_id)
            included_codes.add(parent_code)
            current = all_by_code.get(parent_code)
    rows = [row for row in rows if str(row.menu_code) in included_codes]
    nodes = {
        str(row.menu_code): {
            "MenuId": row.menu_id,
            "MenuCode": row.menu_code,
            "MenuName": row.menu_name,
            "ParentMenuId": row.parent_menu_id,
            "OrderId": row.order_id,
            "ImageUrl": row.image_url,
            "LinkUrl": row.link_url,
            "MenuTypeId": row.menu_type_id,
            "IsActived": row.is_actived,
            "Children": [],
        }
        for row in rows
    }
    roots: list[dict[str, object]] = []
    for node in nodes.values():
        parent = nodes.get(str(node["ParentMenuId"]))
        if str(node["ParentMenuId"]) == "-1":
            roots.append(node)
        elif parent is not None:
            parent["Children"].append(node)
    return roots


@app.get(f"{settings.api_prefix}/legacy/authorization/menu-tree")
def legacy_menu_tree(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    """Compatibility route for the first captured legacy administrator sample."""
    return legacy_staff_menu_tree(1, db)


@app.get(f"{settings.api_prefix}/legacy/authorization/staff/{{staff_id}}")
def legacy_staff(staff_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    staff = db.get(HrStaff, staff_id)
    if staff is None:
        raise HTTPException(status_code=404, detail="Legacy staff record not found")
    return {
        "StaffId": staff.staff_id,
        "StaffNo": staff.staff_no,
        "StaffName": staff.staff_name,
        "StaffChName": staff.staff_ch_name,
        "DepartmentId": staff.department_id,
        "OrgId": staff.org_id,
        "ManagerId": staff.manager_id,
        "RoleId": staff.role_id,
        "IsActived": staff.is_actived,
        "Status": staff.status,
        "IsAdmin": staff.is_admin,
        "IsManager": staff.is_manager,
        "OpenId": staff.open_id,
    }
