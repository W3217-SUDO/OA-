"""HTTP contract for criminal-case creation, list visibility, and cleanup."""
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
NEW_STATUS = "\u65b0\u6848\u5f85\u5206\u914d"
STATUS_ALIAS = "\u5f85\u5206\u914d"
INVALID_STATUS = "\u5df2\u5f52\u6863"
CRIMINAL = "\u5211\u4e8b\u6848\u4ef6"
CLIENT_POSITION = "\u88ab\u544a\u4eba/\u72af\u7f6a\u5acc\u7591\u4eba"
APPROVED = "\u5df2\u901a\u8fc7"


def request(method, path, token="", payload=None, query=None):
    url = BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
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


class CaseCreateContractTest(unittest.TestCase):
    def test_http_criminal_creation_alias_invalid_status_and_list_visibility(self):
        password = os.environ.get("CASE_TEST_PASSWORD")
        self.assertTrue(password, "CASE_TEST_PASSWORD must be set; this test must execute")
        admin_token = login("admin", password)
        prefix = f"CODEX-CASE-C-NEXT-HTTP-{uuid.uuid4().hex[:8]}"
        case_ids: list[int] = []
        contract_id = lawyer_id = None
        lawyer_username = f"codex-case-c-next-http-{uuid.uuid4().hex[:8]}-lawyer"
        conn = sqlite3.connect(DB)
        try:
            status, body = request("POST", "/system/users", admin_token, {
                "username": lawyer_username, "display_name": lawyer_username,
                "department": "\u4e0a\u6d77\u5206\u6240", "password": "Codex-Case-Lawyer-123!",
                "role": "user", "profile": {"position": "\u5f8b\u5e08"},
            })
            self.assertEqual(status, 201, body.decode(errors="replace"))
            lawyer_id = json.loads(body)["id"]
            conn.execute(
                "INSERT INTO business_records(module,serial_no,title,customer,status,owner,department,description,data) VALUES(?,?,?,?,?,?,?,?,?)",
                ("contract", f"{prefix}-CONTRACT", f"{prefix} contract", f"{prefix} customer", APPROVED, "admin", "\u4e0a\u6d77\u5206\u6240", "", json.dumps({"type": "general", "amount": "1.00", "shared_with": []})),
            )
            contract_id = conn.execute("SELECT id FROM business_records WHERE serial_no = ?", (f"{prefix}-CONTRACT",)).fetchone()[0]
            conn.commit()
            payload = {
                "contract_record_id": contract_id, "serial_no": f"{prefix}-CRIMINAL", "title": f"{prefix} criminal case",
                "status": NEW_STATUS, "owner": "admin", "case_type": CRIMINAL, "client_position": CLIENT_POSITION,
                "cause_or_charge": f"{prefix} cause", "handling_lawyers": [lawyer_username], "source_person": "admin",
            }
            status, body = request("POST", "/cases", admin_token, payload)
            self.assertEqual(status, 201, body.decode(errors="replace"))
            created = json.loads(body); case_ids.append(created["id"])
            self.assertEqual(created["status"], NEW_STATUS)
            status, body = request("GET", "/records", admin_token, query={"module": "case", "keyword": payload["serial_no"], "page_size": 10})
            self.assertEqual(status, 200, body.decode(errors="replace"))
            self.assertEqual([item["id"] for item in json.loads(body)["items"]], [created["id"]])
            status, body = request("POST", "/cases", admin_token, dict(payload, serial_no=f"{prefix}-ALIAS", status=STATUS_ALIAS))
            self.assertEqual(status, 201, body.decode(errors="replace"))
            alias = json.loads(body); case_ids.append(alias["id"])
            self.assertEqual(alias["status"], NEW_STATUS)
            status, body = request("POST", "/cases", admin_token, dict(payload, serial_no=f"{prefix}-INVALID", status=INVALID_STATUS))
            self.assertEqual(status, 422, body.decode(errors="replace"))
        finally:
            for case_id in case_ids:
                conn.execute("DELETE FROM workflow_events WHERE record_id = ?", (case_id,))
                conn.execute("DELETE FROM business_records WHERE id = ?", (case_id,))
            if contract_id:
                conn.execute("DELETE FROM workflow_events WHERE record_id = ?", (contract_id,))
                conn.execute("DELETE FROM business_records WHERE id = ?", (contract_id,))
            conn.commit(); conn.close()
            if lawyer_id:
                request("DELETE", f"/system/users/{lawyer_id}", admin_token)
            check = sqlite3.connect(DB)
            self.assertEqual(check.execute("SELECT COUNT(*) FROM business_records WHERE serial_no LIKE ?", (prefix + "%",)).fetchone()[0], 0)
            self.assertEqual(check.execute("SELECT COUNT(*) FROM workflow_events WHERE comment LIKE ?", (prefix + "%",)).fetchone()[0], 0)
            self.assertEqual(check.execute("SELECT COUNT(*) FROM users WHERE username = ?", (lawyer_username,)).fetchone()[0], 0)
            check.close()


if __name__ == "__main__":
    unittest.main()
