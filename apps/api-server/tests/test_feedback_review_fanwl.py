"""问题处理中心：免审账号之外提交的单要范文玲审核，内容由后端自动转发（用户要求，2026-11-06）。"""
import unittest
from datetime import timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.system import feedback, feedback_forward, feedback_review_config
from app.core import change_log, soft_delete
from app.core.dependencies import current_identity, get_db
from app.database import Base
from app.models import BusinessRecord, DataChangeLog, User


def person(username, role="staff", name=""):
    return {"username": username, "role": role, "role_ids": [role], "_actual_role_ids": [role],
            "display_name": name or username, "department": "CODEXFWL"}


FWL = person("fwl", "admin", "范文玲")
FWLL = person("fwll", "staff", "范文玲玲")
TGN = person("tgn", "admin", "思法汇成")
SHENHE = person("shenhe", "auditor", "审核管理（赵媛）")
ADMIN = person("admin", "admin", "管理者")
STAFF = person("CODEXFWLSTAFF", "staff", "普通提交人")
BOT = feedback.FEEDBACK_BOT_IDENTITY
NEW = person("CODEXFWLNEW", "staff", "新审核人")
DINGTALK = {"fwl": "156133631033066318", "CODEXFWLNEW": "999"}
API = "/api/v1/feedback"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16


class ReviewBase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor("CODEXFWL")
        async with self.sessions() as db:
            db.add_all([User(username=item["username"], display_name=item["display_name"], password_hash="isolated-only",
                             department="CODEXFWL", role=item["role"],
                             profile={"dingtalk_user_id": DINGTALK.get(item["username"], "")})
                        for item in (FWL, FWLL, TGN, SHENHE, ADMIN, STAFF, NEW)])
            await db.commit()
        self.identity = dict(STAFF)
        app = FastAPI()
        app.include_router(feedback.router)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated")
        self.sent = []
        self.fail_with = None

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _send(self, user_id, title, content):
        if self.fail_with:
            raise self.fail_with
        self.sent.append((user_id, title, content))
        return "1"

    async def _flush(self, minutes=1):
        now = feedback_forward._now() + timedelta(minutes=minutes)
        await feedback_forward.flush_review_forwards(sessions=self.sessions, send=self._send, now=now)

    async def _submit(self, identity=STAFF, description="表头换行了", **extra):
        self.identity = dict(identity)
        created = await self.client.post(f"{API}/submit", json={"description": description, "page": "工作台", **extra})
        self.assertEqual(created.status_code, 200, created.text)
        return created.json()["id"]

    async def _as(self, identity, feedback_id, action, comment=""):
        self.identity = dict(identity)
        return await self.client.post(f"{API}/{feedback_id}/transitions", json={"action": action, "comment": comment})

    async def _detail(self, feedback_id, identity=ADMIN):
        self.identity = dict(identity)
        return (await self.client.get(f"{API}/{feedback_id}")).json()

    async def _record(self, feedback_id):
        async with self.sessions() as db:
            return await db.get(BusinessRecord, feedback_id)


