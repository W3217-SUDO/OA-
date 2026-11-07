"""钉钉收文助手：群里 @ 的消息按发送人本人收文，不发真实消息、不连真实接口。"""
import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.aws.receipt_bot import ApiError, BotMessage, BotSettings, expire_waiting, handle_message
from app.config import settings
from app.database import Base, get_db
from app.dingtalk_receipt_worker import Worker, parse_message
from app.main import app
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import current_identity

GROUP = "临时收文群"
GROUP_ID = "cid-receipt-group"
LINK = "https://zxfw.court.gov.cn/zxfw/#/pagesAjkj/app/wssd/index?qdbh=5f184b3f7c5740d791d35a51bc6b4841&sdbh=6f184b3f7c5740d791d35a51bc6b4841&sdsin=7f184b3f7c5740d791d35a51bc6b4841"
SMS = f"【上海市浦东新区人民法院】向您发送了（2026）沪0115民初1号案件相关文书。点击链接查阅：{LINK}"
CONFIG = BotSettings(group_id=GROUP_ID, use_cloud_agent=False, auto_save_unique=False)
P, D, COURT = "上海甲方科技有限公司", "杭州乙方贸易有限公司", "上海市浦东新区人民法院"
AUTO = BotSettings(group_id=GROUP_ID, use_cloud_agent=False, auto_save_unique=True)
NUMBER = "（2026）沪0115民初1号"
CASE = {"case_id": 7, "serial_no": "HZMS1", "title": "某案", "plaintiff": "甲公司", "defendant": "乙公司", "court_case_no": ""}
DOCS = [{"attachment_id": 9, "name": "传票", "fields": {"文书类型": "传票", "收款账户": {"账号": "6222000011112222"}, "法官电话": "13900000000"}}]
PARTY_DOCS = [{"attachment_id": 9, "name": "传票", "fields": {"文书类型": "传票", "原告": ["上海甲方科技有限公司"], "被告": ["杭州乙方贸易有限公司"], "受理机关": "上海市浦东新区人民法院"}}]


def preview(level="第一级 官方案号直配", **extra):
    return {"status": "待确认入库", "case": CASE, "case_numbers": ["（2026）沪0115民初1号"], "documents": DOCS,
            "match": {"level": level, "basis": "官方案号"},
            "plan": {"hearing": ["2026-12-01 09:30 第一法庭"],
                     "fees": [{"amount": 500, "deadline": "2026-12-10", "payee": "某法院", "account": "6222000011112222"}]}, **extra}


def done():
    return {"status": "已收文", "case": CASE, "case_numbers": ["（2026）沪0115民初1号"], "documents": DOCS,
            "received": [{"name": "传票", "attachment_id": 10, "skipped": False}], "hearing": {"status": "已回填", "hearing": "2026-12-01 09:30 第一法庭"},
            "fees": [{"status": "待确认", "amount": 500, "deadline": "2026-12-10", "account": "6222000011112222"}]}


def sms(message_id="m1", sender="ding-lawyer", text=SMS, group=GROUP_ID, kind="2"):
    return BotMessage(message_id=message_id, conversation_type=kind, conversation_id=group, conversation_title=GROUP, text=text, sender_id=sender, sender_nick="律师甲")


