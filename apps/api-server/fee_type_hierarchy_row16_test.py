import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, SystemParameter, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "row16-admin",
    "role": "admin",
    "display_name": "\u7b2c16\u884c\u7ba1\u7406\u5458",
    "department": "\u7ba1\u7406\u90e8",
}


class FeeTypeHierarchyRow16Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username=IDENTITY["username"],
                display_name=IDENTITY["display_name"],
                department=IDENTITY["department"],
                role="admin",
                password_hash="x",
                is_active=True,
            ))
            root = SystemParameter(
                category="fee_type", code="OFFICIAL", name="\u5b98\u8d39",
                extra={"parent_code": ""}, sort_order=1, is_active=True,
                created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
            )
            child = SystemParameter(
                category="fee_type", code="160000", name="\u8bc9\u8bbc\u8d39",
                extra={"parent_code": "OFFICIAL"}, sort_order=2, is_active=True,
                created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
            )
            leaf = SystemParameter(
                category="fee_type", code="160001", name="\u4e00\u5ba1\u8bc9\u8bbc\u8d39",
                extra={"parent_code": "160000"}, sort_order=3, is_active=True,
                created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
            )
            contract = BusinessRecord(
                module="contract", serial_no="CODEX-831-R16-HT",
                title="\u7b2c16\u884c\u5408\u540c", customer="\u7b2c16\u884c\u5ba2\u6237",
                status="\u5ba1\u6279\u901a\u8fc7", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"contract_body": "\u5f8b\u6240"},
            )
            case = BusinessRecord(
                module="case", serial_no="CODEX-831-R16-CASE",
                title="\u7b2c16\u884c\u6848\u4ef6", customer="\u7b2c16\u884c\u5ba2\u6237",
                status="\u6587\u4e66\u51c6\u5907", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"case_type": "\u6c11\u4e8b\u4e89\u8bae"},
            )
            db.add_all([root, child, leaf, contract, case])
            await db.commit()
            self.root_id = root.id
            self.child_id = child.id
            self.leaf_id = leaf.id
            self.contract_id = contract.id
            self.case_id = case.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://row16.test"
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    def fee_payload(self, **overrides):
        payload = {
            "title": "\u7b2c16\u884c\u4e00\u5ba1\u8bc9\u8bbc\u8d39",
            "customer": "\u7b2c16\u884c\u5ba2\u6237",
            "amount": 160.01,
            "fee_type_id": self.leaf_id,
            "fee_type": "\u5b98\u65b9\u8d39\u7528",
            "expense_scope": "\u5f8b\u6240",
            "expense_subtype": "\u4e00\u5ba1\u8bc9\u8bbc\u8d39",
            "case_no": "CODEX-831-R16-CASE",
            "case_record_id": self.case_id,
            "contract_record_id": self.contract_id,
            "handler": IDENTITY["username"],
        }
        payload.update(overrides)
        return payload

    async def test_catalog_returns_hierarchy_path_and_only_leaf_is_selectable(self) -> None:
        response = await self.client.get(
            f"{API}/system/parameters/options", params={"category": "fee_type"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        by_code = {item["code"]: item for item in response.json()["items"]}
        self.assertFalse(by_code["OFFICIAL"]["selectable"])
        self.assertFalse(by_code["160000"]["selectable"])
        self.assertTrue(by_code["160001"]["selectable"])
        self.assertEqual(
            by_code["160001"]["path"],
            "\u5b98\u8d39 / \u8bc9\u8bbc\u8d39 / \u4e00\u5ba1\u8bc9\u8bbc\u8d39",
        )
        self.assertEqual(by_code["160001"]["base_fee_type"], "\u5b98\u65b9\u8d39\u7528")
        self.assertEqual(by_code["160001"]["expense_scopes"], ["\u5f8b\u6240", "\u5e73\u53f0"])

    async def test_system_center_can_add_nested_types_and_blocks_invalid_parent_changes(self) -> None:
        created = await self.client.post(
            f"{API}/system/parameters",
            json={
                "category": "fee_type", "code": "160002",
                "name": "\u4e8c\u5ba1\u8bc9\u8bbc\u8d39",
                "extra": {"parent_code": "160000"},
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["extra"]["parent_code"], "160000")

        missing = await self.client.post(
            f"{API}/system/parameters",
            json={
                "category": "fee_type", "code": "160003",
                "name": "\u65e0\u6548\u4e0a\u7ea7", "extra": {"parent_code": "NOPE"},
            },
        )
        self.assertEqual(missing.status_code, 422, missing.text)

        deactivate = await self.client.patch(
            f"{API}/system/parameters/{self.child_id}", json={"is_active": False}
        )
        self.assertEqual(deactivate.status_code, 409, deactivate.text)

        cycle = await self.client.patch(
            f"{API}/system/parameters/{self.root_id}",
            json={"extra": {"parent_code": "160001"}},
        )
        self.assertEqual(cycle.status_code, 422, cycle.text)

    async def test_case_fee_requires_matching_leaf_master_and_persists_snapshot(self) -> None:
        missing = self.fee_payload()
        missing.pop("fee_type_id")
        response = await self.client.post(f"{API}/finance/fees", json=missing)
        self.assertEqual(response.status_code, 422, response.text)

        parent = await self.client.post(
            f"{API}/finance/fees", json=self.fee_payload(fee_type_id=self.child_id)
        )
        self.assertEqual(parent.status_code, 422, parent.text)

        mismatch = await self.client.post(
            f"{API}/finance/fees",
            json=self.fee_payload(expense_subtype="\u4f2a\u9020\u8d39\u7528"),
        )
        self.assertEqual(mismatch.status_code, 422, mismatch.text)

        accepted = await self.client.post(
            f"{API}/finance/fees", json=self.fee_payload()
        )
        self.assertEqual(accepted.status_code, 201, accepted.text)
        data = accepted.json()["data"]
        self.assertEqual(data["fee_type_id"], self.leaf_id)
        self.assertEqual(data["fee_type_code"], "160001")
        self.assertEqual(data["fee_type_name"], "\u4e00\u5ba1\u8bc9\u8bbc\u8d39")
        self.assertEqual(
            data["fee_type_path"],
            "\u5b98\u8d39 / \u8bc9\u8bbc\u8d39 / \u4e00\u5ba1\u8bc9\u8bbc\u8d39",
        )

    async def test_batch_fee_uses_the_same_master_record(self) -> None:
        response = await self.client.post(
            f"{API}/cases/batch-fees",
            json={
                "case_ids": [self.case_id], "amount": 88.8,
                "fee_type_id": self.leaf_id, "expense_scope": "\u5f8b\u6240",
                "expense_subtype": "\u4e00\u5ba1\u8bc9\u8bbc\u8d39",
                "handler": IDENTITY["username"], "description": "row16",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        row = response.json()["items"][0]
        self.assertEqual(row["data"]["fee_type_id"], self.leaf_id)
        self.assertEqual(row["data"]["fee_type_path"], "\u5b98\u8d39 / \u8bc9\u8bbc\u8d39 / \u4e00\u5ba1\u8bc9\u8bbc\u8d39")
        async with self.sessions() as db:
            stored = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == row["id"]))
            self.assertEqual(stored.data["fee_type_code"], "160001")


if __name__ == "__main__":
    unittest.main()
