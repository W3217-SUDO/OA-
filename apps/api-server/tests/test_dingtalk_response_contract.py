"""隔离 HTTP 响应与 SQLite 发件箱，验证钉钉发送结果分类。"""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
from app.config import settings
from app.core import notification_delivery
from app.database import Base
from app.dingtalk import (
    DingTalkClient,
    DingTalkError,
    DingTalkRejectedError,
    DingTalkUnknownResultError,
    dingtalk_client,
)
from app.models import Notification, NotificationDelivery, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.environment import validate_test_environment


def response_client(payload, *, status: int = 200, text: str | None = None):
    def respond(request):
        if text is not None:
            return httpx.Response(status, text=text, request=request)
        return httpx.Response(status, json=payload, request=request)

    return httpx.AsyncClient(transport=httpx.MockTransport(respond))


class DingTalkResponseContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        validate_test_environment()
        self.settings_patches = [
            patch.object(settings, "dingtalk_corp_id", "test-corp"),
            patch.object(settings, "dingtalk_agent_id", "1"),
            patch.object(settings, "dingtalk_app_key", "test-key"),
            patch.object(settings, "dingtalk_app_secret", "test-secret"),
            patch.object(settings, "dingtalk_notifications_enabled", True),
        ]
        for item in self.settings_patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.settings_patches)])
        self.client = DingTalkClient()
        self.client._access_token = "test-token"
        self.client._expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    async def test_valid_success_and_explicit_rejection(self):
        for task_id in (12345, "12345"):
            with (
                self.subTest(task_id=task_id),
                patch("app.dingtalk.httpx.AsyncClient", return_value=response_client({"errcode": 0, "task_id": task_id})),
            ):
                self.assertEqual(await self.client.send_work_notification("staff", "标题", "正文"), "12345")
        with (
            patch("app.dingtalk.httpx.AsyncClient", return_value=response_client({"errcode": 40001, "errmsg": "明确拒绝"})),
            self.assertRaisesRegex(DingTalkRejectedError, "明确拒绝"),
        ):
            await self.client.send_work_notification("staff", "标题", "正文")

    async def test_malformed_or_incomplete_response_is_unknown(self):
        responses = [
            ({"task_id": 123}, 200, None),
            ({"errcode": None, "task_id": 123}, 200, None),
            ({"errcode": "0", "task_id": 123}, 200, None),
            ({"errcode": True, "task_id": 123}, 200, None),
            ({"errcode": 0}, 200, None),
            ({"errcode": 0, "task_id": 0}, 200, None),
            ({"errcode": 0, "task_id": "abc"}, 200, None),
            ({"errcode": 0, "task_id": 123}, 500, None),
            ([], 200, None),
            (None, 200, "not json"),
        ]
        for payload, status, raw_text in responses:
            with (
                self.subTest(payload=payload, status=status, text=raw_text),
                patch("app.dingtalk.httpx.AsyncClient", return_value=response_client(payload, status=status, text=raw_text)),
                self.assertRaises(DingTalkUnknownResultError),
            ):
                await self.client.send_work_notification("staff", "标题", "正文")

    async def test_token_failure_precedes_send(self):
        self.client._access_token = ""
        paths = []

        def respond(request):
            paths.append(request.url.path)
            return httpx.Response(200, json={"message": "凭证不可用"}, request=request)

        with (
            patch("app.dingtalk.httpx.AsyncClient", return_value=httpx.AsyncClient(transport=httpx.MockTransport(respond))),
            self.assertRaisesRegex(DingTalkError, "凭证不可用"),
        ):
            await self.client.send_work_notification("staff", "标题", "正文")
        self.assertEqual(paths, ["/v1.0/oauth2/accessToken"])

    async def test_unknown_response_persists_and_is_not_claimed_again(self):
        with tempfile.TemporaryDirectory(prefix="oa-test-dingtalk-response-") as temporary:
            database = Path(temporary) / "outbox.sqlite"
            engine = create_async_engine(f"sqlite+aiosqlite:///{database.as_posix()}")
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            try:
                async with engine.begin() as connection:
                    await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=[
                        User.__table__, Notification.__table__, NotificationDelivery.__table__,
                    ]))
                async with sessions() as db:
                    db.add(User(username="staff", display_name="测试员工", role="user", role_ids=["user"],
                                department="测试部门", password_hash="test-only",
                                profile={"dingtalk_user_id": "ding-staff"}, is_active=True))
                    db.add(Notification(source_key="malformed-response", source_type="task", recipient="staff",
                                        title="任务提醒", content="待处理"))
                    await db.commit()
                with patch.object(notification_delivery, "SessionLocal", sessions):
                    async with sessions() as db:
                        self.assertEqual(await notification_delivery.enqueue_dingtalk_notifications(db), 1)
                    with patch.object(dingtalk_client, "_access_token", "test-token"), patch.object(
                        dingtalk_client, "_expires_at", datetime.now(timezone.utc) + timedelta(hours=1)
                    ), patch("app.dingtalk.httpx.AsyncClient", return_value=response_client({"errcode": 0})), patch.object(
                        notification_delivery.logger, "exception"
                    ) as log_exception:
                        self.assertTrue(await notification_delivery.dispatch_one("dingtalk"))
                        self.assertFalse(await notification_delivery.dispatch_one("dingtalk"))
                        log_exception.assert_called_once()
                    async with sessions() as db:
                        delivery = await db.scalar(select(NotificationDelivery))
                        notice = await db.scalar(select(Notification))
                        self.assertEqual((delivery.state, delivery.attempts), ("unknown", 1))
                        self.assertEqual(notice.dingtalk_status, "unknown")
                        self.assertIn("task_id", delivery.error)
            finally:
                await engine.dispose()


if __name__ == "__main__":
    unittest.main()
