"""待缴官费：先按费用自身类型挑候选、只对候选聚合，结果必须与全量聚合后再筛选完全一致。"""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core import finance
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity


IDENTITY = {"username": "admin", "role": "admin"}


def dump(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


class UnpaidOfficialFeeCandidatesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="admin", display_name="管理员", department="测试部", role="admin", password_hash="x", is_active=True))
            db.add(User(username="other", display_name="他人", department="测试部", role="user", password_hash="x", is_active=True))
            for case_no in ("CODEX-OF-CASE-A", "CODEX-OF-CASE-B"):
                db.add(BusinessRecord(module="case", serial_no=case_no, title=case_no, customer="客户", status="一审",
                                      owner="admin", department="测试部", data={"hearing_lawyer": "范文玲"}))
            fees = [
                # (编号, 负责人, 状态, 标题, data)
                ("OF-1", "admin", "已审批", "官方费用", {"fee_type": "官方费用", "amount": 300, "case_no": "CODEX-OF-CASE-A"}),
                ("OF-2", "other", "已审批", "诉讼费", {"fee_type": "其他费用", "fee_type_name": "一审诉讼费", "amount": 500, "case_no": "CODEX-OF-CASE-A"}),
                ("OF-3", "admin", "已审批", "保全", {"fee_type": "其他费用", "expense_subtype": "保全费", "amount": 80, "case_no": "CODEX-OF-CASE-B"}),
                ("OF-4", "admin", "已审批", "执行费", {"amount": 60, "case_no": "CODEX-OF-CASE-B"}),
                ("OF-5", "admin", "已付款", "官方费用", {"fee_type": "官方费用", "amount": 200, "case_no": "CODEX-OF-CASE-B"}),
                ("OF-6", "admin", "已审批", "官方费用", {"fee_type": "官方费用", "amount": 100, "paid_amount": 100, "case_no": "CODEX-OF-CASE-B"}),
                ("OF-7", "admin", "已审批", "代理费", {"fee_type": "代理费", "amount": 1000, "case_no": "CODEX-OF-CASE-A"}),
                ("OF-8", "admin", "已删除", "官方费用", {"fee_type": "官方费用", "amount": 70, "case_no": "CODEX-OF-CASE-A"}),
                ("OF-9", "admin", "已审批", "官方费用", {"fee_type": "官方费用", "amount": 90, "case_no": "CODEX-OF-CASE-C"}),
            ]
            # 足量非官费，使候选占比低于一半，确保走候选子集路径。
            fees += [(f"AG-{index}", "admin", "已审批", "代理费", {"fee_type": "代理费", "amount": 50, "case_no": "CODEX-OF-CASE-D"})
                     for index in range(10)]
            for serial_no, owner, status, title, data in fees:
                db.add(BusinessRecord(module="finance", serial_no=f"CODEX-{serial_no}", title=title, customer="客户",
                                      status=status, owner=owner, department="测试部", data=data))
            # 只按案号关联的旧发票：案件 A 有多笔费用，不能被唯一归属；案件 C 只有一笔官费。
            db.add(BusinessRecord(module="invoice", serial_no="CODEX-OF-INV-A", title="发票", customer="客户", status="已开票",
                                  owner="admin", department="测试部", data={"case_no": "CODEX-OF-CASE-A", "amount": 300}))
            db.add(BusinessRecord(module="invoice", serial_no="CODEX-OF-INV-C", title="发票", customer="客户", status="已开票",
                                  owner="admin", department="测试部", data={"case_no": "CODEX-OF-CASE-C", "amount": 90}))
            await db.commit()

    async def asyncTearDown(self):
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def dashboard_identity(self, db, exclude=()):
        """工作台待缴官费入口：授权费用集合放在 _dashboard_fee_ids 中。"""
        ids = set((await db.scalars(select(BusinessRecord.id).where(BusinessRecord.module == "finance"))).all())
        return {**IDENTITY, "_dashboard_fee_ids": ids - set(exclude)}

    async def test_candidate_subset_matches_full_aggregation(self):
        async with self.sessions() as db:
            hidden = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-OF-3"))
            for label, identity in (("all", await self.dashboard_identity(db)),
                                    ("partial", await self.dashboard_identity(db, exclude={hidden}))):
                for summary_only in (True, False):
                    with self.subTest(identity=label, summary_only=summary_only):
                        with patch.object(finance, "OFFICIAL_FEE_CANDIDATE_LIMIT", -1):
                            full = await finance._fee_query_rows(identity, db, unpaid_official=True, summary_only=summary_only)
                        with patch.object(finance, "OFFICIAL_FEE_NARROWING_MIN_SCANNED", 0):
                            narrowed = await finance._fee_query_rows(identity, db, unpaid_official=True, summary_only=summary_only)
                        self.assertEqual(dump(narrowed), dump(full))
            with patch.object(finance, "OFFICIAL_FEE_NARROWING_MIN_SCANNED", 0):
                rows = await finance._fee_query_rows(await self.dashboard_identity(db), db, unpaid_official=True, summary_only=True)
        self.assertEqual({row["serial_no"] for row in rows}, {"CODEX-OF-1", "CODEX-OF-2", "CODEX-OF-3", "CODEX-OF-4", "CODEX-OF-9"})

    async def test_endpoint_response_is_unchanged(self):
        async def override_db():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://official-fee.test") as client:
            for url in ("/api/v1/finance/fees/query?unpaid_official=true&scope=company&page=1&page_size=2",
                        "/api/v1/finance/fees/query?unpaid_official=true&scope=company&page=2&page_size=2"):
                with self.subTest(url=url):
                    with patch.object(finance, "OFFICIAL_FEE_CANDIDATE_LIMIT", -1):
                        full = await client.get(url)
                    with patch.object(finance, "OFFICIAL_FEE_NARROWING_MIN_SCANNED", 0):
                        narrowed = await client.get(url)
                    self.assertEqual(full.status_code, 200, full.text)
                    self.assertEqual(dump(narrowed.json()), dump(full.json()))

    async def test_narrowing_applies_only_when_it_helps(self):
        async with self.sessions() as db:
            identity = await self.dashboard_identity(db)
            candidates, scanned = await finance._official_fee_candidate_ids(
                identity, db, scope="company", ids=None, scope_authorized_fee_ids=identity["_dashboard_fee_ids"])
            self.assertEqual(len(candidates), 7)  # OF-1..6、OF-9；已删除的 OF-8 和代理费不在内
            self.assertEqual(scanned, 18)
            calls = []
            original = finance._invoice_case_fee_rows

            async def spy(*args, **kwargs):
                calls.append(kwargs.get("ids"))
                return await original(*args, **kwargs)

            with patch.object(finance, "_invoice_case_fee_rows", spy):
                # 授权集合未达阈值、或普通记录范围查询：不预筛。
                await finance._fee_query_rows(identity, db, unpaid_official=True, summary_only=True)
                with patch.object(finance, "OFFICIAL_FEE_NARROWING_MIN_SCANNED", 0):
                    await finance._fee_query_rows(IDENTITY, db, scope="company", unpaid_official=True, summary_only=True)
                    await finance._fee_query_rows(identity, db, unpaid_official=True, summary_only=True)
            self.assertIsNone(calls[0])
            self.assertIsNone(calls[1])
            self.assertEqual(calls[2], candidates)

    async def test_large_id_sets_match_plain_in(self):
        async with self.sessions() as db:
            existing = set((await db.scalars(select(BusinessRecord.id))).all())
            for extra in (0, 5000):
                wanted = existing | set(range(100000, 100000 + extra))
                with self.subTest(size=len(wanted)):
                    found = set((await db.scalars(select(BusinessRecord.id).where(finance._record_id_in(wanted)))).all())
                    self.assertEqual(found, existing)

    async def test_no_official_fee_returns_empty(self):
        async with self.sessions() as db:
            self.assertEqual(await finance._fee_query_rows(IDENTITY, db, scope="company", unpaid_official=True,
                                                           ids={999999}, summary_only=True), [])


if __name__ == "__main__":
    unittest.main()