class FakeApi:
    def __init__(self, *results):
        self.results, self.calls = list(results), []

    async def __call__(self, username, path, body):
        self.calls.append((username, path, body))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class ReceiptBotTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="lawyer", display_name="律师甲", department="诉讼部", password_hash="x", role="user", is_active=True,
                     profile={"dingtalk_user_id": "ding-lawyer"}, must_change_password=False),
                User(username="helper", display_name="助理乙", department="诉讼部", password_hash="x", role="user", is_active=True,
                     profile={"dingtalk_user_id": "ding-helper"}, must_change_password=False),
                User(username="helper2", display_name="助理丙", department="诉讼部", password_hash="x", role="user", is_active=True,
                     profile={}, must_change_password=False),
                User(username="stopped", display_name="停用", department="诉讼部", password_hash="x", role="user", is_active=False,
                     profile={"dingtalk_user_id": "ding-stopped"}, must_change_password=False),
                User(username="outer", display_name="外部", department="外部", password_hash="x", role="user", is_active=True,
                     profile={"dingtalk_user_id": "ding-outer", "permission_role": "合作律师"}, must_change_password=False),
                BusinessRecord(id=7, module="case", serial_no="HZMS1", title="某案", customer="", status="办理中", owner="lawyer", department="",
                               description="", data={"assistants": ["助理乙", "助理丙"], "assistant_usernames": ["helper", "helper2"]}),
            ])
            await db.commit()

        # 全所检索在 sqlite 里匹配不了中文（JSON 按转义存储），这里按用例给结果；真实库的查询另行只读核对过。
        self.firm_ids = [7]

        async def firm_match(numbers, plaintiffs, defendants, identity, db):
            return {"records": [SimpleNamespace(id=item) for item in self.firm_ids], "level": "", "basis": "", "tried": []}
        firm_patch = patch("app.areas.aws.court_intake._match_case", firm_match)
        firm_patch.start()
        self.addCleanup(firm_patch.stop)

    async def asyncTearDown(self):
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def _waiting_id(self, owner="lawyer"):
        records = [record for record in await self._records() if record.status == "待确认" and record.owner == owner]
        return records[-1].id

    async def _run(self, message, api, config=CONFIG, agent_turn=None):
        async with self.sessions() as db:
            return await handle_message(message, config, api=api, db=db, agent_turn=agent_turn)

    async def _records(self):
        async with self.sessions() as db:
            return (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "court_group_receipt").order_by(BusinessRecord.id))).all()

    async def test_unbound_stopped_and_external_are_refused_without_calling_api(self):
        api = FakeApi()
        for sender, words in (("ding-nobody", "还没绑定钉钉"), ("ding-stopped", "还没绑定钉钉"), ("ding-outer", "外部账号")):
            reply = await self._run(sms(sender=sender), api)
            self.assertIn(words, reply.text)
            self.assertEqual(reply.at_user_ids, [sender])
        self.assertEqual(api.calls, [])
        self.assertEqual(await self._records(), [])

    async def test_other_group_ignored_and_direct_chat_points_to_group(self):
        api = FakeApi()
        self.assertIsNone(await self._run(sms(group="cid-other-same-name"), api))
        self.assertIsNone(await self._run(sms(), api, BotSettings(group_id="", use_cloud_agent=False, auto_save_unique=False)))
        self.assertIn("收文群", (await self._run(sms(kind="1"), api)).text)
        self.assertEqual(api.calls, [])

    async def test_preview_then_confirm_saves_as_sender_and_tells_assistants(self):
        api = FakeApi(preview(), done())
        first = await self._run(sms(), api)
        self.assertEqual(api.calls[0], ("lawyer", "/documents/court-service/bot-receipts/intake", {"link": LINK}))
        self.assertIn("回复“确认 ", first.text)
        self.assertEqual(len(api.calls), 1)
        self.assertEqual((await self._records())[0].status, "待确认")
        second = await self._run(sms(message_id="m2", text=f"确认 {await self._waiting_id()}"), api)
        self.assertEqual(api.calls[1], ("lawyer", "/documents/court-service/bot-receipts/intake", {"link": LINK, "case_id": 7, "confirm": True}))
        self.assertEqual(second.at_user_ids, ["ding-lawyer", "ding-helper"])
        for words in ("HZMS1", "（2026）沪0115民初1号", "甲公司", "乙公司", "传票", "2026-12-01", "500", "2026-12-10", "已存入", "助理丙", "?page=documents-official"):
            self.assertIn(words, second.text)
        self.assertEqual((await self._records())[0].status, "已导入")

    async def test_group_text_never_shows_account_phone_or_body(self):
        api = FakeApi(preview(), done())
        first = await self._run(sms(), api)
        for reply in (first, await self._run(sms(message_id="m2", text=f"确认 {await self._waiting_id()}"), api)):
            self.assertNotIn("6222000011112222", reply.text)
            self.assertNotIn("13900000000", reply.text)

    async def _set_case(self, **data):
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, 7)
            case.data = {**case.data, **data}
            await db.commit()

    async def test_switch_off_always_asks_even_when_unique(self):
        await self._set_case(court_case_no=NUMBER)
        api = FakeApi(preview())
        self.assertIn("回复“确认 ", (await self._run(sms(), api)).text)
        self.assertEqual(len(api.calls), 1)

    async def test_unique_court_number_saves_directly_with_undo_hint(self):
        await self._set_case(court_case_no=NUMBER)
        api = FakeApi(preview(), done())
        reply = await self._run(sms(), api, AUTO)
        for words in ("收文完成", "匹配依据", "存错了"):
            self.assertIn(words, reply.text)
        self.assertEqual(api.calls[1][2], {"link": LINK, "case_id": 7, "confirm": True})
        record = (await self._records())[0]
        self.assertEqual((record.status, record.data["auto_saved"]), ("已导入", True))

    async def test_court_number_must_be_registered_on_the_case(self):
        await self._set_case(remark=NUMBER, court_case_no="（2025）沪0115民初9号")
        reply = await self._run(sms(), FakeApi(preview()), AUTO)
        await self._assert_not_auto(reply, "法院案号与该案登记的不一致")

    async def test_two_numbers_on_documents_are_not_unique(self):
        await self._set_case(court_case_no=NUMBER)
        reply = await self._run(sms(), FakeApi(preview(case_numbers=[NUMBER, "（2026）沪0115民初2号"])), AUTO)
        await self._assert_not_auto(reply, "文书上有多个法院案号")

    async def _assert_not_auto(self, reply, reason):
        """没直接存：群里只说请核对，具体原因只存记录（全所还有别的案件这种话不能进群）。"""
        self.assertIn("回复“确认 ", reply.text)
        self.assertNotIn("收文完成", reply.text)
        self.assertNotIn(reason, reply.text)
        records = await self._records()
        self.assertEqual(records[-1].data["not_auto_reason"], reason)

    async def _party_case(self, **change):
        await self._set_case(**{**dict(plaintiff=P, opponent=D, court=COURT), **change})

    def _party(self, **extra):
        return preview(**{**dict(level="第二级 当事人+机关反查", case_numbers=[], court=COURT, documents=PARTY_DOCS), **extra})

    async def test_party_match_saves_when_all_match(self):
        await self._party_case()
        self.assertIn("收文完成", (await self._run(sms(), FakeApi(self._party(case_numbers=[NUMBER]), done()), AUTO)).text)

    async def test_party_mismatch_is_not_unique(self):
        for index, (change, reason) in enumerate(((dict(plaintiff="广州甲方科技有限公司"), "原告、被告没有全部对上"),
                                                  (dict(opponent="成都丁方有限公司"), "原告、被告没有全部对上"),
                                                  (dict(court="别的法院"), "受理法院与该案登记的不一致"))):
            await self._party_case(**change)
            reply = await self._run(sms(message_id=f"p{index}"), FakeApi(self._party()), AUTO)
            await self._assert_not_auto(reply, reason)

    async def test_party_name_is_not_substring(self):
        await self._party_case(plaintiff="张三丰贸易有限公司", opponent="李四光建材有限公司")
        docs = [{"attachment_id": 9, "name": "传票", "fields": {"文书类型": "传票", "原告": ["张三"], "被告": ["李四"]}}]
        await self._assert_not_auto(await self._run(sms(), FakeApi(self._party(documents=docs)), AUTO), "原告、被告没有全部对上")

    async def test_all_document_parties_must_match(self):
        await self._party_case()
        docs = [{"attachment_id": 9, "name": "传票", "fields": {"文书类型": "传票", "原告": [P, "另一原告有限公司"], "被告": [D]}}]
        await self._assert_not_auto(await self._run(sms(), FakeApi(self._party(documents=docs)), AUTO), "原告、被告没有全部对上")

    async def test_same_parties_new_lawsuit_goes_to_confirm(self):
        await self._party_case(first_court_case_no="（2025）沪0115民初9号")
        reply = await self._run(sms(), FakeApi(self._party(case_numbers=[NUMBER])), AUTO)
        await self._assert_not_auto(reply, "法院案号与该案登记的不一致")

    async def test_other_instance_number_does_not_block_party_match(self):
        await self._party_case(first_court_case_no="（2025）沪0115民初9号")
        reply = await self._run(sms(), FakeApi(self._party(case_numbers=["（2026）沪01民终5号"]), done()), AUTO)
        self.assertIn("收文完成", reply.text)

    async def test_case_invisible_to_sender_blocks_direct_save_without_telling_group(self):
        await self._party_case()
        self.firm_ids = [7, 8]
        reply = await self._run(sms(), FakeApi(self._party(case_numbers=[NUMBER])), AUTO)
        await self._assert_not_auto(reply, "全所不止这一个案件符合")
        self.assertNotIn("全所", reply.text)

    async def test_reply_and_record_list_what_was_written(self):
        await self._set_case(court_case_no=NUMBER)
        result = done()
        result.update(hearing={"status": "已有开庭未覆盖", "hearing": "2026-11-30 09:30 第一庭", "previous": "2026-12-20T09:00:00 第九庭"},
                      court_staff={"status": "已回填", "filled": ["承办法官 王法官"]},
                      fees=[{"status": "待确认", "fee_id": 31, "serial_no": "FY1", "amount": 500}],
                      received=[{"attachment_id": 10, "receipt_id": 20, "skipped": False}])
        reply = await self._run(sms(), FakeApi(preview(), result), AUTO)
        for words in ("系统已登记开庭 2026-12-20 09:00 第九庭", "未覆盖", "承办法官 王法官", "FY1", "费用草稿到费用单"):
            self.assertIn(words, reply.text)
        changes = (await self._records())[0].data["changes"]
        self.assertEqual((changes["attachment_ids"], changes["receipt_ids"], changes["fee_ids"]), ([10], [20], [31]))
        self.assertEqual(changes["staff_filled"], ["承办法官 王法官"])
        self.assertEqual(changes["hearing"]["previous"], "2026-12-20T09:00:00 第九庭")

    async def test_partial_failure_is_reported_not_called_unfinished(self):
        await self._set_case(court_case_no=NUMBER)
        result = done()
        result.update(hearing={"status": "失败", "step": "开庭回填", "detail": "没有法院信息修改权限"})
        reply = await self._run(sms(), FakeApi(preview(), result), AUTO)
        for words in ("收文完成", "已存入", "开庭回填失败：没有法院信息修改权限"):
            self.assertIn(words, reply.text)

    async def test_double_confirm_saves_once(self):
        calls = []

        async def api(username, path, body):
            calls.append(body.get("confirm"))
            if body.get("confirm"):
                await asyncio.sleep(0.05)
                return done()
            return preview()
        await self._run(sms(), api)
        code = await self._waiting_id()
        first, second = await asyncio.gather(self._run(sms(message_id="m2", text=f"确认 {code}"), api), self._run(sms(message_id="m3", text=f"确认 {code}"), api))
        self.assertEqual(sum(1 for item in calls if item), 1)
        self.assertEqual(sorted(("收文完成" in first.text, "收文完成" in second.text)), [False, True])

    async def test_two_lawyers_same_case_run_one_at_a_time(self):
        running, peak = [0], [0]

        async def api(username, path, body):
            if not body.get("confirm"):
                return preview()
            running[0] += 1
            peak[0] = max(peak[0], running[0])
            await asyncio.sleep(0.05)
            running[0] -= 1
            return done()
        await self._run(sms(), api)
        await self._run(sms(message_id="b1", sender="ding-helper"), api)
        lawyer, helper = await self._waiting_id(), await self._waiting_id("helper")
        await asyncio.gather(self._run(sms(message_id="m2", text=f"确认 {lawyer}"), api), self._run(sms(message_id="b2", sender="ding-helper", text=f"确认 {helper}"), api))
        self.assertEqual(peak[0], 1)

    async def test_uncertain_result_says_do_not_resend(self):
        reply_api = FakeApi(preview(), ApiError(504, "系统处理超时，结果不确定"))
        await self._run(sms(), reply_api)
        reply = await self._run(sms(message_id="m2", text=f"确认 {await self._waiting_id()}"), reply_api)
        self.assertIn("不要重发", reply.text)
        self.assertEqual((await self._records())[0].status, "待处理")

    async def test_several_messages_each_confirmed_by_number(self):
        api = FakeApi(preview(), preview(), done(), done())
        await self._run(sms(), api)
        second_link = LINK.replace("7f184b3f", "8f184b3f")
        await self._run(sms(message_id="m2", text=f"【某人民法院】 {second_link}"), api)
        first, second = await self._records()
        self.assertEqual((first.status, second.status), ("待确认", "待确认"))
        await self._run(sms(message_id="m3", text=f"确认 {first.id}"), api)
        self.assertEqual(api.calls[-1][2]["link"], LINK)
        await self._run(sms(message_id="m4", text=f"确认 {second.id}"), api)
        self.assertEqual(api.calls[-1][2]["link"], second_link)
        self.assertEqual([record.status for record in await self._records()], ["已导入", "已导入"])

    async def test_first_level_without_document_number_is_not_unique(self):
        await self._set_case(court_case_no=NUMBER)
        reply = await self._run(sms(), FakeApi(preview(case_numbers=[])), AUTO)
        await self._assert_not_auto(reply, "文书上没有识别出法院案号")

    async def test_pending_assign_success_records_changes_then_refuses_repeat(self):
        api = FakeApi(ApiError(502, "法院接口失败"))
        await self._run(sms(), api)
        record = (await self._records())[0]

        async def _db():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[current_identity] = lambda: {"username": "admin", "display_name": "管理者", "role": "admin", "role_ids": ["admin"],
                                                              "_actual_role_ids": ["admin"], "_actual_role": "admin", "department": "", "action_keys": ["*"], "menu_keys": ["documents-official"]}
        result = done()
        result["fees"] = [{"status": "待确认", "fee_id": 31, "serial_no": "FY1"}]
        intake = AsyncMock(return_value=result)
        url = f"{settings.api_prefix}/documents/court-service/bot-receipts/{record.id}/assign"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://bot.test") as client:
            with patch("app.areas.aws.court_intake.intake_court_service", intake):
                first = await client.post(url, json={"case_no": "HZMS1"})
                again = await client.post(url, json={"case_no": "HZMS1"})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["status"], "已导入")
        self.assertEqual(again.status_code, 409)
        self.assertIn("状态为“已导入”", again.text)
        body = intake.await_args.args[0]
        self.assertEqual((body.link, body.case_id, body.confirm), (LINK, 7, True))
        changes = (await self._records())[0].data["changes"]
        self.assertEqual((changes["attachment_ids"], changes["fee_ids"]), ([10], [31]))

    async def _client_as(self, identity):
        async def _db():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[current_identity] = lambda: identity
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://bot.test")

    async def test_external_accounts_refused_on_all_bot_routes(self):
        await self._run(sms(text="【某某人民法院】请到本院领取文书"), FakeApi())
        record = (await self._records())[0]
        outer = {"username": "outer", "display_name": "外部", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["user"], "_actual_role": "user",
                 "permission_role": "合作律师", "department": "", "action_keys": ["*"], "menu_keys": ["documents-official"]}
        base = settings.api_prefix + "/documents/court-service/bot-receipts"
        async with await self._client_as(outer) as client:
            self.assertEqual((await client.get(base)).status_code, 403)
            self.assertEqual((await client.post(f"{base}/{record.id}/assign", json={"case_no": "HZMS1"})).status_code, 403)
            self.assertEqual((await client.post(f"{base}/{record.id}/close", json={})).status_code, 403)
            self.assertEqual((await client.post(f"{base}/intake", json={"link": LINK})).status_code, 403)
        self.assertEqual((await self._records())[0].status, "待处理")

    async def test_bot_route_saves_directly_public_route_does_not(self):
        admin = {"username": "admin", "display_name": "管理者", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"], "_actual_role": "admin",
                 "department": "", "action_keys": ["*"], "menu_keys": ["documents-official"]}
        run = AsyncMock(return_value={"status": "待确认入库"})
        async with await self._client_as(admin) as client:
            with patch("app.areas.aws.court_intake.run_intake", run):
                await client.post(settings.api_prefix + "/documents/court-service/bot-receipts/intake", json={"link": LINK})
                self.assertTrue(run.await_args.kwargs["direct_save"])
                refused = await client.post(settings.api_prefix + "/documents/court-service/intake", json={"link": LINK, "direct_save": True})
                self.assertEqual(refused.status_code, 422)
                await client.post(settings.api_prefix + "/documents/court-service/intake", json={"link": LINK})
                self.assertFalse(run.await_args.kwargs.get("direct_save", False))

    def test_tool_catalog_has_no_direct_save(self):
        from app.agent_mcp.catalog import get_catalog
        for tool in get_catalog(app).tools:
            self.assertNotIn("direct_save", str(getattr(tool, "input_schema", "")), getattr(tool, "name", ""))

    async def test_firm_check_finds_same_number_stored_with_spaces(self):
        await self._set_case(court_case_no=NUMBER)
        async with self.sessions() as db:
            db.add(BusinessRecord(id=8, module="case", serial_no="HZMS2", title="另案", customer="", status="办理中", owner="other", department="", description="",
                                  data={"first_court_case_no": "（2026）沪 0115 民初 1 号"}))
            await db.commit()
        await self._assert_not_auto(await self._run(sms(), FakeApi(preview()), AUTO), "全所不止这一个案件符合")

    async def test_party_match_accepts_registered_court_code(self):
        await self._party_case(court="沪0115")
        reply = await self._run(sms(), FakeApi(self._party(case_numbers=[NUMBER]), done()), AUTO)
        self.assertIn("收文完成", reply.text)

    async def test_non_standard_court_code_is_not_a_match(self):
        """徐知、沪仲、宁知这类非标准代字，即使和案件登记的一样，也不算法院一致（陶威 11-07）。"""
        for index, code in enumerate(("徐知", "沪仲", "宁知")):
            number = f"（2026）{code}民初1号"
            await self._party_case(court=code)
            reply = await self._run(sms(message_id=f"c{index}"), FakeApi(self._party(case_numbers=[number], court="")), AUTO)
            await self._assert_not_auto(reply, "受理法院与该案登记的不一致")

    def test_standard_court_code_shape(self):
        from app.areas.aws.receipt_bot import standard_court_code
        for code in ("皖1226", "沪0110", "苏0281", "京73", "兵0101"):
            self.assertEqual(standard_court_code(code), code)
        for code in ("徐知", "沪仲", "宁知", "0009", "沪01101", "上海"):
            self.assertEqual(standard_court_code(code), "")

    async def test_closed_or_archived_case_is_not_saved_directly(self):
        """已结、已归档的案件不直接存，转确认（陶威 11-07）。"""
        await self._set_case(court_case_no=NUMBER)
        cases = ((dict(status="已归档"), {}), (dict(status="一审判决结案"), {}), (dict(status="执行终本"), {}),
                 (dict(status="归档审核"), {}), (dict(status="一审待客户回款"), dict(case_closed_at="2026-10-01")))
        for index, (column, data) in enumerate(cases):
            async with self.sessions() as db:
                case = await db.get(BusinessRecord, 7)
                case.status = column["status"]
                case.data = {**case.data, **data}
                await db.commit()
            reply = await self._run(sms(message_id=f"e{index}"), FakeApi(preview()), AUTO)
            await self._assert_not_auto(reply, "案件已结案或已归档")

    async def test_truncation_flag_does_not_block_registered_number_match(self):
        """法院案号直配不看当事人名称，标了可能截短也照常直接存。"""
        await self._set_case(court_case_no=NUMBER)
        docs = [{"attachment_id": 9, "name": "传票", "fields": {"文书类型": "传票", "当事人可能截短": ["某公司"]}}]
        self.assertIn("收文完成", (await self._run(sms(), FakeApi(preview(documents=docs), done()), AUTO)).text)

    async def test_truncated_party_names_are_not_saved_directly(self):
        """解析标出“当事人可能截短”的，哪怕截短后的名字和案件对得上，也不直接存。"""
        await self._party_case(opponent="漳州锦客隆贸易有限公司")
        docs = [{"attachment_id": 9, "name": "传票", "fields": {"文书类型": "传票", "原告": [P], "被告": ["漳州锦客隆贸易有限公司"],
                                                                "受理机关": COURT, "当事人可能截短": ["漳州锦客隆贸易有限公司"]}}]
        reply = await self._run(sms(), FakeApi(self._party(case_numbers=[NUMBER], documents=docs)), AUTO)
        await self._assert_not_auto(reply, "当事人名称可能识别不全")

    def test_party_names_keep_full_company_and_branch(self):
        from app.agent_skill_packages.court_doc_intake.scripts.extract_doc_fields import extract
        # 句式写法取到的名称完整了，但分不清名称在哪结束，仍标为可能不全（不用来直接存）；冒号写法可信。
        cases = (
            ("原告青岛万盛联有限公司诉被告广州逸达酒店有限公司侵害商标权纠纷一案", ["青岛万盛联有限公司"], ["广州逸达酒店有限公司"], True),
            ("原告甲贸易有限公司诉被告漳州锦客隆贸易有限公司霞美分公司侵害商标权纠纷一案", ["甲贸易有限公司"], ["漳州锦客隆贸易有限公司霞美分公司"], True),
            ("原告甲贸易有限公司诉被告上海某某百货店（个体工商户）侵害商标权纠纷一案", ["甲贸易有限公司"], ["上海某某百货店（个体工商户）"], True),
            ("原告：某某（上海）有限公司\n被告：乙商行（个体工商户）\n法定代表人：张三", ["某某（上海）有限公司"], ["乙商行（个体工商户）"], False),
            ("原告：甲有限公司（以下简称甲公司）\n被告：张三，男", ["甲有限公司"], ["张三"], False),
        )
        for text, plaintiffs, defendants, sentence in cases:
            fields = extract(text, "传票.pdf")
            self.assertEqual((fields["原告"], fields["被告"]), (plaintiffs, defendants), text)
            self.assertEqual(fields["当事人可能截短"], [*plaintiffs, *defendants] if sentence else [], text)

    def test_sentence_form_still_reads_parties_for_web_intake(self):
        """网页一键收文要显示当事人：被告带（个人独资）或后面接数字的，也要取到原告和被告（都标为可能不全）。"""
        from app.agent_skill_packages.court_doc_intake.scripts.extract_doc_fields import extract
        for text, defendant in (("原告甲贸易有限公司诉被告某某眼镜店（个人独资）侵害商标权纠纷一案", "某某眼镜店（个人独资）"),
                                ("原告甲贸易有限公司诉被告正品建材店0738侵害商标权纠纷一案", "正品建材店")):
            fields = extract(text, "传票.pdf")
            self.assertEqual((fields["原告"], fields["被告"]), (["甲贸易有限公司"], [defendant]), text)
            self.assertIn(defendant, fields["当事人可能截短"])

    def test_core_names_drop_form_note_in_both_bracket_widths(self):
        from app.areas.aws.court_intake import _core_names
        self.assertEqual(_core_names("乙商行（个体工商户）"), ["乙商行"])
        self.assertEqual(_core_names("乙商行(个体工商户)"), ["乙商行"])
        self.assertEqual(_core_names("某某眼镜店（个人独资）"), ["某某眼镜店"])

    def test_name_cut_by_line_break_is_flagged(self):
        from app.agent_skill_packages.court_doc_intake.scripts.extract_doc_fields import extract, truncated_parties
        self.assertEqual(extract("原告：上海某某贸易有\n限公司\n被告：李四", "传票.pdf")["当事人可能截短"], ["上海某某贸易有"])
        self.assertEqual(extract("原告甲贸易有限公司诉被告广州颜佳宜生物科技有限公司实力供应商侵害商标权纠纷一案", "传票.pdf")["当事人可能截短"],
                         ["甲贸易有限公司", "广州颜佳宜生物科技有限公司"])
        self.assertEqual(truncated_parties("被告漳州锦客隆贸易有限公司霞美分公司", ["漳州锦客隆贸易有限公司"]), ["漳州锦客隆贸易有限公司"])
        self.assertEqual(truncated_parties("被告广州逸达酒店有限公司", ["广州逸达酒店"]), ["广州逸达酒店"])

    def test_case_attachment_date_uses_beijing_time(self):
        from datetime import datetime, timezone
        from app.areas.aws.receipt_sources import _case_attachment_row
        attachment = SimpleNamespace(id=1, created_at=datetime(2026, 11, 6, 23, 30, tzinfo=timezone.utc), original_name="传票", uploader="u", remark="")
        case = BusinessRecord(id=7, module="case", serial_no="H", customer="", data={})
        self.assertEqual(_case_attachment_row(attachment, case)["data"]["uploaded_at"], "2026-11-07")

    async def test_document_without_number_always_asks(self):
        await self._party_case()
        await self._assert_not_auto(await self._run(sms(), FakeApi(self._party()), AUTO), "文书上没有识别出法院案号")

    async def test_expired_waiting_moves_to_pending_without_reply(self):
        await self._run(sms(), FakeApi(preview()))
        async with self.sessions() as db:
            self.assertEqual(await expire_waiting(db), 0)
            record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "court_group_receipt"))
            record.data = {**record.data, "expires_at": "2020-01-01T00:00:00+00:00"}
            await db.commit()
            self.assertEqual(await expire_waiting(db), 1)
        self.assertEqual((await self._records())[0].data["reason"], "超时未确认")

    async def test_stuck_saving_moves_to_pending(self):
        await self._run(sms(), FakeApi(preview()))
        async with self.sessions() as db:
            record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "court_group_receipt"))
            record.status = "入库中"
            record.data = {**record.data, "saving_at": "2020-01-01T00:00:00+00:00"}
            await db.commit()
            self.assertEqual(await expire_waiting(db), 1)
        self.assertEqual((await self._records())[0].status, "待处理")

    async def test_superscript_digit_does_not_crash(self):
        reply = await self._run(sms(message_id="m1", text="²"), FakeApi())
        self.assertIn("转发法院送达短信", reply.text)

    async def test_save_failure_after_auto_goes_to_pending_without_undo_hint(self):
        await self._set_case(court_case_no=NUMBER)
        reply = await self._run(sms(), FakeApi(preview(), ApiError(409, "案件已进入归档流程，不能上传案件文档")), AUTO)
        self.assertIn("待处理", reply.text)
        self.assertNotIn("存错了", reply.text)
        self.assertEqual((await self._records())[0].status, "待处理")

    async def test_several_candidates_pick_by_number(self):
        report = {"status": "需要选择案件", "documents": DOCS, "match": {"candidates": [
            {"case_id": 7, "serial_no": "HZMS1", "title": "某案"}, {"case_id": 8, "serial_no": "HZMS2", "title": "另案"}]}}
        api = FakeApi(report, done())
        self.assertIn("2. HZMS2", (await self._run(sms(), api)).text)
        code = await self._waiting_id()
        self.assertIn(str(code), (await self._run(sms(message_id="m1b", text="1"), api)).text)
        self.assertEqual(len(api.calls), 1)
        self.assertIn("序号", (await self._run(sms(message_id="m2", text=f"确认 {code} 9"), api)).text)
        await self._run(sms(message_id="m3", text=f"确认 {code} 1"), api)
        self.assertEqual(api.calls[-1][2], {"link": LINK, "case_id": 7, "confirm": True})

    async def test_unmatched_and_failures_go_to_pending(self):
        api = FakeApi({"status": "系统内未登记该案", "documents": DOCS, "match": {"candidates": []}})
        reply = await self._run(sms(), api)
        self.assertIn("系统里没找到这个案号对应的案件（只在你能看到的案件里找）", reply.text)
        self.assertNotIn("有权限的案件", reply.text)
        self.assertEqual((await self._records())[0].status, "待处理")
        api = FakeApi(ApiError(502, "法院送达接口暂时无法访问"))
        reply = await self._run(sms(message_id="m2"), api)
        self.assertIn("法院送达接口暂时无法访问", reply.text)
        self.assertEqual((await self._records())[1].status, "待处理")

    async def test_no_service_link_goes_to_pending_and_chat_gets_help(self):
        api = FakeApi()
        reply = await self._run(sms(text="【某某人民法院】请到本院领取文书"), api)
        self.assertIn("待处理", reply.text)
        self.assertEqual((await self._records())[0].status, "待处理")
        reply = await self._run(sms(message_id="m2", text="你好"), api)
        self.assertIn("转发法院送达短信", reply.text)
        self.assertEqual(len(await self._records()), 1)

    async def test_same_message_only_processed_once(self):
        api = FakeApi(preview())
        await self._run(sms(), api)
        self.assertIsNone(await self._run(sms(), api))
        self.assertEqual(len(api.calls), 1)
        self.assertEqual(len(await self._records()), 1)

    async def test_cancel_and_expired_and_nothing_waiting(self):
        api = FakeApi(preview(), preview())
        self.assertIn("没有等你确认", (await self._run(sms(message_id="m0", text="确认"), api)).text)
        await self._run(sms(), api)
        self.assertIn("已取消", (await self._run(sms(message_id="m2", text=f"取消 {await self._waiting_id()}"), api)).text)
        self.assertEqual((await self._records())[0].status, "已取消")
        await self._run(sms(message_id="m3"), api)
        async with self.sessions() as db:
            record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "court_group_receipt", BusinessRecord.status == "待确认"))
            record.data = {**record.data, "expires_at": "2020-01-01T00:00:00+00:00"}
            await db.commit()
        self.assertIn("超过", (await self._run(sms(message_id="m4", text=f"确认 {record.id}"), api)).text)
        self.assertEqual((await self._records())[1].status, "待处理")

    async def test_court_number_line_only_when_really_filled(self):
        planned = preview()
        planned["plan"] = {**planned["plan"], "court_case_no": NUMBER}
        result = done()
        result["court_case_no"] = NUMBER
        reply = await self._run(sms(), api := FakeApi(planned, result))
        reply = await self._run(sms(message_id="m2", text=f"确认 {await self._waiting_id()}"), api)
        self.assertIn(f"已回填法院案号 {NUMBER}", reply.text)
        self.assertEqual((await self._records())[0].data["changes"]["court_no_filled"], NUMBER)
        result = done()
        result.update(court_case_no=NUMBER, received=[{"attachment_id": 10, "skipped": True}])
        api = FakeApi(planned, result)
        await self._run(sms(message_id="m3"), api)
        reply = await self._run(sms(message_id="m4", text=f"确认 {await self._waiting_id()}"), api)
        self.assertNotIn("已回填法院案号", reply.text)
        self.assertEqual((await self._records())[1].data["changes"]["court_no_filled"], "")

    async def test_oversized_number_is_refused_not_an_error(self):
        api = FakeApi(preview())
        await self._run(sms(), api)
        reply = await self._run(sms(message_id="m2", text="确认 999999999999"), api)
        self.assertIn("没有等你确认", reply.text)
        self.assertEqual(len(api.calls), 1)

    async def test_cancel_and_confirm_race_only_one_wins(self):
        release = asyncio.Event()

        async def api(username, path, body):
            if body.get("confirm"):
                await release.wait()
                return done()
            return preview()
        await self._run(sms(), api)
        code = await self._waiting_id()
        saving = asyncio.create_task(self._run(sms(message_id="m2", text=f"确认 {code}"), api))
        await asyncio.sleep(0.05)
        cancelled = await self._run(sms(message_id="m3", text=f"取消 {code}"), api)
        self.assertNotIn("已取消", cancelled.text)
        release.set()
        self.assertIn("收文完成", (await saving).text)
        self.assertEqual((await self._records())[0].status, "已导入")

    async def test_sweep_runs_while_connection_keeps_failing(self):
        from app import dingtalk_receipt_worker as module
        from app.areas.agent_admin.dingtalk_bots import BotConfig
        attempts, sweeps = [0], [0]
        real_sleep = asyncio.sleep

        class Session:
            async def __aenter__(self):
                return None

            async def __aexit__(self, *args):
                return False

        async def load(db):
            return BotConfig(True, "k", "s", GROUP_ID, False, False)

        async def fail(self, key, secret):
            attempts[0] += 1
            raise RuntimeError("connect failed")

        async def sweep():
            sweeps[0] += 1

        async def sleep(seconds):
            await real_sleep(10 if seconds == module.RECHECK_SECONDS else 0)
        with patch.object(module, "SessionLocal", Session), patch.object(module, "load_bot", load), patch.object(module.Worker, "connect", fail), \
                patch.object(module, "_sweep", sweep), patch.object(module.asyncio, "sleep", sleep), \
                patch.object(module, "_package_version", lambda: "v1" if attempts[0] < 5 else "v2"):
            await asyncio.wait_for(module.main(), 10)
        self.assertEqual(sweeps[0], attempts[0])

    def test_reconnect_backs_off_and_resets(self):
        from app.dingtalk_receipt_worker import RECONNECT_MAX_SECONDS, RECONNECT_MIN_SECONDS, next_reconnect_delay
        delay = RECONNECT_MIN_SECONDS
        delays = []
        for _ in range(8):
            delay = next_reconnect_delay(delay, 0.1)
            delays.append(delay)
        self.assertEqual(delays[0], RECONNECT_MIN_SECONDS * 2)
        self.assertEqual(delays[-1], RECONNECT_MAX_SECONDS)
        self.assertEqual(next_reconnect_delay(RECONNECT_MAX_SECONDS, 600), RECONNECT_MIN_SECONDS)

    async def test_auto_save_crash_before_claim_is_swept(self):
        await self._set_case(court_case_no=NUMBER)

        async def boom(*args, **kwargs):
            raise RuntimeError("crash")
        with patch("app.areas.aws.receipt_bot._save", boom):
            with self.assertRaises(RuntimeError):
                await self._run(sms(), FakeApi(preview()), AUTO)
        record = (await self._records())[0]
        self.assertEqual(record.status, "待确认")
        self.assertTrue(record.data["expires_at"])

    async def test_confirm_without_number_never_saves(self):
        api = FakeApi(preview())
        await self._run(sms(), api)
        code = await self._waiting_id()
        for index, text in enumerate(("确认", "取消", "1")):
            reply = await self._run(sms(message_id=f"n{index}", text=text), api)
            self.assertIn(str(code), reply.text)
        self.assertEqual(len(api.calls), 1)
        self.assertEqual((await self._records())[0].status, "待确认")

    async def test_one_person_cannot_confirm_for_another(self):
        api = FakeApi(preview())
        await self._run(sms(), api)
        reply = await self._run(sms(message_id="m2", sender="ding-helper", text=f"确认 {await self._waiting_id()}"), api)
        self.assertIn("没有等你确认", reply.text)
        self.assertEqual((await self._records())[0].status, "待确认")
        self.assertEqual(len(api.calls), 1)

    async def test_cloud_agent_runs_only_when_on_and_failure_does_not_block(self):
        turns = []

        async def turn(username, text):
            turns.append(username)
            raise RuntimeError("cloud down")
        await self._run(sms(), FakeApi(preview()), agent_turn=turn)
        self.assertEqual(turns, [])
        config = BotSettings(group_id=GROUP_ID, use_cloud_agent=True, auto_save_unique=False)
        reply = await self._run(sms(message_id="m2"), FakeApi(preview()), config, turn)
        self.assertEqual(turns, ["lawyer"])
        self.assertIn("回复“确认 ", reply.text)

    def _agent_server(self, first, created, calls, existing=None, fail=False):
        import json

        def handler(request):
            body = json.loads(request.content or b"{}")
            calls.append((request.method, request.url.path.split("/api/v1")[-1], body))
            if request.method == "GET":
                listing = dict(first)
                if existing:
                    listing["items"] = [*first["items"], existing]
                return httpx.Response(200, json=listing)
            if request.method == "PATCH":
                return httpx.Response(200, json=created)
            if request.url.path.endswith("/personal-agent/conversations"):
                return httpx.Response(200, json=created)
            if request.url.path.endswith("/personal-agent/messages"):
                if fail:
                    return httpx.Response(200, text='data: {"type": "error", "detail": "x"}\n\n')
                state = {"pending_actions": [{"id": "act-1", "status": "pending"}]}
                return httpx.Response(200, text=f"data: {json.dumps({'type': 'state', 'state': state})}\n\ndata: {json.dumps({'type': 'done'})}\n\n")
            return httpx.Response(200, json={})
        return httpx.MockTransport(handler)

    async def _real_snapshots(self):
        import tempfile
        from pathlib import Path
        from app.areas.personal_agent import conversations
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            first = await conversations.create_conversation(directory)  # 用户网页上原来选中的对话
            created = await conversations.create_conversation(directory)  # 真实的新建对话返回结构
        return first, created

    async def test_first_time_creates_fixed_conversation_and_restores_selection(self):
        from app import dingtalk_receipt_worker as module
        first, created = await self._real_snapshots()
        previous, new_id = first["active_id"], created["active_id"]
        self.assertNotIn("conversation_id", created)  # 接口返回里没有这个字段，取它会得到空值
        self.assertEqual(module.conversation_id_of(created), new_id)
        calls = []
        with patch.object(module, "_token", AsyncMock(return_value="t")):
            await module.agent_turn("lawyer", "短信", transport=self._agent_server(first, created, calls))
        self.assertEqual([(m, p) for m, p, _ in calls], [
            ("GET", "/personal-agent/conversations"), ("POST", "/personal-agent/conversations"),
            ("PATCH", f"/personal-agent/conversations/{new_id}"), ("POST", f"/personal-agent/conversations/{previous}/select"),
            ("POST", "/personal-agent/messages"), ("POST", f"/personal-agent/conversations/{new_id}/actions/dismiss")])
        self.assertEqual(calls[2][2], {"title": "钉钉收文助手"})
        self.assertEqual(calls[4][2]["conversation_id"], new_id)

    async def test_later_messages_reuse_fixed_conversation_without_switching(self):
        from app import dingtalk_receipt_worker as module
        first, created = await self._real_snapshots()
        fixed = {"id": "fixed-1", "title": "钉钉收文助手", "skill_id": "court-doc-intake"}
        calls = []
        with patch.object(module, "_token", AsyncMock(return_value="t")):
            await module.agent_turn("lawyer", "短信", transport=self._agent_server(first, created, calls, existing=fixed))
        paths = [(m, p) for m, p, _ in calls]
        self.assertNotIn(("POST", "/personal-agent/conversations"), paths)
        self.assertFalse(any(p.endswith("/select") for _, p in paths))
        self.assertEqual(calls[1][2]["conversation_id"], "fixed-1")

    def test_fixed_conversation_rule(self):
        from app import dingtalk_receipt_worker as module
        items = [{"id": "a", "title": "钉钉收文助手", "skill_id": "general-office"},
                 {"id": "b", "title": "收文 （2026）沪1号", "skill_id": "court-doc-intake"},
                 {"id": "c", "title": "钉钉收文助手", "skill_id": ""}]
        self.assertEqual(module.fixed_conversation_of({"items": items}), "c")
        self.assertEqual(module.fixed_conversation_of({"items": items[:2]}), "")

    async def test_two_messages_at_once_create_only_one_fixed_conversation(self):
        from app import dingtalk_receipt_worker as module
        first, created = await self._real_snapshots()
        made = []
        state = {"fixed": None}
        import json

        async def slow_handler(request):
            body = json.loads(request.content or b"{}")
            path = request.url.path.split("/api/v1")[-1]
            if request.method == "GET":
                items = list(first["items"]) + ([state["fixed"]] if state["fixed"] else [])
                return httpx.Response(200, json={**first, "items": items})
            if request.method == "POST" and path == "/personal-agent/conversations":
                await asyncio.sleep(0.05)
                made.append(1)
                return httpx.Response(200, json=created)
            if request.method == "PATCH":
                state["fixed"] = {"id": created["active_id"], "title": body["title"], "skill_id": ""}
                return httpx.Response(200, json=created)
            if path == "/personal-agent/messages":
                return httpx.Response(200, text='data: {"type": "done"}\n\n')
            return httpx.Response(200, json={})

        class Async(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                await request.aread()
                return await slow_handler(request)
        with patch.object(module, "_token", AsyncMock(return_value="t")):
            await asyncio.gather(module.agent_turn("lawyer", "一", transport=Async()), module.agent_turn("lawyer", "二", transport=Async()))
        self.assertEqual(len(made), 1)

    async def test_agent_turn_failure_after_creation_keeps_selection_restored(self):
        from app import dingtalk_receipt_worker as module
        first, created = await self._real_snapshots()
        calls = []
        with patch.object(module, "_token", AsyncMock(return_value="t")), self.assertRaises(RuntimeError):
            await module.agent_turn("lawyer", "短信", transport=self._agent_server(first, created, calls, fail=True))
        self.assertIn(("POST", f"/personal-agent/conversations/{first['active_id']}/select"), [(m, p) for m, p, _ in calls])

    async def test_preview_lists_everything_that_will_be_written(self):
        report = preview()
        report["plan"] = {**report["plan"], "court_case_no": NUMBER, "receipts": ["HZMS1_传票.pdf"],
                          "hearing_plan": {"status": "将回填", "hearing": "2026-12-01 09:30 第一法庭", "also_filled": ["一审法院 某院"]},
                          "court_staff": {"display": ["一审承办法官 王法官", "一审书记员 李书记"]}}
        reply = await self._run(sms(), FakeApi(report))
        for words in ("确认后将：", "存入文书 1 份", f"回填法院案号 {NUMBER}", "回填开庭 2026-12-01 09:30 第一法庭", "回填一审法院 某院",
                      "回填一审承办法官 王法官、一审书记员 李书记", "缴费通知 500 元", "费用单要到系统里选合同后新建"):
            self.assertIn(words, reply.text)
        self.assertNotIn("生成费用草稿", reply.text)
        report["plan"] = {**report["plan"], "court_case_no": "已登记 X，不覆盖", "receipts": ["已收过，跳过：a.pdf"], "fees": [],
                          "hearing_plan": {"status": "已有开庭未覆盖", "hearing": "2026-12-01 09:30 第一法庭", "previous": "2026-12-20T09:00:00 第九庭"},
                          "court_staff": {"display": []}}
        reply = await self._run(sms(message_id="m9", text=SMS.replace("7f184b3f", "9f184b3f")), FakeApi(report))
        for words in ("1 份此前已收过，不重复存", "系统已登记开庭 2026-12-20 09:00 第九庭", "不覆盖"):
            self.assertIn(words, reply.text)
        self.assertNotIn("回填法院案号", reply.text)

    async def test_preview_hearing_matches_what_backfill_does(self):
        """预览和入库用同一套判断：分支 4 列出的几种情况，预览说什么，入库就做什么。"""
        from app.areas.aws import court_intake
        documents = [{"fields": {"开庭日期": "2026-11-30", "开庭时刻": "09:30", "开庭法庭": "第一庭"}}]
        cases = [
            ("再审案号审级不明", {}, "再审", "某院", "（2026）沪民再1号", False),
            ("执行案号审级不明", {}, "执行", "某院", "（2026）沪0115执1号", False),
            ("只登记了法庭", {"first_court_courtroom": "第九庭", "first_court_name": "某院"}, "一审", "某院", "案号", True),
            ("时间相同法庭空", {"first_court_hearing_date": "2026-11-30T09:30:00", "first_court_name": "某院"}, "一审", "某院", "案号", True),
            ("缺法院名称", {}, "一审", "", "案号", True),
            ("顺带回填法院和案号", {}, "一审", "某院", "（2026）沪0115民初1号", True),
            ("已登记不同时间", {"first_court_hearing_date": "2026-12-20T09:00:00", "first_court_name": "某院"}, "一审", "某院", "案号", True),
        ]
        for name, data, level, court, number, keep in cases:
            for keep_existing in ({keep, False} if name.startswith("只登记") else {keep}):
                plan = court_intake._hearing_plan(data, documents, level, court, number, keep_existing=keep_existing)
                record = BusinessRecord(id=1, module="case", serial_no="H", data=dict(data))
                update = AsyncMock()
                with patch("app.areas.legal.router.update_case_court_info", update):
                    done = await court_intake._backfill_hearing(record, documents, level, court, number, {"username": "u"}, None,
                                                                keep_existing=keep_existing)
                expected = "已回填" if plan["status"] == "将回填" else plan["status"]
                self.assertEqual(done["status"], expected, name)
                self.assertEqual(update.await_count, 1 if plan["status"] == "将回填" else 0, name)
                if plan["status"] == "将回填":
                    self.assertEqual(done["also_filled"], plan["also_filled"], name)
        added = court_intake._hearing_plan({}, documents, "一审", "某院", "（2026）沪0115民初1号", keep_existing=True)
        self.assertEqual(added["also_filled"], ["一审法院 某院", "一审案号 （2026）沪0115民初1号"])
        only_room = court_intake._hearing_plan({"first_court_courtroom": "第九庭", "first_court_name": "某院"}, documents, "一审", "某院", "案号", keep_existing=True)
        self.assertEqual(only_room["status"], "已有开庭未覆盖")
        empty_room = court_intake._hearing_plan({"first_court_hearing_date": "2026-11-30T09:30:00", "first_court_name": "某院"}, documents, "一审", "某院", "案号", keep_existing=True)
        self.assertEqual(empty_room["status"], "将回填")

    def test_parse_message_and_seen(self):
        message = parse_message({"msgId": "a", "conversationType": "2", "conversationTitle": GROUP, "senderStaffId": "s",
                                 "text": {"content": " 确认 "}, "senderNick": "n"})
        self.assertEqual((message.text, message.sender_id), ("确认", "s"))
        worker = Worker()
        self.assertTrue(worker.is_new("a"))
        self.assertFalse(worker.is_new("a"))

    async def test_direct_save_keeps_existing_hearing_web_path_still_updates(self):
        from app.areas.aws import court_intake
        case = BusinessRecord(id=1, module="case", serial_no="H", data={"first_court_hearing_date": "2026-12-20T09:00:00", "first_court_courtroom": "第九庭", "first_court_name": "某院"})
        documents = [{"fields": {"开庭日期": "2026-11-30", "开庭时刻": "09:30", "开庭法庭": "第一庭"}}]
        update = AsyncMock()
        with patch("app.areas.legal.router.update_case_court_info", update):
            kept = await court_intake._backfill_hearing(case, documents, "一审", "某院", "案号", {"username": "u"}, None, keep_existing=True)
            update.assert_not_awaited()
            self.assertEqual(kept["status"], "已有开庭未覆盖")
            self.assertIn("2026-12-20", kept["previous"])
            web = await court_intake._backfill_hearing(case, documents, "一审", "某院", "案号", {"username": "u"}, None)
        self.assertEqual(web["status"], "已回填")
        update.assert_awaited_once()
        empty = BusinessRecord(id=2, module="case", serial_no="E", data={"first_court_name": "某院"})
        with patch("app.areas.legal.router.update_case_court_info", AsyncMock()) as filled:
            result = await court_intake._backfill_hearing(empty, documents, "一审", "某院", "案号", {"username": "u"}, None, keep_existing=True)
        self.assertEqual(result["status"], "已回填")
        filled.assert_awaited_once()

    async def test_pending_list_hides_service_link(self):
        await self._run(sms(), FakeApi(ApiError(502, "法院接口失败")))

        async def _db():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[current_identity] = lambda: {"username": "admin", "display_name": "管理者", "role": "admin", "role_ids": ["admin"],
                                                              "_actual_role_ids": ["admin"], "_actual_role": "admin", "department": "", "action_keys": ["*"], "menu_keys": ["documents-official"]}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://bot.test") as client:
            listed = await client.get(settings.api_prefix + "/documents/court-service/bot-receipts")
        self.assertNotIn("sdsin", listed.text)
        self.assertIn("[送达链接]", listed.text)


    async def test_pending_list_gives_attachment_ids_for_viewing(self):
        await self._run(sms(), FakeApi({"status": "系统内未登记该案", "documents": DOCS, "match": {"candidates": []}}))

        async def _db():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[current_identity] = lambda: {"username": "admin", "display_name": "管理者", "role": "admin", "role_ids": ["admin"],
                                                              "_actual_role_ids": ["admin"], "_actual_role": "admin", "department": "", "action_keys": ["*"], "menu_keys": ["documents-official"]}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://bot.test") as client:
            listed = await client.get(settings.api_prefix + "/documents/court-service/bot-receipts")
        self.assertEqual(listed.json()["items"][0]["documents"], [{"attachment_id": 9, "name": "传票", "kind": "传票"}])
        self.assertEqual(listed.json()["items"][0]["reason"], "系统里没找到这个案号对应的案件")

    async def test_record_shows_processing_while_downloading_and_failure_reason_after(self):
        from app.areas.aws.receipt_bot import PROCESSING_REASON, ApiError, _reason
        seen = []

        async def api(username, path, body):
            seen.append([(r.status, r.data.get("reason")) for r in await self._records()])
            raise ApiError(422, "法院接口拒绝：校验失败,对路径进行了修改；请确认链接完整且未过期")
        reply = await self._run(sms(), api)
        self.assertEqual(seen, [[("待处理", PROCESSING_REASON)]], "处理中就写明在识别")
        self.assertIn("对路径进行了修改", reply.text)
        record = (await self._records())[0]
        self.assertEqual((record.status, record.data["reason"]), ("待处理", "法院接口拒绝：校验失败,对路径进行了修改；请确认链接完整且未过期"))
        stalled = BusinessRecord(module="court_group_receipt", status="待处理",
                                 data={"reason": PROCESSING_REASON, "sent_at": "2026-11-07T00:00:00+00:00"})
        self.assertIn("识别中断", _reason(stalled))

    async def test_result_dropped_when_record_handled_during_processing(self):
        """识别期间收文台已处理（超时后才允许），机器人结果不写回、不发确认消息，只告诉发送人已处理。"""
        async def api(username, path, body):
            async with self.sessions() as db:
                record = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "court_group_receipt"))).one()
                record.status, record.data = "不入库", {**record.data, "close_note": "手工处理"}
                await db.commit()
            return preview()
        reply = await self._run(sms(), api)
        self.assertIn("已在收文台处理", reply.text)
        self.assertNotIn("确认 ", reply.text)
        self.assertEqual((await self._records())[0].status, "不入库")

    async def test_assign_and_close_refused_while_processing(self):
        from app.areas.aws.receipt_bot import PROCESSING_REASON, _now, _pending_record, _reason, STALLED_REASON
        async with self.sessions() as db:
            record = BusinessRecord(module="court_group_receipt", serial_no="QSWP1", title="t", customer="", status="待处理",
                                    owner="lawyer", department="", data={"reason": PROCESSING_REASON, "sent_at": _now()})
            db.add(record)
            await db.commit()
            with self.assertRaises(HTTPException) as caught:
                await _pending_record(record.id, db)
            self.assertEqual((caught.exception.status_code, caught.exception.detail), (409, "正在识别，请稍后再处理"))
            # 没时区的时间不让列表 500，按中断处理。
            record.data = {**record.data, "sent_at": "2026-11-07T20:00:00"}
            self.assertEqual(_reason(record), STALLED_REASON)
            self.assertEqual((await _pending_record(record.id, db)).id, record.id)

    async def test_processing_reason_cleared_when_waiting_for_confirm(self):
        await self._run(sms(), FakeApi(preview()))
        self.assertEqual((await self._records())[0].data["reason"], "")

    def test_bot_receipts_are_not_agent_tools(self):
        from app.agent_mcp.semantic_metadata import exclusion_reasons
        routes = [route for route in app.routes if "bot-receipts" in getattr(route, "path", "")]
        self.assertEqual(len(routes), 4)
        for route in routes:
            self.assertTrue(exclusion_reasons(route), route.path)

    async def test_stream_connection_acks_ping_and_callback_then_processes(self):
        import json
        import websockets
        from app import dingtalk_receipt_worker as module
        received, acks = [], []

        async def server(socket):
            await socket.send(json.dumps({"type": "SYSTEM", "headers": {"topic": "ping", "messageId": "p1"}, "data": json.dumps({"opaque": "x"})}))
            acks.append(json.loads(await socket.recv()))
            await socket.send(json.dumps({"type": "CALLBACK", "headers": {"topic": module.BOT_TOPIC, "messageId": "c1"},
                                          "data": json.dumps({"msgId": "m1", "conversationType": "2"})}))
            acks.append(json.loads(await socket.recv()))
            await socket.send(json.dumps({"type": "SYSTEM", "headers": {"topic": "disconnect", "messageId": "d1"}, "data": "{}"}))
            await socket.recv()

        async with websockets.serve(server, "127.0.0.1", 0) as running:
            port = running.sockets[0].getsockname()[1]
            opened = httpx.Response(200, json={"endpoint": f"ws://127.0.0.1:{port}", "ticket": "t k"}, request=httpx.Request("POST", module.OPEN_URL))
            worker = Worker()

            async def process(data):
                received.append(data)
            worker.process = process
            with patch("httpx.AsyncClient.post", AsyncMock(return_value=opened)) as post:
                await asyncio.wait_for(worker.connect("key", "secret"), 5)
                await asyncio.sleep(0)
        self.assertEqual(post.await_args.kwargs["json"]["subscriptions"], [{"type": "CALLBACK", "topic": module.BOT_TOPIC}])
        self.assertEqual(acks[0]["headers"]["messageId"], "p1")
        self.assertEqual(json.loads(acks[0]["data"]), {"opaque": "x"})
        self.assertEqual((acks[1]["code"], acks[1]["headers"]["messageId"], json.loads(acks[1]["data"])), (200, "c1", {"response": "OK"}))
        self.assertEqual(received, [{"msgId": "m1", "conversationType": "2"}])

    async def test_pending_list_requires_menu_and_close(self):
        await self._run(sms(text="【某某人民法院】请到本院领取文书"), FakeApi())
        record = (await self._records())[0]

        async def _db():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = _db
        admin = {"username": "admin", "display_name": "管理者", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
                 "_actual_role": "admin", "department": "", "action_keys": ["*"], "menu_keys": ["documents-official"]}
        plain = {"username": "someone", "display_name": "某人", "role": "user", "role_ids": ["user"], "_actual_role_ids": ["user"],
                 "_actual_role": "user", "department": "", "action_keys": [], "menu_keys": []}
        api = settings.api_prefix + "/documents/court-service/bot-receipts"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://bot.test") as client:
            app.dependency_overrides[current_identity] = lambda: plain
            denied = AsyncMock(side_effect=HTTPException(403, "当前账号没有该收文窗口的查看权限"))
            with patch("app.areas.aws.receipt_sources._require_receipt_menu", denied):
                self.assertEqual((await client.get(api)).status_code, 403)
                self.assertEqual((await client.post(f"{api}/{record.id}/close", json={})).status_code, 403)
                self.assertEqual((await client.post(f"{api}/{record.id}/assign", json={"case_no": "HZMS1"})).status_code, 403)
            app.dependency_overrides[current_identity] = lambda: admin
            listed = await client.get(api)
            self.assertEqual([item["id"] for item in listed.json()["items"]], [record.id])
            assign = await client.post(f"{api}/{record.id}/assign", json={"case_no": "HZMS1"})
            self.assertEqual(assign.status_code, 409)
            closed = await client.post(f"{api}/{record.id}/close", json={"reason": "已手工上传"})
            self.assertEqual(closed.json()["status"], "不入库")
            async with self.sessions() as db:
                kept = (await db.get(BusinessRecord, record.id)).data
            self.assertEqual((kept["reason"], kept["close_note"]), ("没有人民法院在线服务送达链接", "已手工上传"), "不入库不覆盖原来的原因")
            self.assertEqual((await client.get(api)).json()["items"], [])
        async with self.sessions() as db:
            events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == record.id))).all()
        self.assertEqual(events[-1].operator, "admin")


if __name__ == "__main__":
    unittest.main()
