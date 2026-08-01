"""Authenticated system-cache registry, pagination, clear and permission contract."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import unittest
import uuid

BASE = os.getenv("SYSTEM_CACHE_TEST_BASE", "http://127.0.0.1:8000/api/v1")


def request(method, path, token="", payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def login(password):
    body = urllib.parse.urlencode({"username": "admin", "password": password}).encode()
    req = urllib.request.Request(BASE + "/auth/login", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)["access_token"]


def login_as(username, password):
    body = urllib.parse.urlencode({"username": username, "password": password}).encode()
    req = urllib.request.Request(BASE + "/auth/login", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)["access_token"]


@unittest.skipUnless(os.getenv("SYSTEM_CACHE_TEST_PASSWORD"), "set SYSTEM_CACHE_TEST_PASSWORD for authenticated local test")
class SystemCacheContractTest(unittest.TestCase):
    def test_registry_pagination_and_safe_clear_contract(self):
        status, body = request("GET", "/system/caches")
        self.assertEqual(status, 401, body)
        status, body = request("POST", "/system/caches/clear", payload={"cache_keys": ["IPR_CASETYPE_PREFIX_casetype"]})
        self.assertEqual(status, 401, body)
        token = login(os.environ["SYSTEM_CACHE_TEST_PASSWORD"])
        username = f"codex-cache-user-{uuid.uuid4().hex[:8]}"
        password = "CacheUser123!"
        status, created = request("POST", "/system/users", token, {"username": username, "display_name": username, "department": "上海分所", "password": password, "role": "user"})
        self.assertEqual(status, 201, created)
        try:
            user_token = login_as(username, password)
            self.assertTrue(user_token)
            changed_password = "CacheUserChanged123!"
            status, body = request("PATCH", "/auth/me", user_token, {"current_password": password, "new_password": changed_password})
            self.assertEqual(status, 200, body)
            user_token = login_as(username, changed_password)
            status, body = request("GET", "/system/caches", user_token)
            self.assertEqual(status, 403, body)
            status, body = request("POST", "/system/caches/clear", user_token, {"cache_keys": ["IPR_CASETYPE_PREFIX_casetype"]})
            self.assertEqual(status, 403, body)
        finally:
            status, deleted = request("DELETE", f"/system/users/{created['id']}", token)
            self.assertIn(status, (200, 204), deleted)
            status, users = request("GET", f"/system/users?keyword={urllib.parse.quote(username)}", token)
            self.assertEqual(status, 200, users)
            rows = users.get("items", users if isinstance(users, list) else [])
            self.assertFalse(any(item.get("username") == username for item in rows), users)
        status, body = request("GET", "/system/caches?page=1&page_size=3", token)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["total"], 8)
        self.assertEqual(len(body["items"]), 3)
        self.assertTrue(all(item["key"] and item["name"] and item["description"] for item in body["items"]))
        status, body = request("GET", "/system/caches?page=2&page_size=3", token)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["page"], 2)
        key = body["items"][0]["key"]
        status, cleared = request("POST", f"/system/caches/{urllib.parse.quote(key, safe='')}/clear", token)
        self.assertEqual(status, 200, cleared)
        self.assertEqual(cleared["key"], key)
        status, batch = request("POST", "/system/caches/clear", token, {"cache_keys": [key, key]})
        self.assertEqual(status, 200, batch)
        self.assertEqual(batch["cleared"], [key])
        status, body = request("POST", "/system/caches/clear", token, {"cache_keys": []})
        self.assertEqual(status, 422, body)
        status, body = request("POST", "/system/caches/clear", token, {"cache_keys": ["CODEX-SYS-E-UNKNOWN"]})
        self.assertEqual(status, 404, body)


if __name__ == "__main__":
    unittest.main()
