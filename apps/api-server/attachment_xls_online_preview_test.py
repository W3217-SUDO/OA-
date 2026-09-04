import tempfile
import unittest
from pathlib import Path

import xlwt

from app.main import _xls_preview_sheets


class AttachmentXlsOnlinePreviewTest(unittest.TestCase):
    def test_legacy_xls_is_extracted_as_bounded_workbook_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.xls"
            workbook = xlwt.Workbook()
            sheet = workbook.add_sheet("费用表")
            for column, value in enumerate(["案号", "合同号", "金额"]):
                sheet.write(0, column, value)
            for column, value in enumerate(["CASE-001", "CONTRACT-001", 100]):
                sheet.write(1, column, value)
            workbook.save(str(path))
            original = path.read_bytes()

            sheets, truncated = _xls_preview_sheets(path)

            self.assertFalse(truncated)
            self.assertEqual(sheets, [{"name": "费用表", "rows": [["案号", "合同号", "金额"], ["CASE-001", "CONTRACT-001", "100"]]}])
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
