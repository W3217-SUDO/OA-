"""10.22 第8行：案件律所/平台费用“移到其他案子”。

用户答复“全按照建议”：手输目标案件编号；同一客户按客户记录 ID → 客户编号 → 名称；
合同号保留；有后续单据的费用不允许迁移；归档中/已归档/已合并案件不能迁出迁入；
只限律所、平台费用；两案和费用各记一条系统日志；权限 case.fee.move。

10.26 第11行：只保留“同一客户、一次一条”两条限制——已有后续单据、已归档/已合并案件都允许迁移。
"""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, Department, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
PREFIX = "CODEX-1022-8-"
IDENTITY = {
    "username": "codex-1022-8-admin",
    "role": "admin",
    "role_ids": ["admin"],
    "display_name": "CODEX-1022-8 管理员",
    "department": "诉讼一部",
}


class CaseFeeMove1022Row8Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(Department(code="CODEX-1022-8-DEPT", name=IDENTITY["department"], is_active=True))
            db.add(User(
                username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"],
                role="admin", role_ids=["admin"], password_hash="x", profile={"position": "律师"}, is_active=True,
            ))
            source = self._case("SRC", customer_id=101, customer="CODEX 客户甲")
            target = self._case("DST", customer_id=101, customer="CODEX 客户甲（改名）")
            other = self._case("OTHER", customer_id=202, customer="CODEX 客户甲")
            archived = self._case("ARCH", customer_id=101, customer="CODEX 客户甲", status="已归档")
            db.add_all([source, target, other, archived])
            await db.flush()
            self.source, self.target = source, target
            self.fee = self._fee("FEE", source, scope="律所")
            self.platform_fee = self._fee("PFEE", source, scope="平台")
            self.internal_fee = self._fee("IFEE", source, scope="内部")
            self.paid_fee = self._fee("PAID", source, scope="律所", extra={"payment_requested_amount": 100})
            self.commission_source = self._fee("COMM", source, scope="律所")
            db.add_all([self.fee, self.platform_fee, self.internal_fee, self.paid_fee, self.commission_source])
            await db.flush()
            db.add(BusinessRecord(
                module="finance", serial_no=f"{PREFIX}COMMISSION", title="提成", customer=source.customer, status="待审批",
                owner=IDENTITY["username"], department=IDENTITY["department"],
                data={"expense_scope": "内部", "source_fee_id": self.commission_source.id, "case_id": source.id, "case_no": source.serial_no, "amount": 10},
            ))
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://case-fee-move-1022.test")

    @staticmethod
    def _case(code: str, *, customer_id: int, customer: str, status: str = "在办") -> BusinessRecord:
        return BusinessRecord(
            module="case", serial_no=f"{PREFIX}{code}", title=f"{code} 案件", customer=customer, status=status,
            owner=IDENTITY["username"], department=IDENTITY["department"],
            data={"case_type": "民事争议", "customer_id": customer_id, "customer_record_id": customer_id,
                  "case_team_usernames": [IDENTITY["username"]], "contract_no": f"{PREFIX}HT-{code}"},
        )

    @staticmethod
    def _fee(code: str, case: BusinessRecord, *, scope: str, extra: dict | None = None) -> BusinessRecord:
        return BusinessRecord(
            module="finance", serial_no=f"{PREFIX}{code}", title=f"{code} 费用", customer=case.customer, status="草稿",
            owner=IDENTITY["username"], department=IDENTITY["department"],
            data={"expense_scope": scope, "fee_type": "官费", "amount": 100, "case_id": case.id, "case_record_id": case.id,
                  "case_no": case.serial_no, "converted_case_no": case.serial_no, "contract_no": f"{PREFIX}HT-FEE", **(extra or {})},
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def _move(self, fee_id: int, target_no: str, **extra):
        return await self.client.post(f"{API}/finance/fees/{fee_id}/move-case", json={"target_case_no": target_no, **extra})

    async def _fee_case_no(self, fee_id: int) -> str:
        async with self.sessions() as db:
            return (await db.get(BusinessRecord, fee_id)).data["case_no"]

    async def test_move_firm_and_platform_fee_to_same_customer_case(self) -> None:
        for fee in (self.fee, self.platform_fee):
            response = await self._move(fee.id, f"{PREFIX}DST")
            self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            moved = await db.get(BusinessRecord, self.fee.id)
            self.assertEqual(moved.data["case_id"], self.target.id)
            self.assertEqual(moved.data["case_record_id"], self.target.id)
            self.assertEqual(moved.data["case_no"], f"{PREFIX}DST")
            self.assertEqual(moved.data["converted_case_no"], f"{PREFIX}DST")
            self.assertEqual(moved.data["contract_no"], f"{PREFIX}HT-FEE", "合同编号保留原值")
            self.assertEqual(moved.data["moved_from_case_no"], f"{PREFIX}SRC")
            events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.action == "案件费用移到其他案件"))).all()
            self.assertEqual({event.record_id for event in events}, {self.fee.id, self.platform_fee.id, self.source.id, self.target.id})
        source_fees = (await self.client.get(f"{API}/cases/{self.source.id}/relations", params={"include": "fees"})).json()
        target_fees = (await self.client.get(f"{API}/cases/{self.target.id}/relations", params={"include": "fees"})).json()
        source_ids = {item["id"] for item in source_fees.get("fees") or []}
        target_ids = {item["id"] for item in target_fees.get("fees") or []}
        self.assertNotIn(self.fee.id, source_ids)
        self.assertIn(self.fee.id, target_ids)
        self.assertIn(self.platform_fee.id, target_ids)

    async def test_rejected_moves_leave_fee_unchanged(self) -> None:
        cases = (
            (self.fee.id, f"{PREFIX}OTHER", 422, "同一客户"),
            (self.fee.id, f"{PREFIX}SRC", 422, "相同"),
            (self.fee.id, f"{PREFIX}NOPE", 404, "未找到目标案件"),
            (self.internal_fee.id, f"{PREFIX}DST", 422, "律所费用和平台费用"),
        )
        for fee_id, target_no, status_code, text in cases:
            response = await self._move(fee_id, target_no)
            self.assertEqual(response.status_code, status_code, (target_no, response.text))
            self.assertIn(text, response.text)
            self.assertEqual(await self._fee_case_no(fee_id), f"{PREFIX}SRC")

    async def test_no_extra_limits_beyond_customer_and_single_fee(self) -> None:
        """10.26 第11行：有后续单据的费用、已归档的目标案件都允许迁移。"""
        for fee_id, target_no in (
            (self.paid_fee.id, f"{PREFIX}DST"),
            (self.commission_source.id, f"{PREFIX}DST"),
            (self.fee.id, f"{PREFIX}ARCH"),
        ):
            response = await self._move(fee_id, target_no)
            self.assertEqual(response.status_code, 200, (target_no, response.text))
            self.assertEqual(await self._fee_case_no(fee_id), target_no)

    async def test_only_one_fee_per_request_and_target_required(self) -> None:
        response = await self._move(self.fee.id, f"{PREFIX}DST", fee_ids=[self.fee.id, self.platform_fee.id])
        self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.post(f"{API}/finance/fees/{self.fee.id}/move-case", json={"target_case_no": ""})
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(await self._fee_case_no(self.fee.id), f"{PREFIX}SRC")

    async def test_capability_exposed_for_admin(self) -> None:
        response = await self.client.get(f"{API}/cases/{self.source.id}/action-capabilities")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json().get("can_move_fee"))


if __name__ == "__main__":
    unittest.main()