class ReviewFlowTest(ReviewBase):
    async def test_three_exempt_accounts_skip_review_and_forward(self):
        for identity in (FWL, TGN, SHENHE):
            feedback_id = await self._submit(identity)
            self.assertEqual((await self._detail(feedback_id))["status"], "待处理")
            self.assertNotIn("reviewer", (await self._record(feedback_id)).data)
        await self._flush()
        self.assertEqual(self.sent, [])

    async def test_other_accounts_wait_for_review_by_account_not_name(self):
        # fwll 叫范文玲玲，是另一个账号，要审核；admin 也不免审。
        for identity in (STAFF, FWLL, ADMIN):
            feedback_id = await self._submit(identity)
            self.assertEqual((await self._detail(feedback_id))["status"], "待审核")
        events = (await self._detail(feedback_id))["events"]
        self.assertEqual((events[0]["action"], events[0]["to_status"]), ("提交反馈", "待审核"))

    async def test_only_fwl_can_approve(self):
        feedback_id = await self._submit()
        for identity in (ADMIN, TGN, BOT, STAFF):
            response = await self._as(identity, feedback_id, "审核通过", "范文玲说可以")
            self.assertEqual(response.status_code, 403, identity["username"])
        # fwll 是另一个账号，连这张单都看不到。
        self.assertEqual((await self._as(FWLL, feedback_id, "审核通过")).status_code, 404)
        self.assertIn("审核通过", (await self._detail(feedback_id, FWL))["available_actions"])
        self.assertNotIn("审核通过", (await self._detail(feedback_id, ADMIN))["available_actions"])
        self.assertEqual((await self._as(FWL, feedback_id, "审核通过")).json(), {"status": "待处理"})
        # 通过后不能再点一次。
        self.assertEqual((await self._as(FWL, feedback_id, "审核通过")).status_code, 409)

    async def test_handlers_blocked_during_review_but_replies_allowed(self):
        feedback_id = await self._submit()
        for identity in (ADMIN, BOT, TGN, FWL):
            for action in ("请确认修改方案", "处理完成，请验证"):
                response = await self._as(identity, feedback_id, action, "打算这样改")
                self.assertEqual(response.status_code, 409, (identity["username"], action))
                self.assertIn("范文玲审核", response.json()["detail"])
        self.assertEqual((await self._as(BOT, feedback_id, "确认修改", "代记")).status_code, 409)
        self.identity = dict(BOT)
        reply = await self.client.post(f"{API}/{feedback_id}/replies", json={"content": "收到，正在处理"})
        self.assertEqual(reply.status_code, 200, reply.text)
        self.assertEqual((await self._detail(feedback_id))["status"], "待审核")

    async def test_normal_flow_after_approval_and_reopen_goes_back_to_review(self):
        feedback_id = await self._submit()
        await self._as(FWL, feedback_id, "审核通过")
        self.assertEqual((await self._as(BOT, feedback_id, "请确认修改方案", "这样改")).json(), {"status": "待确认"})
        self.assertEqual((await self._as(STAFF, feedback_id, "确认修改")).json(), {"status": "待处理"})
        self.assertEqual((await self._as(BOT, feedback_id, "处理完成，请验证", "好了")).json(), {"status": "待验证"})
        # 不能从待验证直接发方案绕过审核，页面上也不出现这个按钮。
        self.assertEqual((await self._as(BOT, feedback_id, "请确认修改方案", "新需求")).status_code, 409)
        self.assertNotIn("请确认修改方案", (await self._detail(feedback_id, BOT))["available_actions"])
        self.assertEqual((await self._as(STAFF, feedback_id, "未解决，重新打开", "还要加一列")).json(), {"status": "待审核"})
        self.assertEqual((await self._as(ADMIN, feedback_id, "处理完成，请验证", "x")).status_code, 409)
        self.assertEqual((await self._as(FWL, feedback_id, "审核通过")).json(), {"status": "待处理"})
        await self._as(BOT, feedback_id, "处理完成，请验证", "好了")
        # 问题处理助手代转回，同样回到待审核。
        self.assertEqual((await self._as(BOT, feedback_id, "未解决，重新打开", "提交人回复说没好")).json(), {"status": "待审核"})

    async def test_exempt_ticket_flow_unchanged(self):
        feedback_id = await self._submit(TGN)
        await self._as(BOT, feedback_id, "处理完成，请验证", "好了")
        self.assertEqual((await self._as(BOT, feedback_id, "请确认修改方案", "新需求")).json(), {"status": "待确认"})
        await self._as(TGN, feedback_id, "确认修改")
        await self._as(BOT, feedback_id, "处理完成，请验证", "好了")
        self.assertEqual((await self._as(TGN, feedback_id, "未解决，重新打开", "没好")).json(), {"status": "待处理"})

    async def test_old_tickets_are_not_reviewed(self):
        # 上线前的单没有 data.reviewer，流程不变。
        async with self.sessions() as db:
            record = BusinessRecord(module="bug_feedback", serial_no="BUG20260101001", title="旧单", customer="",
                                    status="待验证", owner=STAFF["username"], description="旧单", data={"page": "x"})
            db.add(record)
            await db.commit()
            feedback_id = record.id
        self.assertEqual((await self._as(BOT, feedback_id, "请确认修改方案", "新需求")).json(), {"status": "待确认"})
        await self._as(STAFF, feedback_id, "确认修改")
        await self._as(BOT, feedback_id, "处理完成，请验证", "好了")
        self.assertEqual((await self._as(STAFF, feedback_id, "未解决，重新打开", "没好")).json(), {"status": "待处理"})

    async def test_reporter_can_withdraw_during_review(self):
        feedback_id = await self._submit()
        self.assertTrue((await self._detail(feedback_id, STAFF))["can_withdraw"])
        self.assertEqual((await self._as(STAFF, feedback_id, "撤回")).json(), {"status": "已撤回"})

    async def test_status_filter_counts_and_open_group(self):
        feedback_id = await self._submit()
        self.identity = dict(ADMIN)
        counts = (await self.client.get(f"{API}/status-counts")).json()["counts"]
        self.assertEqual(counts["待审核"], 1)
        listed = (await self.client.get(API, params={"status": "待审核"})).json()
        self.assertEqual([item["id"] for item in listed["items"]], [feedback_id])
        grouped = (await self.client.get(API, params={"group": "open"})).json()
        self.assertEqual([item["id"] for item in grouped["items"]], [feedback_id])

    async def test_reviewer_keeps_access_even_without_admin_role(self):
        feedback_id = await self._submit()
        reviewer = person("fwl", "staff", "范文玲")
        self.assertIn("审核通过", (await self._detail(feedback_id, reviewer))["available_actions"])
        listed = (await self.client.get(API)).json()
        self.assertEqual([item["id"] for item in listed["items"]], [feedback_id])


