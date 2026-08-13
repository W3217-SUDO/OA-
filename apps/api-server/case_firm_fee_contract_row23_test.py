"""Regression coverage for 8.12 row 23 firm-fee contract binding."""

import unittest

from app.main import EXPENSE_SUBTYPE_FEE_TYPE, EXPENSE_SCOPE_FEE_TYPES


class FirmFeeContractRow23Test(unittest.TestCase):
    def test_law_firm_fee_branches_have_valid_backend_mappings(self):
        expected = {
            "官费": "官方费用",
            "诉讼费": "官方费用",
            "保全费": "官方费用",
            "鉴定费": "官方费用",
            "公证费": "官方费用",
            "公告费": "官方费用",
            "执行费": "官方费用",
            "第三方费用": "其他费用",
            "代理费": "代理费",
            "其他费用": "其他费用",
        }
        self.assertEqual({key: EXPENSE_SUBTYPE_FEE_TYPE[key] for key in expected}, expected)
        for fee_type in expected.values():
            self.assertIn(fee_type, EXPENSE_SCOPE_FEE_TYPES["律所"])


if __name__ == "__main__":
    unittest.main()
