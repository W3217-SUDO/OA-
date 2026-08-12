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
