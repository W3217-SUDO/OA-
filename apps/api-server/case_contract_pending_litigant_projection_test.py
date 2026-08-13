"""Regression: pending contracts can start a case and defendants reach detail fields."""
from __future__ import annotations

import pathlib
import unittest

SOURCE = pathlib.Path(__file__).parent / "app" / "main.py"


class CaseContractPendingLitigantProjectionTest(unittest.TestCase):
    def test_pending_contract_is_an_eligible_case_source(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('CASE_SOURCE_CONTRACT_STATUSES = {"审批中", "已通过", "履行中", "已完成"}', source)
        self.assertIn('if contract.status not in CASE_SOURCE_CONTRACT_STATUSES:', source)

    def test_litigants_sync_the_legacy_detail_projection(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index('async def update_case_litigants')
        block = source[start:source.index('@app.put', start + 1)]
        self.assertIn('"defendants": defendants', block)
        self.assertIn('"opponent": "、".join(defendants)', block)
        self.assertIn('"plaintiff": "、".join(plaintiffs)', block)

    def test_contract_case_creation_persists_defendant_for_list_and_detail(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def create_case(body:")
        block = source[start:source.index("@app.post", start + 1)]
        self.assertIn("opponent = body.opponent.strip()", block)
        self.assertIn('"opponent": opponent', block)
        self.assertIn('"defendants": [opponent] if opponent else []', block)


if __name__ == "__main__":
    unittest.main()
