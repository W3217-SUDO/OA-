"""Static contract for the administrative seal-application ZIP endpoint.

This test deliberately uses no HTTP session, database, or upload directory. It
guards the endpoint shape and its read-only authorization/file-selection rules.
"""

from pathlib import Path
import unittest


MAIN = Path(__file__).resolve().parent / "app" / "main.py"


class SealBatchDownloadEndpointContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MAIN.read_text(encoding="utf-8")
        marker = '@app.post(f"{settings.api_prefix}/seals/applications/batch-download")'
        cls.start = cls.source.index(marker)
        cls.end = cls.source.index("@app.post", cls.start + len(marker))
        cls.endpoint = cls.source[cls.start:cls.end]

    def test_request_requires_at_least_one_and_limits_the_batch(self):
        self.assertIn("class SealPackageDownloadInput", self.source)
        self.assertIn("application_ids: list[int] = Field(min_length=1, max_length=100)", self.source)
        self.assertIn("list(dict.fromkeys(body.application_ids))", self.endpoint)

    def test_endpoint_checks_each_selected_seal_and_only_archives_seal_files(self):
        self.assertIn('_ensure_record_module(record_id, "seal", identity, db)', self.endpoint)
        self.assertIn("SEAL_APPLICATION_FILE_CATEGORY", self.endpoint)
        self.assertIn("SEAL_STAMPED_FILE_CATEGORY", self.endpoint)
        self.assertIn("_attachment_storage_path(attachment)", self.endpoint)

    def test_endpoint_returns_zip_or_a_meaningful_not_found_response_without_writing(self):
        self.assertIn('media_type="application/zip"', self.endpoint)
        self.assertIn("StreamingResponse", self.endpoint)
        self.assertIn("所选用印申请暂无可下载附件", self.endpoint)
        self.assertIn("所选附件文件不存在", self.endpoint)
        self.assertNotIn("db.delete", self.endpoint)
        self.assertNotIn("await db.commit", self.endpoint)


if __name__ == "__main__":
    unittest.main()
