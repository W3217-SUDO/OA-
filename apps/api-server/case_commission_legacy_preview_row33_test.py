from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
API = (ROOT / "apps" / "api-server" / "app" / "main.py").read_text(encoding="utf-8")
PAGE = (ROOT / "apps" / "admin-web" / "src" / "CaseCenterPage.tsx").read_text(encoding="utf-8")


class CaseCommissionLegacyPreviewRow33Test(unittest.TestCase):
    def test_commission_action_uses_legacy_more_actions_entry(self) -> None:
        firm_fee_toolbar = PAGE.split('{key:"firm-fees"', 1)[1].split('{key:"platform-fees"', 1)[0]
        create_menu, more_menu = firm_fee_toolbar.split('<Button>新增案件费用</Button>', 1)
        self.assertNotIn('新建提成(选择代理费)', create_menu)
        self.assertIn('新建提成(选择代理费)', more_menu)
        self.assertIn('key === "commission" ? void openCaseCommission()', more_menu)

    def test_unlinked_participant_uses_legacy_missing_setting_message(self) -> None:
        self.assertIn('missing.append(f"{token}未设{role[\'label\']}提成")', API)
        self.assertNotIn('未关联员工档案，无法读取', API)

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
