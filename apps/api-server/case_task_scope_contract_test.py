"""Executable contract for independent case/customer task pagination."""

from __future__ import annotations

import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.main import list_case_tasks
from app.models import BusinessRecord, User


class CaseTaskScopeContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(
                sync, tables=[BusinessRecord.__table__, User.__table__],
            ))
        sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.db = sessions()
        self.db.add(User(
            username="admin", password_hash="unused", display_name="管理者",
            role="admin", department="上海分所",
        ))
        self.case = BusinessRecord(
            module="case", serial_no="CASE-SCOPE-1", title="案件",
            customer="客户", status="一审", owner="admin", department="上海分所", data={},
        )
        self.db.add(self.case)
        await self.db.flush()
        self.db.add_all([
            BusinessRecord(
                module="task", serial_no="TASK-CASE-1", title="案件任务",
                customer="客户", status="待接收", owner="admin", department="上海分所",
                data={"case_id": self.case.id, "source": "案件任务", "initiator": "admin"},
            ),
            BusinessRecord(
                module="task", serial_no="TASK-CUSTOMER-1", title="客户任务",
                customer="客户", status="待接收", owner="admin", department="上海分所",
                data={"case_id": self.case.id, "source": "客户任务", "initiator": "admin"},
            ),
        ])
        await self.db.commit()

    async def asyncTearDown(self) -> None:
        await self.db.close()
        await self.engine.dispose()

    async def test_scopes_return_matching_rows_and_totals(self) -> None:
        identity = {"username": "admin", "role": "admin"}
        case_page = await list_case_tasks(self.case.id, 1, 15, "case", identity, self.db)
        customer_page = await list_case_tasks(self.case.id, 1, 15, "customer", identity, self.db)

        self.assertEqual(case_page["total"], 1)
        self.assertEqual([item["serial_no"] for item in case_page["items"]], ["TASK-CASE-1"])
        self.assertEqual(customer_page["total"], 1)
        self.assertEqual([item["serial_no"] for item in customer_page["items"]], ["TASK-CUSTOMER-1"])


if __name__ == "__main__":
    unittest.main()
