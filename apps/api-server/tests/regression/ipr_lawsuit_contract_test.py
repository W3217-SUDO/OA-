"""Isolated API contract for IPR litigation records, courts, parties and fees."""

import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {"username": "ipr-lawsuit-admin", "role": "admin", "display_name": "IPR Lawsuit Admin", "department": "IPR"}


class IprLawsuitContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.identity = dict(IDENTITY)
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], password_hash="test", role="admin"),
                User(username="ipr-lawsuit-viewer", display_name="IPR Lawsuit Viewer", department=IDENTITY["department"], password_hash="test", role="user"),
            ])
            rows = [
                BusinessRecord(module="ipr_case", serial_no="IPR-LAWSUIT-001", title="litigation", customer="客户", status="在办", owner=IDENTITY["username"], department="IPR", data={"case_kind": "专利", "case_category": "litigation", "litigation_courts": [], "litigation_parties": [], "shared_to": ["ipr-lawsuit-viewer"]}),
                BusinessRecord(module="ipr_case", serial_no="IPR-NONLIT-001", title="non litigation", customer="客户", status="在办", owner=IDENTITY["username"], department="IPR", data={"case_kind": "专利"}),
                BusinessRecord(module="ipr_case", serial_no="IPR-LAWSUIT-ARCHIVED", title="archived", customer="客户", status="归档", owner=IDENTITY["username"], department="IPR", data={"case_kind": "商标", "case_category": "litigation"}),
                BusinessRecord(module="ipr_case", serial_no="IPR-LAWSUIT-002", title="other litigation", customer="客户", status="在办", owner=IDENTITY["username"], department="IPR", data={"case_kind": "专利", "case_category": "litigation"}),
            ]
            db.add_all(rows)
            await db.flush()
            self.lawsuit_id, self.non_litigation_id, self.archived_id, self.other_lawsuit_id = [row.id for row in rows]
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ipr-lawsuit.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_lawsuit_data_isolated_from_non_litigation_and_archived_records(self):
        lawsuit_list = await self.client.get(f"{API}/ipr/lawsuit/cases?page_size=100")
        self.assertEqual(lawsuit_list.status_code, 200, lawsuit_list.text)
        self.assertEqual({row["id"] for row in lawsuit_list.json()["items"]}, {self.lawsuit_id, self.archived_id, self.other_lawsuit_id})
        non_litigation_list = await self.client.get(f"{API}/ipr/cases?case_category=non_litigation&page_size=100")
        self.assertEqual(non_litigation_list.status_code, 200, non_litigation_list.text)
        self.assertEqual([row["id"] for row in non_litigation_list.json()["items"]], [self.non_litigation_id])
        invalid = await self.client.get(f"{API}/ipr/cases?case_category=bad")
        self.assertEqual(invalid.status_code, 422, invalid.text)

        court_info = await self.client.put(f"{API}/ipr/lawsuit/cases/{self.lawsuit_id}/court-info", json={"court_case_no": "(2026)沪01民初1号", "court_name": "上海知识产权法院", "judge": "法官", "clerk": "书记员", "plaintiff": "客户", "defendant": "被告", "third_parties": "第三人"})
        self.assertEqual(court_info.status_code, 200, court_info.text)
        self.assertEqual(court_info.json()["court_name"], "上海知识产权法院")
        cannot_reclassify = await self.client.patch(f"{API}/ipr/cases/{self.lawsuit_id}", json={"case_category": "non_litigation"})
        self.assertEqual(cannot_reclassify.status_code, 409, cannot_reclassify.text)
        self.identity = {"username": "ipr-lawsuit-viewer", "role": "user", "display_name": "IPR Lawsuit Viewer", "department": "IPR"}
        forbidden = await self.client.post(f"{API}/ipr/lawsuit/cases/{self.lawsuit_id}/courts", json={"court_name": "不可越权写入"})
        self.assertEqual(forbidden.status_code, 403, forbidden.text)
        self.identity = dict(IDENTITY)
        non_litigation = await self.client.post(f"{API}/ipr/lawsuit/cases/{self.non_litigation_id}/courts", json={"court_name": "不可写入"})
        self.assertEqual(non_litigation.status_code, 422, non_litigation.text)
        archived = await self.client.post(f"{API}/ipr/lawsuit/cases/{self.archived_id}/courts", json={"court_name": "不可写入"})
        self.assertEqual(archived.status_code, 409, archived.text)

    async def test_court_party_and_fee_persist_on_the_lawsuit_case_only(self):
        first = await self.client.post(f"{API}/ipr/lawsuit/cases/{self.lawsuit_id}/courts", json={"court_level": "一审", "court_name": "上海知识产权法院", "case_no": "(2026)沪01民初1号", "judge": "法官", "clerk": "书记员"})
        second = await self.client.post(f"{API}/ipr/lawsuit/cases/{self.lawsuit_id}/courts", json={"court_level": "二审", "court_name": "上海市高级人民法院", "case_no": "(2026)沪民终2号"})
        self.assertEqual((first.status_code, second.status_code), (201, 201))
        courts = await self.client.get(f"{API}/ipr/lawsuit/cases/{self.lawsuit_id}/courts")
        self.assertEqual(courts.json()["total"], 2)
        deleted = await self.client.delete(f"{API}/ipr/lawsuit/cases/{self.lawsuit_id}/courts/{first.json()['id']}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual((await self.client.delete(f"{API}/ipr/lawsuit/cases/{self.lawsuit_id}/courts/{first.json()['id']}")).status_code, 404)
        party = await self.client.post(f"{API}/ipr/lawsuit/cases/{self.lawsuit_id}/parties", json={"party_type": "原告", "name": "客户", "contact_name": "联系人", "contact_phone": "13800000000"})
        self.assertEqual(party.status_code, 201, party.text)
        self.assertEqual((await self.client.get(f"{API}/ipr/lawsuit/cases/{self.lawsuit_id}/parties")).json()["items"][0]["name"], "客户")

        bad_amount = await self.client.post(f"{API}/ipr/cases/{self.lawsuit_id}/fees", json={"amount": 0, "fee_type": "官方费用"})
        self.assertEqual(bad_amount.status_code, 422, bad_amount.text)
        fee = await self.client.post(f"{API}/ipr/cases/{self.lawsuit_id}/fees", json={"title": "诉讼费", "amount": 100, "fee_type": "官方费用", "court": "上海知识产权法院"})
        self.assertEqual(fee.status_code, 201, fee.text)
        self.assertEqual(fee.json()["title"], "诉讼费")
        self.assertEqual((await self.client.get(f"{API}/ipr/cases/{self.lawsuit_id}/fees")).json()["total"], 1)
        self.assertIn((await self.client.delete(f"{API}/ipr/cases/{self.other_lawsuit_id}/fees/{fee.json()['id']}")).status_code, {404, 409})
        self.assertEqual((await self.client.delete(f"{API}/ipr/cases/{self.lawsuit_id}/fees/{fee.json()['id']}")).status_code, 204)


if __name__ == "__main__":
    unittest.main()
