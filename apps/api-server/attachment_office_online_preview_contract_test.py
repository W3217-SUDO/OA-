import unittest
from pathlib import Path


ROUTER = Path(__file__).resolve().parent / "app" / "areas" / "system" / "router.py"


class AttachmentOfficeOnlinePreviewContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ROUTER.read_text(encoding="utf-8")

    def test_authenticated_endpoint_issues_short_lived_office_token(self):
        self.assertIn("async def create_office_preview_link(", self.source)
        self.assertIn('"purpose": "office-online-preview"', self.source)
        self.assertIn("timedelta(minutes=10)", self.source)
        self.assertIn("_ensure_attachment_record_visible(item.record_id, identity, db)", self.source)

    def test_public_endpoint_validates_token_and_streams_original_file_inline(self):
        self.assertIn("async def stream_office_preview_attachment(", self.source)
        self.assertIn('jwt.decode(token, settings.secret_key, algorithms=["HS256"])', self.source)
        self.assertIn('content_disposition_type="inline"', self.source)
        self.assertIn('"Cache-Control": "private, max-age=600"', self.source)


if __name__ == "__main__":
    unittest.main()
