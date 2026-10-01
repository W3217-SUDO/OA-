import unittest
from pathlib import Path


class LegacyProjectionBackfillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("scripts/backfill_legacy_projections.py").read_text(encoding="utf-8")

    def test_targets_every_synchronized_legacy_module(self):
        for module in ("customer", "contract", "case", "investigation", "task", "clue"):
            self.assertIn(f'"{module}"', self.source)
        self.assertIn("await _sync_legacy_projection(record, record_identity(record), db)", self.source)

    def test_dry_run_is_default_and_apply_is_atomic(self):
        self.assertIn('parser.add_argument("--apply", action="store_true"', self.source)
        self.assertIn("if apply:\n                await db.commit()\n            else:\n                await db.rollback()", self.source)
        self.assertIn("except Exception:\n            await db.rollback()\n            raise", self.source)


if __name__ == "__main__":
    unittest.main()
