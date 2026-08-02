"""Regression test for deleting an unlinked HR external/customer account.

The fixture uses only a unique CODEX-HR-D4 record and removes its record,
workflow event and any accidentally-created user in finally.
"""
import json
import os
import pathlib
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import unittest
import uuid

BASE = os.getenv("HR_TEST_BASE", "http://127.0.0.1:8000/api/v1")
DB = pathlib.Path(__file__).with_name("legal_platform.db")


def request(method, path, token, payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def login(password):
    body = urllib.parse.urlencode({"username": "admin", "password": password}).encode()
    req = urllib.request.Request(BASE + "/auth/login", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)["access_token"]


def residue_counts(conn, prefix, employee_id):
    records = conn.execute(
        "SELECT COUNT(*) FROM business_records WHERE serial_no=? OR title=?",
        (prefix, prefix),
    ).fetchone()[0]
    users = conn.execute(
        "SELECT COUNT(*) FROM users WHERE username LIKE ?",
        (prefix.lower() + "%",),
    ).fetchone()[0]
    workflow_events = conn.execute(
        "SELECT COUNT(*) FROM workflow_events WHERE record_id=?",
        (employee_id,),
    ).fetchone()[0]
    attachments = conn.execute(
        "SELECT COUNT(*) FROM file_attachments WHERE record_id=?",
        (employee_id,),
    ).fetchone()[0]
    return records, users, workflow_events, attachments


@unittest.skipUnless(os.getenv("HR_TEST_PASSWORD"), "set HR_TEST_PASSWORD for authenticated local test")
class HrExternalAccountDeleteTest(unittest.TestCase):
    def test_unlinked_external_account_employee_is_deletable(self):
        token = login(os.environ["HR_TEST_PASSWORD"])
        prefix = f"CODEX-HR-D4-DELETE-{uuid.uuid4().hex[:10]}"
        employee_id = None
        try:
            status, body = request("POST", "/hr/employees", token, {
                "username": "", "display_name": prefix, "employee_no": prefix,
                "company": "上海申浩律师事务所", "department": "诉讼二部",
                "password": "", "role": "user", "position": "业务专员",
                "is_active": True, "account_type": "外部合作账号",
                "data": {"account_type": "外部合作账号"},
            })
            self.assertEqual(status, 201, body)
            employee_id = body["employee"]["id"]
            self.assertEqual(body["employee"]["data"]["account_type"], "外部合作账号")
            self.assertIsNone(body["user"])
            status, impact = request("GET", f"/hr/employees/{employee_id}/deletion-impact", token)
            self.assertEqual(status, 200, impact)
            self.assertTrue(impact["deletable"], impact)
            self.assertEqual(request("DELETE", f"/hr/employees/{employee_id}", token)[0], 204)
            conn = sqlite3.connect(DB)
            residues = residue_counts(conn, prefix, employee_id)
            conn.close()
            self.assertEqual(residues, (0, 0, 0, 0))
        finally:
            conn = sqlite3.connect(DB)
            rows = conn.execute("SELECT id FROM business_records WHERE serial_no=? OR title=?", (prefix, prefix)).fetchall()
            record_ids = {record_id for (record_id,) in rows}
            if employee_id is not None:
                record_ids.add(employee_id)
            for record_id in record_ids:
                conn.execute("DELETE FROM file_attachments WHERE record_id=?", (record_id,))
                conn.execute("DELETE FROM workflow_events WHERE record_id=?", (record_id,))
                conn.execute("DELETE FROM business_records WHERE id=?", (record_id,))
            conn.execute("DELETE FROM users WHERE username LIKE ?", (prefix.lower() + "%",))
            conn.commit()
            residues = residue_counts(conn, prefix, employee_id)
            conn.close()
            self.assertEqual(residues, (0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