class ReviewForwardTest(ReviewBase):
    async def test_new_ticket_forwarded_with_full_content_and_late_files(self):
        feedback_id = await self._submit(description="完整描述第一行\n第二行", controls=["保存", "删除"])
        self.identity = dict(STAFF)
        uploaded = await self.client.post(f"{API}/{feedback_id}/files", params={"name": "截图一.png"}, content=PNG)
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        await feedback_forward.flush_review_forwards(sessions=self.sessions, send=self._send, now=feedback_forward._now())
        self.assertEqual(self.sent, [], "要等几秒，附件传完再发")
        await self._flush()
        self.assertEqual(len(self.sent), 1)
        user_id, title, content = self.sent[0]
        self.assertEqual(user_id, "156133631033066318")
        record = await self._record(feedback_id)
        self.assertIn(record.serial_no, title)
        for expected in ("普通提交人", "工作台", "保存、删除", "完整描述第一行\n第二行", "截图一.png",
                         f"https://huzhilawfirm.com/?page=feedback&id={feedback_id}"):
            self.assertIn(expected, content)
        self.assertNotIn(feedback_forward.PENDING_KEY, record.data)
        self.assertEqual(record.data[feedback_forward.SENT_KEY], 1)
        # 发过之后再上传的文件单独发。
        self.identity = dict(STAFF)
        await self.client.post(f"{API}/{feedback_id}/files", params={"name": "截图二.png"}, content=PNG)
        await self._flush()
        self.assertEqual(len(self.sent), 2)
        self.assertIn("截图二.png", self.sent[1][2])

    async def test_long_description_split_without_loss(self):
        description = "\n".join(f"第{index}行：" + "问" * 60 for index in range(200))
        feedback_id = await self._submit(description=description)
        await self._flush()
        self.assertGreater(len(self.sent), 1)
        for index, (_, title, content) in enumerate(self.sent, 1):
            self.assertIn(f"（{index}/{len(self.sent)}）", title)
            # send_work_notification 连同标题和结尾地址截到 2000 字。
            self.assertLessEqual(len(title) + len(content) + 60, 2000)
        joined = "\n".join(content for _, _, content in self.sent)
        self.assertIn(description, joined)
        self.assertIn(f"id={feedback_id}", self.sent[-1][2])

    async def test_split_keeps_text_without_line_breaks(self):
        text = "问" * 5000
        parts = feedback_forward.split_parts(text)
        self.assertEqual("".join(parts), text)
        self.assertTrue(all(len(part) <= feedback_forward.PART_LIMIT for part in parts))

    async def test_send_failure_does_not_block_and_is_retried(self):
        self.fail_with = RuntimeError("钉钉不通")
        feedback_id = await self._submit()
        await self._flush()
        record = await self._record(feedback_id)
        self.assertEqual(record.status, "待审核")
        pending = record.data[feedback_forward.PENDING_KEY]
        self.assertEqual((pending[0]["attempts"], pending[0]["error"]), (1, "钉钉不通"))
        self.fail_with = None
        await self._flush(minutes=0)
        self.assertEqual(self.sent, [], "退避时间没到不重发")
        await self._flush(minutes=5)
        self.assertEqual(len(self.sent), 1)
        self.assertNotIn(feedback_forward.PENDING_KEY, (await self._record(feedback_id)).data)

    async def test_forward_does_not_touch_updated_at(self):
        feedback_id = await self._submit()
        before = (await self._record(feedback_id)).updated_at
        await self._flush()
        self.assertEqual((await self._record(feedback_id)).updated_at, before)

    async def test_reporter_reply_and_reply_files_forwarded_others_not(self):
        feedback_id = await self._submit()
        await self._flush()
        self.sent.clear()
        self.identity = dict(BOT)
        await self.client.post(f"{API}/{feedback_id}/replies", json={"content": "收到，正在处理"})
        await self._flush()
        self.assertEqual(self.sent, [], "处理人的回复不转发")
        self.identity = dict(STAFF)
        reply = await self.client.post(f"{API}/{feedback_id}/replies", json={"content": "我再补充一点", "file_count": 1})
        event_id = reply.json()["event_id"]
        await self.client.post(f"{API}/{feedback_id}/files", params={"name": "补充.pdf", "event_id": event_id}, content=b"%PDF-1")
        await self._flush()
        self.assertEqual(len(self.sent), 1)
        self.assertIn("我再补充一点", self.sent[0][2])
        self.assertIn("补充.pdf", self.sent[0][2])

    async def test_form_reply_with_file_forwarded(self):
        feedback_id = await self._submit()
        await self._flush()
        self.sent.clear()
        self.identity = dict(STAFF)
        response = await self.client.post(f"{API}/{feedback_id}/messages", data={"content": "表单回复"},
                                          files={"files": ("图.png", PNG, "image/png")})
        self.assertEqual(response.status_code, 200, response.text)
        await self._flush()
        self.assertIn("表单回复", self.sent[0][2])
        self.assertIn("图.png", self.sent[0][2])

    async def test_reopen_forwarded_even_when_bot_records_it(self):
        feedback_id = await self._submit()
        await self._flush()
        await self._as(FWL, feedback_id, "审核通过")
        await self._as(BOT, feedback_id, "处理完成，请验证", "好了")
        self.sent.clear()
        await self._as(BOT, feedback_id, "未解决，重新打开", "提交人说还没好")
        await self._flush()
        self.assertEqual(len(self.sent), 1)
        self.assertIn("提交人说还没好", self.sent[0][2])
        self.assertIn("待审核", self.sent[0][2])

    async def test_items_sent_in_order_after_failure(self):
        self.fail_with = RuntimeError("钉钉不通")
        feedback_id = await self._submit(description="正文在前")
        await self._flush()
        self.fail_with = None
        self.identity = dict(STAFF)
        await self.client.post(f"{API}/{feedback_id}/replies", json={"content": "回复在后"})
        await self._flush(minutes=5)
        self.assertEqual(len(self.sent), 2)
        self.assertIn("正文在前", self.sent[0][2])
        self.assertIn("回复在后", self.sent[1][2])


