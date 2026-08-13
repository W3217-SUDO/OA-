import unittest
from pathlib import Path


class LegacyCaseAttachmentReconcileContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("scripts/reconcile_legacy_case_attachments.py").read_text(encoding="utf-8")

    def test_dry_run_is_default_and_apply_is_atomic(self):
        self.assertIn('parser.add_argument("--apply", action="store_true")', self.source)
        self.assertIn('"mode": "apply" if apply else "dry-run"', self.source)
        self.assertIn("if apply:\n                await db.commit()\n            else:\n                await db.rollback()", self.source)

    def test_requires_verified_physical_file_size(self):
        self.assertIn("size mismatch for legacy file", self.source)
        self.assertIn("existing legacy file size mismatch", self.source)
        self.assertIn("partial.replace(target)", self.source)
        self.assertIn("semaphore = asyncio.Semaphore(8)", self.source)
        self.assertIn("await asyncio.gather(*(prefetch(item) for item in items))", self.source)
        self.assertIn('parser.add_argument("--source-root", type=Path)', self.source)

    def test_only_matching_empty_placeholders_are_deleted(self):
        for guard in (
            "candidate.record_id == case.id",
            "candidate.remark in PLACEHOLDER_REMARKS",
            "candidate.original_name == attachment.original_name",
            "candidate.size == attachment.size",
            "not Path(candidate.path).is_file()",
        ):
            self.assertIn(guard, self.source)

    def test_stale_placeholders_are_scoped_to_manifest_cases(self):
        for guard in (
            "attachment.remark in PLACEHOLDER_REMARKS",
            "not Path(attachment.path).is_file()",
            "case_number_by_id.get(attachment.record_id) in manifest_case_numbers",
            ") not in manifest_file_keys",
        ):
            self.assertIn(guard, self.source)

    def test_shared_upload_root_is_version_independent(self):
        config = Path("app/config.py").read_text(encoding="utf-8")
        main = Path("app/main.py").read_text(encoding="utf-8")
        self.assertIn('upload_root: str = ""', config)
        self.assertIn("Path(settings.upload_root).expanduser().resolve()", main)


if __name__ == "__main__":
    unittest.main()
