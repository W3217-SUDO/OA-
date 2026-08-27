"""8.27 row 18: My Cases must contain only concrete personal relations."""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "row18-me",
    "role": "admin",
    "role_ids": ["admin"],
    "display_name": "第18行本人",
    "department": "诉讼部",
}


class CaseMinePersonalScopeRow18Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(
                    username=IDENTITY["username"],
                    display_name=IDENTITY["display_name"],
                    department=IDENTITY["department"],
                    role="admin",
                    role_ids=["admin"],
                    password_hash="x",
                    profile={},
                    is_active=True,
                ),
                User(
                    username="row18-other",
                    display_name="第18行他人",
                    department=IDENTITY["department"],
                    role="user",
                    role_ids=["user"],
                    password_hash="x",
                    profile={},
                    is_active=True,
                ),
            ])
            await db.flush()
            fixtures = {
                "OWNER": ({}, IDENTITY["username"]),
                "TEAM": ({"case_team_usernames": [IDENTITY["username"]]}, "row18-other"),
                "LAWYER": ({"handling_lawyer_usernames": [IDENTITY["username"]]}, "row18-other"),
                "SOURCE": ({"source_person_username": IDENTITY["username"]}, "row18-other"),
                "DISPLAY": ({"handling_lawyers": [IDENTITY["display_name"]]}, "row18-other"),
                "ASSISTANT": ({"assistant_username": IDENTITY["username"]}, "row18-other"),
                "INVESTIGATOR": ({"investigator": IDENTITY["username"]}, "row18-other"),
                "COURT": ({"court_lawyer_username": IDENTITY["username"]}, "row18-other"),
                "DOCUMENT": ({}, "row18-other"),
                "UNRELATED": ({"handling_lawyer_usernames": ["row18-other"]}, "row18-other"),
                "SUBSTRING": ({"case_team_usernames": ["row18-me-extra"]}, "row18-other"),
            }
            records = {}
            for suffix, (data, owner) in fixtures.items():
                record = BusinessRecord(
                    module="case",
                    serial_no=f"CODEX-827-18-{suffix}",
                    title=f"第18行{suffix}",
                    customer="第18行客户",
                    status="文书准备",
                    owner=owner,
                    department=IDENTITY["department"],
                    data={"case_type": "民事案件", **data},
                )
                db.add(record)
                await db.flush()
                records[suffix] = record
            db.add(FileAttachment(
                record_id=records["DOCUMENT"].id,
                category="案件文书",
                original_name="第18行本人文书.docx",
                stored_name="row18-document.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                size=1,
                path="row18-document.docx",
                uploader=IDENTITY["username"],
            ))
            await db.commit()

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row18.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def test_mine_scope_keeps_only_concrete_personal_relations_for_admin(self) -> None:
        response = await self.client.get(
            f"{API}/records",
            params={"module": "case", "scope": "mine", "page": 1, "page_size": 100},
        )
        self.assertEqual(response.status_code, 200, response.text)
        serials = {item["serial_no"] for item in response.json()["items"]}
        self.assertEqual(serials, {
            "CODEX-827-18-OWNER",
            "CODEX-827-18-TEAM",
            "CODEX-827-18-LAWYER",
            "CODEX-827-18-SOURCE",
            "CODEX-827-18-ASSISTANT",
            "CODEX-827-18-INVESTIGATOR",
            "CODEX-827-18-COURT",
            "CODEX-827-18-DOCUMENT",
        })
        self.assertEqual(response.json()["total"], len(serials))

    async def test_company_scope_remains_unfiltered_for_admin(self) -> None:
        response = await self.client.get(
            f"{API}/records",
            params={"module": "case", "scope": "company", "page": 1, "page_size": 100},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 11)

    async def test_ordinary_case_search_uses_the_same_mine_scope_as_the_browser(self) -> None:
        response = await self.client.post(
            f"{API}/cases/search",
            json={
                "scope": "mine",
                "case_types": ["民事案件"],
                "advanced_logic": "and",
                "page": 1,
                "page_size": 100,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        serials = {item["serial_no"] for item in response.json()["items"]}
        self.assertIn("CODEX-827-18-LAWYER", serials)
        self.assertIn("CODEX-827-18-DOCUMENT", serials)
        self.assertNotIn("CODEX-827-18-UNRELATED", serials)
        self.assertNotIn("CODEX-827-18-SUBSTRING", serials)


if __name__ == "__main__":
    unittest.main()
