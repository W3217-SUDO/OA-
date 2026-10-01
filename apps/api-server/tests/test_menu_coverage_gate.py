"""菜单覆盖门禁需从真实声明与页面分派发现缺口。"""

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = REPOSITORY_ROOT / "scripts" / "audit-menu-coverage.py"
SPEC = importlib.util.spec_from_file_location("audit_menu_coverage", AUDIT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("无法载入菜单覆盖审计")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class MenuCoverageGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="oa-test-menu-coverage-")
        self.root = Path(self.directory.name)
        self.paths = (
            "apps/api-server/app/core/constants.py",
            "apps/api-server/app/areas/system/router.py",
            "apps/admin-web/src/App.tsx",
        )
        for relative in self.paths:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPOSITORY_ROOT / relative, target)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def replace_once(self, relative: str, old: str, new: str) -> None:
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_current_menu_is_covered(self) -> None:
        nodes, leaves = AUDIT.audit(self.root)
        self.assertGreater(nodes, leaves)
        self.assertGreater(leaves, 0)

    def test_unknown_menu_leaf_is_rejected(self) -> None:
        self.replace_once(
            self.paths[0], "DEFAULT_SYSTEM_MENUS = [",
            'DEFAULT_SYSTEM_MENUS = [("unrouted-alpha", "", "无页面", "", 1),',
        )
        with self.assertRaisesRegex(AssertionError, "unrouted-alpha"):
            AUDIT.audit(self.root)

    def test_removed_page_dispatch_is_rejected(self) -> None:
        self.replace_once(self.paths[2], 'route.startsWith("ipr-")', 'route.startsWith("ipr-disabled-")')
        with self.assertRaisesRegex(AssertionError, "ipr-"):
            AUDIT.audit(self.root)

    def test_removed_server_route_guard_is_rejected(self) -> None:
        self.replace_once(self.paths[1], "menu_key not in SYSTEM_MENU_ROUTE_KEYS", "menu_key not in set()")
        with self.assertRaisesRegex(AssertionError, "写入缺少"):
            AUDIT.audit(self.root)
