"""Ordinary-case litigant maintenance API contract."""
import json
import os
import pathlib
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import unittest
import uuid

BASE = os.getenv("CASE_TEST_BASE", "http://127.0.0.1:8000/api/v1")
DB = pathlib.Path(__file__).with_name("legal_platform.db")


def request(method, path, token="", payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def login(username, password):
    body = urllib.parse.urlencode({"username": username, "password": password}).encode()
    req = urllib.request.Request(BASE + "/auth/login", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())["access_token"]


class CaseLitigantsApiTest(unittest.TestCase):
    def test_ordinary_case_save_event_and_archived_409(self):
        password = os.environ.get("CASE_TEST_PASSWORD")
        if not password:
            self.skipTest("CASE_TEST_PASSWORD is not set; external integration test skipped")
        admin_token = login("admin", password)
        prefix = f"CODEX-CASE-C-LITIGANTS-{uuid.uuid4().hex[:8]}"
        case_id = user_id = None
        conn = sqlite3.connect(DB)
        try:
            username = f"codex-case-c-litigants-{uuid.uuid4().hex[:8]}-user"
            initial_password = "Codex-Case-User-123!"
            status, body = request("POST", "/system/users", admin_token, {"username": username, "display_name": username, "department": "上海分所", "password": initial_password, "role": "user"})
            self.assertEqual(status, 201, body.decode(errors="replace"))
            user_id = json.loads(body)["id"]
            first_token = login(username, initial_password)
            changed_password = "Codex-Case-User-Changed123!"
            status, body = request("PATCH", "/auth/me", first_token, {"current_password": initial_password, "new_password": changed_password})
            self.assertEqual(status, 200, body.decode(errors="replace"))
            user_token = login(username, changed_password)

            data = {"case_type": "民事案件", "case_creation_step": "completed", "plaintiffs": ["旧原告"], "defendants": ["旧被告"], "case_team_usernames": [username]}
            conn.execute("INSERT INTO business_records(module,serial_no,title,customer,status,owner,department,description,data) VALUES(?,?,?,?,?,?,?,?,?)", ("case", f"{prefix}-CASE", f"{prefix} 普通案件", f"{prefix} 客户", "在办", "admin", "上海分所", "", json.dumps(data, ensure_ascii=False)))
            case_id = conn.execute("SELECT id FROM business_records WHERE serial_no = ?", (f"{prefix}-CASE",)).fetchone()[0]
            conn.commit()
            payload = {"plaintiffs": [f"{prefix} 原告"], "plaintiff_agents": ["代理人甲"], "defendants": [f"{prefix} 被告"], "defendant_agents": [], "third_parties": [], "third_party_agents": [], "comment": prefix}

            status, body = request("PUT", f"/cases/{case_id}/litigants", admin_token, payload)
            self.assertEqual(status, 200, body.decode(errors="replace"))
            self.assertEqual(json.loads(body)["data"]["plaintiffs"], payload["plaintiffs"])
            event = conn.execute("SELECT comment FROM workflow_events WHERE record_id = ? ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
            self.assertIsNotNone(event); self.assertIn(prefix, event[0])

            status, body = request("PUT", "/cases/999999999/litigants", admin_token, payload)
            self.assertEqual(status, 404, body.decode(errors="replace"))
            status, body = request("PUT", f"/cases/{case_id}/litigants", user_token, payload)
            self.assertEqual(status, 403, body.decode(errors="replace"))

            conn.execute("UPDATE business_records SET status = ? WHERE id = ?", ("已归档", case_id)); conn.commit()
            status, body = request("PUT", f"/cases/{case_id}/litigants", admin_token, payload)
            self.assertEqual(status, 409, body.decode(errors="replace"))
            self.assertIn("归档", json.loads(body).get("detail", ""))
        finally:
            if case_id:
                conn.execute("DELETE FROM workflow_events WHERE record_id = ?", (case_id,))
                conn.execute("DELETE FROM business_records WHERE id = ?", (case_id,))
            conn.commit(); conn.close()
            if user_id:
                request("DELETE", f"/system/users/{user_id}", admin_token)
            check = sqlite3.connect(DB)
            self.assertEqual(check.execute("SELECT COUNT(*) FROM business_records WHERE serial_no LIKE ?", (prefix + "%",)).fetchone()[0], 0)
            self.assertEqual(check.execute("SELECT COUNT(*) FROM workflow_events WHERE comment LIKE ?", (prefix + "%",)).fetchone()[0], 0)
            self.assertEqual(check.execute("SELECT COUNT(*) FROM users WHERE username LIKE ?", (prefix + "%",)).fetchone()[0], 0)
            check.close()


if __name__ == "__main__":
    unittest.main()
