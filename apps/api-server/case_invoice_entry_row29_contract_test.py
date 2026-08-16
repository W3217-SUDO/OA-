"""Static contract checks for the row 29 case-fee invoice entry flow."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = (ROOT / "apps" / "api-server" / "app" / "main.py").read_text(encoding="utf-8")


class CaseInvoiceEntryRow29Contract(unittest.TestCase):
    def test_case_relations_expose_active_invoice_state_for_each_fee(self):
        self.assertIn("active_invoices_by_fee", BACKEND)
        self.assertIn('result_data["invoice_status"]', BACKEND)
        self.assertIn('result_data["invoice_application_no"]', BACKEND)
        self.assertIn("INVOICE_RELEASED_STATUSES", BACKEND)


if __name__ == "__main__":
    unittest.main()
