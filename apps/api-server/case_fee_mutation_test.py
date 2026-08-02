"""Draft case-fee edit/delete guards."""
import json, os, pathlib, sqlite3, urllib.error, urllib.parse, urllib.request, unittest, uuid

BASE = os.getenv("CASE_FEE_TEST_BASE", "http://127.0.0.1:8000/api/v1")
DB = pathlib.Path(__file__).with_name("legal_platform.db")

def req(method, path, token="", payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    h = {"Authorization": f"Bearer {token}"} if token else {}
    if body is not None: h["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + path, data=body, headers=h, method=method), timeout=20) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()

def login(user, password):
    body = urllib.parse.urlencode({"username": user, "password": password}).encode()
    with urllib.request.urlopen(urllib.request.Request(BASE + "/auth/login", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST"), timeout=20) as r: return json.loads(r.read())["access_token"]

class CaseFeeMutationTest(unittest.TestCase):
    def test_draft_edit_delete_and_guards(self):
        password = os.environ.get("CASE_FEE_TEST_PASSWORD"); self.assertTrue(password)
        admin = login("admin", password); prefix = f"CODEX-CASE-C-FEE-{uuid.uuid4().hex[:8]}"; case_id = fee_id = deleted_fee_id = user_id = None
        c = sqlite3.connect(DB)
        try:
            username = f"codex-case-fee-{uuid.uuid4().hex[:8]}-user"; initial = "CodexFeeUser123!"
            s,b=req("POST","/system/users",admin,{"username":username,"display_name":username,"department":"上海分所","password":initial,"role":"user"}); self.assertEqual(s,201,b.decode())
            user_id=json.loads(b)["id"]; first=login(username,initial); changed="CodexFeeUserChanged123!"; self.assertEqual(req("PATCH","/auth/me",first,{"current_password":initial,"new_password":changed})[0],200); user=login(username,changed)
            data={"case_type":"民事案件","case_creation_step":"completed","case_team_usernames":[username]}
            c.execute("insert into business_records(module,serial_no,title,customer,status,owner,department,description,data) values(?,?,?,?,?,?,?,?,?)",("case",prefix,prefix+"案件",prefix+"客户","一审立案受理","admin","上海分所","",json.dumps(data,ensure_ascii=False))); case_id=c.execute("select last_insert_rowid()").fetchone()[0]; c.commit()
            payload={"title":prefix+"费用","customer":prefix+"客户","amount":101.01,"fee_type":"官方费用","expense_scope":"律所","expense_subtype":"官费","case_no":prefix,"case_record_id":case_id,"handler":"admin","description":prefix}
            s,b=req("POST","/finance/fees",admin,payload); self.assertEqual(s,201,b.decode()); fee_id=json.loads(b)["id"]
            edit={**payload,"title":prefix+"修改","amount":202.02}; s,b=req("PUT",f"/finance/fees/{fee_id}",admin,edit); self.assertEqual(s,200,b.decode()); self.assertEqual(json.loads(b)["data"]["amount"],202.02)
            s,b=req("PUT",f"/finance/fees/{fee_id}",user,edit); self.assertEqual(s,403,b.decode())
            c.execute("update business_records set status=? where id=?",("已归档",case_id)); c.commit(); s,b=req("DELETE",f"/finance/fees/{fee_id}",admin); self.assertEqual(s,409,b.decode()); self.assertIn("归档",json.loads(b)["detail"])
            c.execute("update business_records set status=? where id=?",("一审立案受理",case_id)); c.commit(); s,b=req("DELETE",f"/finance/fees/{fee_id}",admin); self.assertEqual(s,204,b.decode()) ; deleted_fee_id, fee_id = fee_id, None
        finally:
            record_ids = [record_id for record_id in (case_id, fee_id, deleted_fee_id) if record_id]
            if record_ids:
                placeholders = ",".join("?" for _ in record_ids)
                c.execute(f"delete from workflow_events where record_id in ({placeholders})", record_ids)
            c.execute("delete from workflow_events where comment like ?", (prefix + "%",))
            for record_id in (fee_id, deleted_fee_id):
                if record_id: c.execute("delete from business_records where id=?",(record_id,))
            if case_id: c.execute("delete from business_records where id=?",(case_id,))
            c.commit(); c.close()
            if user_id: req("DELETE",f"/system/users/{user_id}",admin)
            check=sqlite3.connect(DB); self.assertEqual(check.execute("select count(*) from business_records where serial_no like ?",(prefix+"%",)).fetchone()[0],0); self.assertEqual(check.execute("select count(*) from workflow_events where comment like ?",(prefix+"%",)).fetchone()[0],0); self.assertEqual(check.execute("select count(*) from file_attachments where original_name like ?",(prefix+"%",)).fetchone()[0],0); check.close()

if __name__ == "__main__": unittest.main()
