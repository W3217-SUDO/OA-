from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("app") / "main.py"


class ContractDirectSealSubmissionRow2Test(unittest.TestCase):
    def test_approved_contract_can_submit_seal_application_directly(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def create_contract_seal_application")
        end = source.index("async def create_contract_investigation", start)
        branch = source[start:end]

        self.assertIn(
            'direct_submission = contract.status in {CONTRACT_APPROVED_STATUS, "已完成"} and body.submit',
            branch,
        )
        self.assertIn('sync_seal_requested = bool((contract.data or {}).get("sync_seal"))', branch)
        self.assertIn('sync_seal_draft = contract.status == "审批中" and sync_seal_requested', branch)
        self.assertIn("submitted = direct_submission or (sync_seal_draft and body.submit)", branch)
        self.assertIn('seal_status = "待审批" if submitted else "草稿"', branch)
        self.assertIn("serial = await _next_seal_application_serial(db)", branch)
        self.assertIn('"sync_seal": sync_seal_requested', branch)
        self.assertNotIn("sync_submission", branch)
        self.assertNotIn("只有合同提交同步用印时才能在此直接提交审批", branch)

    def test_duplicate_and_permission_guards_remain_in_place(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def create_contract_seal_application")
        end = source.index("async def create_contract_investigation", start)
        branch = source[start:end]

        self.assertIn("await _require_record_owner_or_manager", branch)
        self.assertIn("seal_application_id", branch)
        self.assertIn("合同已生成用印申请", branch)

    def test_unique_linked_case_is_carried_into_contract_seal_record(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def create_contract_seal_application")
        end = source.index("async def create_contract_investigation", start)
        branch = source[start:end]

        self.assertIn("linked_case = await _single_linked_case_for_contract(contract, identity, db)", branch)
        self.assertIn('"case_record_id": linked_case.id if linked_case else None', branch)
        self.assertIn('"case_no": linked_case.serial_no if linked_case else ""', branch)


if __name__ == "__main__":
    unittest.main()
