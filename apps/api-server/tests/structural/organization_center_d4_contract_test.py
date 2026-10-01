"""Static organization API contract checks; intentionally does not mutate main.py or SQLite."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAIN = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in (
    "app/areas/hr/router.py", "app/api_schemas/organization.py", "app/core/system.py", "app/core/permissions.py",
))
from app.models import Department, JobRole
from app.models_shared import DepartmentInput, DepartmentUpdate, JobRoleInput, JobRoleUpdate

MODEL_FIELDS = set(Department.__table__.columns.keys()) | set(JobRole.__table__.columns.keys())


def test_organization_routes_and_dtos_are_present() -> None:
    for route in (
        '@router.get(f"{settings.api_prefix}/hr/departments")',
        '@router.post(f"{settings.api_prefix}/hr/departments"',
        '@router.patch(f"{settings.api_prefix}/hr/departments/',
        '@router.delete(f"{settings.api_prefix}/hr/departments/',
        '@router.get(f"{settings.api_prefix}/hr/job-roles")',
        '@router.post(f"{settings.api_prefix}/hr/job-roles"',
        '@router.patch(f"{settings.api_prefix}/hr/job-roles/',
        '@router.delete(f"{settings.api_prefix}/hr/job-roles/',
    ):
        assert route in MAIN
    for dto in ("class DepartmentInput", "class DepartmentUpdate", "class JobRoleInput", "class JobRoleUpdate"):
        assert dto in MAIN
    for dto, fields in (
        (DepartmentInput, {"code", "name", "parent_department_id", "manager", "sort_order"}),
        (DepartmentUpdate, {"code", "name", "parent_department_id", "manager", "sort_order"}),
        (JobRoleInput, {"code", "name", "permissions", "data_scope"}),
        (JobRoleUpdate, {"code", "name", "permissions", "data_scope"}),
    ):
        assert fields.issubset(dto.model_fields), dto.__name__
    assert "page: int | None = Query(default=None" in MAIN
    assert "page_size: int | None = Query(default=None" in MAIN
    assert '"page": effective_page' in MAIN
    assert '"page_size": effective_page_size' in MAIN
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/api/v1/hr/departments" in paths
    assert "/api/v1/hr/job-roles" in paths


def test_dynamic_role_permission_tree_matches_legacy_menu_action_shape() -> None:
    assert '/hr/job-roles/{{role_id}}/permissions' in MAIN
    assert 'node_type": "M"' in MAIN
    assert 'node_type": "A"' in MAIN
    assert 'RolePermissionUpdate' in MAIN
    assert 'permissions' in MAIN
    assert '系统管理员角色权限不可修改' in MAIN
    assert '角色权限不存在' in MAIN or '岗位角色不存在' in MAIN


def test_organization_contract_has_admin_guard_and_error_paths() -> None:
    assert "_require_admin(identity); code, name = body.code.strip().upper(), body.name.strip()" in MAIN
    assert "Department.code == code, Department.name == name" in MAIN
    assert "JobRole.code == code, JobRole.name == name" in MAIN
    assert "child_count" in MAIN
    assert "BusinessRecord.module == \"hr\"" in MAIN
    assert 'item.code == "SYSTEM-ADMIN"' in MAIN
    assert "status_code=409" in MAIN
    assert "status_code=422" in MAIN


def test_organization_response_and_audit_fields_match_models() -> None:
    for field in (
        "parent_department_id",
        "manager",
        "overdue_deduction",
        "sort_order",
        "is_active",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    ):
        assert field in MODEL_FIELDS
        assert field in MAIN
    assert '_department_dict(item' in MAIN
    assert '_job_role_dict(item' in MAIN
    for field in ("manager_display_name", "created_by_display_name", "updated_by_display_name"):
        assert field in MAIN


def test_organization_transaction_and_identity_audit_are_explicit() -> None:
    assert 'created_by=identity["username"]' in MAIN
    assert 'updated_by=identity["username"]' in MAIN
    assert "await db.commit(); await db.refresh(item)" in MAIN
    assert "await db.delete(item); await db.commit()" in MAIN
    assert "_record_organization_audit" in MAIN
    assert "record_id=audit.id" in MAIN
