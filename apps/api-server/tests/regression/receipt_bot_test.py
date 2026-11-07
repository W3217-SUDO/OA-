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
        self.assertEqual(api.calls[0], ("lawyer", "/documents/court-service/intake", {"link": LINK}))
        self.assertIn("回复“确认 ", first.text)
        self.assertEqual(len(api.calls), 1)
        self.assertEqual((await self._records())[0].status, "待确认")
        second = await self._run(sms(message_id="m2", text=f"确认 {await self._waiting_id()}"), api)
        self.assertEqual(api.calls[1], ("lawyer", "/documents/court-service/intake", {"link": LINK, "case_id": 7, "confirm": True, "direct_save": True}))
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
        self.assertEqual(api.calls[1][2], {"link": LINK, "case_id": 7, "confirm": True, "direct_save": True})
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
        self.assertIn("收文完成", (await self._run(sms(), FakeApi(self._party(), done()), AUTO)).text)

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
        reply = await self._run(sms(), FakeApi(self._party()), AUTO)
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
        for words in ("系统已登记开庭 2026-12-20 09:00:00 第九庭", "未覆盖", "承办法官 王法官", "FY1", "费用草稿到费用单"):
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

    async def test_new_message_retires_earlier_waiting_one(self):
        api = FakeApi(preview(), preview(), done())
        await self._run(sms(), api)
        second_link = LINK.replace("7f184b3f", "8f184b3f")
        reply = await self._run(sms(message_id="m2", text=f"【某人民法院】 {second_link}"), api)
        self.assertIn("之前未确认的 1 条", reply.text)
        records = await self._records()
        old_reply = await self._run(sms(message_id="m3a", text=f"确认 {records[0].id}"), api)
        self.assertIn("待处理", old_reply.text)
        self.assertEqual(len(api.calls), 2)
        await self._run(sms(message_id="m3", text=f"确认 {records[1].id}"), api)
        self.assertEqual(api.calls[-1][2]["link"], second_link)
        self.assertEqual([record.status for record in await self._records()], ["待处理", "已导入"])

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
        self.assertEqual(api.calls[-1][2], {"link": LINK, "case_id": 7, "confirm": True, "direct_save": True})

    async def test_unmatched_and_failures_go_to_pending(self):
        api = FakeApi({"status": "系统内未登记该案", "documents": DOCS, "match": {"candidates": []}})
        reply = await self._run(sms(), api)
        self.assertIn("未找到你有权限的案件", reply.text)
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

    def test_bot_receipts_are_not_agent_tools(self):
        from app.agent_mcp.semantic_metadata import exclusion_reasons
        routes = [route for route in app.routes if "bot-receipts" in getattr(route, "path", "")]
        self.assertEqual(len(routes), 3)
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
            self.assertEqual((await client.get(api)).json()["items"], [])
        async with self.sessions() as db:
            events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == record.id))).all()
        self.assertEqual(events[-1].operator, "admin")


if __name__ == "__main__":
    unittest.main()
