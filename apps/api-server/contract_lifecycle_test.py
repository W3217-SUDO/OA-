"""Authenticated contract lifecycle smoke test for local dev.

Run with ``CONTRACT_TEST_PASSWORD=... python contract_lifecycle_test.py``.
The password is read only from the process environment and is never printed.
"""
import datetime
import hashlib
import json
import os
import pathlib
import sqlite3
import urllib.parse
import urllib.request
import uuid
import unittest

BASE = os.getenv("CONTRACT_TEST_BASE", "http://127.0.0.1:8000/api/v1")
DB = pathlib.Path(__file__).with_name("legal_platform.db")


def request(method, path, token, payload=None, form=None, files=None):
    headers = {"Authorization": f"Bearer {token}"}
    if files is not None:
        boundary = uuid.uuid4().hex
        chunks = []
        for name, value in (form or {}).items():
            chunks += [f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()]
        filename, content, content_type = files
        chunks += [f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n".encode(), content, b"\r\n", f"--{boundary}--\r\n".encode()]
        body = b"".join(chunks); headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif form is not None:
        body = urllib.parse.urlencode(form).encode(); headers["Content-Type"] = "application/x-www-form-urlencoded"
    else:
        body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        if body is not None: headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status, dict(res.headers), res.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


@unittest.skipUnless(os.getenv("CONTRACT_TEST_PASSWORD"), "set CONTRACT_TEST_PASSWORD")
class ContractLifecycleTest(unittest.TestCase):
    def test_draft_approval_change_archive_and_attachment(self):
        status, _, body = request("POST", "/auth/login", "", form={"username": "admin", "password": os.environ["CONTRACT_TEST_PASSWORD"]})
        self.assertEqual(status, 200); token = json.loads(body)["access_token"]
        prefix = f"CODEX-CONTRACT-C-{datetime.datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}"
        customer_id = None; contract_ids = []; attachment_ids = []; attachment_paths = []
        try:
            status, _, body = request("POST", "/customers", token, {"serial_no": f"{prefix}-CUS", "title": f"{prefix}-客户", "owner": "admin", "department": "Shanghai", "description": "lifecycle"})
            self.assertEqual(status, 201); customer = json.loads(body); customer_id = customer["id"]
            for index, signed_at in ((1, "2026-08-01"), (2, "2026-08-02")):
                status, _, body = request("POST", "/contracts", token, {"serial_no": f"{prefix}-CON-{index}", "title": f"{prefix}-合同-{index}", "customer": customer["title"], "owner": "admin", "department": "Shanghai", "description": "lifecycle", "data": {"type": "legal", "signed_at": signed_at}})
                self.assertEqual(status, 201); contract_ids.append(json.loads(body)["id"])
            for cid, marker in zip(contract_ids, ("one", "two")):
                status, _, body = request("POST", "/attachments", token, form={"record_id": str(cid), "category": "合同附件", "remark": "lifecycle"}, files=(f"{prefix}-{marker}.txt", f"Chinese 中文 {marker}".encode(), "text/plain"))
                self.assertEqual(status, 201); item = json.loads(body); attachment_ids.append(item["id"]); attachment_paths.append(item.get("path", ""))
            for cid in contract_ids:
                self.assertEqual(request("POST", f"/contracts/{cid}/submit", token, {"approvers": ["admin"], "comment": "submit"})[0], 200)
            self.assertEqual(request("POST", f"/contracts/{contract_ids[0]}/approve", token, {"approved": True, "comment": "approved"})[0], 200)
            self.assertEqual(request("POST", f"/contracts/{contract_ids[1]}/approve", token, {"approved": False, "comment": "rejected"})[0], 200)
            self.assertEqual(request("DELETE", f"/contracts/{contract_ids[0]}/draft", token)[0], 409)
            self.assertEqual(request("POST", f"/contracts/{contract_ids[0]}/changes", token, {"change_type": "amend", "reason": "scope", "amount": 100})[0], 201)
            self.assertEqual(request("POST", f"/contracts/{contract_ids[0]}/changes/review", token, {"approved": True, "comment": "change approved"})[0], 200)
            self.assertEqual(request("POST", f"/contracts/{contract_ids[0]}/changes", token, {"change_type": "amend", "reason": "reject branch", "title": f"{prefix}-合同-1-变更"})[0], 201)
            self.assertEqual(request("POST", f"/contracts/{contract_ids[0]}/changes/review", token, {"approved": False, "comment": "change rejected"})[0], 200)
            for aid in attachment_ids:
                status, headers, content = request("GET", f"/attachments/{aid}/download", token); self.assertEqual(status, 200); self.assertGreater(len(content), 0); self.assertTrue(any("attachment" in str(value).lower() for key, value in headers.items() if key.lower() == "content-disposition")); self.assertEqual(len(hashlib.sha256(content).hexdigest()), 64)
            self.assertEqual(request("POST", f"/contracts/{contract_ids[0]}/archive", token)[0], 200)
            self.assertEqual(request("DELETE", f"/contracts/{contract_ids[0]}/draft", token)[0], 409)
        finally:
            conn = sqlite3.connect(DB); conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("delete from contract_approval_steps where contract_record_id in (?,?)", contract_ids or [-1, -1])
            ids = [customer_id or -1, *(contract_ids or [-1, -1])]
            conn.execute("delete from workflow_events where record_id in (?, ?, ?)", ids)
            conn.execute("delete from file_attachments where id in (?,?)", attachment_ids or [-1, -1])
            conn.execute("delete from business_records where id in (?, ?, ?)", ids); conn.commit(); conn.close()
            for raw in attachment_paths:
                if raw and pathlib.Path(raw).is_file(): pathlib.Path(raw).unlink()
            conn = sqlite3.connect(DB)
            residue = conn.execute("select count(*) from business_records where serial_no like ?", (prefix + "%",)).fetchone()[0]; conn.close()
            self.assertEqual(residue, 0)


if __name__ == "__main__": unittest.main()
