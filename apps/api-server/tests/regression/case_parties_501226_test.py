"""501226：案件原被告可点开看——410 已返回的字段全存、查过的不再计费、只有“重新查询”才计费、个人不查工商。只用假 Key。"""

import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.crm import company_lookup as qcc
from app.areas.legal import case_parties
from app.database import Base
from app.models import BusinessRecord, PartyRecord

ADMIN = {"username": "admin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"]}
LAWYER = {"username": "lawyer", "role": "user", "role_ids": ["user"]}
FULL_410 = {
    "KeyNo": "k1", "Name": "上饶市广信区有明眼镜店", "No": "361121600123456", "BelongOrg": "上饶市广信区市场监督管理局",
    "OperName": "王五", "StartDate": "2018-05-06 00:00:00", "Status": "存续", "CreditCode": "92361121MA00000000",
    "RegistCapi": "10万元人民币", "EconKind": "个体工商户", "Address": "上饶市广信区七六路32号", "Scope": "眼镜零售",
    "TermStart": "2018-05-06", "TermEnd": "", "CheckDate": "2023-01-02", "OrgNo": "MA000000-0", "IsOnStock": "0",
    "OriginalName": [{"Name": "广信区有明眼镜店", "ChangeDate": "2020-03-04"}], "EntType": "0", "RecCap": "5万元人民币",
    "RevokeInfo": {"CancelDate": "", "CancelReason": "", "RevokeDate": "", "RevokeReason": ""},
    "Area": {"Province": "江西省", "City": "上饶市", "County": "广信区"}, "AreaCode": "361121", "UpdatedDate": "2026-10-01",
    "DesignatedRepresentativeList": [],
}


class CasePartiesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.calls = []
        self.patches = [patch.object(qcc, "_require_admin", lambda identity: None),
                        patch.object(qcc, "_qcc_get", self.fake_get)]
        for item in self.patches:
            item.start()
        async with self.sessions() as db:
            await qcc.save_qcc_credentials(qcc.CredentialInput(key="fake-key-12345678", secret="fake-secret-87654321"), ADMIN, db)
            self.case = BusinessRecord(module="case", serial_no="HZMS2600441", title="大光明诉有明眼镜店", status="在办", owner="lawyer", data={
                "plaintiffs": ["浙江大光明眼镜有限公司"], "defendants": ["广信区有明眼镜店"], "third_parties": ["张三"],
                "third_party_identities": [{"name": "张三", "organization_type": "个人", "identity_no": "110101199001011234"}]})
            db.add(self.case)
            db.add(BusinessRecord(module="customer", serial_no="HZKH2610610", title="广信区有明眼镜店", status="T", owner="hehs",
                                  data={"credit_code": "2573", "bank_account": "6222000000000000", "legacy_record": {"ContactAddress": "上饶市广信区七六路32号3幢007号"}}))
            db.add(PartyRecord(party_no="HZKH2610610", name="广信区有明眼镜店", party_type="未设置", data={}))
            await db.commit()

    async def asyncTearDown(self):
        for item in self.patches:
            item.stop()
        await self.engine.dispose()

    async def fake_get(self, path, params, key, secret):
        self.calls.append((path, params))
        return {"Status": "200", "Result": FULL_410}

    async def test_all_410_fields_kept(self):
        detail = qcc._detail(FULL_410)
        rows = {row["label"]: row["value"] for row in qcc.business_rows(detail)}
        self.assertEqual(rows["注册号"], "361121600123456")
        self.assertEqual(rows["组织机构代码"], "MA000000-0")
        self.assertEqual(rows["实缴资本"], "5万元人民币")
        self.assertEqual(rows["营业期限"], "2018-05-06 至 无固定期限")
        self.assertEqual(rows["曾用名"], "广信区有明眼镜店（2020-03-04 变更）")
        self.assertEqual(rows["所在地区"], "江西省上饶市广信区")
        self.assertEqual(rows["企业性质"], "大陆企业")
        self.assertNotIn("吊销信息", rows, "空的不显示")
        self.assertNotIn("上市情况", rows)

    async def test_view_query_once_then_free_refresh_charges(self):
        async with self.sessions() as db:
            info = await case_parties.party_info(self.case, "广信区有明眼镜店", db)
            self.assertEqual(info["role"], "被告")
            self.assertIsNone(info["business"], "没查过就不显示工商信息，也不自动调接口")
            self.assertEqual(self.calls, [])
            local = {row["label"]: row["value"] for row in info["local"][0]["rows"]}
            self.assertEqual(local["地址"], "上饶市广信区七六路32号3幢007号")
            self.assertNotIn("6222000000000000", str(info), "不带银行账号")
            self.assertEqual(len(info["local"]), 1, "当事人库和客户编号相同只列一次")
            with patch("app.core.permissions._ensure_record_module", self._case):
                first = await case_parties.query_case_party_business_info(self.case.id, case_parties.PartyLookupInput(name="广信区有明眼镜店"), LAWYER, db)
                self.assertEqual(len(self.calls), 1)
                self.assertEqual({row["label"]: row["value"] for row in first["business"]["rows"]}["统一社会信用代码"], "92361121MA00000000")
                await case_parties.query_case_party_business_info(self.case.id, case_parties.PartyLookupInput(name="广信区有明眼镜店"), LAWYER, db)
                self.assertEqual(len(self.calls), 1, "查过的再点不计费")
                again = await case_parties.get_case_party_info(self.case.id, "广信区有明眼镜店", LAWYER, db)
                self.assertIsNotNone(again["business"], "按案件里的名称也能找到（企业名称已变更）")
                await case_parties.query_case_party_business_info(self.case.id, case_parties.PartyLookupInput(name="广信区有明眼镜店", refresh=True), LAWYER, db)
                self.assertEqual(len(self.calls), 2, "重新查询才计费")

    async def _case(self, case_id, module, identity, db):
        return self.case

    async def test_person_and_outsider(self):
        async with self.sessions() as db:
            info = await case_parties.party_info(self.case, "张三", db)
            self.assertEqual((info["role"], info["person"], info["business"]), ("第三人", True, None))
            with patch("app.core.permissions._ensure_record_module", self._case):
                with self.assertRaises(HTTPException) as caught:
                    await case_parties.query_case_party_business_info(self.case.id, case_parties.PartyLookupInput(name="张三"), LAWYER, db)
                self.assertEqual(caught.exception.status_code, 422)
                with self.assertRaises(HTTPException) as caught:
                    await case_parties.get_case_party_info(self.case.id, "别的公司", LAWYER, db)
                self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(self.calls, [])
