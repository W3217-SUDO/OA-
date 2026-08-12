from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .legacy_models import HrRole, HrRolePermission, HrStaff, IprUser, IprUserRole, SysMenu

settings = get_settings()
app = FastAPI(title="Sunhold Legacy Parity API", version="0.1.0")


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
