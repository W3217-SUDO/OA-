"""Local-only regression for case tasks and customer portal demands.

Run with CODEX_TASK_TEST_ADMIN_PASSWORD set in the process environment.  The
fixture is inserted into the local SQLite database and is removed in finally;
no password is written to the repository or output.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from time import strftime


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "apps" / "api-server" / "legal_platform.db"
API_BASE = os.environ.get("CODEX_TASK_API_BASE", "http://127.0.0.1:8000/api/v1").rstrip("/")
ADMIN_PASSWORD = os.environ.get("CODEX_TASK_TEST_ADMIN_PASSWORD", "")


class ApiError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:500]}")
        self.status = status
        self.body = body


def request(path: str, *, method: str = "GET", payload: object | None = None, token: str = "") -> tuple[int, object]:
    body = None
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{API_BASE}{path}", data=body, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as exc:
        raise ApiError(exc.code, exc.read().decode("utf-8", errors="replace")) from exc
    raw = response.read().decode("utf-8", errors="replace")
    try:
        return response.status, json.loads(raw)
    except json.JSONDecodeError:
        return response.status, raw


def expect_error(path: str, expected: set[int], *, method: str = "POST", payload: object | None = None, token: str = "") -> int:
    try:
        request(path, method=method, payload=payload, token=token)
    except ApiError as exc:
        if exc.status not in expected:
            raise AssertionError(f"{path} expected {expected}, got {exc.status}: {exc.body}") from exc
        return exc.status
    raise AssertionError(f"{path} unexpectedly succeeded")


def insert_fixture(conn: sqlite3.Connection, marker: str) -> dict[str, int | str]:
    from app.security import hash_password  # type: ignore[import-not-found]

    now = "2026-08-01T00:00:00"
    customer_serial = f"{marker}-CUSTOMER"
    contract_serial = f"{marker}-CONTRACT"
    case_serial = f"{marker}-CASE"
    account = f"{marker.lower()}-portal"
    portal_password = f"{marker}-Portal!"
    portal = {
        "account": account,
        "enabled": True,
        "activated_at": now,
        "password_hash": hash_password(portal_password),
        "activation_code_hash": "",
    }
    contract_data = {
        "type": "争议解决合同",
        "fee_type": "固定收费",
        "source_person": "admin",
        "external_contract_no": f"{marker}-EXT",
    }
    case_data = {
        "contract_id": 0,
        "contract_no": contract_serial,
        "contract_title": f"{marker}-CONTRACT-TITLE",
        "case_type": "民事案件",
        "client_position": "原告",
        "cause_or_charge": "侵害商标权纠纷",
        "source_person": marker,
        "handling_lawyers": ["admin"],
        "handling_lawyer_usernames": ["admin"],
        "case_creation_step": "completed",
        "case_creation_approval_status": "已通过",
        "business_stage": "立案",
    }
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO business_records(module,serial_no,title,customer,status,owner,department,description,data,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("customer", customer_serial, f"{marker}-CUSTOMER-TITLE", f"{marker}-CUSTOMER-TITLE", "目标", "admin", "诉讼一部", "", json.dumps({"portal_access": portal}, ensure_ascii=False), now, now),
    )
    customer_id = cur.lastrowid
    cur.execute(
        "INSERT INTO business_records(module,serial_no,title,customer,status,owner,department,description,data,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("contract", contract_serial, f"{marker}-CONTRACT-TITLE", f"{marker}-CUSTOMER-TITLE", "已通过", "admin", "诉讼一部", "", json.dumps(contract_data, ensure_ascii=False), now, now),
    )
    contract_id = cur.lastrowid
    case_data["contract_id"] = contract_id
    cur.execute(
        "INSERT INTO business_records(module,serial_no,title,customer,status,owner,department,description,data,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("case", case_serial, f"{marker}-CASE-TITLE", f"{marker}-CUSTOMER-TITLE", "新案待分配", "admin", "诉讼一部", "", json.dumps(case_data, ensure_ascii=False), now, now),
    )
    case_id = cur.lastrowid
    conn.commit()
    return {"customer_id": customer_id, "contract_id": contract_id, "case_id": case_id, "case_no": case_serial, "account": account, "portal_password": portal_password}


def cleanup(conn: sqlite3.Connection, ids: set[int], marker: str) -> None:
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in ids)
    values = tuple(sorted(ids))
    cur.execute(f"DELETE FROM file_attachments WHERE record_id IN ({placeholders})", values)
    cur.execute(f"DELETE FROM notifications WHERE source_id IN ({placeholders})", values)
    cur.execute(f"DELETE FROM workflow_events WHERE record_id IN ({placeholders})", values)
    cur.execute(f"DELETE FROM business_records WHERE id IN ({placeholders})", values)
    # Guard against an unexpected fixture row surviving with the marker.
    cur.execute("DELETE FROM file_attachments WHERE original_name LIKE ?", (f"{marker}%",))
    cur.execute("DELETE FROM notifications WHERE title LIKE ? OR content LIKE ?", (f"{marker}%", f"%{marker}%"))
    cur.execute("DELETE FROM workflow_events WHERE comment LIKE ?", (f"%{marker}%",))
    cur.execute("DELETE FROM business_records WHERE serial_no LIKE ? OR title LIKE ?", (f"{marker}%", f"{marker}%"))
    conn.commit()


def main() -> None:
    if not ADMIN_PASSWORD:
        raise SystemExit("Set CODEX_TASK_TEST_ADMIN_PASSWORD in the process environment")
    sys.path.insert(0, str(ROOT / "apps" / "api-server"))
    marker = f"CODEX-CASE-TASK-B-AUTO-{strftime('%Y%m%d%H%M%S')}"
    conn = sqlite3.connect(DB_PATH)
    fixture: dict[str, int | str] = {}
    created_task_ids: set[int] = set()
    try:
        fixture = insert_fixture(conn, marker)
        # OAuth2PasswordRequestForm is form encoded rather than JSON.
        form = urllib.parse.urlencode({"username": "admin", "password": ADMIN_PASSWORD}).encode()
        login_req = urllib.request.Request(f"{API_BASE}/auth/login", data=form, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        login_res = urllib.request.urlopen(login_req, timeout=20)
        token = json.loads(login_res.read().decode())["access_token"]
        case_id = int(fixture["case_id"])
        case_no = str(fixture["case_no"])
        task_payload = {"title": f"{marker}-CASE-TASK", "owner": "admin", "deadline": str(date.today() + timedelta(days=7)), "priority": "普通", "source": "案件任务", "case_no": case_no, "description": "API regression"}
        assert expect_error("/tasks", {422}, payload={**task_payload, "case_no": ""}, token=token) == 422
        assert expect_error("/tasks", {422}, payload={**task_payload, "owner": "missing-user"}, token=token) == 422
        assert expect_error("/tasks", {422}, payload={**task_payload, "deadline": str(date.today() + timedelta(days=31))}, token=token) == 422
        status, created = request("/tasks", method="POST", payload=task_payload, token=token)
        assert status == 201 and created["source"] == "案件任务"
        created_task_ids.add(int(created["id"]))
        task_id = int(created["id"])
        status, edited = request("/tasks/batch-update", method="POST", payload={"task_ids": [task_id], "owner": "admin", "deadline": str(date.today() + timedelta(days=8)), "priority": "重要", "comment": "fixture edit"}, token=token)
        assert status == 200 and edited["updated"] == 1
        for action, expected in (("accept", "处理中"), ("complete", "已完成"), ("confirm", "已验收")):
            status, result = request(f"/tasks/{task_id}/{action}", method="POST", payload={"comment": f"{marker}-{action}"}, token=token)
            assert status == 200 and result["status"] == expected
        assert expect_error(f"/tasks/{task_id}/accept", {409}, payload={"comment": "illegal"}, token=token) == 409
        assert expect_error(f"/tasks/{task_id}/complete", {409}, payload={"comment": "illegal"}, token=token) == 409
        portal_payload = {"account": fixture["account"], "password": fixture["portal_password"]}
        assert expect_error("/customer-portal/overview", {401}, method="POST", payload={"account": fixture["account"], "password": "wrong-password"}) == 401
        status, overview = request("/customer-portal/overview", method="POST", payload=portal_payload)
        assert status == 200 and overview["customer"]["id"] == fixture["customer_id"]
        demand = {**portal_payload, "title": f"{marker}-CUSTOMER-TASK", "content": "Customer portal demand", "case_no": case_no}
        status, customer_task = request("/customer-portal/demands", method="POST", payload=demand)
        assert status == 201
        created_task_ids.add(int(customer_task["id"]))
        status, case_tasks = request(f"/cases/{case_id}/tasks", token=token)
        assert status == 200
        sources = {item["source"] for item in case_tasks["items"] if item["id"] in created_task_ids}
        assert sources == {"案件任务", "客户任务"}
        for task_id in created_task_ids:
            assert request(f"/tasks/{task_id}/history", token=token)[0] == 200
            assert request("/attachments", token=token)[0] == 200
        print(f"PASS marker={marker} case_id={case_id} task_ids={sorted(created_task_ids)}")
    finally:
        ids = {int(value) for key, value in fixture.items() if key.endswith("_id") and isinstance(value, int)} | created_task_ids
        cleanup(conn, ids, marker)
        leftovers = conn.execute("SELECT COUNT(*) FROM business_records WHERE serial_no LIKE ? OR title LIKE ?", (f"{marker}%", f"{marker}%")).fetchone()[0]
        if leftovers:
            raise AssertionError(f"fixture residue: {leftovers}")
        conn.close()


if __name__ == "__main__":
    main()
