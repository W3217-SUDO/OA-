from pathlib import Path
import unittest


ROOT = Path(__file__).parent
BACKEND_SOURCE = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
FRONTEND_SOURCE = (ROOT.parent / "admin-web" / "src" / "ContractCenterPage.tsx").read_text(encoding="utf-8")


class ContractSyncDualChannelRow5Test(unittest.TestCase):
    def test_sync_seal_submission_keeps_contract_and_seal_in_distinct_channels(self):
        submit_start = BACKEND_SOURCE.index("async def submit_contract")
        submit_end = BACKEND_SOURCE.index("async def _sync_legacy_contract_audit", submit_start)
        submit_block = BACKEND_SOURCE[submit_start:submit_end]
        self.assertIn('contract.status = "审批中"', submit_block)
        self.assertIn('"current_approver": approvers[0]', submit_block)
        self.assertIn('"sync_seal": body.sync_seal', submit_block)

        seal_start = BACKEND_SOURCE.index("async def create_contract_seal_application")
        seal_end = BACKEND_SOURCE.index("async def create_contract_investigation", seal_start)
        seal_block = BACKEND_SOURCE[seal_start:seal_end]
        self.assertIn('seal_status = "待审批" if submitted else "草稿"', seal_block)
        self.assertIn('"approver": approver.username', seal_block)
        self.assertIn('"contract_record_id": contract.id', seal_block)

    def test_sync_seal_primary_action_submits_without_forcing_seal_center_navigation(self):
        action_start = FRONTEND_SOURCE.index("const createSealApplication = async")
        action_end = FRONTEND_SOURCE.index("const downloadAttachment", action_start)
        action_block = FRONTEND_SOURCE[action_start:action_end]
        self.assertIn("合同审批与用印申请已分别提交至对应审批渠道", action_block)
        self.assertIn("buildContractDetailRoute(contract)", action_block)
        self.assertNotIn('onNavigate?.("seal-my-pending")', action_block)
        self.assertNotIn("生成用印申请并进入用印中心", FRONTEND_SOURCE)
        self.assertGreaterEqual(FRONTEND_SOURCE.count(">提交申请</Button>"), 2)


if __name__ == "__main__":
    unittest.main()
