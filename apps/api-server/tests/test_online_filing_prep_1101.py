"""陶国南 11-01：网上立案材料准备——Word 只有“立案信息表”和“立案材料清单”，证件号由程序写进 Word、预览不给原文。"""
import unittest
from io import BytesIO

from docx import Document
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.main  # noqa: F401  注册全部模型
from app.core.online_filing_prep import PENDING, build_sheet, masked_rows, render_docx
from app.data_models.parties import PartyRecord
from app.database import Base
from app.models import BusinessRecord, FileAttachment, User


class OnlineFilingPrepTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add(User(username="lawyer", display_name="张律师", password_hash="x", role="staff", profile={"mobile": "13800000000"}))
            db.add(PartyRecord(party_no="P1", name="某某眼镜店", party_type="当事人", data={
                "organization_type": "个体工商户", "credit_code": "92360000MA00000001", "registered_address": "上饶市某路1号"}))
            db.add(PartyRecord(party_no="P2", name="李四", party_type="当事人", data={"organization_type": "个人", "identity_no": "110101199001011234"}))
            db.add(BusinessRecord(id=1, module="customer", serial_no="KH1", title="甲眼镜有限公司", status="T", owner="mgr",
                                  data={"credit_code": "91330000MA00000002", "legal_representative": "王五"}))
            db.add(BusinessRecord(id=11, module="case", serial_no="HZMS1", title="甲诉某某眼镜店", status="文书准备", owner="lawyer", data={
                "plaintiffs": ["甲眼镜有限公司"], "defendants": ["某某眼镜店", "李四"], "cause_or_charge": "侵害商标权纠纷",
                "handling_lawyer_usernames": ["lawyer"], "customer_record_id": 1,
                "first_court_name": "某区人民法院", "first_court_case_no": "（2026）浙0102民初1号",
                "appellant_names": ["甲眼镜有限公司"], "appellee_names": ["某某眼镜店"]}))
            await db.flush()
            db.add(FileAttachment(record_id=11, category="主体及委托资料", original_name="授权委托书.pdf", stored_name="a", content_type="application/pdf",
                                  size=1, path="x/a", uploader="lawyer"))
            db.add(FileAttachment(record_id=1, category="客户文档", original_name="甲公司营业执照.pdf", stored_name="b", content_type="application/pdf",
                                  size=1, path="x/b", uploader="lawyer"))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def sheet(self, instance):
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, 11)
            return case, await build_sheet(case, instance, db)

    async def test_first_instance_sheet_masks_ids_in_preview_but_word_has_them(self):
        case, sheet = await self.sheet("一审")
        rows = {row["栏目"]: row["填写内容"] for row in masked_rows(sheet)}
        self.assertEqual(rows["案件类型"], "民事一审")
        self.assertEqual(rows["案由"], "侵害商标权纠纷")
        self.assertEqual(rows["原告（单位）名称"], "甲眼镜有限公司")
        self.assertEqual(rows["原告法定代表人/负责人"], "王五")
        self.assertEqual(rows["被告（自然人）姓名"], "李四")
        self.assertEqual(rows["被告证件号码"], "已有（保存后在 Word 里显示）")  # 预览不给原文
        self.assertEqual(rows["律师执业证号"], PENDING)
        self.assertTrue(rows["管辖法院建议"].startswith("案件已登记法院"))
        self.assertNotIn("110101199001011234", str(masked_rows(sheet)))
        text = "\n".join(cell.text for table in Document(BytesIO(render_docx(case, sheet))).tables for row in table.rows for cell in row.cells)
        self.assertIn("110101199001011234", text)  # Word 里有原文（有案件权限的人可看，陶国南 11-01）
        self.assertIn("13800000000", text)
        document = Document(BytesIO(render_docx(case, sheet)))
        headings = [p.text for p in document.paragraphs if p.style.name.startswith("Heading")]
        self.assertEqual(headings[1:], ["一、立案信息表", "二、立案材料清单"])  # 只有两部分，不含起诉状
        materials = {label: state for label, state, _note in sheet.materials}
        self.assertEqual(materials["授权委托书"], "OA 已有")
        self.assertEqual(materials["原告/上诉人主体证明（营业执照或身份证）"], "OA 已有")  # 客户档案里的营业执照也算
        self.assertEqual(materials["律师执业证"], "缺")

    async def test_second_instance_uses_appeal_roles_and_original_court(self):
        _case, sheet = await self.sheet("二审")
        rows = {row["栏目"]: row["填写内容"] for row in masked_rows(sheet)}
        self.assertEqual(rows["案件类型"], "民事二审（上诉）")
        self.assertEqual((rows["原审法院"], rows["原审案号"]), ("某区人民法院", "（2026）浙0102民初1号"))
        self.assertEqual(rows["上诉人（单位）名称"], "甲眼镜有限公司")
        self.assertEqual(rows["被上诉人（单位）名称"], "某某眼镜店")
        self.assertIn("上诉请求", rows)
        self.assertIn("一审判决书/裁定书", {label for label, _s, _n in sheet.materials})
