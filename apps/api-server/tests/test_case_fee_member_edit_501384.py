"""501384（fwl 11-04）：案件费用还没产生数据时本案人员都能改删；产生数据后只有分配了权限的角色能改删。"""
import unittest
from unittest.mock import AsyncMock, patch

from app.core import case_fee_member_edit as rule
from app.models import BusinessRecord


def fee(status="草稿", **data):
    return BusinessRecord(module="finance", serial_no="F1", title="公证费", customer="客户", status=status, owner="fwl", department="诉讼部",
                          data={"amount": 100, "case_id": 9, "fee_type": "官方费用", "expense_scope": "律所", **data})


CASE = BusinessRecord(module="case", serial_no="HZMS2650001", title="案", customer="客户", status="新案待分配", owner="admin", department="诉讼部",
                      data={"handling_lawyer_usernames": ["lawyer1"], "investigator": "fwl"})


class CaseFeeMemberEditTest(unittest.IsolatedAsyncioTestCase):
    def test_activity(self):
        self.assertFalse(rule.fee_has_activity(fee()))
        self.assertFalse(rule.fee_has_activity(fee("已记录", payment_requested_amount=0, invoice_no="")))
        for item in (fee("待审批"), fee("已付款"), fee(payment_requested_amount=50), fee(cashed_amount=1), fee(invoice_no="123"),
                     fee(refund_requested_amount=10), fee(receipt_files=[{"id": 1}]), fee(settlement_no="JS1")):
            self.assertTrue(rule.fee_has_activity(item), item.status + str(item.data))
        self.assertTrue(rule.fee_has_activity(fee(), {"invoice_amount": 100}), "回款/开票/付款看真实关联的投影")

    async def _member(self, item, username, projected=None):
        rows = [{"data": projected or {}}]
        with patch("app.core.finance._invoice_case_fee_rows", AsyncMock(return_value=rows)):
            return await rule.member_may_change_untouched_fee(item, CASE, {"username": username}, None)

    async def test_member_can_change_only_untouched(self):
        self.assertTrue(await self._member(fee(), "fwl"), "调查员是本案人员")
        self.assertTrue(await self._member(fee(), "LAWYER1"))
        self.assertFalse(await self._member(fee(), "outsider"), "不是本案人员按角色权限")
        self.assertFalse(await self._member(fee(payment_requested_amount=10), "fwl"))
        self.assertFalse(await self._member(fee(), "fwl", {"cashed_amount": 5}))


if __name__ == "__main__":
    unittest.main()
