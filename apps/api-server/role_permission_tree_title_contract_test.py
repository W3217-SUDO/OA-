import unittest
from pathlib import Path


class RolePermissionTreeTitleContractTest(unittest.TestCase):
    def test_permission_tree_exposes_ant_design_title_for_menus_and_actions(self):
        source = (Path(__file__).parent / "app" / "main.py").read_text(encoding="utf-8")
        tree_start = source.index("async def _system_permission_tree")
        tree_end = source.index("def _normalize_system_user_role_ids", tree_start)
        tree = source[tree_start:tree_end]
        self.assertIn('"text": definition["label"], "title": definition["label"]', tree)
        self.assertIn('"text": label, "title": label', tree)
        self.assertIn('"text": definition["menu_key"], "title": definition["menu_key"]', tree)


if __name__ == "__main__":
    unittest.main()
