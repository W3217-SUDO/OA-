from pathlib import Path
import unittest


SOURCE = (Path(__file__).parent / "app" / "main.py").read_text(encoding="utf-8")


class ContractSealApproverContractTest(unittest.TestCase):
    def test_contract_seal_input_requires_approver(self):
        block = SOURCE[SOURCE.index("class ContractSealApplicationInput"):SOURCE.index("class ContractInvestigationInput")]
        self.assertRegex(block, r"approver:\s*str\s*=\s*Field\(min_length=1")

    def test_contract_seal_persists_and_enforces_selected_approver(self):
        create_block = SOURCE[SOURCE.index("async def create_contract_seal_application"):SOURCE.index("async def create_contract_investigation")]
        self.assertIn('"approver": approver.username', create_block)
        approve_block = SOURCE[SOURCE.index("async def approve_seal_application"):SOURCE.index("async def stamp_seal_application")]
        self.assertIn("selected_approver = str", approve_block)
        self.assertIn("approver", approve_block)
        self.assertIn("当前账号不是该用印申请指定的审批人", approve_block)


if __name__ == "__main__":
    unittest.main()
