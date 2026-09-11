import ast
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parent


class FeeTypeDefaultRepairRow4Test(unittest.TestCase):
    def test_startup_loads_default_fee_type_catalog_entries(self):
        source = (ROOT / "app" / "core" / "lifecycle.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        text = ast.unparse(tree)
        self.assertIn("for index, (category, code, name, extra) in enumerate(DEFAULT_SYSTEM_PARAMETERS, start=1)", text)
        self.assertIn("created_by='system'", text)
        self.assertIn("sort_order=index", text)

    def test_default_catalog_keeps_legacy_root_and_leaf_relationships(self):
        source = (ROOT / "app" / "core" / "constants.py").read_text(encoding="utf-8")
        self.assertIn('("fee_type", "OFFICIAL", "官方费用", {"parent_code": ""})', source)
        self.assertIn('("fee_type", "11010010", "差旅费", {"parent_code": "OFFICIAL", "legacy_code": "11010010"})', source)
        self.assertIn('("fee_type", "1101010", "一审诉讼费", {"parent_code": "OFFICIAL"})', source)
        self.assertIn('("fee_type", "AGENCY", "代理费", {"parent_code": ""})', source)
        self.assertIn('("fee_type", "1102010", "律师代理费", {"parent_code": "AGENCY"})', source)

    def test_legacy_case_fee_filter_names_are_present_in_the_catalog(self):
        source = (ROOT / "app" / "core" / "constants.py").read_text(encoding="utf-8")
        for name in ("官费", "差旅费", "一审诉讼费", "二审诉讼费", "再审诉讼费", "公证费", "调解金额", "判决金额", "保全费", "公告费", "担保费", "鉴定费", "执行费", "公证服务费", "代理费", "律师代理费", "律师咨询费", "律师培训费", "律师见证费", "核定成本"):
            self.assertIn(f'"{name}"', source, name)



if __name__ == "__main__":
    unittest.main()

