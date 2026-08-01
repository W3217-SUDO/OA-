"""Authenticated seal view/status and permission contract test.

Runs only when SEAL_TEST_PASSWORD is set; credentials stay in process memory.
"""
import datetime
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import unittest
import uuid

BASE = os.getenv("SEAL_TEST_BASE", "http://127.0.0.1:8000/api/v1")


def request(method, path, token, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def login(username, password):
    body = urllib.parse.urlencode({"username": username, "password": password}).encode()
    req = urllib.request.Request(BASE + "/auth/login", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)["access_token"]


@unittest.skipUnless(os.getenv("SEAL_TEST_PASSWORD"), "set SEAL_TEST_PASSWORD for authenticated local test")
class SealViewAccessTest(unittest.TestCase):
    def test_view_status_and_non_admin_scope(self):
        admin = login("admin", os.environ["SEAL_TEST_PASSWORD"])
        for view in ("my", "audit", "all"):
            status, body = request("GET", f"/seals/applications?view={view}&record_status=%E5%BE%85%E5%AE%A1%E6%89%B9", admin)
            self.assertEqual(status, 200, (view, body))
        status, body = request("GET", "/seals/applications?view=invalid-seal-view", admin)
        self.assertEqual(status, 422, body)

        username = f"codex_seal_view_{datetime.datetime.now():%H%M%S}_{uuid.uuid4().hex[:6]}"
        password = "CodexSealTemp123!"
        created = request("POST", "/system/users", admin, {"username": username, "display_name": username, "department": "上海分所", "password": password, "role": "user"})
        self.assertEqual(created[0], 201, created[1])
        try:
            user_token = login(username, password)
            changed_password = password + "X"
            status, body = request("PATCH", "/auth/me", user_token, {"current_password": password, "new_password": changed_password})
            self.assertEqual(status, 200, body)
            user_token = login(username, changed_password)
            status, body = request("GET", "/seals/applications?view=all", user_token)
            self.assertEqual(status, 403, body)
            status, body = request("GET", "/seals/applications?view=audit", user_token)
            self.assertEqual(status, 200, body)
        finally:
            request("DELETE", f"/system/users/{created[1]['id']}", admin)


if __name__ == "__main__":
    unittest.main()
