import json, os, pathlib, sqlite3, urllib.error, urllib.parse, urllib.request, unittest, uuid

BASE = os.getenv("CASE_FEE_TEST_BASE", "http://127.0.0.1:8000/api/v1")
DB = pathlib.Path(__file__).with_name("legal_platform.db")

def req(method, path, token="", payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if body is not None: headers["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + path, data=body, headers=headers, method=method), timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()

def login(username, password):
    body = urllib.parse.urlencode({"username": username, "password": password}).encode()
    with urllib.request.urlopen(urllib.request.Request(BASE + "/auth/login", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST"), timeout=20) as response:
        return json.loads(response.read())["access_token"]

class CaseOtherOperationsRow26Test(unittest.TestCase):
    def test_mark_no_payment(self):
        password = os.environ.get("CASE_FEE_TEST_PASSWORD")
        if not password:
            self.skipTest("CASE_FEE_TEST_PASSWORD is not set; external integration test skipped")
        token = login("admin", password)
        prefix = f"CODEX-812-ROW26-{uuid.uuid4().hex[:8]}"
        db = sqlite3.connect(DB)
        case_id = fee_id = None
        try:
            db.execute("insert into business_records(module,serial_no,title,customer,status,owner,department,description,data) values(?,?,?,?,?,?,?,?,?)", ("case", prefix, prefix, prefix + "客户", "一审立案受理", "admin", "上海分所", "", json.dumps({"case_type": "民事案件"}, ensure_ascii=False)))
            case_id = db.execute("select last_insert_rowid()").fetchone()[0]
            db.commit()
            payload = {"title": prefix + "费用", "customer": prefix + "客户", "amount": 100, "fee_type": "官方费用", "expense_scope": "律所", "expense_subtype": "官费", "case_no": prefix, "case_record_id": case_id, "handler": "admin", "court": "上海法院", "document_no": prefix}
            status, raw = req("POST", "/finance/fees", token, payload)
            self.assertEqual(status, 201, raw.decode())
            fee_id = json.loads(raw)["id"]
            status, raw = req("POST", f"/finance/fees/{fee_id}/mark-no-payment", token, {"comment": prefix + "标记"})
            self.assertEqual(status, 200, raw.decode())
            result = json.loads(raw)
            self.assertEqual(result["status"], "不缴费")
            self.assertEqual(result["data"]["payment_status"], "不缴费")
        finally:
            ids = [item for item in (fee_id, case_id) if item]
            if ids:
                marks = ",".join("?" for _ in ids)
                db.execute(f"delete from workflow_events where record_id in ({marks})", ids)
                db.execute(f"delete from business_records where id in ({marks})", ids)
            db.commit()
            db.close()

if __name__ == "__main__":
    unittest.main()
