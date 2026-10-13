import unittest
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from fastapi import FastAPI

from app.skill_catalog import JSON_LIMIT, _cache, _json, _requests, catalog, catalog_preview, catalog_quota
from app.github_agent_skills import parse_github_skill, github_skill_location
from app.api_schemas.agents import UserAgentSkillInput, UserAgentSkillUpdate
from app.user_agent_skills import CUSTOM_SKILL_DESCRIPTION_LIMIT, CUSTOM_SKILL_INSTRUCTION_LIMIT, normalize_custom_skill

SHA = "a" * 40
CONTENT = b'---\nname: pdf\ndescription: Parse PDF documents\n---\nRead and summarize supplied PDF files.\n'


def fixture(request, *, duplicate=False, truncated=False):
    path = request.url.path
    if request.url.host == "skills.sh":
        return httpx.Response(200, json={"skills": [{"id": "anthropics/skills/pdf", "source": "anthropics/skills",
            "skillId": "pdf", "name": "PDF tools", "installs": 123}]})
    if path.endswith("/repos/anthropics/skills") or path.endswith("/repos/openai/skills"):
        return httpx.Response(200, json={"default_branch": "development"})
    if "/commits/" in path:
        return httpx.Response(200, json={"sha": SHA})
    if "/git/trees/" in path:
        paths = ["skills/pdf/SKILL.md", "skills/.curated/pdf/SKILL.md"] if "openai" in path else ["deep/real/pdf/SKILL.md"]
        if duplicate:
            paths.append("another/pdf/SKILL.md")
        return httpx.Response(200, json={"truncated": truncated, "tree": [
            {"type": "blob", "mode": "100644", "path": value} for value in paths]})
    if "/contents/" in path:
        return httpx.Response(200, content=CONTENT)
    return httpx.Response(404)


