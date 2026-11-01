"""数据量上来后，客户 ROI 与案件阶段统计不能因绑定参数上限或整条读取而失败/超时。"""
import unittest

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.legal.stage_export import stage_statistics_rows
from app.database import Base
from app.main import _customer_roi_analytics
from app.models import BusinessRecord, FinanceTransaction, User


ADMIN = {"username": "admin", "role": "admin"}
# 超过 asyncpg 的 32767 个参数上限，也超过 SQLite 的 32766 个变量上限。
OVER_BIND_LIMIT = 33000


class LargeScopeQueryLimitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_customer_roi_survives_more_finance_sources_than_the_bind_limit(self):
        async with self.sessions() as db:
            db.add(User(username="admin", display_name="管理员", role="admin", role_ids=["admin"], password_hash="x"))
            customer = BusinessRecord(module="customer", serial_no="CODEX-LIMIT-C1", title="客户", customer="客户", status="正常", owner="admin", data={})
            db.add(customer)
            await db.flush()
            db.add_all([
                BusinessRecord(module="finance", serial_no=f"CODEX-LIMIT-F{i}", title="费用", customer="客户", status="已付款", owner="admin",
                               data={"customer_id": customer.id, "customer_no": "CODEX-LIMIT-C1", "case_id": 900000 + i, "case_no": f"CODEX-LIMIT-CASE{i}"})
                for i in range(OVER_BIND_LIMIT)
            ])
            await db.flush()
            fee_id = (await db.execute(BusinessRecord.__table__.select().where(BusinessRecord.serial_no == "CODEX-LIMIT-F0"))).first().id
            db.add(FinanceTransaction(finance_record_id=fee_id, transaction_type="回款", amount=100, transaction_date=date(2026, 9, 30), operator="admin"))
            await db.commit()
        async with self.sessions() as db:
            result = await _customer_roi_analytics(ADMIN, db)
        self.assertEqual(result["view"], "customer-roi")
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["income"], 100.0)

    async def test_stage_statistics_counts_phase_and_refund_columns_per_assistant(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="管理员", role="admin", role_ids=["admin"], password_hash="x"),
                User(username="a1", display_name="助理甲", role="user", role_ids=["user"], password_hash="x"),
            ])
            case = BusinessRecord(module="case", serial_no="CODEX-STAGE-CASE", title="案件", customer="客户", status="文书准备", owner="admin",
                                  data={"assistant_username": "a1", "case_phase_id": 101011})
            legacy_case = BusinessRecord(module="case", serial_no="CODEX-STAGE-LEGACY", title="旧案件", customer="客户", status="历史数据", owner="admin",
                                         data={"legacy_record": {"CaseAssistant": "助理甲", "CasePhaseId": 1010121}})
            db.add_all([case, legacy_case])
            await db.flush()
            db.add(BusinessRecord(module="finance", serial_no="CODEX-STAGE-FEE", title="费用", customer="客户", status="已通知", owner="admin",
                                  data={"case_record_id": case.id, "legacy_record": {"RefundStatus": "10"}}))
            await db.commit()
        async with self.sessions() as db:
            rows = await stage_statistics_rows(ADMIN, db, action="查看")
        by_name = {row["name"]: row["values"] for row in rows}
        self.assertEqual(set(by_name), {"助理甲"})
        values = by_name["助理甲"]
        # values 从模板第 2 列开始：文书准备=第 2 列、客户盖章=第 3 列、退费准备材料=第 10 列
        self.assertEqual(values[0], 1)
        self.assertEqual(values[1], 1)
        self.assertEqual(values[8], 1)

    async def test_stage_statistics_counts_clue_status_and_customer_manager_columns(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="管理员", role="admin", role_ids=["admin"], password_hash="x"),
                User(username="a1", display_name="助理甲", role="user", role_ids=["user"], password_hash="x"),
            ])
            db.add(BusinessRecord(module="case", serial_no="CODEX-CLUE-STAGE-CASE", title="案件", customer="客户", status="文书准备", owner="admin",
                                  data={"assistant_username": "a1", "case_phase_id": 101011}))
            managed = BusinessRecord(module="customer", serial_no="CODEX-CLUE-STAGE-C1", title="经理客户", customer="", status="正常", owner="admin",
                                     data={"customer_managers": ["a1"]})
            owned = BusinessRecord(module="customer", serial_no="CODEX-CLUE-STAGE-C2", title="负责人客户", customer="", status="正常", owner="a1",
                                   data={"customer_managers": []})
            other = BusinessRecord(module="customer", serial_no="CODEX-CLUE-STAGE-C3", title="别人的客户", customer="", status="正常", owner="admin",
                                   data={"customer_managers": ["someone-else"]})
            db.add_all([managed, owned, other])
            await db.flush()

            def clue(serial, status, customer, **data):
                return BusinessRecord(module="clue", serial_no=f"CODEX-CLUE-STAGE-{serial}", title=serial, customer="", status=status, owner="admin",
                                      data={"customer_record_id": customer.id, **data})
            db.add_all([
                clue("PENDING", "待审批", managed),                                         # 第 26 列
                clue("LEGACY-DATA", "历史数据", managed, clue_status="15"),                  # 第 28 列（来自 data.clue_status）
                clue("LEGACY-RECORD", "历史数据", managed, legacy_record={"Status": "20"}),  # 第 27 列（来自旧库状态）
                clue("NOTARY-REVIEWED", "待取证", owned, customer_reviewed_at="2026-10-01"),  # 第 29 列，客户经理为空按负责人
                clue("NOTARY-WAITING", "待取证", owned),                                    # 第 27 列
                clue("DRAFT", "草稿", managed),                                             # 不计入任何列
                clue("DELETED", "已删除", managed),                                         # 已删除不统计
                clue("OTHER-MANAGER", "待审批", other),                                     # 不是 a1 管理的客户
            ])
            await db.commit()
        async with self.sessions() as db:
            rows = await stage_statistics_rows(ADMIN, db, action="查看")
        values = {row["name"]: row["values"] for row in rows}["助理甲"]
        # values 下标 = 模板列号 - 2
        self.assertEqual((values[24], values[25], values[26], values[27]), (1, 2, 1, 1))


if __name__ == "__main__":
    unittest.main()
