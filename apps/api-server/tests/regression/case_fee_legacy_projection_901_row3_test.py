"""9.1 row 3: legacy case-fee finance fields retain their distinct meanings."""

from __future__ import annotations

import unittest

from app.main import _case_fee_link_maps, _legacy_case_fee_projection, _resolve_case_fee_link_id
from app.models import BusinessRecord
from scripts.import_sh_latest50_samples import legacy_case_fee_finance_data


class CaseFeeLegacyProjectionRow3Test(unittest.TestCase):
    def test_resolves_migrated_receipt_link_by_legacy_case_fee_id(self) -> None:
        fee = BusinessRecord(
            id=9001,
            module="finance",
            serial_no="ROW3-FEE",
            title="law firm fee",
            customer="ROW3 customer",
            status="historical",
            owner="admin",
            department="finance",
            data={"legacy_case_fee_id": 42738, "case_no": "SHMS2600395"},
        )
        fee_ids, legacy_fee_ids = _case_fee_link_maps([fee])

        self.assertEqual(
            _resolve_case_fee_link_id({"legacy_case_fee_id": 42738}, fee_ids, legacy_fee_ids),
            9001,
        )

    def test_ambiguous_legacy_id_is_not_assigned(self) -> None:
        fees = [
            BusinessRecord(id=value, module="finance", serial_no=f"F-{value}", title="fee", customer="c", status="active", owner="admin", department="finance", data={"legacy_case_fee_id": 42738})
            for value in (9001, 9002)
        ]
        fee_ids, legacy_fee_ids = _case_fee_link_maps(fees)

        self.assertEqual(_resolve_case_fee_link_id({"legacy_case_fee_id": 42738}, fee_ids, legacy_fee_ids), 0)

    def test_new_imports_keep_every_legacy_finance_field_distinct(self) -> None:
        mapped = legacy_case_fee_finance_data({
            "Amount": 200,
            "RefundAmount": 120,
            "RefundedAmount": 80,
            "CashedDate": "2025-09-20",
            "CashedAmount": 200,
            "PaidAmount": 150,
            "InformDate": "2024-11-21",
            "RequestUser": "fwl",
        })

        self.assertEqual(mapped["refund_amount"], 120)
        self.assertEqual(mapped["refund_requested_amount"], 120)
        self.assertEqual(mapped["refunded_amount"], 80)
        self.assertEqual(mapped["received_at"], "2025-09-20")
        self.assertEqual(mapped["received_amount"], 200)
        self.assertEqual(mapped["payment_requested_amount"], 150)

    def test_repairs_the_early_import_shape(self) -> None:
        projected = _legacy_case_fee_projection({
            "legacy_case_fee_id": 31003,
            "legacy_record": {
                "RefundAmount": 200,
                "RefundedAmount": 80,
                "CashedDate": "2025-09-20T00:00:00",
                "CashedAmount": 200,
                "PaidAmount": 150,
                "InformDate": "2024-11-21T00:00:00",
                "RequestUser": "fwl",
                "InvoiceDate": "2025-12-02T00:00:00",
                "InvoiceNo": "4444444",
            },
            # This was the incorrect value written by the early importer.
            "refund_amount": 80,
        })

        self.assertEqual(projected["refund_amount"], 200)
        self.assertEqual(projected["refund_requested_amount"], 200)
        self.assertEqual(projected["refunded_amount"], 80)
        self.assertEqual(projected["received_at"], "2025-09-20T00:00:00")
        self.assertEqual(projected["cashed_date"], "2025-09-20T00:00:00")
        self.assertEqual(projected["received_amount"], 200)
        self.assertEqual(projected["cashed_amount"], 200)
        self.assertEqual(projected["payment_requested_amount"], 150)
        self.assertEqual(projected["submitted_at"], "2024-11-21T00:00:00")
        self.assertEqual(projected["submitted_by"], "fwl")
        self.assertEqual(projected["invoice_date"], "2025-12-02T00:00:00")
        self.assertEqual(projected["invoice_no"], "4444444")

    def test_does_not_overwrite_new_oa_transactions(self) -> None:
        projected = _legacy_case_fee_projection({
            "legacy_case_fee_id": 31003,
            "legacy_record": {
                "RefundAmount": 200,
                "RefundedAmount": 80,
                "CashedDate": "2025-09-20",
                "CashedAmount": 200,
            },
            "refund_amount": 300,
            "refund_requested_amount": 300,
            "refunded_amount": 300,
            "received_at": "2026-09-01",
            "cashed_date": "2026-09-01",
            "received_amount": 500,
            "cashed_amount": 500,
        })

        self.assertEqual(projected["refund_amount"], 300)
        self.assertEqual(projected["refunded_amount"], 300)
        self.assertEqual(projected["received_at"], "2026-09-01")
        self.assertEqual(projected["received_amount"], 500)


if __name__ == "__main__":
    unittest.main()
