"""Authenticated HR employee-archive permission and cleanup regression test."""

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


def parsed(body):
    return json.loads(body.decode() or "{}")


def login(username, password):
    status, body = request("POST", "/auth/login", form={"username": username, "password": password})
    if status != 200:
        raise AssertionError(body.decode(errors="replace"))
    result = parsed(body)
    token = result["access_token"]
    if result.get("must_change_password"):
        new_password = password + "-ready"
        status, body = request("PATCH", "/auth/me", token, {
            "current_password": password,
            "new_password": new_password,
        })
        if status != 200:
            raise AssertionError(body.decode(errors="replace"))
        return login(username, new_password)
    return token


def upload(token, record_id, category, filename, content=b"CODEX D4 archive fixture"):
    boundary = "----codex-hr-d4-" + uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"record_id\"\r\n\r\n{record_id}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"category\"\r\n\r\n{category}\r\n".encode("utf-8"),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: text/plain\r\n\r\n".encode(),
        content,
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        BASE + "/attachments",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def employee_payload(prefix, username, password, role, department):
    return {
        "username": username,
        "display_name": prefix,
        "employee_no": prefix,
        "company": "上海申浩律师事务所",
        "department": department,
        "password": password,
        "role": role,
        "position": "普通用户",
        "is_active": True,
        "account_type": "员工账号",
        "data": {"account_type": "员工账号"},
    }


