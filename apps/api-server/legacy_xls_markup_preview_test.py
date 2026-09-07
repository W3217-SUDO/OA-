from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.core.storage import _xls_preview_sheets


class LegacyXlsMarkupPreviewTest(unittest.TestCase):
    def _preview(self, content: str) -> tuple[list[dict], bool]:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.xls"
            path.write_bytes(content.encode("utf-8"))
            return _xls_preview_sheets(path)

    def test_html_workbook_with_xls_extension_is_readable(self) -> None:
        sheets, truncated = self._preview(
            "<html><table><tr><th>文件</th><th>状态</th></tr>"
            "<tr><td>申请表</td><td>待审核</td></tr></table></html>"
        )

        self.assertFalse(truncated)
        self.assertEqual(sheets, [{"name": "表格1", "rows": [["文件", "状态"], ["申请表", "待审核"]]}])

    def test_spreadsheetml_workbook_with_xls_extension_is_readable(self) -> None:
        sheets, truncated = self._preview(
            '<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
            'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="用印文件">'
            '<Table><Row><Cell><Data ss:Type="String">申请人</Data></Cell>'
            '<Cell ss:Index="3"><Data ss:Type="String">文件名</Data></Cell></Row></Table>'
            '</Worksheet></Workbook>'
        )

        self.assertFalse(truncated)
        self.assertEqual(sheets, [{"name": "用印文件", "rows": [["申请人", "", "文件名"]]}])


if __name__ == "__main__":
    unittest.main()
