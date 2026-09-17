"""案件到账导出接口验证，复用隔离的内存数据库。"""
import unittest
from xml.etree import ElementTree

from sqlalchemy import select

from finance_0916_batch_test import FinanceBatchTest, API
from app.models import BusinessRecord, IncomingPayment, LegacyFinanceRecord, LegacyFinanceAllocation, User, RolePermission
from app.main import app
from app.security import current_identity


class ReceiptExportTest(FinanceBatchTest):
    async def test_receipt_export(self):
        async with self.sessions() as db:
            other = BusinessRecord(module="case", serial_no="CODEX-OTHER", title="UNRELATED-SECRET", owner="another", status="有效", data={"case_type": "刑事案件"})
            db.add(other)
            await db.flush()
            payment = await db.scalar(select(IncomingPayment))
            payment.amount = 500
            payment.allocated_amount = 130
            payment.status = "部分分配"
            payment.allocations = [{"case_id": self.case_id, "amount": 30}, {"case_id": other.id, "amount": 100}]
            header = LegacyFinanceRecord(source_table="FAM_AR_Payment", legacy_id="old-receipt", record_kind="ar_payment", primary_amount=900, source_payload={"CashedDate": "2026-01-01", "PayerName": "OLD-PAYER"})
            db.add(header)
            await db.flush()
            db.add(LegacyFinanceAllocation(legacy_finance_record_id=header.id, source_table="FAM_AR_Payment_Object", legacy_key="old-detail", allocation_kind="ar_payment", case_record_id=self.case_id, amount=20))
            await db.commit()
            original = payment.allocations
        response = await self.client.get(f"{API}/cases/export/receipts", params={"ids": str(self.case_id)})
        self.assertEqual(response.status_code, 200, response.text)
        ElementTree.fromstring(response.content)
        for amount in ["30.00", "20.00"]:
            self.assertIn(amount, response.text)
        for excluded in ["500.00", "900.00", "UNRELATED-SECRET"]:
            self.assertNotIn(excluded, response.text)
        self.assertIn("filename*=", response.headers["content-disposition"])
        for ids, status in [("", 422), ("999999", 404)]:
            response = await self.client.get(f"{API}/cases/export/receipts", params={"ids": ids})
            self.assertEqual(response.status_code, status, response.text)
        async with self.sessions() as db:
            payment = await db.scalar(select(IncomingPayment))
            self.assertEqual(payment.allocations, original)
            self.assertEqual(payment.status, "部分分配")
            payment.allocations = []
            allocation = await db.scalar(select(LegacyFinanceAllocation))
            allocation.is_active = False
            await db.commit()
        response = await self.client.get(f"{API}/cases/export/receipts", params={"ids": str(self.case_id)})
        self.assertEqual(response.status_code, 422, response.text)
        async with self.sessions() as db:
            db.add(User(username="receipt-other", display_name="导出权限测试", role="user", password_hash="unused", is_active=True))
            db.add(RolePermission(role="user", display_name="普通用户", data_scope="本人及共享数据", menu_keys=["case"], field_keys=[]))
            await db.commit()
        app.dependency_overrides[current_identity] = lambda: {"username": "receipt-other", "role": "user", "department": "other"}
        response = await self.client.get(f"{API}/cases/export/receipts", params={"ids": str(self.case_id)})
        self.assertEqual(response.status_code, 404, response.text)


if __name__ == "__main__":
    suite = unittest.TestSuite([ReceiptExportTest("test_receipt_export")])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
