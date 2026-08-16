"""8.13 row 5: copied cases keep the source number with Excel-style suffixes."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
import app.main as main_module
from app.main import CASE_CREATABLE_TYPES, CASE_SOURCE_CONTRACT_STATUSES, app
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "row5-admin", "role": "admin", "display_name": "Row5 Admin", "department": "Row5"}
ROOT_NO = "SHMS2600424"


class CaseDuplicateNumberRow5Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.case_type = next(iter(CASE_CREATABLE_TYPES))
        async with self.sessions() as db:
            db.add(User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="x", is_active=True))
            contract = BusinessRecord(
                module="contract", serial_no="ROW5-CONTRACT", title="Row 5 Contract", customer="Row 5 Customer",
                status=next(iter(CASE_SOURCE_CONTRACT_STATUSES)), owner=ADMIN["username"], department=ADMIN["department"], data={},
            )
            db.add(contract)
            await db.flush()
            source = BusinessRecord(
                module="case", serial_no=ROOT_NO, title="Row 5 Source", customer=contract.customer,
                status="Active", owner=ADMIN["username"], department=ADMIN["department"], data=self._case_data(contract),
            )
            db.add(source)
            await db.flush()
            self.source_id = source.id
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row5.test")

    @staticmethod
    def _case_data(contract: BusinessRecord) -> dict:
        return {
            "case_type": next(iter(CASE_CREATABLE_TYPES)),
            "contract_id": contract.id,
            "contract_record_id": contract.id,
            "contract_no": contract.serial_no,
            "case_creation_step": "completed",
        }

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def _duplicate(self, case_id: int) -> dict:
        response = await self.client.post(f"{API}/cases/{case_id}/duplicate")
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_root_and_child_copies_share_one_suffix_sequence(self) -> None:
        first = await self._duplicate(self.source_id)
        second = await self._duplicate(self.source_id)
        third = await self._duplicate(first["id"])

        self.assertEqual(first["serial_no"], f"{ROOT_NO}A")
        self.assertEqual(second["serial_no"], f"{ROOT_NO}B")
        self.assertEqual(third["serial_no"], f"{ROOT_NO}C")
        self.assertEqual(third["data"]["copy_root_case_no"], ROOT_NO)

    async def test_existing_letter_conflicts_continue_into_double_letters(self) -> None:
        async with self.sessions() as db:
            source = await db.get(BusinessRecord, self.source_id)
            for index in range(1, 27):
                suffix = chr(ord("A") + index - 1)
                db.add(BusinessRecord(
                    module="case", serial_no=f"{ROOT_NO}{suffix}", title=f"Existing {suffix}", customer=source.customer,
                    status="Active", owner=ADMIN["username"], department=ADMIN["department"], data=self._case_data(await db.get(BusinessRecord, int(source.data["contract_id"]))),
                ))
            await db.commit()

        copied = await self._duplicate(self.source_id)
        self.assertEqual(copied["serial_no"], f"{ROOT_NO}AA")

    async def test_next_available_suffix_skips_existing_conflict(self) -> None:
        async with self.sessions() as db:
            source = await db.get(BusinessRecord, self.source_id)
            contract = await db.get(BusinessRecord, int(source.data["contract_id"]))
            db.add(BusinessRecord(
                module="case", serial_no=f"{ROOT_NO}A", title="Existing A", customer=source.customer,
                status="Active", owner=ADMIN["username"], department=ADMIN["department"], data=self._case_data(contract),
            ))
            await db.commit()

        copied = await self._duplicate(self.source_id)
        self.assertEqual(copied["serial_no"], f"{ROOT_NO}B")

    async def test_historical_contract_does_not_block_copy(self) -> None:
        async with self.sessions() as db:
            source = await db.get(BusinessRecord, self.source_id)
            contract = await db.get(BusinessRecord, int(source.data["contract_id"]))
            contract.status = "历史数据"
            await db.commit()

        copied = await self._duplicate(self.source_id)
        self.assertEqual(copied["serial_no"], f"{ROOT_NO}A")
        self.assertEqual(copied["data"]["contract_no"], "ROW5-CONTRACT")

    async def test_legacy_case_without_contract_can_be_copied(self) -> None:
        legacy_no = "SHMS2600999"
        async with self.sessions() as db:
            legacy = BusinessRecord(
                module="case", serial_no=legacy_no, title="Legacy case without contract",
                customer="Legacy customer", status="历史数据", owner=ADMIN["username"],
                department=ADMIN["department"],
                data={"case_type": self.case_type, "case_creation_step": "completed"},
            )
            db.add(legacy)
            await db.flush()
            legacy_id = legacy.id
            await db.commit()

        copied = await self._duplicate(legacy_id)
        self.assertEqual(copied["serial_no"], f"{legacy_no}A")
        self.assertEqual(copied["customer"], "Legacy customer")

    async def test_unique_constraint_collision_retries_the_next_suffix(self) -> None:
        async with self.sessions() as db:
            source = await db.get(BusinessRecord, self.source_id)
            contract = await db.get(BusinessRecord, int(source.data["contract_id"]))
            db.add(BusinessRecord(
                module="case", serial_no=f"{ROOT_NO}A", title="Concurrent A", customer=source.customer,
                status="Active", owner=ADMIN["username"], department=ADMIN["department"], data=self._case_data(contract),
            ))
            await db.commit()

        with patch.object(main_module, "_next_case_copy_serial", new=AsyncMock(side_effect=[f"{ROOT_NO}A", f"{ROOT_NO}B"])):
            copied = await self._duplicate(self.source_id)
        self.assertEqual(copied["serial_no"], f"{ROOT_NO}B")


if __name__ == "__main__":
    unittest.main()
