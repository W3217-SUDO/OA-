import unittest
from pathlib import Path


class LegacyParentRepairContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("scripts/repair_legacy_parent_records.py").read_text(encoding="utf-8")

    def test_recovery_requires_real_number_and_name(self):
        self.assertIn("if number and name:", self.source)
        self.assertIn("Conflicting {key} values", self.source)
        self.assertNotIn("uuid4", self.source)

    def test_dry_run_is_default_and_apply_is_atomic(self):
        self.assertIn('parser.add_argument("--apply", action="store_true"', self.source)
        self.assertIn("if apply:\n            await db.commit()\n        else:\n            await db.rollback()", self.source)

    def test_unrecoverable_links_remain_auditable(self):
        for relation in (
            '("contract", "customer", "customer_no")',
            '("case", "contract", "contract_no")',
            '("investigation", "contract", "contract_no")',
            '("task", "investigation", "investigation_no")',
            '("clue", "task", "investigation_task_no")',
        ):
            self.assertIn(relation, self.source)
        self.assertIn('"unresolved_by_source"', self.source)
        self.assertIn('"wrong_module_counts"', self.source)
        self.assertIn('"unresolved_samples"', self.source)


if __name__ == "__main__":
    unittest.main()
