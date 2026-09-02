import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, SystemParameter, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {"username": "row13-admin", "role": "admin", "display_name": "第13行管理员", "department": "管理部"}


class CasePlatformAgencyFeeRow13Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username=IDENTITY["username"], display_name=IDENTITY["display_name"],
                department=IDENTITY["department"], role="admin", password_hash="x", is_active=True,
            ))
            case = BusinessRecord(
                module="case", serial_no="CODEX-831-R13-CASE", title="第13行平台费用案件",
                customer="第13行客户", status="文书准备", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"case_type": "民事争议", "case_creation_step": "completed"},
            )
            platform_contract = BusinessRecord(
                module="contract", serial_no="CODEX-831-R13-PLATFORM", title="第13行平台合同",
                customer="第13行客户", status="审批通过", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"contract_body": "平台"},
            )
            firm_contract = BusinessRecord(
                module="contract", serial_no="CODEX-831-R13-FIRM", title="第13行律所合同",
                customer="第13行客户", status="审批通过", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"contract_body": "律所"},
            )
            db.add_all([case, platform_contract, firm_contract])
            await db.commit()
            await db.refresh(case); await db.refresh(platform_contract); await db.refresh(firm_contract)
            self.case_id = case.id
            self.platform_contract_id = platform_contract.id
            self.firm_contract_id = firm_contract.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row13.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    def payload(self, scope: str, subtype: str, contract_id: int) -> dict:
        return {
            "title": f"第13行{subtype}", "customer": "第13行客户", "amount": 831.13,
            "fee_type": "代理费", "expense_scope": scope, "expense_subtype": subtype,
            "case_no": "CODEX-831-R13-CASE", "case_record_id": self.case_id,
            "contract_record_id": contract_id, "handler": IDENTITY["username"],
        }

    async def test_platform_agency_fee_is_created_and_echoed_exactly(self) -> None:
        response = await self.client.post(
            f"{API}/finance/fees",
            json=self.payload("平台", "平台代理费", self.platform_contract_id),
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["data"]["expense_scope"], "平台")
        self.assertEqual(response.json()["data"]["expense_subtype"], "平台代理费")
        self.assertEqual(response.json()["data"]["fee_type"], "代理费")

    async def test_platform_rejects_generic_and_law_firm_agency_subtypes(self) -> None:
        for subtype in ("代理费", "律师代理费"):
            response = await self.client.post(
                f"{API}/finance/fees",
                json=self.payload("平台", subtype, self.platform_contract_id),
            )
            self.assertEqual(response.status_code, 422, response.text)
            self.assertIn("平台代理费", response.json()["detail"])

    async def test_law_firm_rejects_platform_agency_subtype(self) -> None:
        response = await self.client.post(
            f"{API}/finance/fees",
            json=self.payload("律所", "平台代理费", self.firm_contract_id),
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("只能归属于平台", response.json()["detail"])

    async def test_platform_master_data_rejects_law_firm_agency_subtype(self) -> None:
        async with self.sessions() as db:
            agency = SystemParameter(
                category="fee_type", code="AGENCY", name="代理费", extra={},
                sort_order=1, is_active=True, created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
            )
            witness = SystemParameter(
                category="fee_type", code="WITNESS", name="律师见证费", extra={"parent_code": "AGENCY"},
                sort_order=2, is_active=True, created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
            )
            platform = SystemParameter(
                category="fee_type", code="PLATFORM", name="平台代理费", extra={"parent_code": "AGENCY"},
                sort_order=3, is_active=True, created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
            )
            db.add_all([agency, witness, platform])
            await db.flush()
            witness_id, platform_id = witness.id, platform.id
            await db.commit()

        invalid_payload = self.payload("平台", "律师见证费", self.platform_contract_id)
        invalid_payload["fee_type_id"] = witness_id
        invalid = await self.client.post(f"{API}/finance/fees", json=invalid_payload)
        self.assertEqual(invalid.status_code, 422, invalid.text)
        self.assertIn("只能是平台代理费", invalid.json()["detail"])

        valid_payload = self.payload("平台", "平台代理费", self.platform_contract_id)
        valid_payload["fee_type_id"] = platform_id
        valid = await self.client.post(f"{API}/finance/fees", json=valid_payload)
        self.assertEqual(valid.status_code, 201, valid.text)
        self.assertEqual(valid.json()["data"]["expense_subtype"], "平台代理费")

    async def test_batch_platform_agency_fee_uses_the_same_constraint(self) -> None:
        valid = await self.client.post(f"{API}/cases/batch-fees", json={
            "case_ids": [self.case_id], "amount": 100, "expense_scope": "平台",
            "expense_subtype": "平台代理费", "handler": IDENTITY["username"],
        })
        self.assertEqual(valid.status_code, 201, valid.text)
        self.assertEqual(valid.json()["items"][0]["data"]["expense_subtype"], "平台代理费")
        invalid = await self.client.post(f"{API}/cases/batch-fees", json={
            "case_ids": [self.case_id], "amount": 100, "expense_scope": "平台",
            "expense_subtype": "代理费", "handler": IDENTITY["username"],
        })
        self.assertEqual(invalid.status_code, 422, invalid.text)
        self.assertIn("平台代理费", invalid.json()["detail"])


if __name__ == "__main__":
    unittest.main()
