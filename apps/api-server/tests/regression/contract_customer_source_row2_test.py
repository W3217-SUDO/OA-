"""8.14 row 2: contracts inherit the selected customer's fixed source person."""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "row2-creator", "role": "admin", "display_name": "合同创建人", "department": "上海分所"}


class ContractCustomerSourceRow2Test(unittest.IsolatedAsyncioTestCase):
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
                    username=ADMIN["username"],
                    display_name=ADMIN["display_name"],
                    department=ADMIN["department"],
                    role="admin",
                    password_hash="x",
                    is_active=True,
                ),
                User(
                    username="row2-source",
                    display_name="固定案源人",
                    department="客户部",
                    role="user",
                    password_hash="x",
                    is_active=True,
                ),
                BusinessRecord(
                    module="customer",
                    serial_no="CODEX-814-R2-CUSTOMER",
                    title="第2行固定案源客户",
                    customer="",
                    status="正常",
                    owner=ADMIN["username"],
                    department=ADMIN["department"],
                    data={
                        "customer_source": "row2-source",
                        "source_person": "row2-source",
                        "customer_managers": [ADMIN["username"]],
                    },
                ),
            ])
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row2.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    @staticmethod
    def _payload(*, serial_no: str = "") -> dict:
        return {
            "serial_no": serial_no,
            "title": "第2行客户来源继承合同",
            "customer": "第2行固定案源客户",
            "owner": ADMIN["username"],
            "department": ADMIN["department"],
            "description": "",
            "data": {
                "customer_id": 1,
                "type": "争议解决合同",
                "fee_type": "固定收费",
                "contract_body": "律所",
                "amount": 0,
                "source_person": ADMIN["username"],
            },
        }

    async def test_create_and_edit_keep_customer_source_instead_of_current_user(self) -> None:
        created = await self.client.post(f"{API}/contracts", json=self._payload())
        self.assertEqual(created.status_code, 201, created.text)
        contract = created.json()
        self.assertEqual(contract["owner"], ADMIN["username"])
        self.assertEqual(contract["data"]["source_person"], "row2-source")
        self.assertEqual(contract["data"]["source_person_display_name"], "固定案源人")

        edited = await self.client.patch(
            f"{API}/contracts/{contract['id']}",
            json=self._payload(serial_no=contract["serial_no"]),
        )
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(edited.json()["data"]["source_person"], "row2-source")
        self.assertEqual(edited.json()["data"]["source_person_display_name"], "固定案源人")


if __name__ == "__main__":
    unittest.main()
