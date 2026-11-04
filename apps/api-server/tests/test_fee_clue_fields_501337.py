"""501337：新增/修改公证费时登记所属线索，只能选本案关联的线索。"""

import asyncio
import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.core.case_fee_move import fee_clue_fields


class FeeClueFields501337Test(unittest.TestCase):
    def run_fields(self, clue_id, case=NS(id=1), clues=(NS(id=7),)):
        with patch("app.core.case_fee_move._case_clue_records", AsyncMock(return_value=list(clues))):
            return asyncio.run(fee_clue_fields(clue_id, case, None))

    def test_not_sent_keeps_existing(self):
        self.assertEqual(self.run_fields(None), {})

    def test_zero_clears(self):
        self.assertEqual(self.run_fields(0), {"clue_record_id": None})

    def test_case_clue_is_stored(self):
        self.assertEqual(self.run_fields(7), {"clue_record_id": 7})

    def test_other_clue_rejected(self):
        with self.assertRaises(HTTPException) as caught:
            self.run_fields(8)
        self.assertEqual(caught.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
