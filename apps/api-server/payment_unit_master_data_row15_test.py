import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, ContractObject, SystemParameter, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "row15-admin",
    "role": "admin",
    "display_name": "第15行管理员",
    "department": "管理部",
}


class PaymentUnitMasterDataRow15Test(unittest.IsolatedAsyncioTestCase):
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
            contract = BusinessRecord(
                module="contract",
                serial_no="CODEX-831-R15-CONTRACT",
                title="第15行合同",
                customer="第15行客户",
                status="审批通过",
                owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={},
            )
            case = BusinessRecord(
                module="case",
                serial_no="CODEX-831-R15-CASE",
                title="第15行案件",
                customer="第15行客户",
                status="文书准备",
                owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={"case_type": "民事争议"},
            )
            known = SystemParameter(
                category="payment_type",
                code="CODEX-R15-KNOWN",
                name="官费",
                extra={
                    "nature": "官费",
                    "payee": "第15行权威收款单位",
                    "account_bank": "第15行权威开户行",
                    "account": "R15-AUTHORITATIVE-ACCOUNT",
                },
                sort_order=1,
                is_active=True,
                created_by=IDENTITY["username"],
                updated_by=IDENTITY["username"],
            )
            incomplete = SystemParameter(
                category="payment_type",
                code="CODEX-R15-INCOMPLETE",
                name="官费",
                extra={"nature": "官费", "payee": "资料不完整单位"},
                sort_order=2,
                is_active=True,
                created_by=IDENTITY["username"],
                updated_by=IDENTITY["username"],
            )
            db.add_all([contract, case, known, incomplete])
            await db.flush()
            contract_object = ContractObject(
                contract_record_id=contract.id,
                case_record_id=case.id,
                fee_type="代理费",
                amount=1500,
                remark="第15行合同付款",
                created_by=IDENTITY["username"],
                updated_by=IDENTITY["username"],
            )
            db.add(contract_object)
            await db.commit()
            self.contract_id = contract.id
            self.contract_object_id = contract_object.id
            self.known_id = known.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://row15.test"
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_system_parameter_search_matches_payment_unit_details(self) -> None:
        response = await self.client.get(
            f"{API}/system/parameters",
            params={"category": "payment_type", "keyword": "权威开户行"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["id"] for item in response.json()["items"]], [self.known_id])

    async def test_contract_candidates_expose_master_id_and_complete_label(self) -> None:
        response = await self.client.get(
            f"{API}/contracts/{self.contract_id}/payment-candidates"
        )
        self.assertEqual(response.status_code, 200, response.text)
        option = next(
            item for item in response.json()["payment_types"] if item["id"] == self.known_id
        )
        self.assertEqual(option["value"], self.known_id)
        self.assertEqual(
            option["label"],
            "第15行权威收款单位｜第15行权威开户行｜R15-AUTHORITATIVE-ACCOUNT",
        )
        self.assertNotIn(
            "资料不完整单位",
            [item["payee"] for item in response.json()["payment_types"]],
        )

    async def test_contract_payment_uses_authoritative_master_snapshot(self) -> None:
        missing = await self.client.post(
            f"{API}/contracts/{self.contract_id}/payment-applications",
            json={
                "payment_type": "伪造付款类型",
                "payee": "伪造收款单位",
                "account": "FAKE",
                "application_date": "2026-08-31",
                "lines": [{"contract_object_id": self.contract_object_id, "amount": 150}],
            },
        )
        self.assertEqual(missing.status_code, 422, missing.text)

        accepted = await self.client.post(
            f"{API}/contracts/{self.contract_id}/payment-applications",
            json={
                "payment_type_id": self.known_id,
                "payee": "伪造收款单位",
                "account": "FAKE",
                "application_date": "2026-08-31",
                "remark": "第15行主数据关联",
                "lines": [{"contract_object_id": self.contract_object_id, "amount": 150}],
            },
        )
        self.assertEqual(accepted.status_code, 201, accepted.text)
        data = accepted.json()["data"]
        self.assertEqual(data["payment_type_id"], self.known_id)
        self.assertEqual(data["payee"], "第15行权威收款单位")
        self.assertEqual(data["account_bank"], "第15行权威开户行")
        self.assertEqual(data["account"], "R15-AUTHORITATIVE-ACCOUNT")

    async def test_contract_can_create_shared_payment_unit(self) -> None:
        response = await self.client.post(
            f"{API}/contracts/{self.contract_id}/payment-types",
            json={
                "nature": "其他费用",
                "payee": "第15行合同新增单位",
                "account_bank": "第15行合同新增银行",
                "account": "R15-CONTRACT-ACCOUNT",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        created = response.json()
        parameters = await self.client.get(
            f"{API}/system/parameters",
            params={"category": "payment_type", "keyword": "合同新增单位"},
        )
        self.assertEqual(parameters.status_code, 200, parameters.text)
        self.assertEqual(
            [item["id"] for item in parameters.json()["items"]], [created["id"]]
        )


if __name__ == "__main__":
    unittest.main()
