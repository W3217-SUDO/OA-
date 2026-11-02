"""智能体从国家法律法规数据库查找、下载法规原文（陶国南 11-02）。"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.agent_mcp import flk_laws
from app.areas.personal_agent.mcp_tools import PersonalMcpToolSession

ID = "ff808081729d1efe01729d50b5c500bf"
SEARCH = {"code": 200, "total": 2, "rows": [
    {"bbbs": ID, "title": "中华人民共和国<em class='highlight'>民法典</em>", "zdjgName": "全国人民代表大会",
     "flxz": "法律", "sxx": 3, "gbrq": "2020-05-28", "sxrq": "2021-01-01"},
    {"bbbs": "2c909fdd678bf17901678bf674710415", "title": "中华人民共和国民法通则", "zdjgName": "全国人民代表大会",
     "flxz": "法律", "sxx": 1, "gbrq": "2009-08-27", "sxrq": "2009-08-27"},
]}
DETAIL = {"code": 200, "data": {"bbbs": ID, "title": "中华人民共和国民法典", "zdjgName": "全国人民代表大会", "sxx": 3,
                                "gbrq": "2020-05-28", "sxrq": "2021-01-01",
                                "ossFile": {"ossPdfPath": "prod/x.pdf", "ossWordPath": ""}}}
OFFICIAL = "https://flkoss.obs-bj2.cucloud.cn/prod/x.pdf?X-Amz-Signature=abc"


class _Response:
    def __init__(self, content, status_code=200):
        self.content, self.status_code = content, status_code


class _Client:
    def __init__(self, content):
        self.content = content
        self.urls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url):
        self.urls.append(url)
        return _Response(self.content)


class FlkLawsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        flk_laws._usage.clear()
        self.identity = {"username": "lawyer"}

    async def test_search_lists_candidates_with_validity(self):
        with patch.object(flk_laws, "_flk", AsyncMock(return_value=SEARCH)) as call:
            result = await flk_laws.search_laws("《民法典》", self.identity)
        body = call.await_args.kwargs["json"]
        self.assertEqual((body["searchContent"], body["searchType"], body["searchRange"], body["pageSize"]), ("民法典", 1, 1, 10))
        self.assertEqual(result["items"][0], {
            "law_id": ID, "title": "中华人民共和国民法典", "issuer": "全国人民代表大会", "category": "法律",
            "validity": "现行有效", "published_on": "2020-05-28", "effective_on": "2021-01-01"})
        self.assertEqual(result["items"][1]["validity"], "已废止")

    async def test_falls_back_to_fuzzy_search_when_exact_finds_nothing(self):
        with patch.object(flk_laws, "_flk", AsyncMock(side_effect=[{"code": 200, "total": 0, "rows": []}, SEARCH])) as call:
            result = await flk_laws.search_laws("民法", self.identity)
        self.assertEqual([item.kwargs["json"]["searchType"] for item in call.await_args_list], [1, 2])
        self.assertEqual(len(result["items"]), 2)

    async def test_daily_limit(self):
        with patch.object(flk_laws, "_flk", AsyncMock(return_value=SEARCH)), patch.object(flk_laws, "DAILY_SEARCHES", 2):
            await flk_laws.search_laws("民法典", self.identity)
            await flk_laws.search_laws("民法典", self.identity)
            with self.assertRaises(HTTPException) as error:
                await flk_laws.search_laws("民法典", self.identity)
        self.assertEqual(error.exception.status_code, 429)

    async def test_download_saves_official_pdf_to_personal_space(self):
        client = _Client(b"%PDF-1.7 ...")
        save = AsyncMock(return_value={"file": {}})
        with patch.object(flk_laws, "_flk", AsyncMock(side_effect=[DETAIL, {"code": 200, "data": {"url": OFFICIAL}}])), \
                patch.object(flk_laws.httpx2, "AsyncClient", lambda **kwargs: client), \
                patch("app.core.generated_file_storage.save_generated_file", save), \
                patch("app.agent_mcp.artifacts._generated_metadata", lambda file: {}), \
                patch("app.agent_mcp.artifacts.resource_metadata", lambda meta: {"type": "resource_link"}):
            result = await flk_laws.download_law(ID, "pdf", self.identity, db="db", conversation_id="c1")
        self.assertEqual(client.urls, [OFFICIAL])
        kwargs = save.await_args.kwargs
        self.assertEqual((kwargs["name"], kwargs["content_type"], kwargs["conversation_id"], kwargs["source_kind"]),
                         ("中华人民共和国民法典_20200528.pdf", "application/pdf", "c1", "flk_download"))
        self.assertNotIn("case_record", kwargs)
        self.assertEqual(result["law"]["validity"], "现行有效")

    async def test_download_rejects_missing_format_foreign_link_and_bad_file(self):
        with patch.object(flk_laws, "_flk", AsyncMock(return_value=DETAIL)):
            with self.assertRaises(HTTPException) as error:
                await flk_laws.download_law(ID, "word", self.identity, db=None, conversation_id="c1")
        self.assertEqual(error.exception.status_code, 404)
        with patch.object(flk_laws, "_flk", AsyncMock(side_effect=[DETAIL, {"code": 200, "data": {"url": "https://evil.example.com/x.pdf"}}])):
            with self.assertRaises(HTTPException) as error:
                await flk_laws.download_law(ID, "pdf", self.identity, db=None, conversation_id="c1")
        self.assertEqual(error.exception.status_code, 502)
        with patch.object(flk_laws, "_flk", AsyncMock(side_effect=[DETAIL, {"code": 200, "data": {"url": OFFICIAL}}])), \
                patch.object(flk_laws.httpx2, "AsyncClient", lambda **kwargs: _Client(b"<html>captcha</html>")):
            with self.assertRaises(HTTPException) as error:
                await flk_laws.download_law(ID, "pdf", self.identity, db=None, conversation_id="c1")
        self.assertEqual(error.exception.status_code, 502)
        for bad in ("../../etc", "x" * 100, None):
            with self.assertRaises(HTTPException):
                await flk_laws.download_law(bad, "pdf", self.identity, db=None, conversation_id="c1")

    async def test_file_transport_only_allows_official_storage(self):
        import httpx2
        transport = flk_laws._FileTransport()
        with self.assertRaises(HTTPException):
            await transport.handle_async_request(httpx2.Request("GET", "https://example.com/a.pdf"))

    async def test_personal_agent_exposes_tools(self):
        session = PersonalMcpToolSession({"username": "lawyer"}, None, conversation_id="c1")
        names = {tool["function"]["name"] for tool in session.model_tools}
        self.assertTrue({"flk_search_laws", "flk_download_law"} <= names)
        with patch.object(flk_laws, "search_laws", AsyncMock(return_value={"items": []})) as search:
            await session._execute("flk_search_laws", {"keyword": "民法典"})
        search.assert_awaited_once()
        with self.assertRaises(HTTPException):
            await session._execute("flk_download_law", {"law_id": ID})
        with patch.object(flk_laws, "download_law", AsyncMock(return_value={})) as download:
            await session._execute("flk_download_law", {"law_id": ID, "format": "word"})
        self.assertEqual(download.await_args.kwargs["conversation_id"], "c1")


if __name__ == "__main__":
    unittest.main()
