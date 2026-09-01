import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import InvestigationTaskInput, create_investigation_task
from app.models import BusinessRecord, User, WorkflowEvent


class InvestigationContractRelationRow19Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    def _payload(self):
        return InvestigationTaskInput(
            title="审批中合同调查子任务", owner="investigator",
            deadline=date(2026, 9, 12), start_date=date(2026, 8, 13),
            end_date=date(2026, 9, 12), province="北京市", city="市辖区", district="东城区",
        )

    async def _seed(self, db, valid_status="审批中"):
        db.add_all([
            User(username="admin", display_name="管理员", department="总部", password_hash="x", role="admin"),
            User(username="investigator", display_name="调查员", department="调查部", password_hash="x", role="user"),
        ])
        stale = BusinessRecord(
            module="contract", serial_no="SHHT-DELETED-DRAFT", title="旧草稿投影",
            customer="测试客户12", status="草稿", owner="admin", department="总部", data={},
        )
        valid = BusinessRecord(
            module="contract", serial_no="SHHT2673398", title="测试合同部",
            customer="测试客户12", status=valid_status, owner="admin", department="总部", data={},
        )
        db.add_all([stale, valid])
        await db.flush()
        source = BusinessRecord(
            module="investigation", serial_no="DC202608131401163F21",
            title="测试合同部调查任务", customer="测试客户12", status="进行中",
            owner="admin", department="总部",
            data={
                "contract_id": stale.id,
                "contract_record_id": stale.id,
                "contract_no": valid.serial_no,
                "authorized_from": "2026-08-13", "authorized_to": "2026-09-12",
            },
        )
        db.add(source)
        await db.commit()
        return source, stale, valid

    async def test_contract_number_repairs_stale_id_and_allows_pending_contract(self):
        async with self.sessions() as db:
            source, stale, valid = await self._seed(db)

            created = await create_investigation_task(
                source.id, self._payload(), {"username": "admin", "role": "admin"}, db
            )
            await db.refresh(source)
            events = list((await db.execute(
                WorkflowEvent.__table__.select().where(WorkflowEvent.record_id == source.id)
            )).mappings())

        self.assertNotEqual(stale.id, valid.id)
        self.assertEqual(created["data"]["contract_record_id"], valid.id)
        self.assertEqual(created["data"]["contract_no"], "SHHT2673398")
        self.assertEqual(source.data["contract_id"], valid.id)
        self.assertEqual(source.data["contract_record_id"], valid.id)
        self.assertTrue(any(event["action"] == "修复调查事项合同关联" for event in events))

    async def test_contract_number_does_not_bypass_draft_status(self):
        async with self.sessions() as db:
            source, _, _ = await self._seed(db, valid_status="草稿")

            with self.assertRaises(HTTPException) as raised:
                await create_investigation_task(
                    source.id, self._payload(), {"username": "admin", "role": "admin"}, db
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "草稿合同不能创建调查子任务")


if __name__ == "__main__":
    unittest.main()
