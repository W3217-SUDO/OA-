"""合同审批与用印审批路径（BUG20261031002 第④⑤步）。

人事中心“用印审批设置”保存在 system_configs（key=seal_approval_settings），不加表不加列：
- firm_approver：所里审批人（一人）；
- stamp_users：行政用印人，设了以后只有他们能在“待用印”里盖章，没设时仍按用印岗位权限；
- department_paths：{部门 id: [第一步换人, 第二步换人]}，空串表示不换人。
每个部门默认两步：本部门负责人 → 所里审批人。没设负责人的第一步跳过，提交人自己是第一步审批人的也跳过。
"""

from __future__ import annotations

import hashlib
import weakref
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, Department, FileAttachment, SystemConfig, User

SEAL_APPROVAL_CONFIG_KEY = "seal_approval_settings"
FIRM_APPROVER_MISSING = "请先在人事中心“用印审批设置”里设置所里审批人"


def _clean(value) -> str:
    return str(value or "").strip()


def normalize_settings(value: dict | None) -> dict:
    value = value if isinstance(value, dict) else {}
    paths: dict[str, list[str]] = {}
    for key, steps in (value.get("department_paths") or {}).items():
        if not str(key).isdigit() or not isinstance(steps, list):
            continue
        cleaned = [_clean(item) for item in steps[:2]] + [""] * (2 - len(steps[:2]))
        if any(cleaned):
            paths[str(int(key))] = cleaned
    return {
        "firm_approver": _clean(value.get("firm_approver")),
        "stamp_users": list(dict.fromkeys(_clean(item) for item in (value.get("stamp_users") or []) if _clean(item))),
        "department_paths": paths,
    }


_CONFIG_TABLE_PRESENT: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


async def _config_table_present(db: AsyncSession) -> bool:
    """用印权限判断每次都会读设置；只建了部分表的库（单元测试夹具）没有 system_configs 时按未设置处理。按引擎只查一次。"""
    engine = db.bind.engine if hasattr(db.bind, "engine") else db.bind
    if engine not in _CONFIG_TABLE_PRESENT:
        _CONFIG_TABLE_PRESENT[engine] = await db.run_sync(lambda sync: inspect(sync.connection()).has_table(SystemConfig.__tablename__))
    return _CONFIG_TABLE_PRESENT[engine]


async def load_seal_approval_settings(db: AsyncSession) -> dict:
    if not await _config_table_present(db):
        return normalize_settings(None)
    row = await db.scalar(select(SystemConfig).where(SystemConfig.key == SEAL_APPROVAL_CONFIG_KEY))
    return normalize_settings(row.value if row else None)


async def save_seal_approval_settings(value: dict, username: str, db: AsyncSession) -> dict:
    settings = normalize_settings(value)
    people = {settings["firm_approver"], *settings["stamp_users"], *(item for steps in settings["department_paths"].values() for item in steps)} - {""}
    if people:
        active = set((await db.scalars(select(User.username).where(User.username.in_(people), User.is_active.is_(True)))).all())
        missing = sorted(people - active)
        if missing:
            raise HTTPException(status_code=422, detail=f"人员不存在或已停用：{'、'.join(missing)}")
    if settings["department_paths"]:
        ids = [int(key) for key in settings["department_paths"]]
        known = {str(item) for item in (await db.scalars(select(Department.id).where(Department.id.in_(ids)))).all()}
        settings["department_paths"] = {key: steps for key, steps in settings["department_paths"].items() if key in known}
    row = await db.scalar(select(SystemConfig).where(SystemConfig.key == SEAL_APPROVAL_CONFIG_KEY))
    if row:
        row.value = settings
        row.updated_by = username
    else:
        db.add(SystemConfig(key=SEAL_APPROVAL_CONFIG_KEY, label="用印审批设置", group="人事中心", value=settings,
                            description="所里审批人、行政用印人和各部门合同/用印审批路径", updated_by=username))
    return settings


