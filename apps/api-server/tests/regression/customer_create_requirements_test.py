"""智能体新建客户：缺必填信息要在提交前就列出来，而不是确认后才保存失败。"""
import unittest
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agent_mcp.business_preflight import prepare_business_arguments
from app.areas.crm.router import create_customer
from app.core.customer_create_requirements import missing_customer_create_fields
from app.database import Base
from app.models import BusinessRecord, SystemParameter

CODE = "91310000MA1K3ABCDE"


class CustomerCreateRequirementsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([SystemParameter(category="customer_type", code=c, name=n, is_active=True) for c, n in (("CUSTOMER", "客户"), ("2", "申请人"))])
            db.add(BusinessRecord(module="customer", serial_no="CODEX-C-1", title="已有公司", customer="", status="正常", owner="u1",
                                  data={"credit_code": "91310000MA1K3EXIST", "organization_type": "公司企业"}))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _missing(self, body):
        async with self.sessions() as db:
            return await missing_customer_create_fields(body, db)

    async def test_missing_organization_type_is_reported_first(self):
        self.assertEqual(await self._missing({"title": "新公司"}),
                         ["组织类型（可选：个人、个体工商户、事业单位、公司企业、其他、机关团体）"])

    async def test_company_needs_credit_code_and_person_needs_id_number(self):
        self.assertEqual(await self._missing({"title": "新公司", "organization_type": "公司企业"}), ["统一社会信用代码（公司企业必填）"])
        self.assertEqual(await self._missing({"title": "张三", "organization_type": "个人"}), ["身份证号（个人必填）"])
        self.assertEqual(await self._missing({"title": "新公司", "organization_type": "公司企业", "credit_code": CODE}), [])
        self.assertEqual(await self._missing({"title": "张三", "organization_type": "个人", "identity_no": "11010119900101123X"}), [])

    async def test_format_duplicates_and_nested_data_are_checked(self):
        self.assertEqual(await self._missing({"title": "新公司", "organization_type": "公司企业", "credit_code": "123"}),
                         ["统一社会信用代码格式无效（应为 18 位字母数字）"])
        self.assertEqual(await self._missing({"title": "已有公司", "organization_type": "公司企业", "credit_code": CODE}),
                         ["客户名称「已有公司」已存在，不能重复创建，请确认是否换一个名称或改用已有客户"])
        self.assertEqual(await self._missing({"title": "另一公司", "organization_type": "公司企业", "credit_code": "91310000MA1K3EXIST"}),
                         ["统一社会信用代码已被其他客户使用，请确认是否已有该客户"])
        nested = {"title": "嵌套公司", "data": {"organization_type": "公司企业", "credit_code": CODE}}
        self.assertEqual(await self._missing(nested), [])  # 资料放在 data 里同样识别

    async def test_all_problems_come_back_together_and_invalid_type_is_listed(self):
        problems = await self._missing({"title": "", "status": "乱写", "customer_type": "不存在"})
        self.assertEqual(problems[0], "客户名称")
        self.assertTrue(problems[1].startswith("客户状态（可选："))
        self.assertTrue(problems[2].startswith("客户类型（可选："))
        self.assertTrue(problems[3].startswith("组织类型（可选："))

    async def test_preflight_stops_before_confirmation_with_an_ask_the_user_message(self):
        spec = SimpleNamespace(_route=SimpleNamespace(endpoint=create_customer))
        body = {"title": "新公司"}
        async with self.sessions() as db:
            with self.assertRaises(HTTPException) as caught:
                await prepare_business_arguments(spec, {"body": body}, {"body": body}, {}, db)
            self.assertEqual(caught.exception.status_code, 422)
            self.assertIn("组织类型", caught.exception.detail)
            self.assertIn("向用户询问", caught.exception.detail)
            ok = {"title": "新公司", "organization_type": "公司企业", "credit_code": CODE}
            arguments = {"body": ok}
            self.assertIs(await prepare_business_arguments(spec, arguments, {"body": ok}, {}, db), arguments)


if __name__ == "__main__":
    unittest.main()


class FinanceFeePreflightHintTest(unittest.IsolatedAsyncioTestCase):
    async def test_fee_preflight_errors_tell_the_agent_to_ask_the_user(self):
        from unittest.mock import AsyncMock, patch
        from app.agent_mcp import business_preflight
        from app.areas.finance.router import create_finance_fee
        spec = SimpleNamespace(_route=SimpleNamespace(endpoint=create_finance_fee))
        with patch.object(business_preflight, "_resolve_fee_arguments", new=AsyncMock(side_effect=HTTPException(422, "费用类型不存在或已停用"))):
            with self.assertRaises(HTTPException) as caught:
                await business_preflight.prepare_business_arguments(spec, {}, {"body": {}}, {}, None)
        self.assertEqual(caught.exception.status_code, 422)
        self.assertIn("费用类型不存在或已停用", caught.exception.detail)
        self.assertIn("向用户询问", caught.exception.detail)
        options = HTTPException(422, {"detail": "费用类型名称存在多个有效分类", "options": [{"id": 1}]})
        with patch.object(business_preflight, "_resolve_fee_arguments", new=AsyncMock(side_effect=options)):
            with self.assertRaises(HTTPException) as caught:
                await business_preflight.prepare_business_arguments(spec, {}, {"body": {}}, {}, None)
        self.assertEqual(caught.exception.detail["options"], [{"id": 1}])
        self.assertIn("向用户询问", caught.exception.detail["hint"])
