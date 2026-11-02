"""仓库一览表“调查员”列显示真实姓名，不再全部显示“姓名待维护”；按姓名也能筛（陶威 11-02）。"""
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.wms import router as wms_router
from app.core import person_names
from app.database import Base
from app.models import BusinessRecord, User


def evidence(serial, owner, investigator=None):
    return BusinessRecord(module="warehouse", serial_no=serial, title=serial, customer="权利人", status="在库",
                          owner=owner, department="调查部",
                          data={"investigator": investigator} if investigator is not None else {})


class WarehouseInvestigatorNameTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            db.add_all([
                User(username="fanyg", display_name="范应根", password_hash="x", role="user", department="调查部"),
                evidence("EV-1", "fanyg", ""),            # 调查员只记在负责人账号上（迁移数据的常态）
                evidence("EV-2", "sugq", "刘波"),         # 登记时直接填了姓名
                evidence("EV-3", "fujianhongxin"),        # 旧系统账号，新系统没有
            ])
            await db.commit()
            await person_names.refresh_person_names(db, force=True)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def query(self, investigator=""):
        with patch("app.core.permissions._require_record_module_menu", AsyncMock()), \
                patch("app.core.permissions._record_scope_conditions", AsyncMock(return_value=[])):
            async with self.sessions() as db:
                return await wms_router.list_warehouse_evidence(
                    page=1, page_size=15, warehouse_id=None, storage_location_id=None, keyword="", rights_holder="",
                    evidence_status="", case_no="", shop_name="", investigator=investigator, notary_no="",
                    evidence_date_from="", evidence_date_to="", identity={"username": "admin"}, db=db)

    async def test_investigator_shows_real_name(self):
        result = await self.query()
        names = {item["serial_no"]: item["data"]["investigator_display_name"] for item in result["items"]}
        self.assertEqual(names, {"EV-1": "范应根", "EV-2": "刘波", "EV-3": "fujianhongxin"})
        owner_names = {item["serial_no"]: item["owner_display_name"] for item in result["items"]}
        self.assertEqual(owner_names["EV-1"], "范应根")

    async def test_filter_by_name_or_account(self):
        self.assertEqual([item["serial_no"] for item in (await self.query("范应根"))["items"]], ["EV-1"])
        self.assertEqual([item["serial_no"] for item in (await self.query("fanyg"))["items"]], ["EV-1"])
        self.assertEqual([item["serial_no"] for item in (await self.query("刘波"))["items"]], ["EV-2"])


if __name__ == "__main__":
    unittest.main()
