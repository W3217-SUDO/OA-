"""Local authenticated contract export/filter smoke test.

Set CONTRACT_TEST_PASSWORD in the process environment to run; the password is
never written to output or repository files.
"""
import datetime
import json
import os
import urllib.parse
import urllib.request
import unittest
import uuid
import xml.etree.ElementTree as ET


BASE = os.getenv("CONTRACT_TEST_BASE", "http://127.0.0.1:8000/api/v1")
NS = "{urn:schemas-microsoft-com:office:spreadsheet}"


def call(method, path, token, payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.status, response.headers, response.read()


@unittest.skipUnless(os.getenv("CONTRACT_TEST_PASSWORD"), "set CONTRACT_TEST_PASSWORD for authenticated local test")
class ContractExportFilteredTest(unittest.TestCase):
    def test_filtered_excel_contains_only_matching_contract(self):
        form = urllib.parse.urlencode({"username": "admin", "password": os.environ["CONTRACT_TEST_PASSWORD"]}).encode()
        request = urllib.request.Request(BASE + "/auth/login", data=form, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(request, timeout=15) as response:
            token = json.load(response)["access_token"]

        prefix = f"CODEX-CONTRACT-C-{datetime.datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}"
        customers = call("GET", "/customers?page_size=10", token)[2]
        customer_items = json.loads(customers)["items"]
        self.assertGreaterEqual(len(customer_items), 2)
        created = []
        try:
            for index, (customer, signed_at) in enumerate(zip(customer_items[:2], ("2026-07-01", "2026-08-01")), 1):
                payload = {
                    "serial_no": f"{prefix}-{index}", "title": f"{prefix}-合同{index}",
                    "customer": customer["title"], "owner": "admin", "department": "上海分所",
                    "description": "中文合同扩展数据验收",
                    "data": {"type": "法律顾问合同", "contract_body": "律所", "signed_at": signed_at, "扩展字段": "中文值"},
                }
                status, _, body = call("POST", "/contracts", token, payload)
                self.assertEqual(status, 201)
                created.append(json.loads(body)["id"])

            for params, included, excluded in (
                ({"serial_no": f"{prefix}-1"}, f"{prefix}-1", f"{prefix}-2"),
                ({"signed_at_start": "2026-08-01", "signed_at_end": "2026-08-01"}, f"{prefix}-2", f"{prefix}-1"),
            ):
                query = urllib.parse.urlencode({"module": "contract", **params})
                status, headers, body = call("GET", f"/records/export-excel?{query}", token)
                self.assertEqual(status, 200)
                self.assertIn("application/vnd.ms-excel", headers.get("Content-Type", ""))
                self.assertIn(".xls", headers.get("Content-Disposition", ""))
                self.assertGreater(len(body), 0)
                root = ET.fromstring(body)
                cells = [node.text or "" for node in root.iter(NS + "Data")]
                text = body.decode("utf-8")
                self.assertIn(included, text)
                self.assertNotIn(excluded, text)
                self.assertIn("中文合同扩展数据验收", text)
                self.assertGreaterEqual(len(cells), 10)
        finally:
            for contract_id in created:
                call("DELETE", f"/contracts/{contract_id}/draft", token)
            remaining = json.loads(call("GET", f"/records?module=contract&keyword={urllib.parse.quote(prefix)}&page_size=100", token)[2])
            self.assertEqual(remaining["items"], [])


if __name__ == "__main__":
    unittest.main()
