"""Real API regression coverage for the local IPR official-file deletion guard."""
import json, os, pathlib, sqlite3, urllib.error, urllib.parse, urllib.request, unittest, uuid

BASE = os.getenv("IPR_OFFICIAL_DELETE_TEST_BASE", "http://127.0.0.1:8000/api/v1")
DB = pathlib.Path(__file__).with_name("legal_platform.db")
UPLOAD_ROOT = DB.with_name("uploads")


def request(method, path, token="", payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if body is not None: headers["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + path, data=body, headers=headers, method=method), timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def login(username, password):
    form = urllib.parse.urlencode({"username": username, "password": password}).encode()
    with urllib.request.urlopen(urllib.request.Request(BASE + "/auth/login", data=form, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST"), timeout=20) as response:
        return json.loads(response.read())["access_token"]


class IprOfficialFileDeleteTest(unittest.TestCase):
    def test_delete_guards_cleanup_and_test_markers(self):
        admin_password = os.environ.get("IPR_OFFICIAL_DELETE_TEST_PASSWORD")
        if not admin_password:
            raise unittest.SkipTest("IPR_OFFICIAL_DELETE_TEST_PASSWORD must be set")
        prefix = f"CODEX-IPR-B-AUTO-{uuid.uuid4().hex[:10]}"
        admin = login("admin", admin_password)
        user_id = None
        record_ids, attachment_ids, batch_ids, paths = [], [], [], []
        conn = sqlite3.connect(DB)
        try:
            username, initial, changed = f"ipr-delete-{uuid.uuid4().hex[:8]}", "CodexIprDelete123!", "CodexIprDeleteChanged123!"
            status, body = request("POST", "/system/users", admin, {"username": username, "display_name": username, "department": "上海分所", "password": initial, "role": "user"})
            self.assertEqual(status, 201, body.decode(errors="replace")); user_id = json.loads(body)["id"]
            first = login(username, initial)
            self.assertEqual(request("PATCH", "/auth/me", first, {"current_password": initial, "new_password": changed})[0], 200)
            owner_token = login(username, changed)

            def official(owner="admin", status="待校验", label="official"):
                serial = f"{prefix}-{label}"
                conn.execute("insert into business_records(module,serial_no,title,customer,status,owner,department,description,data) values(?,?,?,?,?,?,?,?,?)", ("ipr_official_file", serial, serial, prefix, status, owner, "上海分所", prefix, json.dumps({"ipr_case_id": 0}, ensure_ascii=False)))
                record_id = conn.execute("select last_insert_rowid()").fetchone()[0]; record_ids.append(record_id)
                path = UPLOAD_ROOT / f"{serial}.txt"; path.write_text(serial, encoding="utf-8"); paths.append(path)
                conn.execute("insert into file_attachments(record_id,category,file_type_code,original_name,stored_name,content_type,size,path,uploader,remark,requires_transmission,is_transmitted,transmitted_by) values(?,?,?,?,?,?,?,?,?,?,?,?,?)", (record_id, "知识产权官文原件", "", path.name, path.name, "text/plain", path.stat().st_size, str(path), owner, prefix, 0, 0, ""))
                attachment_ids.append(conn.execute("select last_insert_rowid()").fetchone()[0])
                conn.execute("insert into workflow_events(record_id,action,from_status,to_status,operator,comment) values(?,?,?,?,?,?)", (record_id, prefix, "", status, owner, prefix)); conn.commit()
                return record_id, path

            owner_id, owner_path = official(owner=username, label="owner")
            status, body = request("DELETE", f"/ipr/official-files/{owner_id}", owner_token)
            self.assertEqual(status, 204, body.decode(errors="replace"))
            self.assertEqual(conn.execute("select count(*) from business_records where id=?", (owner_id,)).fetchone()[0], 0)
            self.assertEqual(conn.execute("select count(*) from file_attachments where record_id=?", (owner_id,)).fetchone()[0], 0)
            self.assertEqual(conn.execute("select count(*) from workflow_events where record_id=?", (owner_id,)).fetchone()[0], 0)
            self.assertFalse(owner_path.exists())

            admin_id, admin_path = official(label="admin")
            status, body = request("DELETE", f"/ipr/official-files/{admin_id}", admin)
            self.assertEqual(status, 204, body.decode(errors="replace")); self.assertFalse(admin_path.exists())

            denied_id, _ = official(label="denied")
            self.assertEqual(request("DELETE", f"/ipr/official-files/{denied_id}", owner_token)[0], 403)
            for state in ("待转发", "已转发"):
                conn.execute("update business_records set status=? where id=?", (state, denied_id)); conn.commit()
                self.assertEqual(request("DELETE", f"/ipr/official-files/{denied_id}", admin)[0], 409)
            self.assertEqual(request("DELETE", "/ipr/official-files/999999999", admin)[0], 404)

            def batch(filename):
                path = UPLOAD_ROOT / filename; path.write_text(prefix, encoding="utf-8"); paths.append(path)
                conn.execute("insert into ipr_official_import_batches(source_filename,source_path,source_size,status,total_count,error_count,imported_count,created_by,department) values(?,?,?,?,?,?,?,?,?)", (filename, str(path), path.stat().st_size, "待确认", 1, 0, 0, "admin", "上海分所"))
                value = conn.execute("select last_insert_rowid()").fetchone()[0]
                conn.execute("insert into ipr_official_import_candidates(batch_id,row_no,ipr_case_id,application_no,official_type,official_no,received_date,due_date,raw_data,errors,status,official_record_id,confirmed_by,confirmed_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (value, 1, None, prefix, "测试官文", prefix, None, None, "{}", "[]", "待确认", None, "", None))
                batch_ids.append(value); conn.commit(); return value, path

            smoke_id, smoke_path = batch(f"smoke-{prefix}.csv")
            codex_id, codex_path = batch(f".tmp-codex-{prefix}.csv")
            plain_id, plain_path = batch(f"ordinary-{uuid.uuid4().hex}.csv")
            self.assertEqual(request("DELETE", f"/testing/ipr-official-import-batches/{plain_id}", admin)[0], 403); self.assertTrue(plain_path.exists())
            self.assertEqual(request("DELETE", f"/testing/ipr-official-import-batches/{smoke_id}", admin)[0], 204); self.assertFalse(smoke_path.exists())
            self.assertEqual(request("DELETE", f"/testing/ipr-official-import-batches/{codex_id}", admin)[0], 204); self.assertFalse(codex_path.exists())
            self.assertEqual(conn.execute("select count(*) from ipr_official_import_candidates where batch_id in (?,?)", (smoke_id, codex_id)).fetchone()[0], 0)

            code_record = f"{prefix}-cleanup"; conn.execute("insert into business_records(module,serial_no,title,customer,status,owner,department,description,data) values(?,?,?,?,?,?,?,?,?)", ("report", code_record, code_record, prefix, "草稿", "admin", "上海分所", "", "{}")); code_id = conn.execute("select last_insert_rowid()").fetchone()[0]; record_ids.append(code_id); conn.commit()
            self.assertEqual(request("DELETE", f"/testing/records/{code_id}", owner_token)[0], 403)
            self.assertEqual(request("DELETE", f"/testing/records/{code_id}", admin)[0], 204)
        finally:
            for path in paths:
                path.unlink(missing_ok=True)
            if record_ids:
                marks = ",".join("?" for _ in record_ids)
                conn.execute(f"delete from workflow_events where record_id in ({marks})", record_ids)
                conn.execute(f"delete from file_attachments where record_id in ({marks})", record_ids)
                conn.execute(f"delete from business_records where id in ({marks})", record_ids)
            if batch_ids:
                marks = ",".join("?" for _ in batch_ids)
                conn.execute(f"delete from ipr_official_import_candidates where batch_id in ({marks})", batch_ids)
                conn.execute(f"delete from ipr_official_import_batches where id in ({marks})", batch_ids)
            conn.commit(); conn.close()
            if user_id: request("DELETE", f"/system/users/{user_id}", admin)
            check = sqlite3.connect(DB)
            self.assertEqual(check.execute("select count(*) from business_records where serial_no like ? or title like ?", (prefix+"%", prefix+"%")).fetchone()[0], 0)
            self.assertEqual(check.execute("select count(*) from file_attachments where original_name like ?", (prefix+"%",)).fetchone()[0], 0)
            self.assertEqual(check.execute("select count(*) from workflow_events where comment like ?", (prefix+"%",)).fetchone()[0], 0)
            self.assertEqual(check.execute("select count(*) from ipr_official_import_batches where source_filename like ?", ("%"+prefix+"%",)).fetchone()[0], 0)
            check.close()


if __name__ == "__main__": unittest.main()