class CatalogTest(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_routes_require_authenticated_identity(self):
        from app.areas.personal_agent.router import router

        app = FastAPI()
        app.include_router(router)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated") as client:
            response = await client.get("/api/v1/agent/skills/catalog", params={"source": "openai"})
            self.assertEqual(response.status_code, 401)
            response = await client.post("/api/v1/agent/skills/catalog/preview", json={"source": "openai", "id": "any"})
            self.assertEqual(response.status_code, 401)

    async def test_market_selection_discovers_real_path_and_pins_commit(self):
        calls = []

        def response(request):
            calls.append(str(request.url))
            return fixture(request)

        transport = httpx.MockTransport(response)
        result = await catalog("skills-sh", "pdf", transport=transport)
        self.assertEqual(result["items"][0]["installs"], 123)
        self.assertEqual(result["items"][0]["description"], "")
        preview = await catalog_preview("skills-sh", "anthropics/skills/pdf", "pdf", transport=transport)
        self.assertIn("/blob/development/deep/real/pdf/SKILL.md", preview["url"])
        self.assertEqual(preview["resolved_commit"], SHA)
        self.assertEqual(preview["name"], "pdf")
        self.assertIn("?ref=" + SHA, calls[-1])
        self.assertFalse(any("/contents/pdf/SKILL.md" in call for call in calls))

    async def test_unrelated_repository_commit_keeps_stable_install_source(self):
        first = await catalog_preview("skills-sh", "anthropics/skills/pdf", "pdf", transport=httpx.MockTransport(fixture))

        def updated(request):
            if "/commits/" in request.url.path:
                return httpx.Response(200, json={"sha": "b" * 40})
            return fixture(request)

        second = await catalog_preview("skills-sh", "anthropics/skills/pdf", "pdf", transport=httpx.MockTransport(updated))
        self.assertEqual(first["url"], second["url"])
        self.assertEqual(first["source"], second["source"])
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertNotEqual(first["resolved_commit"], second["resolved_commit"])

    async def test_official_directory_filters_actual_paths_without_per_item_download(self):
        calls = []

        def response(request):
            calls.append(str(request.url))
            return fixture(request)

        result = await catalog("openai", transport=httpx.MockTransport(response))
        self.assertEqual(len(result["items"]), 1)
        self.assertIn("skills/.curated/pdf/SKILL.md", result["items"][0]["url"])
        self.assertFalse(any("/contents/" in url for url in calls))
        self.assertNotIn("installs", result["items"][0])

    async def test_forged_selection_ambiguous_path_and_truncated_tree_are_blocked(self):
        with self.assertRaises(HTTPException) as forged:
            await catalog_preview("skills-sh", "evil/repo/pdf", "pdf", transport=httpx.MockTransport(fixture))
        self.assertEqual(forged.exception.status_code, 409)
        for options in ({"duplicate": True}, {"truncated": True}):
            with self.subTest(options=options), self.assertRaises(HTTPException):
                await catalog_preview("skills-sh", "anthropics/skills/pdf", "pdf",
                    transport=httpx.MockTransport(lambda request: fixture(request, **options)))

    async def test_upstream_failures_and_redirects_do_not_become_empty_catalog(self):
        for response in (httpx.Response(302, headers={"location": "http://127.0.0.1/"}),
                         httpx.Response(429), httpx.Response(200, content=b"not json"),
                         httpx.Response(200, json={"skills": [{"id": "bad", "source": "../evil", "skillId": "pdf"}]}),
                         httpx.Response(200, content=b"x" * (JSON_LIMIT + 1))):
            with self.subTest(status=response.status_code), self.assertRaises(HTTPException) as failure:
                await catalog("skills-sh", "pdf", transport=httpx.MockTransport(lambda request: response))
            self.assertEqual(failure.exception.status_code, 502)
        with self.assertRaises(HTTPException):
            await _json("https://skills.sh.evil/api/search")

    async def test_public_cache_is_bounded_and_expires(self):
        _cache.clear()
        calls = []

        def response(request):
            calls.append(str(request.url))
            return httpx.Response(200, json={"skills": []})

        original = httpx.AsyncClient
        with patch("app.skill_catalog.httpx.AsyncClient", side_effect=lambda **kwargs: original(
                **{**kwargs, "transport": httpx.MockTransport(response)})):
            with patch("app.skill_catalog.time.monotonic", return_value=100):
                await _json("https://skills.sh/api/search?q=pdf")
                await _json("https://skills.sh/api/search?q=pdf")
            self.assertEqual(len(calls), 1)
            with patch("app.skill_catalog.time.monotonic", return_value=221):
                await _json("https://skills.sh/api/search?q=pdf")
            self.assertEqual(len(calls), 2)
        _cache.clear()


class SkillLimitsTest(unittest.TestCase):
    def test_long_official_skill_is_preserved_across_parser_schema_and_storage(self):
        body = "PDF instruction " * 600
        content = CONTENT.replace(b"Parse PDF documents", b"Official description " * 60) + body.encode()
        parsed = parse_github_skill(content, github_skill_location("https://github.com/a/b"))
        self.assertGreater(len(parsed["description"]), 500)
        self.assertGreater(len(parsed["instruction"]), 6000)
        normalized = normalize_custom_skill(parsed)
        self.assertEqual(normalized["instruction"], parsed["instruction"])
        UserAgentSkillInput(**normalized)
        UserAgentSkillUpdate(instruction=normalized["instruction"])
        with self.assertRaises(ValueError):
            normalize_custom_skill({**normalized, "instruction": "x" * (CUSTOM_SKILL_INSTRUCTION_LIMIT + 1)})
        with self.assertRaises(ValueError):
            normalize_custom_skill({**normalized, "description": "x" * (CUSTOM_SKILL_DESCRIPTION_LIMIT + 1)})
        with self.assertRaises(ValueError):
            UserAgentSkillInput(**{**normalized, "description": "x" * (CUSTOM_SKILL_DESCRIPTION_LIMIT + 1)})

    def test_catalog_request_quota_is_per_account(self):
        _requests.clear()
        for _ in range(30):
            catalog_quota("owner")
        with self.assertRaises(HTTPException) as rate:
            catalog_quota("owner")
        self.assertEqual(rate.exception.status_code, 429)
        catalog_quota("other")
        _requests.clear()


if __name__ == "__main__":
    unittest.main()
