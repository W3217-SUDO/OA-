"""陶国南、陶威 11-01：智能体只读网页抓取（白名单、只读、限时限量）和个人空间 PDF 下载。"""
import shutil
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.agent_mcp import web_fetch
from app.core import pdf_conversion


class WebFetchRulesTest(unittest.IsolatedAsyncioTestCase):
    def test_only_whitelisted_https_hosts(self):
        for url in ("https://flk.npc.gov.cn/detail", "https://www.gov.cn/zhengce/", "https://www.court.gov.cn/",
                    "http://www.shanghai.gov.cn/a.html"):
            self.assertTrue(web_fetch.checked_url(url).startswith("https://"))
        for url in ("https://www.pkulaw.com/", "https://gov.cn.evil.com/", "https://evilgov.cn/", "https://localhost/",
                    "ftp://www.gov.cn/", "https://127.0.0.1/", "javascript:alert(1)"):
            with self.assertRaises(HTTPException):
                web_fetch.checked_url(url)

    def test_html_to_text_drops_scripts_and_keeps_title(self):
        title, text = web_fetch.page_text("<html><head><title>数据安全法</title><script>evil()</script></head>"
                                          "<body><h1>第一条</h1><p>为了规范数据处理活动</p><style>x{}</style></body></html>".encode(),
                                          "text/html; charset=utf-8")
        self.assertEqual(title, "数据安全法")
        self.assertEqual(text, "第一条\n为了规范数据处理活动")

    async def test_redirect_off_whitelist_is_refused(self):
        transport = web_fetch._FetchTransport()
        request = web_fetch.httpx2.Request("GET", "https://www.pkulaw.com/")
        with self.assertRaises(HTTPException):
            await transport.handle_async_request(request)

    async def test_internal_address_behind_whitelisted_name_is_refused(self):
        with patch("app.areas.capability_market.connector_transport.public_address",
                   side_effect=HTTPException(422, "不能连接内网、回环或保留地址")):
            with self.assertRaises(HTTPException) as caught:
                await web_fetch.fetch_page("https://intranet.gov.cn/")
        self.assertEqual(caught.exception.status_code, 422)

    def test_limits(self):
        self.assertEqual((web_fetch.TIMEOUT_SECONDS, web_fetch.MAX_BYTES), (15, 5 * 1024 * 1024))
        self.assertIn("不执行", web_fetch.UNTRUSTED_NOTICE)


class PdfConversionTest(unittest.IsolatedAsyncioTestCase):
    async def test_unsupported_and_missing_tool(self):
        with self.assertRaises(HTTPException) as caught:
            await pdf_conversion.convert_to_pdf("表格.xlsx", b"x")
        self.assertEqual(caught.exception.status_code, 422)
        with patch.object(pdf_conversion.shutil, "which", return_value=None):
            with self.assertRaises(HTTPException) as caught:
                await pdf_conversion.convert_to_pdf("法规.md", "# 法规".encode())
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(pdf_conversion.pdf_name("数据安全法.docx"), "数据安全法.pdf")

    @unittest.skipUnless(shutil.which("soffice"), "本机没有 LibreOffice")
    async def test_markdown_converts_to_pdf(self):
        content = await pdf_conversion.convert_to_pdf("法规.md", "# 数据安全法\n第一条 为了规范数据处理活动".encode())
        self.assertTrue(content.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
