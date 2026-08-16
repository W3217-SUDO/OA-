"""Static contract checks for the row 28 case-fee payment request flow."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = (ROOT / "apps" / "api-server" / "app" / "main.py").read_text(encoding="utf-8")
FRONTEND = (ROOT / "apps" / "admin-web" / "src" / "CaseCenterPage.tsx").read_text(encoding="utf-8")


class FinancePaymentRequestRow28Contract(unittest.TestCase):
    def test_backend_accepts_and_persists_amount_and_account(self):
        self.assertIn('amount: float | None = Field(default=None, gt=0)', BACKEND)
        self.assertIn('payment_account: str = Field(default="", max_length=128)', BACKEND)
        self.assertIn('if body.amount is not None:', BACKEND)
        self.assertIn('if not is_payment_request:', BACKEND)
        self.assertIn('payment_requested_amount', BACKEND)
        self.assertIn('"payment_account": account', BACKEND)
        self.assertIn('申请付款金额不能超过未付款金额', BACKEND)

    def test_frontend_exposes_the_two_required_fields(self):
        self.assertIn('label="申请付款金额" name="amount"', FRONTEND)
        self.assertIn('label="付款账号" name="payment_account"', FRONTEND)
        self.assertIn('title:"申请付款金额"', FRONTEND)
        self.assertIn('title:"付款账号"', FRONTEND)


if __name__ == "__main__":
    unittest.main()
