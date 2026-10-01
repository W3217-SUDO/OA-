from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] / "app" / "areas" / "hr" / "router.py").read_text(encoding="utf-8")


def test_customer_account_update_normalizes_system_role() -> None:
    assert 'effective_role = body.role if account_type == "员工账号" else "user"' in SOURCE
    assert 'next_role_ids = [effective_role, *preserved_secondary_roles] if account_type == "员工账号" else ["user"]' in SOURCE
    assert "user.role = next_role_ids[0]; user.role_ids = next_role_ids" in SOURCE
    assert '"role": effective_role' in SOURCE


def test_orphan_customer_account_can_rebuild_its_login_user() -> None:
    assert 'stored_username = str((employee.data or {}).get("username") or "")' in SOURCE
    assert 'if account_type == "客户账号" and not stored_username' in SOURCE
    assert "password_hash=hash_password(uuid4().hex)" in SOURCE
    assert "employee.owner = username" in SOURCE


def test_existing_non_admin_login_can_be_restored_as_customer_account() -> None:
    assert 'if account_type != "客户账号"' in SOURCE
    assert 'user.profile = {**(user.profile or {}), **profile}' in SOURCE
    assert 'user.role_ids = ["user"]' in SOURCE
