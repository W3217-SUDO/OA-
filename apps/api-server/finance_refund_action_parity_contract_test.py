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

    def test_batch_payment_and_internal_fee_fields_are_persisted(self):
        self.assertIn('/finance/payment-types', SOURCE)
        self.assertIn('submit_payment: bool = False', SOURCE)
        self.assertIn('代理费不允许申请付款', SOURCE)
        for field in ('payment_requested_amount', 'payment_type_id', 'payee_username', 'base_amount', 'reference_commission', 'actual_commission'):
            self.assertIn(field, SOURCE)


if __name__ == "__main__":
    unittest.main()
