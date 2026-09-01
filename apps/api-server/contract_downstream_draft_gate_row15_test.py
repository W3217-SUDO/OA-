"""9.1 row 15: only contract drafts are blocked from downstream creation."""
from __future__ import annotations
import unittest
from app.main import _contract_allows_downstream_creation
from app.models import BusinessRecord

def contract(status: str) -> BusinessRecord:
    return BusinessRecord(module="contract",serial_no=f"R15-{status}",title=status,customer="客户",status=status,owner="admin",department="诉讼部",data={})

class ContractDownstreamDraftGateRow15Test(unittest.TestCase):
    def test_draft_is_blocked_and_every_persisted_non_draft_status_is_allowed(self):
        self.assertFalse(_contract_allows_downstream_creation(contract("草稿")))
        for status in ("审批中","审批通过","已完成","已拒绝","已撤回","已归档","执行中"):
            with self.subTest(status=status): self.assertTrue(_contract_allows_downstream_creation(contract(status)))
        self.assertFalse(_contract_allows_downstream_creation(None))
        self.assertFalse(_contract_allows_downstream_creation(BusinessRecord(module="case",serial_no="R15-CASE",title="case",customer="客户",status="办理中",owner="admin",department="诉讼部",data={})))
if __name__=="__main__": unittest.main()
