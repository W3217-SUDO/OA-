"""Contract attachment state guards: draft allows writes, locked states reject them."""
import json
import os
import pathlib
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import unittest
import uuid

BASE = os.getenv("CONTRACT_TEST_BASE", "http://127.0.0.1:8000/api/v1")
DB = pathlib.Path(__file__).with_name("legal_platform.db")
UPLOAD_ROOT = DB.with_name("uploads")


def request(method, path, token="", payload=None, form=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    else:
        body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        if body is not None:
            headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def upload(token, record_id, filename):
    boundary = "----codex" + uuid.uuid4().hex
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"record_id\"\r\n\r\n{record_id}\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"category\"\r\n\r\n合同附件\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        "Content-Type: text/plain\r\n\r\ndraft attachment\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        BASE + "/attachments", data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def detail(body):
    try:
        return json.loads(body.decode()).get("detail", "")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""


class ContractAttachmentStatusTest(unittest.TestCase):
    def test_contract_attachment_state_guards(self):
        password = os.environ.get("CONTRACT_TEST_PASSWORD")
        if not password:
            self.skipTest("CONTRACT_TEST_PASSWORD is required for the live contract attachment test")
        status, body = request("POST", "/auth/login", form={"username": "admin", "password": password})
        self.assertEqual(status, 200, body.decode(errors="replace"))
        token = json.loads(body)["access_token"]
        prefix = f"CODEX-CONTRACT-C-ATTACH-GUARD-{uuid.uuid4().hex[:8]}"
        customer_id = contract_id = attachment_id = None
        try:
            status, body = request("POST", "/customers", token, {
                "serial_no": f"{prefix}-CUS", "title": f"{prefix}-客户", "owner": "admin", "department": "上海分所",
            })
            self.assertEqual(status, 201, body.decode(errors="replace")); customer_id = json.loads(body)["id"]
            status, body = request("POST", "/contracts", token, {
                "serial_no": f"{prefix}-CON", "title": f"{prefix}-合同", "customer": f"{prefix}-客户",
                "owner": "admin", "department": "上海分所", "data": {"type": "法律顾问合同", "signed_at": "2026-08-02", "customer_id": customer_id},
            })
            self.assertEqual(status, 201, body.decode(errors="replace")); contract_id = json.loads(body)["id"]

            status, body = upload(token, contract_id, f"{prefix}.txt")
            self.assertEqual(status, 201, body.decode(errors="replace")); attachment_id = json.loads(body)["id"]
            conn = sqlite3.connect(DB)
            baseline_files = {p.name for p in UPLOAD_ROOT.iterdir()} if UPLOAD_ROOT.exists() else set()
            baseline_attachment_count = conn.execute("SELECT COUNT(*) FROM file_attachments WHERE record_id = ?", (contract_id,)).fetchone()[0]
            conn.close()

            for state in ("审批中", "已归档"):
                conn = sqlite3.connect(DB)
                conn.execute("UPDATE business_records SET status = ? WHERE id = ?", (state, contract_id)); conn.commit(); conn.close()
                upload_status, upload_body = upload(token, contract_id, f"{prefix}-{state}.txt")
                self.assertEqual(upload_status, 409, upload_body.decode(errors="replace"))
                self.assertIn("审批中或已归档合同不能上传或删除附件", detail(upload_body))
                conn = sqlite3.connect(DB)
                current_count = conn.execute("SELECT COUNT(*) FROM file_attachments WHERE record_id = ?", (contract_id,)).fetchone()[0]
                conn.close()
                self.assertEqual(current_count, baseline_attachment_count)
                current_files = {p.name for p in UPLOAD_ROOT.iterdir()} if UPLOAD_ROOT.exists() else set()
                self.assertEqual(current_files, baseline_files)
                delete_status, delete_body = request("DELETE", f"/attachments/{attachment_id}", token)
                self.assertEqual(delete_status, 409, delete_body.decode(errors="replace"))
                self.assertIn("审批中或已归档合同不能上传或删除附件", detail(delete_body))

            conn = sqlite3.connect(DB); conn.execute("UPDATE business_records SET status = '草稿' WHERE id = ?", (contract_id,)); conn.commit(); conn.close()
            self.assertEqual(request("DELETE", f"/attachments/{attachment_id}", token)[0], 204)
            attachment_id = None
        finally:
            conn = sqlite3.connect(DB); conn.execute("PRAGMA foreign_keys=ON")
            ids = [value for value in (customer_id, contract_id) if value]
            if ids:
                marks = ",".join("?" for _ in ids)
                conn.execute(f"DELETE FROM workflow_events WHERE record_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM file_attachments WHERE record_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM business_records WHERE id IN ({marks})", ids)
            conn.commit()
            residue = conn.execute("SELECT COUNT(*) FROM business_records WHERE serial_no LIKE ?", (prefix + "%",)).fetchone()[0]
            attachment_residue = conn.execute("SELECT COUNT(*) FROM file_attachments WHERE original_name LIKE ?", (prefix + "%",)).fetchone()[0]
            event_residue = conn.execute("SELECT COUNT(*) FROM workflow_events WHERE comment LIKE ?", (prefix + "%",)).fetchone()[0]
            conn.close()
            self.assertEqual(residue, 0)
            self.assertEqual(attachment_residue, 0)
            self.assertEqual(event_residue, 0)


if __name__ == "__main__":
    unittest.main()