async def _active_username(value: str, db: AsyncSession) -> str:
    value = _clean(value)
    if not value:
        return ""
    found = await db.scalar(select(User.username).where(User.username == value, User.is_active.is_(True)))
    return found or ""


async def approval_path_preview(department_name: str, submitter: str, db: AsyncSession) -> dict:
    """返回部门默认/换人后的两步，以及按提交人实际要走的审批人顺序；所里审批人没设时 path 为空、带 error。"""
    settings = await load_seal_approval_settings(db)
    department = await db.scalar(select(Department).where(Department.name == _clean(department_name))) if _clean(department_name) else None
    override = settings["department_paths"].get(str(department.id), ["", ""]) if department else ["", ""]
    first = await _active_username(override[0] or (department.manager if department else ""), db)
    second = await _active_username(override[1] or settings["firm_approver"], db)
    path: list[str] = []
    if first and first != _clean(submitter):
        path.append(first)
    error = "" if second else FIRM_APPROVER_MISSING
    if second and second not in path:
        path.append(second)
    return {"department": department.name if department else _clean(department_name), "steps": [first, second], "path": path if second else [], "error": error}


async def resolve_approval_path(department_name: str, submitter: str, db: AsyncSession) -> list[str]:
    preview = await approval_path_preview(department_name, submitter, db)
    if preview["error"]:
        raise HTTPException(status_code=422, detail=preview["error"])
    return preview["path"]


async def is_configured_stamp_user(username: str, db: AsyncSession) -> bool | None:
    """设了行政用印人时返回是否在名单里；没设返回 None，按原用印岗位权限。"""
    stamp_users = (await load_seal_approval_settings(db))["stamp_users"]
    if not stamp_users:
        return None
    return _clean(username) in stamp_users


async def contract_attachment_fingerprint(contract_id: int, db: AsyncSession) -> str:
    rows = (await db.execute(select(FileAttachment.id, FileAttachment.size).where(
        FileAttachment.record_id == contract_id, FileAttachment.category == "合同附件",
    ).order_by(FileAttachment.id))).all()
    return hashlib.sha256(";".join(f"{row[0]}:{row[1]}" for row in rows).encode()).hexdigest()


async def contract_unchanged_since_approval(contract: BusinessRecord, db: AsyncSession) -> bool:
    """审批通过后合同内容和附件都没改过：内容一改就会重新审批（合同变更），这里只需核对合同附件。"""
    approved = _clean((contract.data or {}).get("approved_attachment_fingerprint"))
    if approved:
        return approved == await contract_attachment_fingerprint(contract.id, db)
    approved_at = _clean((contract.data or {}).get("approved_at"))
    if not approved_at:
        return False
    try:
        cutoff = datetime.fromisoformat(approved_at)
    except ValueError:
        return False
    created = (await db.scalars(select(FileAttachment.created_at).where(
        FileAttachment.record_id == contract.id, FileAttachment.category == "合同附件",
    ))).all()
    return all(item is None or item.replace(tzinfo=None) <= cutoff.replace(tzinfo=None) for item in created)


def start_seal_steps(data: dict, path: list[str]) -> dict:
    return {**data, "approval_steps": [{"approver": item, "status": "待审批" if index == 0 else "等待中"} for index, item in enumerate(path)],
            "approval_step_index": 0, "approver": path[0]}


def current_seal_step_approver(data: dict) -> str:
    steps = data.get("approval_steps") if isinstance(data.get("approval_steps"), list) else []
    index = int(data.get("approval_step_index") or 0)
    return _clean(steps[index].get("approver")) if 0 <= index < len(steps) and isinstance(steps[index], dict) else ""


async def record_department(record: BusinessRecord, db: AsyncSession) -> str:
    """合同/用印按所属部门走路径；没填部门的按负责人（申请人）所在部门。"""
    if _clean(record.department):
        return _clean(record.department)
    return _clean(await db.scalar(select(User.department).where(User.username == record.owner))) if record.owner else ""
