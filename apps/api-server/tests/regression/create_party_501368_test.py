"""501368（陶国南 11-04）：新建对方当事人用已查到的企查查工商信息，不再调接口；已有同名客户或当事人不重复建。只用假 Key、假接口。"""

import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.crm import company_lookup as qcc
from app.data_models.parties import PartyRecord
from app.database import Base
from app.models import BusinessRecord, User

LAWYER = {"username": "lawyer", "role": "user", "role_ids": ["user"]}
ADMIN = {"username": "admin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"]}


class CreatePartyTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.calls = []
        self.patches = [patch.object(qcc, "_require_customer_create", self._allow), patch.object(qcc, "_require_company_library", self._allow), patch.object(qcc, "_require_admin", lambda identity: None),
                        patch.object(qcc, "_qcc_get", self.fake_get)]
        for item in self.patches:
            item.start()
        async with self.sessions() as db:
            db.add(User(username="lawyer", display_name="律师", department="诉讼部", is_active=True, password_hash="isolated-only", role="user"))
            await db.commit()

    async def asyncTearDown(self):
        for item in self.patches:
            item.stop()
        await self.engine.dispose()

    async def _allow(self, identity, db):
        return None

    async def fake_get(self, path, params, key, secret):
        self.calls.append(path)
        return {"Status": "200", "Result": {"Name": "合肥鹿山鸣贸易有限公司", "CreditCode": "91340100AAAAAAAAAA", "OperName": "王五",
                                            "Address": "合肥市某路2号", "EconKind": "有限责任公司", "Status": "存续"}}

    async def test_party_uses_looked_up_business_info_without_new_call(self):
        async with self.sessions() as db:
            await qcc.save_qcc_credentials(qcc.CredentialInput(key="fake-key-12345678", secret="fake-secret-87654321"), ADMIN, db)
            await qcc.company_detail("合肥鹿山鸣贸易有限公司", LAWYER, db)
            self.assertEqual(len(self.calls), 1)
            created = await qcc.create_party(qcc.PartyCreateInput(name="合肥鹿山鸣贸易有限公司"), LAWYER, db)
            self.assertEqual(len(self.calls), 1, "新建当事人不再调企查查")
            self.assertTrue(created["party_no"])
            self.assertEqual((created["organization_type"], created["credit_code"], created["business_info_found"]), ("公司企业", "91340100AAAAAAAAAA", True))
            party = await db.get(PartyRecord, created["id"])
            self.assertEqual((party.data["legal_representative"], party.data["registered_address"]), ("王五", "合肥市某路2号"))
            with self.assertRaises(HTTPException) as caught:
                await qcc.create_party(qcc.PartyCreateInput(name="合肥鹿山鸣贸易有限公司"), LAWYER, db)
            self.assertEqual(caught.exception.status_code, 409)

    async def test_existing_customer_is_not_duplicated(self):
        async with self.sessions() as db:
            db.add(BusinessRecord(module="customer", serial_no="KH001", title="上海乙有限公司", customer="上海乙有限公司", status="正常", owner="lawyer", data={}))
            await db.commit()
            with self.assertRaises(HTTPException) as caught:
                await qcc.create_party(qcc.PartyCreateInput(name="上海乙有限公司"), LAWYER, db)
            self.assertEqual(caught.exception.status_code, 409)
            self.assertIn("KH001", caught.exception.detail)
            self.assertEqual(self.calls, [], "没查过的企业也不会因新建当事人去调企查查")

    async def test_library_reuses_archive_and_shows_roles(self):
        async with self.sessions() as db:
            await qcc.save_qcc_credentials(qcc.CredentialInput(key="fake-key-12345678", secret="fake-secret-87654321"), ADMIN, db)
            first = await qcc.lookup_company_library(qcc.CompanyLibraryLookupInput(keyword="合肥鹿山鸣贸易有限公司"), LAWYER, db)
            again = await qcc.lookup_company_library(qcc.CompanyLibraryLookupInput(keyword="91340100AAAAAAAAAA"), LAWYER, db)
            self.assertEqual((first["cached"], again["cached"], len(self.calls)), (False, True, 1), "存档里有就不再扣次数")
            self.assertEqual(first["roles"], {"customers": [], "parties": []}, "查过的企业不是客户也不是当事人")
            listed = await qcc.list_company_library("", 1, 20, LAWYER, db)
            self.assertEqual((listed["total"], listed["items"][0]["credit_code"]), (1, "91340100AAAAAAAAAA"), "同一企业按信用代码合并成一条")
            created = await qcc.create_party(qcc.PartyCreateInput(name="合肥鹿山鸣贸易有限公司"), LAWYER, db)
            listed = await qcc.list_company_library("鹿山", 1, 20, LAWYER, db)
            self.assertEqual(listed["items"][0]["roles"]["parties"][0]["party_no"], created["party_no"])
            await qcc.lookup_company_library(qcc.CompanyLibraryLookupInput(keyword="合肥鹿山鸣贸易有限公司", refresh=True), LAWYER, db)
            self.assertEqual(len(self.calls), 2, "只有重新查询才再扣一次")


class CompanyInfoMenuDefaultTest(unittest.TestCase):
    def test_party_center_users_get_company_info_page(self):
        from app.core.permissions import _expand_menu_permission_keys
        self.assertIn("party-company-info", _expand_menu_permission_keys(["party-mine-civil"]))
        self.assertIn("party-company-info", _expand_menu_permission_keys(["party"]))
        self.assertNotIn("party-company-info", _expand_menu_permission_keys(["customer-company"]))



class AgentAsksPurposeFirstTest(unittest.TestCase):
    """501368（陶国南 11-04 14:23）：没说明用途先问，不先查企查查；说明了就直接查。"""

    def test_rule_and_tool_guidance(self):
        from fastapi.routing import APIRoute
        from app.agent_mcp.operation_guidance import get_operation_guidance
        from app.harness_agent.runtime import oa_persona
        from app.main import app
        persona = oa_persona()
        self.assertIn("没说的，先问是新建客户、新建对方当事人，还是只查一下基本信息，等用户回答后再查，不要先调企查查", persona)
        self.assertIn("说了新建客户、新建对方当事人或查一下基本信息的，直接办", persona)
        for name in ("lookup_company_library", "company_detail"):
            route = next(item for item in app.routes if isinstance(item, APIRoute) and item.endpoint.__name__ == name)
            guidance = get_operation_guidance(route, sorted(route.methods)[0])
            self.assertTrue(any("用途" in text for text in guidance["prerequisites"]), name)


if __name__ == "__main__":
    unittest.main()
