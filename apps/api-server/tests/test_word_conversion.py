"""陶国南 11-01：免费法规原文（PDF、WPS）转成 Word。"""
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.core import word_conversion


class WordConversionTest(unittest.IsolatedAsyncioTestCase):
    def test_pdf_lines_become_law_paragraphs(self):
        lines = ["中华人民共和国数据安全法", "第一章　总　　则", "第一条　为了规范数据处理活动，保障数据安全，促进数据开发利用，",
                 "保护个人、组织的合法权益，制定本法。", "— 1 —", "第二条　在中华人民共和国境内开展数据处理活动，",
                 "适用本法。", "", "2"]
        self.assertEqual(word_conversion.rebuild_paragraphs(lines).split("\n\n"), [
            "中华人民共和国数据安全法", "第一章 总  则",
            "第一条 为了规范数据处理活动，保障数据安全，促进数据开发利用，保护个人、组织的合法权益，制定本法。",
            "第二条 在中华人民共和国境内开展数据处理活动，适用本法。"])

    async def test_unsupported_and_scanned(self):
        with self.assertRaises(HTTPException) as caught:
            await word_conversion.convert_to_word("表.xlsx", b"x")
        self.assertEqual(caught.exception.status_code, 422)
        with patch.object(word_conversion, "_pdf_lines", return_value=["", "1"]):
            with self.assertRaises(HTTPException) as caught:
                await word_conversion.convert_to_word("扫描件.pdf", b"%PDF-")
        self.assertIn("扫描件", caught.exception.detail)
        self.assertEqual(word_conversion.word_name("数据安全法.wps"), "数据安全法.docx")

    async def test_pdf_text_becomes_docx(self):
        with patch.object(word_conversion, "_pdf_lines", return_value=["数据安全法", "第一条　为了规范数据处理活动，制定本法。"]):
            content = await word_conversion.convert_to_word("数据安全法.pdf", b"%PDF-")
        self.assertTrue(content.startswith(b"PK"))


if __name__ == "__main__":
    unittest.main()