class ReviewConfigTest(ReviewBase):
    async def _save(self, identity, reviewer, exempt=()):
        self.identity = dict(identity)
        return await self.client.put(f"{API}/review-config", json={"reviewer": reviewer, "exempt": list(exempt)})

    async def test_missing_or_bad_config_uses_defaults(self):
        self.identity = dict(ADMIN)
        data = (await self.client.get(f"{API}/review-config")).json()
        self.assertEqual((data["reviewer"], data["exempt"]), ("fwl", ["fwl", "shenhe", "tgn"]))
        self.assertTrue(data["can_edit"])
        for value in ("坏数据", {"reviewer": "", "exempt": []}, {"reviewer": "feedback-bot", "exempt": []}, {"reviewer": "x"}):
            config = feedback_review_config.parse_review_config(value)
            self.assertEqual(config.reviewer, "fwl", value)
            self.assertEqual(config.exempt, frozenset({"fwl", "tgn", "shenhe"}))

    async def test_admin_change_takes_effect(self):
        saved = await self._save(TGN, NEW["username"], [STAFF["username"]])
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["reviewer"], NEW["username"])
        # 名单换了：STAFF 免审，原来免审的 shenhe 要审。
        self.assertEqual((await self._detail(await self._submit(STAFF)))["status"], "待处理")
        self.assertEqual((await self._detail(await self._submit(SHENHE)))["status"], "待审核")

    async def test_bot_agents_and_non_admins_cannot_change(self):
        for identity in (BOT, STAFF, SHENHE, person("fwl", "staff", "范文玲")):
            self.assertEqual((await self._save(identity, STAFF["username"])).status_code, 403, identity["username"])
        for source in ("mcp", "agent"):
            token = change_log.set_source(source)
            try:
                self.assertEqual((await self._save(ADMIN, STAFF["username"])).status_code, 403, source)
            finally:
                change_log.source_var.reset(token)
        self.identity = dict(ADMIN)
        self.assertEqual((await self.client.get(f"{API}/review-config")).json()["reviewer"], "fwl")

    async def test_invalid_reviewer_rejected(self):
        self.assertEqual((await self._save(ADMIN, "  ")).status_code, 422)
        self.assertEqual((await self._save(ADMIN, "不存在的人")).status_code, 422)
        self.assertEqual((await self._save(ADMIN, "feedback-bot")).status_code, 422)
        self.assertEqual((await self._save(ADMIN, "fwl", ["feedback-bot"])).status_code, 422)
        self.assertEqual((await self._save(ADMIN, "fwl", ["不存在的人"])).status_code, 422)
        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == NEW["username"]))
            user.is_active = False
            await db.commit()
        self.assertEqual((await self._save(ADMIN, NEW["username"])).status_code, 422)

    async def test_generic_config_route_cannot_change_it(self):
        from app.areas.system import router as system_router
        app = FastAPI()
        app.include_router(system_router.router)
        app.dependency_overrides[current_identity] = lambda: dict(ADMIN)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated") as client:
            response = await client.patch("/api/v1/system/configs/feedback_review", json={"value": {"reviewer": "x"}})
        self.assertEqual(response.status_code, 409, response.text)

    async def test_new_reviewer_takes_over_pending_tickets(self):
        feedback_id = await self._submit(description="换人前的单")
        await self._flush()
        self.assertEqual(self.sent[0][0], "156133631033066318")
        self.sent.clear()
        self.assertEqual((await self._save(ADMIN, NEW["username"], ["tgn"])).status_code, 200)
        self.assertEqual((await self._as(FWL, feedback_id, "审核通过")).status_code, 403)
        # 审核人不是管理员也能看到并通过。
        self.assertIn("审核通过", (await self._detail(feedback_id, NEW))["available_actions"])
        listed = (await self.client.get(API, params={"mine": True})).json()
        self.assertEqual([item["id"] for item in listed["items"]], [feedback_id])
        await self._flush()
        self.assertEqual([item[0] for item in self.sent], ["999"])
        self.assertIn("换人前的单", self.sent[0][2])
        self.assertEqual((await self._as(NEW, feedback_id, "审核通过")).json(), {"status": "待处理"})

    async def test_same_reviewer_saved_again_does_not_resend(self):
        await self._submit()
        await self._flush()
        self.sent.clear()
        self.assertEqual((await self._save(ADMIN, "fwl", ["fwl"])).status_code, 200)
        await self._flush()
        self.assertEqual(self.sent, [])

    async def test_disabled_reviewer_blocks_but_does_not_release(self):
        await self._save(ADMIN, NEW["username"])
        feedback_id = await self._submit()
        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == NEW["username"]))
            user.is_active = False
            await db.commit()
        detail = await self._detail(feedback_id)
        self.assertEqual((detail["status"], detail["reviewer_active"]), ("待审核", False))
        self.assertEqual((await self._as(ADMIN, feedback_id, "处理完成，请验证", "x")).status_code, 409)
        await self._flush()
        self.assertEqual(self.sent, [])
        pending = (await self._record(feedback_id)).data[feedback_forward.PENDING_KEY]
        self.assertIn("审核人已停用", pending[0]["error"])
        # 管理员换人后恢复。
        await self._save(ADMIN, "fwl", ["tgn"])
        await self._flush()
        self.assertEqual(self.sent[0][0], "156133631033066318")
        self.assertEqual((await self._as(FWL, feedback_id, "审核通过")).json(), {"status": "待处理"})

    async def test_change_is_logged(self):
        self.identity = dict(TGN)
        soft_delete.set_actor("tgn")
        await self.client.put(f"{API}/review-config", json={"reviewer": "fwl", "exempt": ["tgn"]})
        await self.client.put(f"{API}/review-config", json={"reviewer": NEW["username"], "exempt": ["tgn"]})
        async with self.sessions() as db:
            logs = (await db.scalars(select(DataChangeLog).where(DataChangeLog.table_name == "system_configs")
                                     .order_by(DataChangeLog.id))).all()
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[-1].actor, "tgn")
        self.assertEqual(logs[-1].changes["value"]["__json__"]["reviewer"], ["fwl", NEW["username"]])


if __name__ == "__main__":
    unittest.main()
