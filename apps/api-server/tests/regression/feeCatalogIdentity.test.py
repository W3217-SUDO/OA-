"""费用目录去重不得删除与初始化代码重合的真实旧类型。"""
import unittest

from app.models import SystemParameter
from app.core.finance import _fee_type_catalog, _fee_type_catalog_aliases, _fee_type_root_replacements


class FeeCatalogIdentityTest(unittest.TestCase):
    def test_other_and_third_party_roots_are_not_conflated(self):
        items = [
            SystemParameter(code="OTHER", name="其他费用", extra={}),
            SystemParameter(code="LEGACY-OTHER", name="其他费用", extra={"legacy_group_id": 3, "base_fee_type": "其他费用"}),
            SystemParameter(code="LEGACY-THIRD", name="第三方费用", extra={"legacy_group_id": 5, "base_fee_type": "其他费用"}),
        ]
        self.assertEqual(_fee_type_root_replacements(items), {"OTHER": "LEGACY-OTHER"})

    def test_legacy_seed_code_is_preserved_and_only_initial_duplicate_is_aliased(self):
        items = [
            SystemParameter(id=1, category="fee_type", code="OFFICIAL", name="官方费用", is_active=True, extra={}),
            SystemParameter(id=2, category="fee_type", code="LEGACY-FEE-GROUP-1", name="官费", is_active=True, extra={"legacy_group_id": 1}),
            SystemParameter(id=3, category="fee_type", code="11010010", name="差旅费", is_active=False, extra={"parent_code": "LEGACY-FEE-GROUP-1", "legacy_source": "SYS_Fee_Type"}),
            SystemParameter(id=4, category="fee_type", code="1101010", name="一审诉讼费", is_active=True, extra={"parent_code": "OFFICIAL"}),
            SystemParameter(id=5, category="fee_type", code="11010020", name="一审诉讼费", is_active=True, extra={"parent_code": "LEGACY-FEE-GROUP-1", "legacy_source": "SYS_Fee_Type"}),
            SystemParameter(id=6, category="fee_type", code="CUSTOM", name="一审诉讼费", is_active=True, extra={"parent_code": "OFFICIAL"}),
        ]
        catalog = _fee_type_catalog(items, include_inactive=True)
        by_code = {item["code"]: item for item in catalog}
        self.assertEqual(set(by_code), {"LEGACY-FEE-GROUP-1", "11010010", "11010020", "CUSTOM"})
        self.assertFalse(by_code["11010010"]["selectable"])
        self.assertEqual(by_code["CUSTOM"]["parent_code"], "LEGACY-FEE-GROUP-1")
        self.assertEqual(_fee_type_catalog_aliases(items), {4: 5})


if __name__ == "__main__":
    unittest.main()
