"""Authenticated HR commission permission, bypass and cleanup regression test."""

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


def commission_payload(start_date="2026-08-01", end_date="", base_salary=6100):
    return {
        "kind": "commission",
        "data": {
            "start_date": start_date,
            "end_date": end_date,
            "base_salary": base_salary,
            "hearing_rate": 0.10,
            "hearing_fixed": 0,
            "document_rate": 0.05,
            "document_fixed": 0,
            "source_rate": 0.05,
            "source_fixed": 0,
            "investigation_rate": 0.05,
            "investigation_fixed": 0,
            "quality_rate": 0.02,
            "quality_fixed": 0,
        },
    }


@unittest.skipUnless(os.getenv("HR_TEST_PASSWORD"), "set HR_TEST_PASSWORD for authenticated local test")
class HrCommissionPermissionsTest(unittest.TestCase):
    def test_commission_write_permissions_cannot_be_bypassed(self):
        admin_token = login("admin", os.environ["HR_TEST_PASSWORD"])
        marker = uuid.uuid4().hex[:10]
        prefix = f"CODEX-HR-D4-COMMISSION-{marker}"
        fixture_password = "D4-Commission-234!"
        usernames = {
            "employee": f"codex_hr_d4_commission_{marker}",
            "manager": f"codex_hr_d4_commission_manager_{marker}",
            "cross_manager": f"codex_hr_d4_commission_cross_{marker}",
        }
        employee_ids = []
        subrecord_ids = []
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

            status, body = request("POST", f"/hr/{created['employee']}/subrecords", admin_token, commission_payload())
            self.assertEqual(status, 201, body.decode(errors="replace"))
            admin_subrecord_id = parsed(body)["id"]
            subrecord_ids.append(admin_subrecord_id)

            list_status, list_body = request("GET", f"/hr/{created['employee']}/subrecords?kind=commission", employee_token)
            employee_create_status, _ = request("POST", f"/hr/{created['employee']}/subrecords", employee_token, commission_payload("2026-09-01"))
            employee_update_status, _ = request("PATCH", f"/hr/{created['employee']}/subrecords/{admin_subrecord_id}", employee_token, {"data": commission_payload(base_salary=6200)["data"]})
            employee_delete_status, _ = request("DELETE", f"/hr/{created['employee']}/subrecords/{admin_subrecord_id}", employee_token)

            manager_create_status, manager_create_body = request("POST", f"/hr/{created['employee']}/subrecords", manager_token, commission_payload("2026-09-01", base_salary=6300))
            self.assertEqual(manager_create_status, 201, manager_create_body.decode(errors="replace"))
            manager_subrecord_id = parsed(manager_create_body)["id"]
            subrecord_ids.append(manager_subrecord_id)
            manager_update_status, manager_update_body = request("PATCH", f"/hr/{created['employee']}/subrecords/{manager_subrecord_id}", manager_token, {"data": commission_payload("2026-09-01", base_salary=6400)["data"]})
            manager_delete_status, _ = request("DELETE", f"/hr/{created['employee']}/subrecords/{manager_subrecord_id}", manager_token)

            cross_create_status, _ = request("POST", f"/hr/{created['employee']}/subrecords", cross_manager_token, commission_payload("2026-10-01"))
            cross_update_status, _ = request("PATCH", f"/hr/{created['employee']}/subrecords/{admin_subrecord_id}", cross_manager_token, {"data": commission_payload(base_salary=6500)["data"]})
            cross_delete_status, _ = request("DELETE", f"/hr/{created['employee']}/subrecords/{admin_subrecord_id}", cross_manager_token)
            mismatched_employee_status, _ = request("PATCH", f"/hr/{created['manager']}/subrecords/{admin_subrecord_id}", manager_token, {"data": commission_payload(base_salary=6600)["data"]})
            wrong_kind_status, _ = request("POST", f"/hr/{created['employee']}/subrecords", manager_token, {"kind": "archive", "data": {"start_date": "2026-11-01"}})

            self.assertEqual(list_status, 200, list_body.decode(errors="replace"))
            self.assertIn(admin_subrecord_id, [item["id"] for item in parsed(list_body)["items"]])
            self.assertEqual(employee_create_status, 403)
            self.assertEqual(employee_update_status, 403)
            self.assertEqual(employee_delete_status, 403)
            self.assertEqual(manager_update_status, 200, manager_update_body.decode(errors="replace"))
            self.assertEqual(parsed(manager_update_body)["data"]["base_salary"], 6400)
            self.assertEqual(manager_delete_status, 204)
            self.assertEqual(cross_create_status, 404)
            self.assertEqual(cross_update_status, 404)
            self.assertEqual(cross_delete_status, 404)
            self.assertEqual(mismatched_employee_status, 404)
            self.assertEqual(wrong_kind_status, 422)
        finally:
            for subrecord_id in subrecord_ids:
                request("DELETE", f"/hr/{created.get('employee', 0)}/subrecords/{subrecord_id}", admin_token)
            for employee_id in reversed(employee_ids):
                request("DELETE", f"/hr/employees/{employee_id}", admin_token)

            conn = sqlite3.connect(DB)
            ids = [row[0] for row in conn.execute(
                "SELECT id FROM business_records WHERE serial_no LIKE ? OR title LIKE ?",
                (prefix + "%", prefix + "%"),
            ).fetchall()]
            if ids:
                marks = ",".join("?" for _ in ids)
                conn.execute(f"DELETE FROM hr_subrecords WHERE employee_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM file_attachments WHERE record_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM workflow_events WHERE record_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM business_records WHERE id IN ({marks})", ids)
            conn.executemany("DELETE FROM users WHERE username = ?", [(username,) for username in usernames.values()])
            conn.commit()
            residue = {
                "records": conn.execute("SELECT COUNT(*) FROM business_records WHERE serial_no LIKE ? OR title LIKE ?", (prefix + "%", prefix + "%")).fetchone()[0],
                "users": conn.execute("SELECT COUNT(*) FROM users WHERE username LIKE ?", (f"codex_hr_d4_commission_%{marker}",)).fetchone()[0],
                "subrecords": conn.execute("SELECT COUNT(*) FROM hr_subrecords WHERE created_by LIKE ? OR updated_by LIKE ?", (f"codex_hr_d4_commission_%{marker}", f"codex_hr_d4_commission_%{marker}")).fetchone()[0],
                "attachments": conn.execute("SELECT COUNT(*) FROM file_attachments WHERE original_name LIKE ?", (prefix + "%",)).fetchone()[0],
            }
            conn.close()
            self.assertEqual(residue, {"records": 0, "users": 0, "subrecords": 0, "attachments": 0})


if __name__ == "__main__":
    unittest.main()
