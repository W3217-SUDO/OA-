from pathlib import Path


SOURCE = (Path(__file__).parent / "app" / "main.py").read_text(encoding="utf-8")


def test_customer_account_update_normalizes_system_role() -> None:
    assert 'effective_role = body.role if account_type == "员工账号" else "user"' in SOURCE
    assert "user.role = effective_role; user.role_ids = [effective_role]" in SOURCE
    assert '"role": effective_role' in SOURCE


def test_orphan_customer_account_can_rebuild_its_login_user() -> None:
    assert 'stored_username = str((employee.data or {}).get("username") or "")' in SOURCE
    assert 'if account_type == "客户账号" and not stored_username' in SOURCE
    assert "password_hash=hash_password(uuid4().hex)" in SOURCE
    assert "employee.owner = username" in SOURCE
