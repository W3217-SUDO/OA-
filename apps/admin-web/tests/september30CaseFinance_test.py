"""9.30 案件合并、法院退费和官费请款的真实 API 回归。"""
import unittest
from datetime import date

from sqlalchemy import select

import finance_0916_batch_test as fixtures
from app.models import BusinessRecord, FinanceTransaction, SystemParameter

API = fixtures.API
IDENTITY = fixtures.IDENTITY

class September30CaseFinanceTest(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.FinanceBatchTest.asyncSetUp
    asyncTearDown = fixtures.FinanceBatchTest.asyncTearDown

    async def test_merge_rejects_fee_from_another_contract_before_moving_rows(self):
        async with self.sessions() as db:
            target = await db.get(BusinessRecord, self.case_id)
            target.data = {**target.data, "contract_record_id": self.contract_id}
            source = BusinessRecord(module="case", serial_no="CODEX-0930-merge-source", title="来源案件",
                owner=IDENTITY["username"], customer=target.customer, status="一审立案受理",
                data={"case_type": "民事争议", "contract_record_id": self.contract_id})
            other_contract = BusinessRecord(module="contract", serial_no="CODEX-0930-other-contract", title="其他合同",
                owner=IDENTITY["username"], customer=target.customer, status="已审批", data={})
            db.add_all([source, other_contract])
            await db.flush()
            source_fee = BusinessRecord(module="finance", serial_no="CODEX-0930-source-fee", title="来源费用",
                owner=IDENTITY["username"], customer=target.customer, status="草稿",
                data={"case_id": source.id, "case_no": source.serial_no, "contract_record_id": other_contract.id,
                    "contract_no": other_contract.serial_no, "amount": 100, "fee_type": "官方费用"})
            db.add(source_fee)
            await db.commit()
            source_id, fee_id = source.id, source_fee.id
        route = f"{API}/cases/{self.case_id}/merge"
        blocked = await self.client.post(route, json={"source_case_no": "CODEX-0930-merge-source"})
        self.assertEqual(blocked.status_code, 409, blocked.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, source_id)).status, "一审立案受理")
            self.assertEqual((await db.get(BusinessRecord, fee_id)).data["case_id"], source_id)
            source_fee = await db.get(BusinessRecord, fee_id)
            contract = await db.get(BusinessRecord, self.contract_id)
            source_fee.data = {**source_fee.data, "contract_record_id": contract.id, "contract_no": contract.serial_no}
            target_fee = await db.get(BusinessRecord, self.fee_id)
            other_contract = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "CODEX-0930-other-contract"))
            target_fee.data = {**target_fee.data, "contract_record_id": other_contract.id, "contract_no": other_contract.serial_no}
            await db.commit()
        blocked_target = await self.client.post(route, json={"source_case_no": "CODEX-0930-merge-source"})
        self.assertEqual(blocked_target.status_code, 409, blocked_target.text)
        async with self.sessions() as db:
            target_fee = await db.get(BusinessRecord, self.fee_id)
            contract = await db.get(BusinessRecord, self.contract_id)
            target_fee.data = {**target_fee.data, "contract_record_id": contract.id, "contract_no": contract.serial_no}
            await db.commit()
        accepted = await self.client.post(route, json={"source_case_no": "CODEX-0930-merge-source"})
        self.assertEqual(accepted.status_code, 200, accepted.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, fee_id)).data["case_id"], self.case_id)
            self.assertEqual((await db.get(BusinessRecord, source_id)).status, "已合并")

    async def test_zero_refund_releases_pending_derivative_without_a_new_fee(self):
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {**fee.data, "fee_type": "官方费用", "expense_subtype": "一审诉讼费"}
            db.add(SystemParameter(category="fee_type", code="AGENCY-REFUND", name="律师代理费（退费）",
                extra={"parent_code": "AGENCY"}, is_active=True))
            await db.commit()
        body = {"fee_record_id": self.fee_id, "case_no": "CODEX-0916-case", "customer": "Batch customer",
            "court": "法院", "original_payment_no": "CODEX-0930", "amount": 50,
            "applicant": "回归申请人", "request_key": "CODEX-0930-first"}
        refund = (await self.client.post(f"{API}/finance/refunds", json=body)).json()
        self.assertIn("refund_fee_id", refund["data"])
        second = await self.client.post(f"{API}/finance/refunds", json={**body, "amount": .01, "request_key": "CODEX-0930-second"})
        self.assertEqual(second.status_code, 201, second.text)
        second_refund = second.json()
        commission_ids = []
        async with self.sessions() as db:
            for refund_fee_id in (refund["data"]["refund_fee_id"], second_refund["data"]["refund_fee_id"]):
                derivative = await db.get(BusinessRecord, refund_fee_id)
                derivative.status = "待审批"
                derivative.data = {**derivative.data, "payment_requested_amount": derivative.data["amount"],
                    "payment_status": "待审批"}
                commission = BusinessRecord(module="finance", serial_no=f"CODEX-0930-commission-{refund_fee_id}",
                    title="退费提成", customer=derivative.customer, owner=IDENTITY["username"], status="待结算",
                    data={"source_fee_id": derivative.id, "fee_type": "内部费用", "amount": 1,
                        "payment_requested_amount": 1, "payment_status": "待结算"})
                db.add(commission)
                await db.flush()
                commission_ids.append(commission.id)
            await db.commit()
        before = (await self.client.get(f"{API}/cases/{self.case_id}/relations")).json()
        source_before = next(item for item in before["fees"] if item["id"] == self.fee_id)
        self.assertEqual(source_before["data"]["refund_requested_amount"], 50.01)
        reset = await self.client.post(f"{API}/finance/fees/{self.fee_id}/court-refund/reset")
        self.assertEqual(reset.status_code, 200, reset.text)
        after = (await self.client.get(f"{API}/cases/{self.case_id}/relations")).json()
        source_after = next(item for item in after["fees"] if item["id"] == self.fee_id)
        self.assertEqual(source_after["data"]["refund_requested_amount"], 0)
        self.assertFalse(any(item["data"].get("refund_fee") for item in after["fees"]))
        async with self.sessions() as db:
            for refund_id in (refund["id"], second_refund["id"]):
                self.assertEqual((await db.get(BusinessRecord, refund_id)).status, "已作废")
            for fee_id in (refund["data"]["refund_fee_id"], second_refund["data"]["refund_fee_id"]):
                derivative = await db.get(BusinessRecord, fee_id)
                self.assertEqual(derivative.status, "已删除")
                self.assertEqual(derivative.data["payment_requested_amount"], 0)
            for commission_id in commission_ids:
                commission = await db.get(BusinessRecord, commission_id)
                self.assertEqual(commission.status, "已删除")
                self.assertEqual(commission.data["payment_requested_amount"], 0)
        repeated = await self.client.post(f"{API}/finance/fees/{self.fee_id}/court-refund/reset")
        self.assertEqual(repeated.status_code, 200, repeated.text)

    async def test_zero_refund_rejects_settled_money_without_partial_change(self):
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {**fee.data, "fee_type": "官方费用", "expense_subtype": "一审诉讼费"}
            refund = BusinessRecord(module="refund", serial_no="CODEX-0930-settled-refund", title="法院退费",
                owner=IDENTITY["username"], customer=fee.customer, status="已退款",
                data={"fee_record_id": fee.id, "amount": 50, "case_no": "CODEX-0916-case"})
            db.add(refund)
            await db.flush()
            db.add(FinanceTransaction(finance_record_id=refund.id, transaction_type="退费", amount=50,
                transaction_date=date(2026, 9, 30), operator=IDENTITY["username"]))
            await db.commit()
            refund_id = refund.id
        reset = await self.client.post(f"{API}/finance/fees/{self.fee_id}/court-refund/reset")
        self.assertEqual(reset.status_code, 409, reset.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, refund_id)).status, "已退款")

    async def test_official_fee_payment_application_allows_no_unit_only_for_official(self):
        route = f"{API}/finance/fees/{self.fee_id}/submit"
        body = {"amount": 100, "comment": "官费申请付款"}
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {**fee.data, "fee_type": "官方费用", "expense_subtype": "一审诉讼费"}
            await db.commit()
        accepted = await self.client.post(route, json=body)
        self.assertEqual(accepted.status_code, 200, accepted.text)
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id)
            self.assertEqual(fee.data["payment_requested_amount"], 100)
            self.assertEqual(fee.data["payment_payee"], "")
            fee.status = "草稿"
            fee.data = {**fee.data, "fee_type": "其他费用", "payment_requested_amount": 0}
            await db.commit()
        blocked = await self.client.post(route, json=body)
        self.assertEqual(blocked.status_code, 422, blocked.text)

    async def test_payment_unit_keyword_search_returns_existing_active_candidate(self):
        async with self.sessions() as db:
            db.add(SystemParameter(category="payment_type", code="CODEX-0930-PAYEE", name="官费",
                extra={"nature": "官费", "payee": "测试付款单位", "account_bank": "测试银行", "account": "0001"},
                is_active=True))
            await db.commit()
        path = f"{API}/finance/fees/{self.fee_id}/payment-types"
        found = await self.client.get(path, params={"keyword": "测试付款"})
        self.assertEqual(found.status_code, 200, found.text)
        self.assertEqual([row["payee"] for row in found.json()["items"]], ["测试付款单位"])
        missing = await self.client.get(path, params={"keyword": "不存在的单位"})
        self.assertEqual(missing.status_code, 200, missing.text)
        self.assertEqual(missing.json()["items"], [])

    async def test_batch_official_payment_does_not_require_payment_unit(self):
        body = {"items": [{"case_id": self.case_id, "contract_record_id": self.contract_id,
            "fee_type_id": self.leaf_id, "fee_type": "官方费用", "amount": 10,
            "payment_amount": 10}], "handler": IDENTITY["username"], "submit_payment": True}
        response = await self.client.post(f"{API}/finance/case-fees/batch", json=body)
        self.assertEqual(response.status_code, 201, response.text)
        created = response.json()["items"][0]
        self.assertEqual(created["data"]["payment_requested_amount"], 10)
        self.assertEqual(created["data"]["payment_payee"], "")


if __name__ == "__main__":
    unittest.main()
