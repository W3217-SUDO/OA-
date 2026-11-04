"""结算单压缩包“法院文书”文件夹另放诉讼费凭证、公证费发票（BUG20261103011）。"""

import unittest
from types import SimpleNamespace as NS

from app.areas.finance.settlement_package import court_folder_extras


def att(id, name, category="案件文档"):
    return NS(id=id, original_name=name, category=category)


class CourtFolderExtrasTest(unittest.TestCase):
    def test_litigation_vouchers_and_notary_invoices(self):
        fees = [NS(id=1, title="一审诉讼费"), NS(id=2, title="公证费"), NS(id=3, title="律师代理费"), NS(id=4, title="保全费")]
        by_record = {
            1: [att(11, "（2026）皖1323民初6448号.png", "案件票据文件")],
            2: [att(21, "公证发票.pdf", "案件发票文件"), att(22, "公证费支付.png", "案件票据文件")],
            3: [att(31, "代理费发票.pdf", "案件发票文件")],
            4: [att(41, "保全费凭证.pdf", "案件票据文件")],
        }
        case_docs = [att(51, "一审诉讼费收据.pdf"), att(52, "交纳诉讼费用通知书.pdf"), att(53, "迪锐克斯公证号2996号发票.pdf"), att(54, "6448撤诉裁定书.pdf")]
        names = [name for name, _ in court_folder_extras(case_docs, fees, by_record)]
        self.assertEqual(names, [
            "诉讼费凭证_一审诉讼费_（2026）皖1323民初6448号.png",
            "公证费发票_公证发票.pdf",
            "诉讼费凭证_一审诉讼费收据.pdf",
            "公证费发票_迪锐克斯公证号2996号发票.pdf",
        ])

    def test_no_notary_fee_skips_notary_invoice_docs(self):
        names = [name for name, _ in court_folder_extras([att(1, "公证费发票.pdf")], [NS(id=9, title="一审诉讼费")], {})]
        self.assertEqual(names, [])


class CaseSheetPdf501225Test(unittest.TestCase):
    def test_case_sheet_prints_landscape_on_one_page_without_header(self):
        import xlrd
        from decimal import Decimal
        from app.areas.finance.settlement_package import render_case_sheet
        content = render_case_sheet({"case_no": "GDMS2400287", "receipt_amount": Decimal("4975")}, [(None, None)] * 9)
        book = xlrd.open_workbook(file_contents=content, formatting_info=True)
        self.assertEqual(book.sheet_by_index(0).cell_value(2, 1), "GDMS2400287")
        # xlwt 写入的打印设置：横向（portrait=0）
        self.assertIn(b"\xa1\x00", content)  # SETUP 记录存在

    def test_batch_pdf_conversion_without_tool_returns_none(self):
        import asyncio
        from unittest.mock import patch
        from app.core.pdf_conversion import convert_many_to_pdf
        with patch("app.core.pdf_conversion.shutil.which", return_value=None):
            self.assertIsNone(asyncio.run(convert_many_to_pdf({"a.xls": b"x"}, ".xls")))


if __name__ == "__main__":
    unittest.main()
