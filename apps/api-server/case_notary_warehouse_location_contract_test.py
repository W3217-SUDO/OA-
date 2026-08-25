import os
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


_TEMP_DIR = tempfile.TemporaryDirectory()
_DB_PATH = Path(_TEMP_DIR.name) / "case-notary-location.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH.as_posix()}"

from app.database import Base
from app.main import CaseNotaryInfoInput, update_case_notary_info
from app.models import BusinessRecord, Warehouse, WarehouseStorageLocation, WorkflowEvent


class CaseNotaryWarehouseLocationContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(os.environ["DATABASE_URL"])
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    async def _fixture(self):
        async with self.sessions() as db:
            warehouse = Warehouse(warehouse_no="SH00001", name="上海一仓", is_active=True)
            db.add(warehouse)
            await db.flush()
            location = WarehouseStorageLocation(
                warehouse_id=warehouse.id,
                storage_location_no="SH-9-4",
                name="9-4",
                is_active=True,
            )
            case = BusinessRecord(
                module="case",
                serial_no="CODEX-825-R2-CASE",
                title="仓库库位公证信息测试",
                status="一审",
                owner="admin",
                data={"case_type": "民事案件", "notary_no": "OLD", "deposit_address": "旧位置"},
            )
            db.add_all([location, case])
            await db.commit()
            return case.id, location.id

    async def test_case_notary_info_persists_master_location_and_audit(self):
        case_id, location_id = await self._fixture()
        identity = {"username": "admin", "role": "admin", "role_ids": ["admin"]}
        async with self.sessions() as db:
            result = await update_case_notary_info(
                case_id,
                CaseNotaryInfoInput(
                    notary_nos="NOTARY-825-R2",
                    warehouse_location_ids=[location_id],
                    comment="row 2 acceptance",
                ),
                identity,
                db,
            )
            self.assertEqual(result["data"]["deposit_address"], "上海一仓（9-4）")
            self.assertEqual(result["data"]["warehouse_location_ids"], [location_id])
            self.assertEqual(result["data"]["warehouse_locations"][0]["storage_location_no"], "SH-9-4")
            event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == case_id))
            self.assertIn("上海一仓（9-4）", event.comment)

    async def test_unknown_location_is_rejected_without_writing(self):
        case_id, _ = await self._fixture()
        identity = {"username": "admin", "role": "admin", "role_ids": ["admin"]}
        async with self.sessions() as db:
            with self.assertRaisesRegex(Exception, "仓库库位不存在"):
                await update_case_notary_info(
                    case_id,
                    CaseNotaryInfoInput(notary_nos="NOTARY-INVALID", warehouse_location_ids=[999999]),
                    identity,
                    db,
                )
            case = await db.get(BusinessRecord, case_id)
            self.assertEqual(case.data["notary_no"], "OLD")
            self.assertEqual(case.data["deposit_address"], "旧位置")


if __name__ == "__main__":
    unittest.main()
