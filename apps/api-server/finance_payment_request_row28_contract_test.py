"""Static contract checks for the row 28 case-fee payment request flow."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = (ROOT / "apps" / "api-server" / "app" / "main.py").read_text(encoding="utf-8")
FRONTEND = (ROOT / "apps" / "admin-web" / "src" / "CaseCenterPage.tsx").read_text(encoding="utf-8")


class FinancePaymentRequestRow28Contract(unittest.TestCase):
    def test_backend_accepts_and_persists_legacy_payment_step_fields(self):
        self.assertIn('amount: float | None = Field(default=None, gt=0)', BACKEND)
        self.assertIn('payment_type_id: int | None = Field(default=None, gt=0)', BACKEND)
        self.assertIn('payment_account: str = Field(default="", max_length=128)', BACKEND)
        self.assertIn('payment_payee: str = Field(default="", max_length=256)', BACKEND)
        self.assertIn('payment_remark: str = Field(default="", max_length=1000)', BACKEND)
        self.assertIn('if body.amount is not None:', BACKEND)
        self.assertIn('if not is_payment_request:', BACKEND)
        self.assertIn('payment_requested_amount', BACKEND)
        self.assertIn('"payment_account": account', BACKEND)
        self.assertIn('"payment_payee": payee', BACKEND)
        self.assertIn('"payment_remark": payment_remark', BACKEND)
        self.assertIn('if not payee:', BACKEND)
        self.assertIn('detail="请选择系统付款单位"', BACKEND)

    def test_frontend_exposes_the_payment_step_fields(self):
        self.assertIn('case-fee-payment-request-table', FRONTEND)
        self.assertIn('name="amount"', FRONTEND)
        self.assertIn('name="payment_remark"', FRONTEND)
        self.assertIn('name="payment_type_id"', FRONTEND)
        self.assertIn('title="新增付款单位"', FRONTEND)


if __name__ == "__main__":
    unittest.main()
