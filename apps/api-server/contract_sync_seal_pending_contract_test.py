from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("app") / "main.py"


class ContractSyncSealPendingContractTest(unittest.TestCase):
    def test_sync_seal_creation_can_enter_my_pending_directly(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def create_contract_seal_application")
        end = source.index("async def create_contract_investigation", start)
        branch = source[start:end]
        self.assertIn('sync_submission = contract.status == "审批中" and body.submit', branch)
        self.assertIn('seal_status = "待审批" if sync_submission else "草稿"', branch)
        self.assertIn('"sync_seal_file_required": False', branch)
        self.assertIn('action="创建合同用印申请并提交审批" if sync_submission else "创建合同用印申请"', branch)

    def test_sync_seal_enters_my_pending_after_contract_approval_without_file_gate(self):
        source = SOURCE.read_text(encoding="utf-8")
        marker = 'if seal_application_id and (contract.data or {}).get("sync_seal"):'
        start = source.index(marker)
        end = source.index("        await _sync_legacy_contract_audit", start)
        branch = source[start:end]
        self.assertIn('seal_application.status = "待审批"', branch)
        self.assertIn('"sync_seal_file_required": False', branch)
        self.assertNotIn("seal_file_count", branch)
        self.assertNotIn('if seal_file_count:', branch)


if __name__ == "__main__":
    unittest.main()
