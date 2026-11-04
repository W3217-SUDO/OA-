"""501337：线索、证物（公证书号/仓库位置）、该线索的费用为一体，移任何一项整条一起移到目标案件。"""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, JobRole, SystemParameter, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "p337-handler",
    "role": "user",
    "role_ids": ["user"],
    "display_name": "经办人337",
    "department": "诉讼部",
}


ADMIN = {**IDENTITY, "role": "admin", "role_ids": ["admin"]}


class ClueBundleMove501337Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department="诉讼部", role="admin", role_ids=["admin"],
                        password_hash="x", profile={}, is_active=True))
            db.add(User(username="sugq", display_name="苏贵全", department="调查部", role="user", role_ids=["user"], password_hash="x", profile={}, is_active=True))
            clue = BusinessRecord(module="clue", serial_no="M337", title="店铺", customer="客户", status="已转案件", owner="sugq", department="调查部", data={})
            other = BusinessRecord(module="clue", serial_no="M338", title="店铺2", customer="客户", status="已转案件", owner="sugq", department="调查部", data={})
            kept = BusinessRecord(module="clue", serial_no="M339", title="目标原有线索", customer="客户", status="已转案件", owner="sugq", department="调查部", data={})
            db.add_all([clue, other, kept])
            await db.flush()
            common = {"case_type": "民事争议", "customer_record_id": 9}
            source = BusinessRecord(module="case", serial_no="A337", title="A", customer="客户", status="文书准备", owner=IDENTITY["username"], department="诉讼部",
                                    data={**common, "investigation_clue_ids": [clue.id, other.id], "investigation_clue_nos": ["M337", "M338"]})
            target = BusinessRecord(module="case", serial_no="B337", title="B", customer="客户", status="文书准备", owner=IDENTITY["username"], department="诉讼部",
                                    data={**common, "investigation_clue_ids": [kept.id], "investigation_clue_nos": ["M339"]})
            db.add_all([source, target])
            await db.flush()
            clue.data = {"case_id": source.id, "case_record_id": source.id, "case_no": "A337"}
            evidence = BusinessRecord(module="evidence", serial_no="EV337", title="证物", customer="客户", status="已入库", owner="sugq", department="调查部",
                                      data={"clue_record_id": clue.id, "clue_no": "M337", "case_no": "A337", "certificate_no": "(2025)第1号"})
            notary = BusinessRecord(module="finance", serial_no="FY337A", title="公证费", customer="客户", status="已通知", owner=IDENTITY["username"], department="诉讼部",
                                    data={"case_id": source.id, "case_record_id": source.id, "case_no": "A337", "expense_scope": "律所", "amount": 300})
            service = BusinessRecord(module="finance", serial_no="FY337B", title="公证服务费", customer="客户", status="已通知", owner=IDENTITY["username"], department="诉讼部",
                                     data={"case_id": source.id, "case_record_id": source.id, "case_no": "A337", "expense_scope": "律所", "amount": 50, "clue_record_id": clue.id})
            court = BusinessRecord(module="finance", serial_no="FY337C", title="一审诉讼费", customer="客户", status="已通知", owner=IDENTITY["username"], department="诉讼部",
                                   data={"case_id": source.id, "case_record_id": source.id, "case_no": "A337", "expense_scope": "律所", "amount": 100})
            db.add_all([evidence, notary, service, court])
            await db.commit()
            self.ids = {"kept": kept.id, "clue": clue.id, "other": other.id, "source": source.id, "target": target.id, "evidence": evidence.id,
                        "notary": notary.id, "service": service.id, "court": court.id}
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://p337.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def record(self, key: str) -> BusinessRecord:
        async with self.sessions() as db:
            return await db.get(BusinessRecord, self.ids[key])

    async def assert_bundle_moved(self) -> None:
        for key in ("clue", "evidence", "notary", "service"):
            self.assertEqual((await self.record(key)).data["case_no"], "B337", key)
        self.assertEqual((await self.record("court")).data["case_no"], "A337")
        source, target = await self.record("source"), await self.record("target")
        self.assertEqual(source.data["investigation_clue_ids"], [self.ids["other"]])
        # fwl 11-04：目标案件原有线索保留，移入的叠加
        self.assertEqual(target.data["investigation_clue_ids"], [self.ids["kept"], self.ids["clue"]])
        self.assertEqual(target.data["investigator_usernames"], ["sugq", "sugq"])

    async def test_fee_move_with_chosen_clue_moves_whole_clue(self) -> None:
        response = await self.client.post(f"{API}/finance/fees/{self.ids['notary']}/move-case", json={"target_case_no": "B337", "clue_id": self.ids["clue"]})
        self.assertEqual(response.status_code, 200, response.text)
        await self.assert_bundle_moved()

    async def test_clue_move_entry_moves_evidence_and_fees(self) -> None:
        preview = await self.client.get(f"{API}/cases/{self.ids['source']}/clues/{self.ids['clue']}/bundle")
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual([item["serial_no"] for item in preview.json()["fees"]], ["FY337B"])
        response = await self.client.post(f"{API}/cases/{self.ids['source']}/clues/{self.ids['clue']}/move-case", json={"target_case_no": "B337"})
        self.assertEqual(response.status_code, 200, response.text)
        for key in ("clue", "evidence", "service"):
            self.assertEqual((await self.record(key)).data["case_no"], "B337", key)
        self.assertEqual((await self.record("notary")).data["case_no"], "A337")  # 没记属于哪条线索、也没选的公证费不动

    async def test_fee_without_clue_moves_alone(self) -> None:
        response = await self.client.post(f"{API}/finance/fees/{self.ids['court']}/move-case", json={"target_case_no": "B337"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.record("court")).data["case_no"], "B337")
        self.assertEqual((await self.record("clue")).data["case_no"], "A337")


if __name__ == "__main__":
    unittest.main()
