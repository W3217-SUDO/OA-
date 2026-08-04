from pathlib import Path
import re
import unittest


class SmokeCaseTaskPaginationSourceContractTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.source = (root / "scripts" / "smoke-api.py").read_text(encoding="utf-8")

    def test_case_task_smoke_paths_do_not_consume_default_first_page(self):
        self.assertTrue("def paged_items(" in self.source, "smoke-api.py must expose paged_items helper")
        naked_case_task_calls = re.findall(
            r'call\("GET",\s*f"/cases/\{[^}]+\}/tasks"\)(?:\["items"\])?',
            self.source,
        )
        self.assertEqual(naked_case_task_calls, [])
        self.assertGreaterEqual(len(re.findall(r'paged_items\(f"/cases/\{[^}]+\}/tasks"', self.source)), 4)


if __name__ == "__main__":
    unittest.main()
