"""Generic uploads must not reject files because a category belongs to another module."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import upload_attachment
from app.models import BusinessRecord, FileAttachment


IDENTITY = {"username": "admin", "role": "admin"}


class FakeUpload:
    filename = "material.doc"
    content_type = "application/msword"

    async def read(self):
        return b"material"


class AttachmentCategoryUnrestrictedContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.db = self.sessions()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.upload_root_patch = patch("app.main.UPLOAD_ROOT", Path(self.temp_dir.name))
        self.upload_root_patch.start()

    async def asyncTearDown(self):
        self.upload_root_patch.stop()
        await self.db.close()
        await self.engine.dispose()
        self.temp_dir.cleanup()

    async def add_record(self, module: str, serial_no: str, status: str = "进行中") -> BusinessRecord:
        record = BusinessRecord(
            module=module,
            serial_no=serial_no,
            title=serial_no,
            customer="测试客户",
            status=status,
            owner="admin",
            department="调查部",
            description="",
            data={},
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def upload(self, record: BusinessRecord, category: str) -> dict:
        return await upload_attachment(
            FakeUpload(),
            record_id=record.id,
            finance_transaction_id=None,
            customer_guid=None,
            is_license=None,
            document_date=None,
            category=category,
            remark="",
            identity=IDENTITY,
            db=self.db,
        )

    async def test_investigation_upload_accepts_a_category_from_another_business_type(self):
        clue = await self.add_record("clue", "CLUE-CATEGORY-OPEN")

        result = await self.upload(clue, "调查授权书")

        attachment = await self.db.get(FileAttachment, result["id"])
        self.assertEqual(attachment.category, "调查授权书")
        self.assertTrue(Path(attachment.path).is_file())

    async def test_fixed_workflow_modules_normalize_instead_of_rejecting_categories(self):
        task = await self.add_record("task", "TASK-CATEGORY-OPEN")
        seal = await self.add_record("seal", "SEAL-CATEGORY-OPEN", "待用印")
        outgoing = await self.add_record("official_outgoing", "OUT-CATEGORY-OPEN", "草稿")
        hr = await self.add_record("hr", "HR-CATEGORY-OPEN", "在职")

        task_result = await self.upload(task, "任意任务材料")
        seal_result = await self.upload(seal, "任意用印材料")
        outgoing_result = await self.upload(outgoing, "任意发文材料")
        hr_result = await self.upload(hr, "任意员工材料")

        expected = {
            task_result["id"]: "任务资料附件",
            seal_result["id"]: "盖章文件",
            outgoing_result["id"]: "正式发文附件",
            hr_result["id"]: "员工档案",
        }
        for attachment_id, category in expected.items():
            attachment = await self.db.get(FileAttachment, attachment_id)
            self.assertEqual(attachment.category, category)


if __name__ == "__main__":
    unittest.main()
