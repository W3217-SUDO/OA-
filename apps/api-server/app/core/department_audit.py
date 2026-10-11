"""批量读取部门原始操作者来源，不修改新旧审计数据。"""

from fastapi import HTTPException
from sqlalchemy import column, func, inspect, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, Department, User


_CRM_HR_MIGRATION_SOURCE = "hz_crm_20260930"


async def _department_actor_sources(items: list[Department], db: AsyncSession) -> dict[int, dict[str, dict]]:
    # 部门代码可编辑；正常更新后不再推测旧创建人，保留真实的系统迁移事件。
    migrated = [item for item in items if item.updated_by == "legacy-hr-migration"]
    if not migrated:
        return {}
    if not await db.run_sync(lambda session: inspect(session.bind).has_table("HR_Department")):
        return {}

    codes = {item.code.strip().lower() for item in migrated}
    current_codes = (await db.execute(
        select(Department.id, Department.code).where(func.lower(func.trim(Department.code)).in_(codes))
    )).all()
    code_ids: dict[str, set[int]] = {}
    for department_id, code in current_codes:
        code_ids.setdefault(code.strip().lower(), set()).add(department_id)
    if any(len(ids) != 1 for ids in code_ids.values()):
        raise HTTPException(status_code=409, detail="部门代码存在多重归属，无法读取旧审计来源")

    legacy_department = table(
        "HR_Department", column("DepartmentId"), column("DepartmentCode"),
        column("CreateUser"), column("ChangeUser"),
    )
    legacy_rows = (await db.execute(
        select(legacy_department).where(func.lower(func.trim(legacy_department.c.DepartmentCode)).in_(codes))
    )).mappings().all()
    rows_by_code: dict[str, list] = {}
    for row in legacy_rows:
        rows_by_code.setdefault(str(row["DepartmentCode"] or "").strip().lower(), []).append(row)
    if any(len(rows) != 1 for rows in rows_by_code.values()):
        raise HTTPException(status_code=409, detail="旧部门代码不唯一，无法读取旧审计来源")
    department_sources = {
        item.id: (rows_by_code[item.code.strip().lower()][0], "department_code")
        for item in migrated if item.code.strip().lower() in rows_by_code
    }

    # 唯一旧代码是部门主体证据；员工转部门不改变它，仅未匹配项读取旧主键辅助证据。
    unmatched = [item for item in migrated if item.id not in department_sources]
    if unmatched:
        names = {item.name for item in unmatched}
        user_links = (await db.execute(
            select(User.department, User.profile["legacy_department_id"].as_string())
            .where(
                User.department.in_(names),
                User.profile["migration_source"].as_string() == _CRM_HR_MIGRATION_SOURCE,
            ).distinct()
        )).all()
        hr_links = (await db.execute(
            select(BusinessRecord.department, BusinessRecord.data["legacy_department_id"].as_string())
            .where(
                BusinessRecord.module == "hr", BusinessRecord.department.in_(names),
                BusinessRecord.data["migration_source"].as_string() == _CRM_HR_MIGRATION_SOURCE,
            ).distinct()
        )).all()
        legacy_ids_by_name: dict[str, set[int]] = {}
        for department_name, legacy_id in [*user_links, *hr_links]:
            value = "" if legacy_id is None else str(legacy_id).strip()
            if not value:
                continue
            if not value.isascii() or not value.isdecimal() or int(value) <= 0:
                raise HTTPException(status_code=409, detail="部门已存旧主键无效，无法读取旧审计来源")
            legacy_ids_by_name.setdefault(department_name, set()).add(int(value))
        if any(len(ids) != 1 for ids in legacy_ids_by_name.values()):
            raise HTTPException(status_code=409, detail="未匹配部门的已存旧主键不一致，旧审计来源冲突")
        stored_ids = {legacy_id for ids in legacy_ids_by_name.values() for legacy_id in ids}
        if stored_ids:
            stored_rows = (await db.execute(
                select(legacy_department).where(legacy_department.c.DepartmentId.in_(stored_ids))
            )).mappings().all()
            rows_by_id: dict[int, list] = {}
            for row in stored_rows:
                rows_by_id.setdefault(row["DepartmentId"], []).append(row)
            source_codes = {str(row["DepartmentCode"] or "").strip().lower() for row in stored_rows}
            code_owners = (await db.execute(
                select(Department.id).where(func.lower(func.trim(Department.code)).in_(source_codes))
            )).all()
            if code_owners:
                raise HTTPException(status_code=409, detail="未匹配部门的旧主键已归属其他部门代码，旧审计来源冲突")
            for item in unmatched:
                stored = legacy_ids_by_name.get(item.name, set())
                if not stored:
                    continue
                matches = rows_by_id.get(next(iter(stored)), [])
                if len(matches) != 1:
                    raise HTTPException(status_code=409, detail="部门已存旧主键无唯一旧部门，无法读取旧审计来源")
                department_sources[item.id] = (matches[0], "legacy_department_id")

    source_ids = [row["DepartmentId"] for row, _ in department_sources.values()]
    if len(source_ids) != len(set(source_ids)):
        raise HTTPException(status_code=409, detail="多个部门指向同一旧部门，旧审计来源冲突")
    actors = {
        str(row[source_field] or "").strip().lower()
        for item in migrated if item.id in department_sources
        for field, source_field in (("created_by", "CreateUser"), ("updated_by", "ChangeUser"))
        for row in (department_sources[item.id][0],)
        if getattr(item, field) == "legacy-hr-migration" and str(row[source_field] or "").strip()
    }
    staff_by_actor: dict[str, list] = {}
    if actors and await db.run_sync(lambda session: inspect(session.bind).has_table("HR_Staff")):
        legacy_staff = table("HR_Staff", column("StaffId"), column("StaffName"), column("StaffChName"))
        staff_rows = (await db.execute(
            select(legacy_staff).where(func.lower(func.trim(legacy_staff.c.StaffName)).in_(actors))
        )).mappings().all()
        for row in staff_rows:
            staff_by_actor.setdefault(str(row["StaffName"] or "").strip().lower(), []).append(row)
        if any(len(rows) != 1 for rows in staff_by_actor.values()):
            raise HTTPException(status_code=409, detail="旧部门操作者账号不唯一，无法读取旧审计来源")

    result: dict[int, dict[str, dict]] = {}
    for item in migrated:
        if item.id not in department_sources:
            continue
        row, matched_by = department_sources[item.id]
        for field, source_field in (("created_by", "CreateUser"), ("updated_by", "ChangeUser")):
            if getattr(item, field) != "legacy-hr-migration":
                continue
            actor = str(row[source_field] or "").strip()
            staff = staff_by_actor.get(actor.lower(), [])
            result.setdefault(item.id, {})[field] = {
                "table": "HR_Department", "legacy_department_id": row["DepartmentId"],
                "matched_by": matched_by, "field": source_field, "actor": actor,
                "legacy_staff_id": staff[0]["StaffId"] if staff else None,
                "legacy_staff_name": staff[0]["StaffChName"] if staff else "",
            }
            if matched_by == "legacy_department_id":
                result[item.id][field]["link_migration_source"] = _CRM_HR_MIGRATION_SOURCE
    return result
