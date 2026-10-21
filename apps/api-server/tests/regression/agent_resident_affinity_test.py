"""隔离端口验证会话转发、原始身份校验、流式响应及私有通道边界。"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException
import httpx
from starlette.requests import Request

from app.harness_agent import affinity


class ResidentAffinityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="oa-affinity-test-")
        self.root = Path(self.temporary.name)
        self.storage = patch("app.harness_agent.runtime.storage_root", return_value=self.root)
        self.storage.start()
        self.received = []

        async def application(scope, receive, send):
            self.received.append(scope)
            headers = dict(scope["headers"])
            if headers.get(b"authorization") != b"Bearer isolated-account":
                await send({"type": "http.response.start", "status": 403, "headers": []})
                await send({"type": "http.response.body", "body": b""})
                return
            await receive()
            await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/event-stream")]})
            for chunk in (b'data: {"type":"delta","content":"A"}\n\n', b'data: {"type":"done"}\n\n'):
                await send({"type": "http.response.body", "body": chunk, "more_body": True})
            await send({"type": "http.response.body", "body": b""})

        self.application = application

    async def asyncTearDown(self):
        await affinity.close()
        self.storage.stop()
        self.temporary.cleanup()

    def request(self, *, authorization="isolated-account", path="messages"):
        async def receive():
            return {"type": "http.request", "body": b'{"content":"probe"}', "more_body": False}
        return Request({"type": "http", "method": "POST", "scheme": "http", "server": ("test", 80),
                        "path": "/api/v1/personal-agent/" + path, "query_string": b"",
                        "headers": [(b"authorization", ("Bearer " + authorization).encode()),
                                    (b"content-type", b"application/json")]}, receive)

    async def claim(self):
        with affinity.request_turn(self.application):
            await affinity.claim("owner", "conversation")

    async def test_external_process_stream_is_relayed_to_the_original_owner(self):
        await self.claim()
        own = affinity._OWNER
        self.assertIsNone(await affinity.forward(self.request(), "owner", "conversation"))
        with patch.object(affinity, "_OWNER", "f" * 32):
            response = await affinity.forward(self.request(), "owner", "conversation")
            body = b"".join([chunk async for chunk in response.body_iterator])
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'"content":"A"', body)
        self.assertTrue(self.received[-1][affinity._SCOPE])
        self.assertNotIn(affinity._HEADER.encode(), dict(self.received[-1]["headers"]))
        route = affinity._route(affinity._directory(), "owner", "conversation")
        self.assertEqual(json.loads(route.read_bytes())["owner"], own)

    async def test_forwarded_requests_still_need_the_original_account_credentials(self):
        await self.claim()
        with patch.object(affinity, "_OWNER", "f" * 32):
            response = await affinity.forward(self.request(authorization="wrong-account"), "owner", "conversation")
            _ = [chunk async for chunk in response.body_iterator]
            self.assertEqual(response.status_code, 403)
            self.assertIsNone(await affinity.forward(self.request(), "another-owner", "conversation"))

    async def test_stop_request_reaches_the_same_owner(self):
        await self.claim()
        with patch.object(affinity, "_OWNER", "f" * 32):
            response = await affinity.forward(self.request(path="conversations/conversation/stop"), "owner", "conversation")
            _ = [chunk async for chunk in response.body_iterator]
        self.assertTrue(self.received[-1]["path"].endswith("/stop"))

    async def test_private_channel_rejects_missing_secret_and_unrelated_routes(self):
        await self.claim()
        record = json.loads(affinity._PEER[2].read_bytes())
        async with httpx.AsyncClient(trust_env=False) as client:
            url = f"http://127.0.0.1:{record['port']}/api/v1/personal-agent/messages"
            self.assertEqual((await client.post(url, headers={"authorization": "Bearer isolated-account"})).status_code, 403)
            url = f"http://127.0.0.1:{record['port']}/api/v1/users"
            self.assertEqual((await client.post(url, headers={affinity._HEADER: record["token"]})).status_code, 403)
        self.assertFalse(self.received)

    async def test_closed_owner_allows_the_next_request_to_claim_without_stale_forwarding(self):
        await self.claim()
        await affinity.close()
        with patch.object(affinity, "_OWNER", "f" * 32):
            self.assertIsNone(await affinity.forward(self.request(), "owner", "conversation"))

    async def test_invalid_routes_fail_explicitly_and_non_http_calls_do_not_start_a_peer(self):
        await affinity.claim("owner", "conversation")
        self.assertIsNone(affinity._PEER)
        root = affinity._directory()
        affinity._write(affinity._route(root, "owner", "conversation"), {"owner": "../../other"})
        with self.assertRaises(HTTPException) as failure:
            await affinity.forward(self.request(), "owner", "conversation")
        self.assertEqual(failure.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
