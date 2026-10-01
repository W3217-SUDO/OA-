"""9.1 row 15: active contracts may create downstream records; terminal states may not."""
from __future__ import annotations
import unittest
from app.main import _contract_allows_downstream_creation
from app.models import BusinessRecord

def contract(status: str) -> BusinessRecord:
    return BusinessRecord(module="contract",serial_no=f"R15-{status}",title=status,customer="客户",status=status,owner="admin",department="诉讼部",data={})

class ContractDownstreamDraftGateRow15Test(unittest.TestCase):
    def test_inactive_contract_statuses_are_blocked_and_active_statuses_are_allowed(self):
        for status in ("审批中","审批通过","已完成","已拒绝","已撤回","执行中"):
            with self.subTest(status=status): self.assertTrue(_contract_allows_downstream_creation(contract(status)))
        for status in ("草稿", "归档中", "归档审核中", "已归档", "已回收", "已删除", "已作废"):
            with self.subTest(status=status): self.assertFalse(_contract_allows_downstream_creation(contract(status)))
        self.assertFalse(_contract_allows_downstream_creation(None))
        self.assertFalse(_contract_allows_downstream_creation(BusinessRecord(module="case",serial_no="R15-CASE",title="case",customer="客户",status="办理中",owner="admin",department="诉讼部",data={})))
if __name__=="__main__": unittest.main()
