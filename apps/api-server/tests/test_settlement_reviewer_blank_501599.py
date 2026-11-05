"""501599（shenhe 11-05）：结算单的个案结算表“审核:”一栏留空，“时间”和其他内容不变。"""
import inspect
import unittest
from decimal import Decimal

import xlrd

from app.areas.finance import settlement_package as module


class SettlementReviewerBlank501599Test(unittest.TestCase):
    def test_reviewer_cell_left_blank_and_date_kept(self):
        source = inspect.getsource(module.build_settlement_package)
        self.assertIn('auditor = ""', source)
        self.assertNotIn('identity.get("display_name") or identity.get("username")', source)
        content = module.render_case_sheet({"case_no": "GDMS2400287", "auditor": "", "audit_date": "2026-11-05",
                                            "receipt_amount": Decimal("100")}, [(None, None)] * 9)
        sheet = xlrd.open_workbook(file_contents=content, formatting_info=True).sheet_by_index(0)
        row, column = module.VALUE_CELLS["auditor"]
        self.assertEqual(sheet.cell_value(row, 0), "审核:")
        self.assertEqual(sheet.cell_value(row, column), "")
        date_row, date_column = module.VALUE_CELLS["audit_date"]
        self.assertEqual(sheet.cell_value(date_row, date_column), "2026-11-05")


if __name__ == "__main__":
    unittest.main()
