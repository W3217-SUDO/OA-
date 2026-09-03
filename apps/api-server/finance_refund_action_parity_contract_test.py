from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("app").joinpath("main.py").read_text(encoding="utf-8")


class RefundActionParityContractTest(unittest.TestCase):
    def test_batch_contract_preserves_legacy_row_fields(self):
        for field in (
            "case_id", "contract_record_id", "fee_type", "amount", "remark", "deadline"
        ):
            self.assertIn(field, SOURCE)

    def test_batch_endpoint_commits_once_and_rolls_back_as_a_unit(self):
        start = SOURCE.index('async def create_refund_page_case_fees(')
        end = SOURCE.index('@app.get(f"{settings.api_prefix}/cases/summary")', start)
        block = SOURCE[start:end]
        self.assertIn('await db.commit()', block)
        self.assertEqual(block.count('await db.commit()'), 1)
        self.assertIn('await db.rollback()', block)
        self.assertIn('_case_detail_action_capabilities', block)
        self.assertIn('_resolve_case_fee_contract', block)


if __name__ == "__main__":
    unittest.main()
