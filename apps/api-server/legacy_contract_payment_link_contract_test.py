import pathlib
import unittest


MAIN = (pathlib.Path(__file__).parent / "app" / "main.py").read_text(encoding="utf-8")


class LegacyContractPaymentLinkContractTest(unittest.TestCase):
    def test_contract_payment_detail_includes_linked_legacy_payments(self):
        start = MAIN.index("async def list_contract_payment_applications")
        end = MAIN.index("@app.get(f\"{settings.api_prefix}/finance/payment-source", start)
        source = MAIN[start:end]
        self.assertIn('BusinessRecord.data["legacy_kind"].as_string() == "ap_payment"', source)
        self.assertIn('BusinessRecord.data["contract_id"].as_integer() == contract.id', source)
        self.assertIn('line.get("settlement_amount", 0)', source)


if __name__ == "__main__":
    unittest.main()
