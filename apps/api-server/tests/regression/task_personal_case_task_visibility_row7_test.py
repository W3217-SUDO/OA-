"""8.31 row 7: case tasks remain visible in the recipient's accepted queue."""

from datetime import date, timedelta
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import list_tasks
from app.models import BusinessRecord, User


IDENTITY = {
    "username": "fwl",
    "role": "user",
    "display_name": "范文林",
    "department": "测试部",
}


class TaskPersonalCaseTaskVisibilityRow7Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    @staticmethod
    def task(serial_no: str, source: str) -> BusinessRecord:
        return BusinessRecord(
            module="task",
            serial_no=serial_no,
            title=serial_no,
            customer="8.31测试客户",
            status="处理中",
            owner="fwl",
            department="测试部",
            data={
                "deadline": str(date.today() + timedelta(days=7)),
                "priority": "普通",
                "source": source,
                "initiator": "admin",
                "collaborators": [],
                "case_no": "SHMS2600436" if source == "案件任务" else "",
            },
        )

    async def test_processing_filter_returns_case_and_ordinary_tasks_for_recipient(self) -> None:
        async with self.sessions() as db:
            db.add(User(
                username="fwl", display_name="范文林", department="测试部",
                role="user", password_hash="x", is_active=True,
            ))
            db.add_all([
                self.task("CODEX-831-R7-CASE", "案件任务"),
                self.task("CODEX-831-R7-DAILY", "日常任务"),
            ])
            await db.commit()

            result = await list_tasks(
                keyword="", status_filter="", reminder_only=False,
                scope="mine", relation="owned", statuses="处理中",
                page_id=None, priority="", serial_no="", title="",
                description="", initiator="", case_no="", source="",
                owner="", plaintiff="", defendant="", created_from=None,
                created_to=None, deadline_from=None, deadline_to=None,
                sort_by="deadline", sort_order="desc", page=1, page_size=15,
                identity=IDENTITY, db=db,
            )

        self.assertEqual(result["total"], 2)
        self.assertEqual(
            {item["serial_no"]: item["status"] for item in result["items"]},
            {
                "CODEX-831-R7-CASE": "进行中",
                "CODEX-831-R7-DAILY": "处理中",
            },
        )
        self.assertEqual(result["status_counts"]["进行中"], 1)
        self.assertEqual(result["status_counts"]["处理中"], 1)
        self.assertEqual(result["summary"]["processing"], 2)


if __name__ == "__main__":
    unittest.main()
