"""钉钉员工详情与 UnionId 成员身份合同的隔离回归。"""

import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
import httpx
from app.areas.personal_agent import dingtalk_office_client as office


class OfficeIdentityTest(unittest.IsolatedAsyncioTestCase):
    async def query(self, detail, member):
        calls = []

        def request_handler(request):
            calls.append((request.url.path, json.loads(request.content)))
            payload = detail if request.url.path.endswith("/v2/user/get") else member
            return httpx.Response(200, json=payload)

        transport = httpx.MockTransport(request_handler)
        client = httpx.AsyncClient(transport=transport)
        with patch.object(office, "_token", AsyncMock(return_value="test-only-token")), patch.object(office.httpx, "AsyncClient", return_value=client):
            result = await office.member_union_id("test-employee")
        return result, calls

    async def test_detail_without_contact_type_uses_member_reverse_lookup(self):
        result, calls = await self.query(
            {"errcode": 0, "result": {"userid": "test-employee", "unionid": "test-union"}},
            {"errcode": 0, "result": {"userid": "test-employee", "contact_type": 0}},
        )
        self.assertEqual(result, "test-union")
        self.assertEqual(calls, [("/topapi/v2/user/get", {"userid": "test-employee"}),
                                 ("/topapi/user/getbyunionid", {"unionid": "test-union"})])

    async def test_external_or_unconfirmed_member_is_rejected(self):
        for contact_type in (1, None, False, "0"):
            with self.subTest(contact_type=contact_type), self.assertRaises(HTTPException) as error:
                await self.query({"errcode": 0, "result": {"userid": "test-employee", "unionid": "test-union"}},
                                 {"errcode": 0, "result": {"userid": "test-employee", "contact_type": contact_type}})
            self.assertEqual(error.exception.status_code, 403)

    async def test_member_user_id_must_match_original_binding(self):
        with self.assertRaises(HTTPException) as error:
            await self.query({"errcode": 0, "result": {"userid": "test-employee", "unionid": "test-union"}},
                             {"errcode": 0, "result": {"userid": "different-employee", "contact_type": 0}})
        self.assertEqual(error.exception.status_code, 403)

    async def test_missing_union_id_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            await self.query({"errcode": 0, "result": {"userid": "test-employee"}}, {})
        self.assertEqual(error.exception.status_code, 502)

    async def test_detail_false_error_code_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            await self.query({"errcode": False, "result": {"userid": "test-employee", "unionid": "test-union"}}, {})
        self.assertEqual(error.exception.status_code, 403)
