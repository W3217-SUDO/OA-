"""Static organization API contract checks; intentionally does not mutate main.py or SQLite."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAIN = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
MODELS = (ROOT / "app" / "models.py").read_text(encoding="utf-8")


def test_organization_routes_and_dtos_are_present() -> None:
    for route in (
        '@app.get(f"{settings.api_prefix}/hr/departments")',
        '@app.post(f"{settings.api_prefix}/hr/departments"',
        '@app.patch(f"{settings.api_prefix}/hr/departments/',
        '@app.delete(f"{settings.api_prefix}/hr/departments/',
        '@app.get(f"{settings.api_prefix}/hr/job-roles")',
        '@app.post(f"{settings.api_prefix}/hr/job-roles"',
        '@app.patch(f"{settings.api_prefix}/hr/job-roles/',
        '@app.delete(f"{settings.api_prefix}/hr/job-roles/',
    ):
        assert route in MAIN
    for dto in ("class DepartmentInput", "class DepartmentUpdate", "class JobRoleInput", "class JobRoleUpdate"):
        assert dto in MAIN


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
        assert field in MODELS
        assert field in MAIN
    assert 'return {"items": [_department_dict' in MAIN
    assert 'return {"items": [_job_role_dict' in MAIN


def test_organization_transaction_and_identity_audit_are_explicit() -> None:
    assert 'created_by=identity["username"]' in MAIN
    assert 'updated_by=identity["username"]' in MAIN
    assert "await db.commit(); await db.refresh(item)" in MAIN
    assert "await db.delete(item); await db.commit()" in MAIN
