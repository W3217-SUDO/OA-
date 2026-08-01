"""Self-contained contract payment application chain smoke test.

The fixture creates its own customer, approved contract, case and active lawyer,
then proves candidate/list/detail echo, review/pay transitions and illegal-state
blocking.  All data is removed exactly in ``finally``.
"""
import datetime
import json
import os
import pathlib
import sqlite3
import urllib.parse
import urllib.request
import unittest
import uuid

BASE = os.getenv("CONTRACT_TEST_BASE", "http://127.0.0.1:8000/api/v1")
DB = pathlib.Path(__file__).with_name("legal_platform.db")


def call(method, path, token="", payload=None, form=None):
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
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def upload(path, token, record_id, filename, content):
    boundary = "----codex" + uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"record_id\"\r\n\r\n{record_id}\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"category\"\r\n\r\n合同附件\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"remark\"\r\n\r\n付款专测\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: text/plain\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(BASE + path, data=body, headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


@unittest.skipUnless(os.getenv("CONTRACT_TEST_PASSWORD"), "set CONTRACT_TEST_PASSWORD")
class ContractPaymentTest(unittest.TestCase):
    def test_payment_positive_chain_and_guards(self):
        status, body = call("POST", "/auth/login", form={"username": "admin", "password": os.environ["CONTRACT_TEST_PASSWORD"]})
        self.assertEqual(status, 200, body.decode())
        token = json.loads(body)["access_token"]
        prefix = f"CODEX-CONTRACT-C-{datetime.datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}"
        customer_id = contract_id = rejected_contract_id = case_id = object_id = payment_id = lawyer_id = user_id = None
        attachment_ids = []; attachment_paths = []
        try:
            lawyer_name = f"{prefix}-律师"
            lawyer_username = f"{prefix.lower().replace('-', '')[:48]}lawyer"
            status, body = call("POST", "/hr/employees", token, {
                "username": lawyer_username, "display_name": lawyer_name,
                "employee_no": f"{prefix}-LAWYER", "company": "CODEX测试事务所",
                "department": "上海分所", "password": f"OnlyProcess-{uuid.uuid4().hex[:12]}",
                "role": "user", "position": "承办律师", "is_active": True,
            })
            self.assertEqual(status, 201, body.decode()); lawyer = json.loads(body)
            lawyer_id = lawyer["employee"]["id"]; user_id = (lawyer.get("user") or {}).get("id")

            status, body = call("POST", "/customers", token, {
                "serial_no": f"{prefix}-CUS", "title": f"{prefix}-客户", "owner": "admin",
                "department": "上海分所", "description": "payment fixture",
            })
            self.assertEqual(status, 201, body.decode()); customer_id = json.loads(body)["id"]
            contract_payload = {
                "serial_no": f"{prefix}-CON", "title": f"{prefix}-合同", "customer": f"{prefix}-客户",
                "owner": "admin", "department": "上海分所", "description": "payment fixture",
                "data": {"type": "legal", "signed_at": "2026-08-01"},
            }
            status, body = call("POST", "/contracts", token, contract_payload)
            self.assertEqual(status, 201, body.decode()); contract_id = json.loads(body)["id"]
            rejected_payload = {**contract_payload, "serial_no": f"{prefix}-REJECTED", "title": f"{prefix}-拒绝合同"}
            status, body = call("POST", "/contracts", token, rejected_payload)
            self.assertEqual(status, 201, body.decode()); rejected_contract_id = json.loads(body)["id"]
            for cid, marker in ((contract_id, "ok"), (rejected_contract_id, "rejected")):
                status, body = upload("/attachments", token, cid, f"{prefix}-{marker}.txt", b"payment fixture")
                self.assertEqual(status, 201, body.decode()); attachment = json.loads(body); attachment_ids.append(attachment["id"]); attachment_paths.append(attachment.get("path", ""))
            for cid in (contract_id, rejected_contract_id):
                submit_status, submit_body = call("POST", f"/contracts/{cid}/submit", token, {"approvers": ["admin"], "comment": "submit"})
                self.assertEqual(submit_status, 200, submit_body.decode())
            self.assertEqual(call("POST", f"/contracts/{contract_id}/approve", token, {"approved": True, "comment": "approved"})[0], 200)
            self.assertEqual(call("POST", f"/contracts/{rejected_contract_id}/approve", token, {"approved": False, "comment": "rejected"})[0], 200)

            status, body = call("POST", "/cases", token, {
                "contract_record_id": contract_id, "serial_no": f"{prefix}-CASE", "title": f"{prefix}-案件",
                "owner": "admin", "case_type": "民事案件", "opponent": "对方",
                "cause_or_charge": "合同纠纷", "client_position": "原告/申请人", "handling_lawyers": [lawyer_name],
            })
            self.assertEqual(status, 201, body.decode()); case_id = json.loads(body)["id"]
            status, body = call("POST", f"/contracts/{contract_id}/objects", token, {"case_record_id": case_id, "fee_type": "代理费", "amount": 100, "remark": "付款专测"})
            self.assertEqual(status, 201, body.decode()); object_id = json.loads(body)["id"]
            status, body = call("GET", f"/contracts/{contract_id}/payment-candidates", token)
            self.assertEqual(status, 200); candidate = json.loads(body)["items"][0]
            self.assertEqual(candidate["contract_object_id"], object_id); self.assertEqual(candidate["remaining_amount"], 100)

            payment_payload = {"payment_type": "法院费用", "payee": "人民法院", "account": "CODEX-ACCOUNT", "application_date": "2026-08-01", "remark": "付款正向链", "lines": [{"contract_object_id": object_id, "amount": 100}]}
            status, body = call("POST", f"/contracts/{contract_id}/payment-applications", token, payment_payload)
            self.assertEqual(status, 201, body.decode()); payment = json.loads(body); payment_id = payment["id"]
            self.assertEqual(payment["status"], "待审批"); self.assertEqual(payment["data"]["amount"], 100)
            status, body = call("GET", f"/contracts/{contract_id}/payment-applications", token)
            self.assertEqual(status, 200); listed = json.loads(body)["items"][0]
            self.assertEqual(listed["id"], payment_id); self.assertEqual(listed["lines"][0]["requested_amount"], 100)
            self.assertEqual(call("POST", f"/contract-payment-applications/{payment_id}/review", token, {"approved": True, "comment": "通过"})[0], 200)
            self.assertEqual(call("POST", f"/contract-payment-applications/{payment_id}/pay", token, {"paid_date": "2026-08-01", "voucher_no": f"{prefix}-VOUCHER", "comment": "已支付"})[0], 200)
            status, body = call("GET", f"/contracts/{contract_id}/payment-applications", token)
            self.assertEqual(status, 200); self.assertEqual(json.loads(body)["items"][0]["status"], "已付款")
            self.assertEqual(call("POST", f"/contract-payment-applications/{payment_id}/pay", token, {"paid_date": "2026-08-01", "voucher_no": "DUP", "comment": "非法重复支付"})[0], 409)
            self.assertEqual(call("POST", f"/contract-payment-applications/{payment_id}/writeoff", token, {"writeoff_date": "2026-08-02", "voucher_no": f"{prefix}-WRITEOFF", "comment": "核销"})[0], 200)
            status, body = call("GET", f"/contracts/{contract_id}/payment-applications", token)
            self.assertEqual(status, 200); self.assertEqual(json.loads(body)["items"][0]["status"], "已核销")
            self.assertEqual(call("POST", f"/contract-payment-applications/{payment_id}/writeoff", token, {"writeoff_date": "2026-08-02", "voucher_no": "DUP-WRITEOFF", "comment": "重复"})[0], 409)
            self.assertEqual(call("POST", "/contract-payment-applications/999999/writeoff", token, {"writeoff_date": "2026-08-02", "voucher_no": "MISSING-WRITEOFF", "comment": "不存在"})[0], 404)
            self.assertEqual(call("POST", f"/contract-payment-applications/{payment_id}/pay", token, {"paid_date": "2026-08-02", "voucher_no": "AFTER-WRITEOFF", "comment": "非法"})[0], 409)
            status, body = call("GET", f"/contracts/{contract_id}/payment-candidates", token)
            self.assertEqual(status, 200); candidate = json.loads(body)["items"][0]
            self.assertEqual(candidate["reserved_amount"], 100); self.assertEqual(candidate["remaining_amount"], 0)
            self.assertIn(call("POST", f"/contracts/{contract_id}/payment-applications", token, {**payment_payload, "lines": [{"contract_object_id": object_id, "amount": 1} ]})[0], (409, 422))
            self.assertEqual(call("POST", f"/contracts/{rejected_contract_id}/payment-applications", token, {**payment_payload, "lines": [{"contract_object_id": object_id, "amount": 1} ]})[0], 409)
        finally:
            conn = sqlite3.connect(DB); conn.execute("PRAGMA foreign_keys=ON")
            ids = [x for x in (customer_id, contract_id, rejected_contract_id, case_id, payment_id) if x]
            if ids:
                marks = ",".join("?" for _ in ids)
                conn.execute(f"DELETE FROM finance_transactions WHERE finance_record_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM contract_payment_lines WHERE payment_record_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM contract_approval_steps WHERE contract_record_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM contract_objects WHERE contract_record_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM workflow_events WHERE record_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM business_records WHERE id IN ({marks})", ids)
            if attachment_ids:
                marks = ",".join("?" for _ in attachment_ids)
                conn.execute(f"DELETE FROM file_attachments WHERE id IN ({marks})", attachment_ids)
            if lawyer_id:
                conn.execute("DELETE FROM workflow_events WHERE record_id = ?", (lawyer_id,))
                conn.execute("DELETE FROM business_records WHERE id = ?", (lawyer_id,))
            if user_id:
                conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            residue = conn.execute("SELECT COUNT(*) FROM business_records WHERE serial_no LIKE ? OR title LIKE ?", (prefix + "%", prefix + "%")).fetchone()[0]
            conn.close()
            for attachment_path in attachment_paths:
                if attachment_path and pathlib.Path(attachment_path).is_file():
                    pathlib.Path(attachment_path).unlink()
            self.assertEqual(residue, 0)


if __name__ == "__main__":
    unittest.main()
