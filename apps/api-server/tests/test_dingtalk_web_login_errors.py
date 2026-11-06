"""钉钉扫码登录：钉钉拒绝时写日志（只有步骤和错误码），不在授权范围的不再让人重新扫码（陶威 11-06）。"""
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI

from app.areas.system import dingtalk_web
from app.config import settings
from app.database import get_db
from app.dingtalk import DingTalkClient, DingTalkLoginStepError, DingTalkMembershipError, DingTalkOutOfScopeError

SECRET_CODE = "SECRET-AUTH-CODE"
USER_TOKEN = "SECRET-USER-TOKEN"
APP_TOKEN = "SECRET-APP-TOKEN"


def dingtalk(*, member=None, detail=None, token_status=200, raises=None):
    """假的钉钉：依次回换凭证、读用户、查员工、读详情。"""
    member = member or {"errcode": 0, "result": {"contact_type": 0, "userid": "u1"}}
    detail = detail or {"errcode": 0, "result": {"userid": "u1", "name": "张三", "mobile": ""}}

    def respond(request):
        path = request.url.path
        if raises and raises in path:
            raise httpx.ConnectError(f"连接失败 {request.url}", request=request)
        if path.endswith("/oauth2/userAccessToken"):
            if token_status != 200:
                return httpx.Response(token_status, json={"code": "invalidAuthCode", "message": SECRET_CODE})
            return httpx.Response(200, json={"accessToken": USER_TOKEN})
        if path.endswith("/contact/users/me"):
            return httpx.Response(200, json={"unionId": "union-1"})
        if path.endswith("/user/getbyunionid"):
            return httpx.Response(200, json=member)
        return httpx.Response(200, json=detail)
    real = httpx.AsyncClient
    return patch("app.dingtalk.httpx.AsyncClient", lambda **_: real(transport=httpx.MockTransport(respond)))


class ClientStepsTest(unittest.IsolatedAsyncioTestCase):
    async def _call(self):
        client = DingTalkClient()
        client._access_token = APP_TOKEN
        client._expires_at = client._expires_at.max.replace(tzinfo=client._expires_at.tzinfo)
        return await client.user_by_web_auth_code(SECRET_CODE)

    async def test_success_unchanged(self):
        with dingtalk():
            self.assertEqual((await self._call())["user_id"], "u1")

    async def test_out_of_scope_at_detail_and_member_steps(self):
        rejected = {"errcode": 50002, "errmsg": "请求的员工userid不在授权范围内"}
        with dingtalk(detail=rejected), self.assertRaises(DingTalkOutOfScopeError) as caught:
            await self._call()
        self.assertEqual((caught.exception.step, caught.exception.code), ("读取员工详情", 50002))
        with dingtalk(member=rejected), self.assertRaises(DingTalkOutOfScopeError) as caught:
            await self._call()
        self.assertEqual((caught.exception.step, caught.exception.code), ("按 unionId 查员工", 50002))

    async def test_other_errors_keep_step_and_code(self):
        with dingtalk(detail={"errcode": 40001, "errmsg": "别的错误"}), self.assertRaises(DingTalkLoginStepError) as caught:
            await self._call()
        self.assertNotIsInstance(caught.exception, DingTalkOutOfScopeError)
        self.assertEqual((caught.exception.step, caught.exception.code), ("读取员工详情", 40001))
        with dingtalk(token_status=400), self.assertRaises(DingTalkLoginStepError) as caught:
            await self._call()
        self.assertEqual((caught.exception.step, caught.exception.code), ("换用户凭证", "http-400/invalidAuthCode"))

    async def test_network_error_does_not_carry_token_url(self):
        with dingtalk(raises="getbyunionid"), self.assertRaises(DingTalkLoginStepError) as caught:
            await self._call()
        self.assertEqual((caught.exception.step, caught.exception.code), ("按 unionId 查员工", "ConnectError"))
        self.assertNotIn(APP_TOKEN, str(caught.exception))

    async def test_external_contact_still_membership_error(self):
        with dingtalk(member={"errcode": 0, "result": {"contact_type": 1, "userid": "u1"}}), self.assertRaises(DingTalkMembershipError):
            await self._call()


class WebLoginRouteTest(unittest.IsolatedAsyncioTestCase):
    async def _login(self, error):
        app = FastAPI()
        app.include_router(dingtalk_web.router)

        async def session():
            yield None
        app.dependency_overrides[get_db] = session
        claims = {"client_id": settings.dingtalk_app_key, "corp_id": settings.dingtalk_corp_id}
        with patch.object(dingtalk_web, "callback_url", lambda: ""), patch.object(dingtalk_web, "verify_ticket", lambda *_: claims), \
                patch.object(dingtalk_web.dingtalk_client, "user_by_web_auth_code", side_effect=error):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://isolated") as client:
                client.cookies.set(dingtalk_web.STATE_COOKIE, "state1")
                return await client.post(f"{settings.api_prefix}/auth/dingtalk/web/login",
                                         json={"auth_code": SECRET_CODE, "state": "state1"})

    async def test_out_of_scope_prompt_does_not_ask_to_rescan(self):
        with self.assertLogs(dingtalk_web.logger, "WARNING") as logs:
            response = await self._login(DingTalkOutOfScopeError("读取员工详情", 50002))
        self.assertEqual(response.status_code, 403)
        self.assertIn("账号不在应用授权范围", response.json()["detail"])
        self.assertNotIn("扫码", response.json()["detail"])
        self.assertIn("读取员工详情", logs.output[0])
        self.assertIn("50002", logs.output[0])
        self.assertNotIn(SECRET_CODE, logs.output[0])

    async def test_other_error_keeps_old_prompt_and_logs(self):
        with self.assertLogs(dingtalk_web.logger, "WARNING") as logs:
            response = await self._login(DingTalkLoginStepError("换用户凭证", "http-400/invalidAuthCode"))
        self.assertEqual(response.status_code, 502)
        self.assertIn("请重新扫码", response.json()["detail"])
        self.assertIn("http-400/invalidAuthCode", logs.output[0])
        self.assertNotIn(SECRET_CODE, logs.output[0])

    async def test_membership_prompt_unchanged_and_logged(self):
        with self.assertLogs(dingtalk_web.logger, "WARNING"):
            response = await self._login(DingTalkMembershipError("x"))
        self.assertEqual(response.status_code, 403)
        self.assertIn("内部员工", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
