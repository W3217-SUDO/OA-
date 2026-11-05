"""501611（fwl 11-05）：知识产权案件“申请类型”改成下拉，选项照旧系统“案件类型”（去重、顺序不变），放系统参数可维护；已有数据不改。"""

import unittest

from app.core.constants import DEFAULT_SYSTEM_PARAMETERS, SYSTEM_PARAMETER_CATEGORIES
from app.core.ipr import _ipr_case_export_values


class IprApplicationTypeTest(unittest.TestCase):
    def test_options_follow_legacy_order_without_duplicates(self):
        names = [name for category, _, name, _ in DEFAULT_SYSTEM_PARAMETERS if category == "ipr_application_type"]
        self.assertEqual(len(names), 22)
        self.assertEqual(len(set(names)), 22)
        self.assertEqual(names[:4], ["国内发明专利", "国内实用新型专利", "国内外观设计专利", "国内商标"])
        self.assertEqual(names[14:16], ["PCT发明进入中国", "PCT实用进入中国"])
        self.assertEqual(names[-2:], ["国内集成电路布图设计", "高新技术企业认定"])
        self.assertEqual(SYSTEM_PARAMETER_CATEGORIES["ipr_application_type"], "知识产权申请类型")

    def test_export_shows_legacy_case_type_when_application_type_empty(self):
        from types import SimpleNamespace
        row = SimpleNamespace(serial_no="ZL1", title="t", customer="c", owner="o", status="s", description="",
                              data={"case_type_name": "国内商标", "case_kind": "商标"})
        self.assertIn("国内商标", _ipr_case_export_values(row))


if __name__ == "__main__":
    unittest.main()
