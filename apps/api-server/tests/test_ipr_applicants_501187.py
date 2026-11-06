"""501187：案号 HZ+类型简码+年份+流水；手填的新申请人进非诉申请人库，已有的不重复；客户只有系统管理员能改。"""
import unittest
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, IprApplicant, IprApplicantCase, RolePermission, SystemParameter, User
from app.security import create_token
from tests.personnel_role_fixture import bind_system_role_pages

API = settings.api_prefix
YEAR = f"{datetime.now():%y}"


class IprApplicantsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add_all([
                User(username="IPRSTAFF", display_name="知产", password_hash="x", department="D", role="user"),
                User(username="IPRADMIN", display_name="管理", password_hash="x", department="D", role="admin"),
                RolePermission(role="user", display_name="普通员工", data_scope="全所数据", menu_keys=["ipr", "ipr-patent", "ipr-trademark", "party", "party-ipr-applicants"], field_keys=[]),
                SystemParameter(category="ipr_case_type", code="1", name="国内发明专利", extra={"short_code": "PI"}, is_active=True),
                SystemParameter(category="ipr_case_type", code="4", name="国内商标", extra={"short_code": "TM"}, is_active=True),
                BusinessRecord(module="customer", serial_no="C1", title="已有客户公司", owner="IPRSTAFF", status="正常", customer="已有客户公司", data={"customer_type": "客户"}),
            ])
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        await bind_system_role_pages(self.sessions)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
                                        headers={"Authorization": f"Bearer {create_token('IPRSTAFF', 'user', 30)}"})

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.pop(get_db, None)
        await self.engine.dispose()

    async def _create(self, **extra):
        body = {"case_kind": "专利", "title": "案件", "customer": "已有客户公司", "application_type": "国内发明专利",
                "agent": "IPRSTAFF", "writer": "IPRSTAFF", "card_no": "A1", "inventor": "张三", **extra}
        response = await self.client.post(f"{API}/ipr/cases", json=body)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_serial_format_and_shared_sequence(self):
        first = await self._create(applicant="甲公司")
        second = await self._create(case_kind="商标", application_type="国内商标", applicant="乙公司")
        self.assertEqual(first["serial_no"], f"HZPI{YEAR}00001")
        self.assertEqual(second["serial_no"], f"HZTM{YEAR}00002")
        self.assertEqual(first["data"]["case_type_name"], "国内发明专利")

    async def test_manual_applicant_registered_once_and_existing_not_duplicated(self):
        first = await self._create(applicant="甲公司，已有客户公司")
        await self._create(applicant="甲公司")
        async with self.sessions() as db:
            names = list((await db.scalars(select(IprApplicant.name))).all())
            links = list((await db.scalars(select(IprApplicantCase))).all())
        self.assertEqual(names, ["甲公司"])
        self.assertEqual(len(links), 2)
        saved = await self.client.patch(f"{API}/ipr/cases/{first['id']}/info", json={"applicant_name": "丙公司"})
        self.assertEqual(saved.status_code, 200, saved.text)
        async with self.sessions() as db:
            self.assertEqual(set((await db.scalars(select(IprApplicant.name))).all()), {"甲公司", "丙公司"})
            links = (await db.scalars(select(IprApplicantCase).where(IprApplicantCase.case_id == first["id"]))).all()
        self.assertEqual(len(links), 1)
        back = await self.client.patch(f"{API}/ipr/cases/{first['id']}/info", json={"applicant_name": "甲公司"})
        self.assertEqual(back.status_code, 200, back.text)  # 改回原申请人不能撞关联的唯一约束

    async def test_options_search_all_three_sources(self):
        await self._create(applicant="甲公司")
        data = (await self.client.get(f"{API}/ipr/applicant-options", params={"keyword": "公司"})).json()["items"]
        self.assertEqual({(item["value"], item["source"]) for item in data}, {("已有客户公司", "客户"), ("甲公司", "申请人库")})

    async def test_library_page_and_customer_gate(self):
        case = await self._create(applicant="甲公司")
        rows = (await self.client.get(f"{API}/party-library/ipr-applicants")).json()
        self.assertEqual(rows["items"][0]["cases"][0]["case_no"], case["serial_no"])
        denied = await self.client.put(f"{API}/ipr/cases/{case['id']}/customers", json={"customer_ids": [1], "primary_customer_id": 1})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["detail"], "客户仅管理员可修改")


if __name__ == "__main__":
    unittest.main()
