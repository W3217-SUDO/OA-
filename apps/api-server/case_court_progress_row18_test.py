"""Row 18: execution and retrial court information must persist real datetimes."""

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


def request(method: str, path: str, token: str = "", payload=None):
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


def login(username: str, password: str) -> str:
    body = urllib.parse.urlencode({"username": username, "password": password}).encode()
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())["access_token"]


class CaseCourtProgressRow18Test(unittest.TestCase):
    def test_execution_and_retrial_datetimes_persist_and_archive_is_blocked(self):
        password = os.environ.get("CASE_TEST_PASSWORD")
        if not password:
            self.skipTest("CASE_TEST_PASSWORD is not set; external integration test skipped")
        token = login("admin", password)
        prefix = f"CODEX-818-R18-{uuid.uuid4().hex[:8]}"
        conn = sqlite3.connect(DB)
        case_id = None
        try:
            case_data = {
                "case_type": "民事案件",
                "plaintiffs": [prefix + "原告"],
                "defendants": [prefix + "被告"],
                "handling_lawyers": ["admin"],
            }
            conn.execute(
                "INSERT INTO business_records(module,serial_no,title,customer,status,owner,department,description,data) VALUES(?,?,?,?,?,?,?,?,?)",
                ("case", prefix, prefix, prefix + "客户", "新案待分配", "admin", "上海分所", "", json.dumps(case_data, ensure_ascii=False)),
            )
            case_id = conn.execute("SELECT id FROM business_records WHERE serial_no = ?", (prefix,)).fetchone()[0]
            conn.commit()

            execution = {
                "execution_court_name": prefix + "执行法院",
                "execution_court_case_no": prefix + "执行案号",
                "execution_court_courtroom": "执行第一法庭",
                "execution_court_judge": "执行法官甲",
                "execution_court_clerk": "执行书记员乙",
                "execution_court_filing_date": "2026-08-20",
                "execution_court_hearing_date": "2026-08-21 10:30:00",
                "execution_court_judgment_date": "2026-08-22",
                "comment": prefix + "执行法院信息",
            }
            status, body = request("POST", f"/cases/{case_id}/progress", token, execution)
            self.assertEqual(status, 200, body.decode(errors="replace"))
            saved = json.loads(body)["data"]
            self.assertEqual(saved["execution_court_hearing_date"], "2026-08-21 10:30:00")

            retrial = {
                **execution,
                "retrial_court_name": prefix + "再审法院",
                "retrial_court_case_no": prefix + "再审案号",
                "retrial_court_courtroom": "再审第一法庭",
                "retrial_court_judge": "再审法官甲",
                "retrial_court_clerk": "再审书记员乙",
                "retrial_court_filing_date": "2026-08-23",
                "retrial_court_hearing_date": "2026-08-24 14:15:00",
                "retrial_court_judgment_date": "2026-08-25",
                "comment": prefix + "再审法院信息",
            }
            status, body = request("POST", f"/cases/{case_id}/progress", token, retrial)
            self.assertEqual(status, 200, body.decode(errors="replace"))
            saved = json.loads(body)["data"]
            self.assertEqual(saved["execution_court_name"], execution["execution_court_name"])
            self.assertEqual(saved["retrial_court_hearing_date"], "2026-08-24 14:15:00")

            conn.execute("UPDATE business_records SET status = ? WHERE id = ?", ("已归档", case_id))
            conn.commit()
            status, body = request("POST", f"/cases/{case_id}/progress", token, execution)
            self.assertEqual(status, 409, body.decode(errors="replace"))
            self.assertIn("不能维护进展或开庭排期", json.loads(body).get("detail", ""))
        finally:
            if case_id:
                conn.execute("DELETE FROM workflow_events WHERE record_id = ?", (case_id,))
                conn.execute("DELETE FROM business_records WHERE id = ?", (case_id,))
            conn.commit()
            conn.close()
            check = sqlite3.connect(DB)
            self.assertEqual(check.execute("SELECT COUNT(*) FROM business_records WHERE serial_no LIKE ?", (prefix + "%",)).fetchone()[0], 0)
            self.assertEqual(check.execute("SELECT COUNT(*) FROM workflow_events WHERE comment LIKE ?", (prefix + "%",)).fetchone()[0], 0)
            check.close()


if __name__ == "__main__":
    unittest.main()
