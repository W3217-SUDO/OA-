"""501190（思法汇成 11-05 确认第 1 条）：非诉专利、商标个案不看案件状态。

老系统迁来的“年费监控”、草稿、待审批、已结案等个案，文档、费用新增修改、发布任务、客户联系人、提醒日志都能维护；
诉讼类知识产权案件仍按原状态限制；开票、付款申请和 CPC 申报暂按原规则（第 2、3 条待定）。
"""
import unittest

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.permissions import (
    _ensure_active_ipr_case_write, _ensure_ipr_case_assisted_fee_write, _ensure_ipr_case_fee_write,
    _ensure_ipr_case_file_write, _ensure_ipr_case_note_write, _ensure_ipr_cpc_write, ipr_case_ignores_status,
)
from app.database import Base
from app.models import BusinessRecord

ADMIN = {"username": "p190-admin", "role": "admin", "role_ids": ["admin"], "display_name": "管理者190", "department": "IPR"}
OPEN_GATES = (_ensure_active_ipr_case_write, _ensure_ipr_case_assisted_fee_write, _ensure_ipr_case_fee_write,
              _ensure_ipr_case_file_write, _ensure_ipr_case_note_write)


class IprNonLitigationStatusFree501190Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.ids = {}
        async with self.sessions() as db:
            for key, status, data in (
                ("legacy", "年费监控", {"case_kind": "专利", "legacy_ipr_case_id": 1}),
                ("closed", "已结案", {"case_kind": "商标"}),
                ("pending", "待审批", {}),
                ("lit_closed", "已结案", {"case_category": "litigation"}),
            ):
                record = BusinessRecord(module="ipr_case", serial_no=f"P190-{key}", title=key, customer="客户190", status=status,
                                        owner=ADMIN["username"], department="IPR", data=data)
                db.add(record)
                await db.flush()
                self.ids[key] = record.id
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_non_litigation_cases_open_regardless_of_status(self):
        async with self.sessions() as db:
            for key in ("legacy", "closed", "pending"):
                for gate in OPEN_GATES:
                    record = await gate(self.ids[key], ADMIN, db)
                    self.assertTrue(ipr_case_ignores_status(record), (key, gate.__name__))

    async def test_litigation_and_cpc_keep_status_rules(self):
        async with self.sessions() as db:
            for gate in OPEN_GATES:
                with self.assertRaises(HTTPException, msg=gate.__name__) as raised:
                    await gate(self.ids["lit_closed"], ADMIN, db)
                self.assertEqual(raised.exception.status_code, 409)
            for key in ("closed", "pending"):
                with self.assertRaises(HTTPException) as raised:
                    await _ensure_ipr_cpc_write(self.ids[key], ADMIN, db)
                self.assertEqual(raised.exception.status_code, 409, "CPC 申报仍按原规则（第 3 条待定）")
            await _ensure_ipr_cpc_write(self.ids["legacy"], ADMIN, db)


if __name__ == "__main__":
    unittest.main()
