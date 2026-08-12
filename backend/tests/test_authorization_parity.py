import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[2]
BASELINE = json.loads((ROOT / "artifacts" / "authorization-summary.json").read_text(encoding="utf-8-sig"))


def test_legacy_authorization_counts_match_exported_baseline() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/legacy/authorization/summary")
    assert response.status_code == 200
    assert response.json() == {
        "menus": BASELINE["menus"],
        "roles": BASELINE["roles"],
        "role_permissions": BASELINE["role_permissions"],
        "staff": BASELINE["staff"],
        "users": BASELINE["users"],
        "user_roles": BASELINE["user_roles"],
    }


def test_menu_api_preserves_legacy_column_names_and_count() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/legacy/authorization/menus")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == BASELINE["menus"]
    assert {"MenuId", "MenuCode", "MenuName", "ParentMenuId", "LinkUrl", "IsActived"} <= set(rows[0])


def test_parity_capture_api_is_read_only() -> None:
    client = TestClient(app)
    assert client.get("/health").json()["legacy_read_only"] is True
