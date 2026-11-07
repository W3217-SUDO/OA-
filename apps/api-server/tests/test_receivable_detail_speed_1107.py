"""11-07 工作台“未到官费”约 10 秒：案件只读用到的字段，接口按全库数据修订缓存。"""
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.contract.receivable_export_rows import _CASE_FIELDS, _case_rows
from app.areas.finance import query_cache_routes
from app.database import Base
from app.models import BusinessRecord


class ReceivableDetailSpeedTest(unittest.IsolatedAsyncioTestCase):
    async def test_case_rows_keep_only_fields_used_by_receivables(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.addAsyncCleanup(engine.dispose)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with sessions() as db:
            db.add_all([
                BusinessRecord(module="case", serial_no="C-1", title="甲", status="进行中", owner="a",
                               data={"case_stage": "一审", "case_type": "民事", "legacy": {"big": "x" * 100}}),
                BusinessRecord(module="case", serial_no="C-2", title="乙", status="结案", owner="a", data={}),
                BusinessRecord(module="contract", serial_no="H-1", title="合同", status="有效", owner="a", data={}),
            ])
            await db.commit()
            rows = await _case_rows(db)
        self.assertEqual([(row.serial_no, row.status, row.data) for row in rows],
                         [("C-1", "进行中", {"case_stage": "一审", "case_type": "民事"}), ("C-2", "结案", {})])
        self.assertEqual(_CASE_FIELDS, ("case_stage", "business_stage", "case_type"))

    def test_detail_endpoint_is_cached(self):
        from app.main import app
        self.assertEqual(query_cache_routes.FINANCE_JSON_QUERIES["/contracts/receivables/detail"],
                         "list_contract_receivable_details")
        route = next(route for route in app.routes if getattr(route, "path", "") == "/api/v1/contracts/receivables/detail")
        self.assertIs(route.dependant.call.__wrapped__, route.endpoint)


if __name__ == "__main__":
    unittest.main()