@unittest.skipUnless(os.getenv("HR_TEST_PASSWORD"), "set HR_TEST_PASSWORD for authenticated local test")
class HrEmployeeArchivePermissionsTest(unittest.TestCase):
    def test_archive_write_permissions_and_read_only_access(self):
        admin_token = login("admin", os.environ["HR_TEST_PASSWORD"])
        marker = uuid.uuid4().hex[:10]
        prefix = f"CODEX-HR-D4-ARCHIVE-{marker}"
        fixture_password = "D4-Archive-234!"
        usernames = {
            "employee": f"codex_hr_d4_archive_{marker}",
            "manager": f"codex_hr_d4_archive_manager_{marker}",
            "cross_manager": f"codex_hr_d4_archive_cross_{marker}",
        }
        employee_ids = []
        attachment_ids = []
        try:
            created = {}
            user_ids = {}
            for key, role, department in (
                ("employee", "user", "行政流程部"),
                ("manager", "manager", "行政流程部"),
                ("cross_manager", "manager", "财务部"),
            ):
                status, body = request("POST", "/hr/employees", admin_token, employee_payload(
                    f"{prefix}-{key.upper()}", usernames[key], fixture_password, role, department,
                ))
                self.assertEqual(status, 201, body.decode(errors="replace"))
                result = parsed(body)
                created[key] = result["employee"]["id"]
                user_ids[key] = result["user"]["id"]
                employee_ids.append(created[key])

            for key in ("manager", "cross_manager"):
                status, body = request("PATCH", f"/system/users/{user_ids[key]}", admin_token, {"role": "manager"})
                self.assertEqual(status, 200, body.decode(errors="replace"))

            employee_token = login(usernames["employee"], fixture_password)
            manager_token = login(usernames["manager"], fixture_password)
            cross_manager_token = login(usernames["cross_manager"], fixture_password)

            status, body = upload(admin_token, created["employee"], "员工档案", f"{prefix}-admin.txt")
            self.assertEqual(status, 201, body.decode(errors="replace"))
            admin_attachment_id = parsed(body)["id"]
            attachment_ids.append(admin_attachment_id)

            list_status, list_body = request("GET", f"/attachments?record_id={created['employee']}&category={urllib.parse.quote('员工档案')}", employee_token)
            download_status, download_body = request("GET", f"/attachments/{admin_attachment_id}/download", employee_token)
            preview_status, preview_body = request("GET", f"/attachments/{admin_attachment_id}/preview", employee_token)
            employee_delete_status, _ = request("DELETE", f"/attachments/{admin_attachment_id}", employee_token)

            employee_upload_status, employee_upload_body = upload(
                employee_token, created["employee"], "员工档案", f"{prefix}-employee.txt",
            )
            if employee_upload_status == 201:
                attachment_ids.append(parsed(employee_upload_body)["id"])

            wrong_category_status, wrong_category_body = upload(
                admin_token, created["employee"], "普通附件", f"{prefix}-wrong-category.txt",
            )
            if wrong_category_status == 201:
                attachment_ids.append(parsed(wrong_category_body)["id"])

            manager_upload_status, manager_upload_body = upload(
                manager_token, created["manager"], "员工档案", f"{prefix}-manager.txt",
            )
            manager_delete_status = None
            if manager_upload_status == 201:
                manager_attachment_id = parsed(manager_upload_body)["id"]
                attachment_ids.append(manager_attachment_id)
                manager_delete_status, _ = request("DELETE", f"/attachments/{manager_attachment_id}", manager_token)

            status, body = upload(admin_token, created["employee"], "员工档案", f"{prefix}-cross-manager.txt")
            self.assertEqual(status, 201, body.decode(errors="replace"))
            cross_attachment_id = parsed(body)["id"]
            attachment_ids.append(cross_attachment_id)
            cross_manager_delete_status, _ = request("DELETE", f"/attachments/{cross_attachment_id}", cross_manager_token)

            self.assertEqual(list_status, 200, list_body.decode(errors="replace"))
            self.assertIn(admin_attachment_id, [item["id"] for item in parsed(list_body)["items"]])
            self.assertEqual(download_status, 200, download_body.decode(errors="replace"))
            self.assertEqual(download_body, b"CODEX D4 archive fixture")
            self.assertEqual(preview_status, 200, preview_body.decode(errors="replace"))
            self.assertEqual(parsed(preview_body)["kind"], "text")
            self.assertEqual(employee_delete_status, 403)
            self.assertEqual(employee_upload_status, 403)
            self.assertEqual(wrong_category_status, 422)
            self.assertEqual(manager_upload_status, 201, manager_upload_body.decode(errors="replace"))
            self.assertEqual(manager_delete_status, 204)
            self.assertEqual(cross_manager_delete_status, 404)
        finally:
            for attachment_id in attachment_ids:
                request("DELETE", f"/attachments/{attachment_id}", admin_token)
            for employee_id in reversed(employee_ids):
                request("DELETE", f"/hr/employees/{employee_id}", admin_token)

            conn = sqlite3.connect(DB)
            rows = conn.execute(
                "SELECT path FROM file_attachments WHERE original_name LIKE ?",
                (prefix + "%",),
            ).fetchall()
            ids = [row[0] for row in conn.execute(
                "SELECT id FROM business_records WHERE serial_no LIKE ? OR title LIKE ?",
                (prefix + "%", prefix + "%"),
            ).fetchall()]
            if ids:
                marks = ",".join("?" for _ in ids)
                conn.execute(f"DELETE FROM file_attachments WHERE record_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM hr_subrecords WHERE employee_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM workflow_events WHERE record_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM business_records WHERE id IN ({marks})", ids)
            conn.execute("DELETE FROM file_attachments WHERE original_name LIKE ?", (prefix + "%",))
            conn.executemany("DELETE FROM users WHERE username = ?", [(username,) for username in usernames.values()])
            conn.commit()
            residue = {
                "records": conn.execute("SELECT COUNT(*) FROM business_records WHERE serial_no LIKE ? OR title LIKE ?", (prefix + "%", prefix + "%")).fetchone()[0],
                "users": conn.execute("SELECT COUNT(*) FROM users WHERE username LIKE ?", (f"codex_hr_d4_archive_%{marker}",)).fetchone()[0],
                "attachments": conn.execute("SELECT COUNT(*) FROM file_attachments WHERE original_name LIKE ?", (prefix + "%",)).fetchone()[0],
            }
            conn.close()
            for (stored_path,) in rows:
                candidate = pathlib.Path(stored_path)
                if candidate.is_file() and UPLOAD_ROOT.resolve() in candidate.resolve().parents:
                    candidate.unlink(missing_ok=True)
            self.assertEqual(residue, {"records": 0, "users": 0, "attachments": 0})


if __name__ == "__main__":
    unittest.main()
