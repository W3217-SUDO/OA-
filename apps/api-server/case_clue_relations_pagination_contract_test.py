"""Contract coverage for the case-detail related-clue list API."""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app, list_case_relations
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "case-clue-page-admin", "role": "admin", "display_name": "Case clue page admin", "department": "Investigation"}
OUTSIDER = {"username": "case-clue-page-outsider", "role": "user", "display_name": "Case clue page outsider", "department": "Other"}


class CaseClueRelationsPaginationContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="x", is_active=True),
                User(username=OUTSIDER["username"], display_name=OUTSIDER["display_name"], department=OUTSIDER["department"], role="user", password_hash="x", is_active=True),
            ])
            clues = [
                BusinessRecord(module="clue", serial_no="CODEX-CLUE-ALPHA-1", title="Alpha storefront", customer="Alpha client", status="draft", owner=ADMIN["username"], department=ADMIN["department"], description="first source", data={"shop_name": "Alpha Store", "shop_address": "Alpha Road"}),
                BusinessRecord(module="clue", serial_no="CODEX-CLUE-ALPHA-2", title="Other storefront", customer="Alpha client", status="draft", owner=ADMIN["username"], department=ADMIN["department"], description="second source", data={"platform": "Alpha platform", "certificate_no": "CERT-ALPHA"}),
                BusinessRecord(module="clue", serial_no="CODEX-CLUE-BETA-1", title="Beta storefront", customer="Beta client", status="draft", owner=ADMIN["username"], department=ADMIN["department"], description="third source", data={"shop_name": "Beta Store"}),
            ]
            db.add_all(clues)
            await db.flush()
            case = BusinessRecord(
                module="case", serial_no="CODEX-CASE-CLUE-PAGE", title="Pagination case", customer="Alpha client",
                status="处理中", owner=ADMIN["username"], department=ADMIN["department"],
                data={"investigation_clue_ids": [item.id for item in clues]},
            )
            db.add(case)
            await db.flush()
            fee = BusinessRecord(module="finance", serial_no="CODEX-FEE-CLUE-PAGE", title="Related fee", customer="Alpha client", status="草稿", owner=ADMIN["username"], department=ADMIN["department"], data={"case_id": case.id})
            db.add(fee)
            await db.commit()
            self.case_id = case.id
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://case-clue-page.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_legacy_unpaged_response_and_opt_in_clue_page_are_compatible(self) -> None:
        legacy = await self.client.get(f"{API}/cases/{self.case_id}/relations")
        self.assertEqual(legacy.status_code, 200, legacy.text)
        self.assertEqual(legacy.json()["clue_total"], 3)
        self.assertEqual(len(legacy.json()["clues"]), 3)
        self.assertEqual(legacy.json()["fee_total"], 1)
        self.assertEqual(len(legacy.json()["fees"]), 1)

        page = await self.client.get(f"{API}/cases/{self.case_id}/relations", params={"clue_page": 2, "clue_page_size": 1})
        self.assertEqual(page.status_code, 200, page.text)
        payload = page.json()
        self.assertEqual(payload["clue_total"], 3)
        self.assertEqual(payload["clue_page"], 2)
        self.assertEqual(payload["clue_page_size"], 1)
        self.assertEqual(payload["clue_pages"], 3)
        self.assertEqual(len(payload["clues"]), 1)
        self.assertEqual(payload["fee_total"], 1)
        self.assertEqual(len(payload["fees"]), 1)

        # The route is also used directly by Python tests and helpers.  Its
        # optional query arguments must therefore default to None rather than
        # FastAPI Query metadata objects.
        async with self.sessions() as db:
            direct_payload = await list_case_relations(self.case_id, identity=ADMIN, db=db)
        self.assertEqual(len(direct_payload["clues"]), 3)

    async def test_keyword_filters_before_pagination_across_clue_fields(self) -> None:
        response = await self.client.get(f"{API}/cases/{self.case_id}/relations", params={"clue_keyword": "cert-alpha", "clue_page": 1, "clue_page_size": 15})
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["clue_total"], 1)
        self.assertEqual([item["serial_no"] for item in payload["clues"]], ["CODEX-CLUE-ALPHA-2"])

    async def test_keyword_is_filtered_before_page_slice_and_empty_pages_are_valid(self) -> None:
        second_alpha_page = await self.client.get(
            f"{API}/cases/{self.case_id}/relations",
            params={"clue_keyword": "alpha", "clue_page": 2, "clue_page_size": 1},
        )
        self.assertEqual(second_alpha_page.status_code, 200, second_alpha_page.text)
        payload = second_alpha_page.json()
        self.assertEqual(payload["clue_total"], 2)
        self.assertEqual(payload["clue_pages"], 2)
        self.assertEqual([item["serial_no"] for item in payload["clues"]], ["CODEX-CLUE-ALPHA-1"])

        no_match = await self.client.get(
            f"{API}/cases/{self.case_id}/relations",
            params={"clue_keyword": "does-not-match", "clue_page": 1, "clue_page_size": 15},
        )
        self.assertEqual(no_match.status_code, 200, no_match.text)
        self.assertEqual(no_match.json()["clue_total"], 0)
        self.assertEqual(no_match.json()["clue_pages"], 0)
        self.assertEqual(no_match.json()["clues"], [])

        beyond_last_page = await self.client.get(
            f"{API}/cases/{self.case_id}/relations", params={"clue_page": 99, "clue_page_size": 1},
        )
        self.assertEqual(beyond_last_page.status_code, 200, beyond_last_page.text)
        self.assertEqual(beyond_last_page.json()["clue_total"], 3)
        self.assertEqual(beyond_last_page.json()["clues"], [])

    async def test_query_bounds_and_unknown_case_are_rejected(self) -> None:
        for params in ({"clue_page": 0}, {"clue_page_size": 201}):
            response = await self.client.get(f"{API}/cases/{self.case_id}/relations", params=params)
            self.assertEqual(response.status_code, 422, response.text)
        unknown = await self.client.get(f"{API}/cases/999999/relations")
        self.assertEqual(unknown.status_code, 404, unknown.text)

        app.dependency_overrides[current_identity] = lambda: OUTSIDER
        invisible = await self.client.get(f"{API}/cases/{self.case_id}/relations")
        self.assertEqual(invisible.status_code, 404, invisible.text)


if __name__ == "__main__":
    unittest.main()
