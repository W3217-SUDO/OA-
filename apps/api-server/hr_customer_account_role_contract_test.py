from pathlib import Path


SOURCE = (Path(__file__).parent / "app" / "main.py").read_text(encoding="utf-8")


def test_customer_account_update_normalizes_system_role() -> None:
    assert 'effective_role = body.role if account_type == "员工账号" else "user"' in SOURCE
    assert "user.role = effective_role; user.role_ids = [effective_role]" in SOURCE
    assert '"role": effective_role' in SOURCE
