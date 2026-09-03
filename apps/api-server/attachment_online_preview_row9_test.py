import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from app.main import _xlsx_preview_text


class AttachmentOnlinePreviewRow9Test(unittest.TestCase):
    def test_xlsx_preview_extracts_each_sheet_without_modifying_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "用印附件.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "申请单"
            sheet.append(["案号", "合同号", "份数"])
            sheet.append(["CASE-001", "CONTRACT-001", 2])
            workbook.create_sheet("备注")["A1"] = "在线查看"
            workbook.save(path)
            original = path.read_bytes()

            text = _xlsx_preview_text(path)

            self.assertIn("工作表：申请单", text)
            self.assertIn("案号\t合同号\t份数", text)
            self.assertIn("CASE-001\tCONTRACT-001\t2", text)
            self.assertIn("工作表：备注", text)
            self.assertIn("在线查看", text)
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
