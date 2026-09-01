from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
API = (ROOT / "apps" / "api-server" / "app" / "main.py").read_text(encoding="utf-8")
PAGE = (ROOT / "apps" / "admin-web" / "src" / "CaseCenterPage.tsx").read_text(encoding="utf-8")


class CaseCommissionLegacyPreviewRow33Test(unittest.TestCase):
    def test_legacy_commission_type_labels_are_preserved(self) -> None:
        for label in (
            "开庭提成", "开庭固定提成", "文书提成", "文书固定提成",
            "案源提成", "案源固定提成", "调查提成", "调查固定提成",
            "品牌管理费", "品牌固定管理费",
        ):
            self.assertIn(f'"{label}"', API)
        for replaced in ("开庭比例提成", "文书比例提成", "案源比例提成", "调查比例提成", "品管比例提成"):
            self.assertNotIn(f'"rate_name": "{replaced}"', API)

    def test_preview_restores_legacy_fee_summary(self) -> None:
        for field in ("refund_amount", "invoice_over_amount", "cost_over_amount"):
            self.assertIn(f'"{field}"', API)
            self.assertIn(field, PAGE)
        for label in ("法院退费", "高开金额", "高开成本", "提成基数"):
            self.assertIn(label, PAGE)


if __name__ == "__main__":
    unittest.main()
