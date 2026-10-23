"""智能体收文：法院送达文书下载、案号归一化与要素识别、按案件 ID 官方收文并回填案号、技能包与上网工具。"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agent_skill_packages import manifest, package_files
from app.agent_skill_packages.court_doc_intake.scripts import fetch_court_docs, normalize_case_no
from app.agent_skill_packages.court_doc_intake.scripts.extract_doc_fields import extract
from app.areas.aws import court_service
from app.config import settings
from app.database import Base, get_db
from app.harness_agent import script_runtime, tool_trace
from app.harness_agent.skills import WEB_TOOL, WorkspaceTools
from app.main import app
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent
from app.security import current_identity

API = settings.api_prefix
IDENTITY = {"username": "CODEX-1023-intake", "role": "admin", "role_ids": ["admin"], "department": "测试部"}
LINK = ("【淮南市大通区人民法院】曹志刚，淮南市大通区人民法院向您发送了（2026）皖0402民初4093号案件相关文书，请及时签收。"
        "点击链接查阅：https://zxfw.court.gov.cn/zxfw/#/pagesAjkj/app/wssd/index?qdbh=5f184b3f7c5740d791d35a51bc6b4841"
        "&sdbh=072201dbce1349b29ced07493bd13292&sdsin=bfed0bbf56712c0564d4501c70b8c4a2")
SUMMONS = ("淮南市大通区人民法院 传票 案号（2026）皖0402民初4093号 案由 侵害商标权纠纷 被传唤人：曹志刚 "
           "应到时间：2026年11月12日上午9时30分 应到处所：本院第三法庭 二〇二六年十月二十二日")


class CaseNumberAndFieldTest(unittest.TestCase):
    def test_dirty_case_numbers_are_normalized_and_split(self):
        cases = {
            "（2025）渝 0 103民 初 40009 号": "（2025）渝0103民初40009号",
            "(2025苏0214民初15189号": "（2025）苏0214民初15189号",
            "（2026)苏12民初46号": "（2026）苏12民初46号",
            "（2026）粤0604民初 816": "（2026）粤0604民初816号",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_case_no.normalize(raw)[0]["归一化"], expected)
        split = normalize_case_no.normalize("（2026）苏0581民初7641号（ 2026）苏0581民初18335号")
        self.assertEqual([item["序号"] for item in split], ["7641", "18335"])
        parsed = normalize_case_no.parse("（2026）皖0402民初4093号")
        self.assertEqual((parsed["受理机关代字"], parsed["类型"], parsed["审级"]), ("皖0402", "民初", "一审"))
        self.assertEqual(parsed["检索变体"][:3], ["（2026）皖0402民初4093号", "2026皖0402民初4093号", "皖0402民初4093号"])
        self.assertEqual(normalize_case_no.parse("（2026）沪73知民终5号")["审级"], "二审")
        self.assertEqual(normalize_case_no.normalize("121925000768")[0]["检索变体"], ["121925000768"])

    def test_summons_and_fee_notice_fields_come_from_text_only(self):
        summons = extract(SUMMONS, "传票")
        self.assertEqual(summons["文书类型"], "传票")
        self.assertEqual(summons["官方案号"], ["（2026）皖0402民初4093号"])
        self.assertEqual((summons["开庭日期"], summons["开庭时刻"], summons["开庭法庭"]), ("2026-11-12", "09:30", "第三法庭"))
        self.assertEqual((summons["受理机关"], summons["案由"], summons["落款日期"]), ("淮南市大通区人民法院", "侵害商标权纠纷", "2026-10-22"))
        fee = extract("（2026）皖0402民初4093号 原告：浙江大光明眼镜有限公司，被告：淮南市蔡氏眼镜有限公司 侵害商标权纠纷一案，"
                      "应预交案件受理费1,050元，请于收到本通知书次日起七日内向本院预交。户名：淮南市财政局非税收入汇缴结算户 "
                      "账号：1234 5678 9012 淮南市大通区人民法院 二〇二六年十月二十二日", "交纳诉讼费用通知书")
        self.assertEqual((fee["缴费金额"], fee["预交天数"]), ("1050", 7))
        self.assertEqual((fee["原告"], fee["被告"]), (["浙江大光明眼镜有限公司"], ["淮南市蔡氏眼镜有限公司"]))
        self.assertEqual(fee["收款账户"]["账号"], "123456789012")
        empty = extract("", "扫描件")
        self.assertEqual(empty["识别状态"], "需人工核对")
        self.assertEqual(empty["官方案号"], [])

    def test_service_link_is_parsed_from_sms_and_other_hosts_are_rejected(self):
        self.assertEqual(fetch_court_docs.parse_service_link(LINK)["sdbh"], "072201dbce1349b29ced07493bd13292")
        for bad in ("https://evil.example/zxfw/#/x?qdbh=a1234567&sdbh=b1234567&sdsin=c1234567",
                    "https://zxfw.court.gov.cn/zxfw/#/x?qdbh=a1234567&sdbh=b1234567", "没有链接"):
            with self.subTest(bad=bad[:30]), self.assertRaises(ValueError):
                fetch_court_docs.parse_service_link(bad)


class CourtServiceFetchTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name="收文测试", role="admin", role_ids=["admin"],
                        department="测试部", password_hash="unused", is_active=True))
            await db.commit()
        self.old_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://intake.test")
        self.temporary = tempfile.TemporaryDirectory(prefix="CODEX-1023-intake-")
        root = Path(self.temporary.name)
        self.patches = [patch(target, root) for target in (
            "app.areas.system.attachments.UPLOAD_ROOT", "app.areas.aws.router.UPLOAD_ROOT", "app.core.storage.UPLOAD_ROOT")]
        self.patches.append(patch.object(court_service, "_public_host", lambda host: None))
        self.patches.append(patch.object(court_service, "_reading", AsyncMock(return_value=("parsed", SUMMONS))))
        for item in self.patches:
            item.start()
        self.court_requests = []

    async def asyncTearDown(self):
        for item in self.patches:
            item.stop()
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.old_overrides)
        await self.engine.dispose()
        self.temporary.cleanup()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    def court(self, payload):
        def handler(request):
            self.court_requests.append(request)
            if request.url.path.endswith("getWsListBySdbhNew"):
                return httpx.Response(200, json=payload)
            return httpx.Response(200, content=b"%PDF-1.7 summons")
        return patch.object(court_service, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    async def test_documents_are_downloaded_once_and_fields_returned(self):
        payload = {"code": 200, "success": True, "data": [{
            "wjlj": "https://oss.example.com/ws/1.pdf", "c_wsmc": "传票", "c_wjgs": "pdf", "c_wsbh": "WS001",
            "c_fymc": "淮南市大通区人民法院", "c_fybh": "1234"}]}
        with self.court(payload):
            first = await self.client.post(f"{API}/documents/court-service/fetch", json={"link": LINK})
            second = await self.client.post(f"{API}/documents/court-service/fetch", json={"link": LINK})
        self.assertEqual(first.status_code, 201, first.text)
        body = first.json()
        document = body["documents"][0]
        self.assertEqual((body["court"], body["case_numbers"]), ("淮南市大通区人民法院", ["（2026）皖0402民初4093号"]))
        self.assertEqual((document["name"], document["size"], document["reused"]), ("传票.pdf", 16, False))
        self.assertEqual(document["fields"]["开庭日期"], "2026-11-12")
        sent = json.loads(self.court_requests[0].content)
        self.assertEqual(set(sent), {"sdbh", "qdbh", "sdsin"})
        self.assertEqual(self.court_requests[0].headers["referer"], fetch_court_docs.REFERER)
        self.assertTrue(second.json()["documents"][0]["reused"])
        self.assertEqual(second.json()["documents"][0]["attachment_id"], document["attachment_id"])
        async with self.sessions() as db:
            saved = (await db.scalars(select(FileAttachment))).all()
        self.assertEqual(len(saved), 1)
        self.assertEqual((saved[0].category, saved[0].record_id, saved[0].uploader), ("法院送达文书", None, IDENTITY["username"]))

    async def test_court_rejection_is_reported_and_private_targets_are_refused(self):
        with self.court({"code": 401, "msg": "校验失败,对路径进行了修改", "success": False}):
            rejected = await self.client.post(f"{API}/documents/court-service/fetch", json={"link": LINK})
        self.assertEqual(rejected.status_code, 422)
        self.assertIn("校验失败", rejected.json()["detail"])
        bad_link = await self.client.post(f"{API}/documents/court-service/fetch", json={"link": "https://example.com/" + "x" * 20})
        self.assertEqual(bad_link.status_code, 422)
        self.patches[3].stop()
        try:
            with self.assertRaises(HTTPException):
                court_service._public_host("127.0.0.1")
        finally:
            self.patches[3].start()

    async def test_official_receipt_by_case_id_backfills_missing_court_number(self):
        async with self.sessions() as db:
            case = BusinessRecord(module="case", serial_no="GDMS2401010", title="大光明诉蔡氏", customer="浙江大光明眼镜有限公司",
                                  owner=IDENTITY["username"], department="测试部", status="提交立案", data={"court": "皖0402"})
            registered = BusinessRecord(module="case", serial_no="GDMS2400604", title="已登记案号", customer="客户",
                                        owner=IDENTITY["username"], department="测试部", status="一审立案受理",
                                        data={"court_case_no": "（2026）皖0802民初2990号"})
            db.add_all([case, registered])
            await db.commit()
            case_id, registered_id = case.id, registered.id
        response = await self.client.post(
            f"{API}/documents/official/upload",
            data={"document_date": "2026-10-22", "case_id": str(case_id), "court_case_no": "（2026）皖0402民初 4093号", "remark": "传票"},
            files={"file": ("传票.pdf", b"%PDF-1.7 summons", "application/pdf")})
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(result["attachment"]["original_name"], "GDMS2401010_（2026）皖0402民初4093号_传票.pdf")
        self.assertEqual(result["attachment"]["category"], "官方收文")
        self.assertEqual(result["record"]["data"]["court_no"], "（2026）皖0402民初4093号")
        kept = await self.client.post(
            f"{API}/documents/official/upload",
            data={"document_date": "2026-10-22", "case_id": str(registered_id), "court_case_no": "（2026）皖08民终1号"},
            files={"file": ("判决书.pdf", b"%PDF-1.7 judgment", "application/pdf")})
        self.assertEqual(kept.status_code, 201, kept.text)
        async with self.sessions() as db:
            filled = await db.get(BusinessRecord, case_id)
            untouched = await db.get(BusinessRecord, registered_id)
            events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.action == "收文回填法院案号"))).all()
        self.assertEqual(filled.data["court_case_no"], "（2026）皖0402民初4093号")
        self.assertEqual(untouched.data["court_case_no"], "（2026）皖0802民初2990号")
        self.assertEqual([(event.record_id, event.comment) for event in events], [(case_id, "（2026）皖0402民初4093号")])
        listing = await self.client.get(f"{API}/documents/receipts", params={"scope": "official"})
        self.assertEqual(listing.json()["total"], 2)


class SkillPackageAndWebToolTest(unittest.IsolatedAsyncioTestCase):
    def test_court_intake_skill_ships_scripts_and_references(self):
        files = package_files("court-doc-intake")
        for path in ("SKILL.md", "scripts/fetch_court_docs.py", "scripts/extract_doc_fields.py",
                     "scripts/normalize_case_no.py", "references/case-number-formats.md", "references/oa-system-notes.md"):
            self.assertIn(path, files)
        self.assertNotIn(b"/Users/", b"".join(files.values()))
        from app.agent_skills import SKILLS_BY_ID
        from app.system_agent_skills import with_package
        skill = with_package(SKILLS_BY_ID["court-doc-intake"], store=False)
        self.assertEqual(skill.bundle, manifest("court-doc-intake"))
        self.assertEqual(skill.public_dict()["skill_runtime"]["mode"], "script")
        self.assertIn("下载法院送达文书", skill.instruction)

    async def test_web_fetch_runs_fixed_code_in_the_isolated_runner(self):
        sent = {}

        async def run_code(language, code, arguments):
            sent.update(language=language, code=code, arguments=arguments)
            return {"exit_code": 0, "isError": False,
                    "stdout": json.dumps({"status": 200, "url": arguments[0], "title": "公告", "text": "正文"}, ensure_ascii=False)}

        trace = tool_trace.begin()
        with patch("app.agent_mcp.auth.authenticated_identity", return_value={"username": "u1"}), \
                patch.object(script_runtime, "run_code", run_code):
            result = await WorkspaceTools(None, {"username": "u1"}, None).execute(
                "harness_web_fetch", {"url": "https://www.court.gov.cn/notice", "max_chars": 2000})
        self.assertEqual(WEB_TOOL["function"]["name"], "harness_web_fetch")
        self.assertEqual((result["title"], sent["language"], sent["arguments"]), ("公告", "python", ["https://www.court.gov.cn/notice", "2000"]))
        self.assertIn("urllib.request", sent["code"])
        self.assertEqual(trace[0]["label"], "上网读取网页")
        for arguments in ({"url": "file:///etc/passwd"}, {"url": "https://a.cn", "max_chars": 10}, {"url": "https://a.cn", "x": 1}):
            with self.subTest(arguments=arguments), patch("app.agent_mcp.auth.authenticated_identity", return_value={"username": "u1"}), \
                    self.assertRaises(HTTPException) as caught:
                await WorkspaceTools(None, {"username": "u1"}, None).execute("harness_web_fetch", arguments)
            self.assertEqual(caught.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
