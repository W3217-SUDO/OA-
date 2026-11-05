"""按固定模板生成文书（陶国南 11-03）：模板管理、字段取值、只替换不改写、确认后存进案件空间。"""
import tempfile
import unittest
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import httpx
from docx import Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.legal import case_word_templates as module
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, JobRole, SystemConfig, SystemParameter, User, WorkflowEvent
from app.security import current_identity

API = settings.api_prefix
ADMIN = {"username": "wt-admin", "role": "admin", "_actual_role": "admin", "display_name": "模板管理员", "department": "诉讼部"}
LAWYER = {"username": "wt-lawyer", "role": "user", "display_name": "沈律师", "department": "诉讼部"}
VIEWER = {"username": "wt-viewer", "role": "user", "display_name": "查看员", "department": "诉讼部"}


def docx(*paragraphs: str) -> bytes:
    document = Document()
    for text in paragraphs:
        document.add_paragraph(text)
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def texts(content: bytes) -> list[str]:
    return [p.text for p in Document(BytesIO(content)).paragraphs]


class CaseWordTemplatesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="case-word-templates-")
        from app.core import storage
        self.upload = patch.object(module, "UPLOAD_ROOT", Path(self.temp.name))
        self.storage = patch.object(storage, "UPLOAD_ROOT", Path(self.temp.name))
        self.upload.start()
        self.storage.start()
        self.saved = []
        self.generated = patch("app.core.generated_file_storage.save_generated_file", self._fake_save)
        self.generated.start()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=LAWYER["username"], display_name="沈建锋", department="诉讼部", role="user", password_hash="x", is_active=True,
                     profile={"permission_role_code": "WT-EDITOR"}),
                User(username=VIEWER["username"], display_name="查看员", department="诉讼部", role="user", password_hash="x", is_active=True,
                     profile={"permission_role_code": "WT-VIEWER"}),
                JobRole(code="WT-EDITOR", name="文书办理岗", permissions=["case-mine", "案件承办", "action:case.document.generate"], data_scope="全所数据", is_active=True),
                JobRole(code="WT-VIEWER", name="查看岗", permissions=["case-mine"], data_scope="全所数据", is_active=True),
                SystemParameter(category="court", code="沪0115", name="上海市浦东新区人民法院", extra={}, is_active=True),
                SystemParameter(category="payment_type", code="HZ-PAY", name="上海沪知律师事务所", is_active=True,
                                extra={"payee": "上海沪知律师事务所", "account_bank": "招商银行某某支行", "account": "1219000000"}),
            ])
            case = BusinessRecord(
                module="case", serial_no="GDMS2100456", title="商标案", customer="青岛尚美数智科技集团有限公司", status="一审准备开庭",
                owner=LAWYER["username"], department="诉讼部",
                data={"case_creation_step": "completed", "case_creation_approval_status": "已通过", "case_type": "民事案件",
                      "plaintiffs": ["青岛尚美数智科技集团有限公司"], "defendants": ["甲店", "北京三快在线科技有限公司"],
                      "cause_or_charge": "十五、侵害商标权纠纷", "first_court_name": "沪0115", "first_court_case_no": "（2022）沪0115民初5795号",
                      "handling_lawyer_usernames": [LAWYER["username"]], "handling_lawyers": ["沈建锋"], "case_team_usernames": [LAWYER["username"]]},
            )
            db.add(case)
            await db.commit()
            self.case_id = case.id
        self.identity = LAWYER
        app.dependency_overrides[get_db] = self._db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://word.test")

    async def _fake_save(self, db, identity, *, name, content, content_type, source_kind, case_record=None, on_available=None, **_):
        """代替统一存储（OSS）：按分支3 的约定记录参数，建附件后调用 on_available。"""
        path = Path(self.temp.name) / name
        path.write_bytes(content)
        attachment = FileAttachment(record_id=case_record.id, category="AI空间", original_name=name, stored_name=name,
                                    content_type=content_type, size=len(content), path=str(path), uploader=identity["username"], remark="")
        db.add(attachment)
        await on_available(db, attachment)
        await db.commit()
        self.saved.append({"name": name, "source_kind": source_kind, "content_type": content_type})
        return {"attachment": attachment}

    async def _db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()
        self.upload.stop()
        self.storage.stop()
        self.generated.stop()
        self.temp.cleanup()

    def url(self, template_id: str, action: str) -> str:
        return f"{API}/cases/{self.case_id}/documents/word-templates/{template_id}/{action}"

    async def test_builtin_withdrawal_fills_case_fields_and_keeps_text(self):
        listed = (await self.client.get(API + "/case-word-templates")).json()
        builtin = next(item for item in listed["items"] if item["id"] == "withdrawal-application")
        self.assertEqual(builtin["fields"], ["法院", "原告", "被告", "案由", "法院案号", "撤诉理由", "开庭律师", "生成日期"])
        self.assertFalse(listed["can_manage"])

        preview = (await self.client.post(self.url("withdrawal-application", "preview"), json={"values": {}})).json()
        values = {field["key"]: field["value"] for field in preview["fields"]}
        self.assertEqual(values["法院"], "上海市浦东新区人民法院", "法院代码换成全称")
        self.assertEqual(values["被告"], "甲店、北京三快在线科技有限公司", "多个被告用顿号连起来")
        self.assertEqual(values["开庭律师"], "沈建锋", "没填开庭律师时取第一位经办律师")
        self.assertEqual(values["法院案号"], "（2022）沪0115民初5795号")
        self.assertEqual(preview["missing"], ["撤诉理由"], "案件里没有的字段列出来让人补")
        self.assertIn("原被告之间已达成和解并履行", next(f for f in preview["fields"] if f["key"] == "撤诉理由")["options"])

        refused = await self.client.post(self.url("withdrawal-application", "generate"), json={"values": {}})
        self.assertEqual(refused.status_code, 422)
        self.assertIn("撤诉理由", refused.json()["detail"])

        done = await self.client.post(self.url("withdrawal-application", "generate"), json={"values": {"撤诉理由": "原被告之间已达成和解并履行"}})
        self.assertEqual(done.status_code, 201, done.text)
        async with self.sessions() as db:
            attachment = await db.scalar(select(FileAttachment).where(FileAttachment.record_id == self.case_id))
            event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id))
        self.assertEqual((attachment.category, attachment.remark), ("AI空间", "按模板生成：撤诉申请书"), "和 501226 同一种存法")
        self.assertEqual(self.saved[0]["source_kind"], "case_word_template")
        self.assertTrue(self.saved[0]["name"].startswith("GDMS2100456_撤诉申请书_"))
        self.assertEqual(event.action, "按模板生成文书")
        body = texts(Path(attachment.path).read_bytes())
        self.assertEqual(body[2], "上海市浦东新区人民法院：")
        self.assertEqual(body[3], "原告青岛尚美数智科技集团有限公司与被告甲店、北京三快在线科技有限公司侵害商标权纠纷一案，即贵院受理的（2022）沪0115民初5795号案件，"
                                  "因原被告之间已达成和解并履行，现原告申请撤回对甲店、北京三快在线科技有限公司的起诉。望法院准许。", "下划线换成案件信息，括号说明去掉，正文不改")
        saved = Document(BytesIO(Path(attachment.path).read_bytes()))
        self.assertFalse(any(run.underline for paragraph in saved.paragraphs for run in paragraph.runs if run.text), "替换后去掉下划线")
        from zipfile import ZipFile
        with ZipFile(attachment.path) as package:
            self.assertNotIn(b"<w:u ", package.read("word/document.xml"), "空白 run、段落标记上也不留下划线")
        self.assertEqual(body[7], "代理人：沈建锋")
        self.assertRegex(body[8], r"^日  期：\d{4}年\d{1,2}月\d{1,2}日$")
        self.assertFalse(any("{" in text for text in body))

    async def test_only_document_generators_can_save(self):
        self.identity = VIEWER
        self.assertEqual((await self.client.post(self.url("withdrawal-application", "preview"), json={"values": {}})).status_code, 200)
        saved = await self.client.post(self.url("withdrawal-application", "generate"), json={"values": {"撤诉理由": "和解"}})
        self.assertEqual(saved.status_code, 403)

    async def test_admin_uploads_updates_disables_and_deletes(self):
        self.identity = LAWYER
        upload = {"file": ("起诉状.docx", docx("{法院}：", "原告{原告}诉被告{被告}，诉讼请求：{诉讼请求}"), module.DOCX_TYPE)}
        self.assertEqual((await self.client.post(API + "/case-word-templates", data={"name": "起诉状"}, files=upload)).status_code, 403)
        self.identity = ADMIN
        bad = await self.client.post(API + "/case-word-templates", data={"name": "空模板"},
                                     files={"file": ("空.docx", docx("没有占位字段"), module.DOCX_TYPE)})
        self.assertEqual(bad.status_code, 422)
        created = (await self.client.post(API + "/case-word-templates", data={"name": "起诉状"}, files=upload)).json()
        self.assertEqual(created["fields"], ["法院", "原告", "被告", "诉讼请求"])
        template_id = created["id"]
        await self.client.patch(f"{API}/case-word-templates/{template_id}", json={"options": {"诉讼请求": ["停止侵权", " "]}})
        await self.client.patch(f"{API}/case-word-templates/withdrawal-application", json={"is_active": False})

        self.identity = LAWYER
        response = await self.client.get(API + "/case-word-templates")
        self.assertEqual(response.status_code, 200, response.text)
        listed = response.json()["items"]
        builtin = [item["id"] for item in module.BUILTIN_TEMPLATES if item["id"] != "withdrawal-application"]
        self.assertEqual([item["id"] for item in listed], [*builtin, template_id], "停用的模板普通用户看不到")
        self.assertEqual(next(item for item in listed if item["id"] == template_id)["options"], {"诉讼请求": ["停止侵权"]})
        self.assertEqual((await self.client.post(self.url("withdrawal-application", "preview"), json={})).status_code, 409)
        preview = (await self.client.post(self.url(template_id, "preview"), json={"values": {"诉讼请求": "停止侵权"}})).json()
        self.assertEqual(preview["missing"], [])
        self.assertEqual(preview["paragraphs"][1], "原告青岛尚美数智科技集团有限公司诉被告甲店、北京三快在线科技有限公司，诉讼请求：停止侵权")

        self.identity = ADMIN
        replaced = await self.client.put(f"{API}/case-word-templates/{template_id}/file",
                                         files={"file": ("起诉状2.docx", docx("{法院}（新版）"), module.DOCX_TYPE)})
        self.assertEqual(replaced.json()["fields"], ["法院"])
        self.assertEqual((await self.client.delete(f"{API}/case-word-templates/withdrawal-application")).status_code, 409, "内置模板只能停用")
        self.assertEqual((await self.client.delete(f"{API}/case-word-templates/{template_id}")).status_code, 200)
        async with self.sessions() as db:
            config = await db.scalar(select(SystemConfig).where(SystemConfig.key == "case_word_templates"))
            files = (await db.scalars(select(FileAttachment).where(FileAttachment.category == "案件文书模板"))).all()
        self.assertTrue(next(item for item in config.value["items"] if item["id"] == template_id)["deleted_at"], "删除只做逻辑删除")
        self.assertEqual(len(files), 2, "旧模板文件保留")

    async def test_underlined_template_upload_recognizes_fields_and_mapping_can_change(self):
        self.identity = ADMIN
        document = Document()
        paragraph = document.add_paragraph("致")
        for text, underline in (("某某法院", True), ("（哪个法院）", True), ("：请", False), ("宁阳恒汇商贸中心（个体工商户）", True), ("（被告名称）", True),
                                ("于", False), ("2026年1月1日", True), ("（付款日期）", True), ("付款。", False)):
            paragraph.add_run(text).underline = underline
        output = BytesIO()
        document.save(output)
        created = await self.client.post(API + "/case-word-templates", data={"name": "催款函"},
                                         files={"file": ("催款函.docx", output.getvalue(), module.DOCX_TYPE)})
        self.assertEqual(created.status_code, 201, created.text)
        body = created.json()
        self.assertEqual([(slot["sample"], slot["note"], slot["source"], slot["key"]) for slot in body["slots"]],
                         [("某某法院", "哪个法院", "case", "法院"), ("宁阳恒汇商贸中心（个体工商户）", "被告名称", "case", "被告"),
                          ("2026年1月1日", "付款日期", "case", "生成日期")], "按说明自动对应；“日期”先猜成生成日期")
        changed = await self.client.patch(f"{API}/case-word-templates/{body['id']}", json={"mapping": {"2": {"source": "manual", "label": "付款日期"}}})
        self.assertEqual([slot["key"] for slot in changed.json()["slots"]], ["法院", "被告", "付款日期"], "对不上的改成生成时手填")
        self.assertEqual((await self.client.patch(f"{API}/case-word-templates/{body['id']}",
                                                  json={"mapping": {"0": {"source": "case", "field": "不存在"}}})).status_code, 422)
        self.identity = LAWYER
        preview = (await self.client.post(self.url(body["id"], "preview"), json={"values": {"付款日期": "2026年12月1日"}})).json()
        self.assertEqual(preview["paragraphs"][0], "致上海市浦东新区人民法院：请甲店、北京三快在线科技有限公司于2026年12月1日付款。")

    async def test_upload_original_underlined_file_as_is(self):
        # 陶国南 16:19：直接上传他们写的范本（下划线 + 括号说明），不用改成 {字段}。这里用他发来的撤诉申请书原件。
        self.identity = ADMIN
        import base64
        from app.areas.legal.builtin_word_templates import WITHDRAWAL_APPLICATION_DOCX
        original = base64.b64decode(WITHDRAWAL_APPLICATION_DOCX)
        self.assertEqual(len(original), 32538, "内置的就是陶国南给的原件")
        created = await self.client.post(API + "/case-word-templates", data={"name": "撤诉申请书（上传）"},
                                         files={"file": ("撤诉申请书.docx", original, module.DOCX_TYPE)})
        self.assertEqual(created.status_code, 201, created.text)
        slots = created.json()["slots"]
        self.assertEqual([(slot["note"], slot["source"], slot["key"]) for slot in slots], [
            ("哪个法院", "case", "法院"), ("原告名称", "case", "原告"), ("被告名称，有几个写几个", "case", "被告"), ("案由", "case", "案由"),
            ("法院案号", "case", "法院案号"), ("撤诉理由", "manual", "撤诉理由"), ("被告名称", "case", "被告"), ("原告", "case", "原告"),
            ("开庭律师", "case", "开庭律师"), ("生成当日", "case", "生成日期")])
        self.assertEqual(slots[4]["sample"], "（2022）沪0115民初5795号")
        self.identity = LAWYER
        preview = (await self.client.post(self.url(created.json()["id"], "preview"), json={"values": {"撤诉理由": "原被告之间已达成和解"}})).json()
        self.assertEqual(preview["missing"], [])
        self.assertEqual(preview["paragraphs"][2], "上海市浦东新区人民法院：")
        self.assertNotIn("（", preview["paragraphs"][7], "括号说明删掉")

    async def test_builtin_mediation_agreement_lists_each_party_and_account(self):
        """陶国南 11-04：调解协议书——原告/被告逐个列出详细信息，赔偿金额自动大写，调解员和付款期限可留空；
        委托诉讼代理人用经办律师、律所用上海沪知律师事务所，收款账户取系统参数“付款单位”里沪知所的账户（14:19）。"""
        from app.data_models.parties import PartyRecord
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            case.data = {**case.data, "settlement_amount": 4500,
                         "plaintiff_identities": [{"name": "青岛尚美数智科技集团有限公司", "organization_type": "公司企业", "identity_no": "91370200MA3C000000"}],
                         "defendant_identities": [{"name": "甲店", "organization_type": "个人", "identity_no": "110101199003070011"},
                                                  {"name": "北京三快在线科技有限公司", "organization_type": "公司企业", "identity_no": "91110108MA0000000X"}],
                         "plaintiff_agents": [{"name": "别的代理人", "law_firm": "别的所", "position": "律师", "phone": "", "authority": ""}]}
            db.add_all([PartyRecord(party_no="DSR2600001", name="甲店", data={"contact_address": "某省某市某路1号", "contact_phone": "13800000000"}),
                        PartyRecord(party_no="DSR2600002", name="青岛尚美数智科技集团有限公司", data={"registered_address": "青岛市某路2号"})])
            await db.commit()
        response = await self.client.post(self.url("mediation-agreement", "preview"), json={"values": {}})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        fields = {field["key"]: field for field in body["fields"]}
        self.assertEqual(body["missing"], [], "调解员、付款期限可留空，其余都从案件带出")
        self.assertTrue(fields["调解员"]["optional"])
        # 日期都生成（陶国南 14:28）：案件里没有约定付款日期时默认生成日起 7 天；签署日期是生成当日。
        due = datetime.now() + timedelta(days=7)
        self.assertEqual(fields["付款期限"]["value"], f"{due.year}年{due.month}月{due.day}日")
        self.assertEqual(fields["签署日期"]["value"], f"{datetime.now().year}年{datetime.now().month}月{datetime.now().day}日")
        self.assertEqual(fields["赔偿金额"]["value"], "4500")
        self.assertEqual(fields["赔偿金额大写"]["value"], "肆仟伍佰元整")
        self.assertTrue(fields["赔偿金额大写"]["derived"] and fields["被告信息"]["multiline"])
        self.assertEqual(fields["委托诉讼代理人"]["value"], "沈建锋")
        self.assertEqual(fields["代理律所"]["value"], "上海沪知律师事务所")
        text = "\n".join(body["paragraphs"])
        self.assertIn("上海市浦东新区人民法院", body["paragraphs"][0])
        self.assertIn("原告：青岛尚美数智科技集团有限公司，联系地址：青岛市某路2号，统一社会信用代码：91370200MA3C000000。", body["paragraphs"])
        self.assertIn("被告：甲店，男，身份证号码：110101199003070011，地址：某省某市某路1号，联系方式：13800000000。", body["paragraphs"])
        # 系统里没有的项留空格（各项都列出）。
        self.assertIn("被告：北京三快在线科技有限公司，地址：\u3000\u3000\u3000\u3000，统一社会信用代码：91110108MA0000000X，联系方式：\u3000\u3000\u3000\u3000。", body["paragraphs"])
        self.assertIn("原告：青岛尚美数智科技集团有限公司      被告：甲店、北京三快在线科技有限公司", body["paragraphs"], "落款带出被告名称")
        self.assertEqual(body["paragraphs"][-1].strip(), fields["签署日期"]["value"])
        self.assertIn("被告甲店、北京三快在线科技有限公司与原告侵害商标权纠纷一案【案号：（2022）沪0115民初5795号】，上海市浦东新区人民法院委派调解员\u3000\u3000\u3000\u3000进行调解", text)
        self.assertIn(f"同意于{fields['付款期限']['value']}前支付赔偿款项（含合理维权开支）共计4500元（大写：肆仟伍佰元整）", text)
        self.assertIn("委托诉讼代理人：沈建锋，上海沪知律师事务所。", body["paragraphs"])
        self.assertIn("名称：上海沪知律师事务所", body["paragraphs"])
        self.assertIn("开户行：招商银行某某支行", body["paragraphs"])
        self.assertIn("账  号：1219000000", body["paragraphs"])
        self.assertNotIn("（", "".join(p for p in body["paragraphs"] if p.startswith(("名称", "开户行", "账"))), "说明括号都去掉了")
        for leaked in ("黄响壮", "445281199603160350", "13434916251", "公牛", "李某", "某某市", "申浩", "别的代理人"):
            self.assertNotIn(leaked, text)
        # 改了赔偿金额，大写跟着变；填了调解员就写进去。
        again = (await self.client.post(self.url("mediation-agreement", "preview"), json={"values": {"赔偿金额": "12000", "调解员": "王调解", "赔偿金额大写": "乱填"}})).json()
        joined = "\n".join(again["paragraphs"])
        self.assertIn("共计12000元（大写：壹万贰仟元整）", joined)
        self.assertIn("委派调解员王调解进行调解", joined)
        download = await self.client.post(self.url("mediation-agreement", "download"), json={"values": {}})
        self.assertEqual(download.status_code, 200, download.text)

    async def test_builtin_applications_1105(self):
        """陶国南 11-05 三份申请书：申请人=原告、被申请人=被告逐个列出；落款日期中文大写；保全金额取诉讼标的额；
        个人身份证号存在统一社会信用代码里也按个人写；样本里的真实信息不进模板。"""
        from app.data_models.parties import PartyRecord
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            case.data = {**case.data, "litigation_amount": "60000.00"}
            db.add_all([PartyRecord(party_no="DSR2600011", name="甲店", data={"credit_code": "41082320020104022X", "registered_address": "某省某县某村1号"}),
                        PartyRecord(party_no="DSR2600012", name="青岛尚美数智科技集团有限公司",
                                    data={"registered_address": "青岛市某路2号", "credit_code": "91370200MA3C000000", "legal_representative": "张三"}),
                        PartyRecord(party_no="DSR2600013", name="北京三快在线科技有限公司", data={"registered_address": "北京三快在线科技有限公司"})])
            await db.commit()
        today = module.chinese_date(datetime.now())
        leaked_words = ("台享", "梅休", "甄旺", "手拉手", "王建正", "张香荣", "叫了个鸡", "共和新路", "华山路", "1302 2224", "zw0551", "浦东新区人民法院", "第五十四条")

        preservation = (await self.client.post(self.url("property-preservation", "preview"), json={"values": {"事实和理由": "申请人系商标权人。"}})).json()
        fields = {field["key"]: field for field in preservation["fields"]}
        self.assertEqual(preservation["missing"], [], "财产线索可留空")
        self.assertTrue(fields["财产线索"]["optional"] and fields["申请人信息"]["multiline"])
        self.assertEqual(fields["保全金额"]["value"], "60000")
        paragraphs = preservation["paragraphs"]
        for line in ("申请人：青岛尚美数智科技集团有限公司", "统一社会信用代码：91370200MA3C000000", "法定代表人：张三  职务：\u3000\u3000\u3000\u3000",
                     "住所：青岛市某路2号", "送达地址：上海市静安区江场路1228弄20号五牛控股大厦603室",
                     "被申请人一：甲店", "统一社会信用代码：41082320020104022X", "地址：某省某县某村1号",
                     "被申请人二：北京三快在线科技有限公司", "地址：\u3000\u3000\u3000\u3000",
                     "申请事项：请求对被申请人甲店、北京三快在线科技有限公司名下财产进行保全，保全金额60000元人民币或等值财产。",
                     "申请人诉被申请人侵害商标权纠纷一案贵院已经受理。申请人系商标权人。", "上海市浦东新区人民法院"):
            self.assertIn(line, paragraphs)
        self.assertEqual(paragraphs[-1].strip(), today)

        change = (await self.client.post(self.url("change-claims", "preview"), json={"values": {}})).json()
        self.assertEqual(change["missing"], ["变更后诉讼请求"])
        change = (await self.client.post(self.url("change-claims", "preview"), json={"values": {"变更后诉讼请求": "1.停止侵权；\n2.赔偿损失。"}})).json()
        self.assertIn("贵院受理的（2022）沪0115民初5795号申请人与甲店、北京三快在线科技有限公司侵害商标权纠纷一案，现依法变更诉讼请求，变更后新的诉讼请求为：",
                      change["paragraphs"])
        self.assertIn("1.停止侵权；", change["paragraphs"])
        self.assertIn("2.赔偿损失。", change["paragraphs"])

        hearing = (await self.client.post(self.url("non-public-hearing", "preview"), json={"values": {}})).json()
        self.assertEqual(hearing["missing"], [])
        self.assertIn("申请事项：你院受理的青岛尚美数智科技集团有限公司诉甲店、北京三快在线科技有限公司侵害商标权纠纷一案，"
                      "根据《中华人民共和国民事诉讼法》第一百三十七条的规定，特申请不公开审理。", hearing["paragraphs"])
        self.assertIn("申请人：青岛尚美数智科技集团有限公司", hearing["paragraphs"])
        for body in (preservation, change, hearing):
            text = "\n".join(body["paragraphs"])
            self.assertNotIn("（", text.replace("（2022）", ""), "说明括号都去掉了")
            for leaked in leaked_words + ("某某",):
                if leaked != "浦东新区人民法院":  # 测试案件本身就在浦东法院
                    self.assertNotIn(leaked, text)
        for item in module.BUILTIN_TEMPLATES[2:]:
            raw = await module._template_bytes(item, None)
            text = "\n".join(texts(raw))
            for leaked in leaked_words:
                self.assertNotIn(leaked, text, item["name"])

    async def test_builtin_case_summary_1105(self):
        """陶国南 11-05 办案小结（诉讼）：委托人、案由、各日期、开庭日期、处理结果初稿从案件带出；案情概况、体会、保管期限可留空手写。"""
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            case.status = "已归档"
            case.data = {**case.data, "case_register_date": "2023-04-01T10:00:00", "first_court_filing_date": "2024-04-22",
                         "case_closed_at": "2026-01-08T10:33:11", "first_court_hearing_date": "2025-07-28T09:30:00",
                         "second_court_hearing_date": "2025-11-25T09:30:00", "litigation_amount": "500000.00",
                         "judgment_amount": "100000.00", "settlement_amount": "100000.00", "archived_at": "2026-09-29T13:53:17"}
            await db.commit()
        body = (await self.client.post(self.url("case-summary", "preview"), json={"values": {}})).json()
        self.assertEqual(body["missing"], [])
        fields = {field["key"]: field["value"] for field in body["fields"]}
        self.assertEqual(fields["客户名称"], "青岛尚美数智科技集团有限公司")
        self.assertEqual((fields["收案日期"], fields["起诉日期"], fields["结案日期"]), ("2023年4月1日", "2024年4月22日", "2026年1月8日"))
        self.assertEqual(fields["开庭日期"], "2025.7.28；2025.11.25")
        self.assertEqual(fields["处理结果"], "判决结案，诉讼标的额500000元，判决金额100000元")
        self.assertEqual(fields["归档日期"], "二〇二六年九月二十九日")
        download = await self.client.post(self.url("case-summary", "download"), json={"values": {"办案体会": "正常处理"}})
        self.assertEqual(download.status_code, 200, download.text)
        document = Document(BytesIO(download.content))
        cells = [cell.text for row in document.tables[0].rows for cell in row.cells]
        for value in ("青岛尚美数智科技集团有限公司", "侵害商标权纠纷", "2023年4月1日", "2025.7.28；2025.11.25", "正常处理"):
            self.assertIn(value, cells)
        self.assertNotIn("（", "".join(cells), "说明括号都去掉了")
        self.assertIn("归 档 日 期：二〇二六年九月二十九日", [p.text for p in document.paragraphs])
        raw = "\n".join(cell.text for row in Document(BytesIO(await module._template_bytes(module.BUILTIN_TEMPLATES[-1], None))).tables[0].rows for cell in row.cells)
        for leaked in ("立邦", "商标侵权", "2024.5.14", "1.2万"):
            self.assertNotIn(leaked, raw)

    def test_handling_result_draft(self):
        record = BusinessRecord(module="case", serial_no="X", title="X", status="一审和解结案")
        self.assertEqual(module._handling_result(record, {"settlement_amount": "8000", "judgment_amount": "8000"}), "和解结案，和解金额8000元")
        record.status = "一审庭后待判"
        self.assertEqual(module._handling_result(record, {}), "")

    def test_id_card_in_credit_code_is_a_person(self):
        number = "41082320020104022X"
        self.assertTrue(module._is_person("刘希杰", {}, number, {"credit_code": number}))
        self.assertEqual(module._applicant_block("刘希杰", "被申请人二", {}, {"credit_code": number, "registered_address": "某村1号"}, applicant=False),
                         [f"被申请人二：刘希杰，女，身份证号码：{number}", "地址：某村1号"])
        self.assertFalse(module._is_person("某科技有限公司", {}, "91370200MA3C000000", {"credit_code": "91370200MA3C000000"}))
        self.assertFalse(module._is_person("张三丰", {}, "", {"credit_code": "91370200MA3C000000"}))

    def test_chinese_date(self):
        self.assertEqual(module.chinese_date(datetime(2017, 12, 19)), "二〇一七年十二月十九日")
        self.assertEqual(module.chinese_date(datetime(2026, 11, 5)), "二〇二六年十一月五日")
        self.assertEqual(module.chinese_date(datetime(2018, 10, 30)), "二〇一八年十月三十日")
        self.assertEqual(module.chinese_date(datetime(2020, 2, 21)), "二〇二〇年二月二十一日")

    def test_amount_upper(self):
        cases = {"4500": "肆仟伍佰元整", "12000": "壹万贰仟元整", "105000": "壹拾万伍仟元整", "10010": "壹万零壹拾元整",
                 "1200.5": "壹仟贰佰元伍角", "3.25": "叁元贰角伍分", "0.05": "伍分", "1000000": "壹佰万元整", "abc": ""}
        for value, expected in cases.items():
            self.assertEqual(module.amount_upper(value), expected, value)

    def test_note_rules(self):
        self.assertEqual(module._split_segment("（2022）沪0115民初5795号（法院案号）"), [("（2022）沪0115民初5795号", "法院案号")], "只有数字的括号是示例本身")
        self.assertEqual(module._split_segment("甲公司（原告名称）侵权纠纷（案由） "), [("甲公司", "原告名称"), ("侵权纠纷", "案由")])
        self.assertEqual(module._split_segment(" 年  月  日（生成当日）"), [(" 年  月  日", "生成当日")])

    def test_fill_keeps_runs_split_by_word(self):
        document = Document()
        paragraph = document.add_paragraph()
        for part in ("致", "{法", "院}", "：", "{原告", "}"):
            run = paragraph.add_run(part)
            run.bold = part == "{法"
        output = BytesIO()
        document.save(output)
        slots = module.resolve_slots(module.scan(output.getvalue()), {})
        self.assertEqual(module.field_keys(slots), ["法院", "原告"])
        filled = Document(BytesIO(module.fill(output.getvalue(), slots, {"法院": "上海知识产权法院", "原告": "甲公司"})))
        self.assertEqual(filled.paragraphs[0].text, "致上海知识产权法院：甲公司")
        self.assertTrue(filled.paragraphs[0].runs[1].bold, "替换后保留原来的字体格式")


if __name__ == "__main__":
    unittest.main()
