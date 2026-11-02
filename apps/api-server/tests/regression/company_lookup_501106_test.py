"""501106：企查查查企业——凭据加密不回显、签名、缓存不重复计费、每人每天限额、查重含回收站。只用假 Key。"""

import hashlib
import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.crm import company_lookup as qcc
from app.database import Base
from app.models import BusinessRecord, SystemConfig

ADMIN = {"username": "admin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"]}
LAWYER = {"username": "lawyer", "role": "user", "role_ids": ["user"]}
FAKE_KEY, FAKE_SECRET = "fake-key-12345678", "fake-secret-87654321"


class CompanyLookupTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.calls = []
        self.allow = patch.object(qcc, "_require_customer_create", self._allow)
        self.admin = patch.object(qcc, "_require_admin", lambda identity: None)
        self.allow.start(); self.admin.start()

    async def asyncTearDown(self):
        self.allow.stop(); self.admin.stop()
        await self.engine.dispose()

    async def _allow(self, identity, db):
        return None

    async def fake_get(self, path, params, key, secret):
        self.calls.append((path, params, key, secret))
        if path == qcc.SEARCH_PATH:
            return {"Status": "200", "Result": [{"Name": "上海甲科技有限公司", "CreditCode": "91310000AAAAAAAAAA", "OperName": "张三",
                                                 "StartDate": "2015-01-01 00:00:00", "Status": "存续"},
                                                {"Name": "上海甲贸易有限公司", "CreditCode": "91310000BBBBBBBBBB", "OperName": "李四", "Status": "注销"}]}
        return {"Status": "200", "Result": {"Name": "上海甲科技有限公司", "CreditCode": "91310000AAAAAAAAAA", "OperName": "张三",
                                            "Address": "上海市某路1号", "EconKind": "有限责任公司（自然人投资或控股）", "RegistCapi": "100万元人民币",
                                            "StartDate": "2015-01-01 00:00:00", "Status": "存续（在营、开业、在册）", "Scope": "技术开发",
                                            "ContactInfo": {"PhoneNumber": "021-12345678"}}}

    async def test_credentials_encrypted_not_echoed_and_signature(self):
        async with self.sessions() as db:
            status = await qcc.save_qcc_credentials(qcc.CredentialInput(key=FAKE_KEY, secret=FAKE_SECRET), ADMIN, db)
            self.assertTrue(status["configured"])
            self.assertNotIn(FAKE_KEY, json.dumps(status)); self.assertNotIn(FAKE_SECRET, json.dumps(status))
            stored = await db.scalar(select(SystemConfig).where(SystemConfig.key == qcc.CREDENTIAL_KEY))
            self.assertNotIn(FAKE_SECRET, json.dumps(stored.value), "数据库里只有密文")
            self.assertEqual((await qcc.credentials(db))[:2], (FAKE_KEY, FAKE_SECRET))
        headers = qcc._signature(FAKE_KEY, FAKE_SECRET)
        self.assertEqual(headers["Token"], hashlib.md5((FAKE_KEY + headers["Timespan"] + FAKE_SECRET).encode()).hexdigest().upper())

    async def test_search_detail_cache_and_quota(self):
        with patch.object(qcc, "_qcc_get", self.fake_get):
            async with self.sessions() as db:
                await qcc.save_qcc_credentials(qcc.CredentialInput(key=FAKE_KEY, secret=FAKE_SECRET), ADMIN, db)
                first = await qcc.search_companies("上海甲", LAWYER, db)
                second = await qcc.search_companies("上海甲", LAWYER, db)
                self.assertEqual((first["cached"], second["cached"]), (False, True))
                self.assertEqual(len(self.calls), 1, "同一关键词 7 天内不重复计费")
                self.assertTrue(first["items"][1]["abnormal"], "注销企业标红")
                detail = await qcc.company_detail("上海甲科技有限公司", LAWYER, db)
                self.assertEqual((detail["credit_code"], detail["legal_representative"], detail["organization_type"], detail["phone"]),
                                 ("91310000AAAAAAAAAA", "张三", "公司企业", "021-12345678"))
                again = await qcc.company_detail("91310000AAAAAAAAAA", LAWYER, db)
                self.assertTrue(again["cached"], "按信用代码再查也命中缓存")
                await qcc.save_qcc_limits(qcc.LimitInput(user_daily=3, total_daily=100), ADMIN, db)
                await qcc.search_companies("另一家", LAWYER, db)
                with self.assertRaises(HTTPException) as caught:
                    await qcc.search_companies("第三家", LAWYER, db)
                self.assertEqual(caught.exception.status_code, 429)
                log = await db.scalar(select(SystemConfig).where(SystemConfig.key.like("qcc_log_%")))
                self.assertEqual(len(log.value["entries"]), 5, "每次调用（含命中缓存）都记日志")
                self.assertNotIn(FAKE_SECRET, json.dumps(log.value))

    async def test_missing_credentials_message(self):
        with patch.dict("os.environ", {"QCC_APP_KEY": "", "QCC_SECRET_KEY": ""}):
            async with self.sessions() as db:
                with self.assertRaises(HTTPException) as caught:
                    await qcc.search_companies("上海甲", LAWYER, db)
        self.assertIn("系统参数 › API 设置", caught.exception.detail)

    async def test_duplicates_by_credit_code_then_name_including_deleted(self):
        async with self.sessions() as db:
            from datetime import datetime, timezone
            db.add_all([BusinessRecord(module="customer", serial_no="KH1", title="上海甲科技有限公司", data={"credit_code": "91310000AAAAAAAAAA"}),
                        BusinessRecord(module="customer", serial_no="KH2", title="上海甲科技", data={}, deleted_at=datetime.now(timezone.utc))])
            await db.commit()
            items = (await qcc.customer_duplicates("91310000AAAAAAAAAA", "上海甲科技", LAWYER, db))["items"]
        self.assertEqual([(item["serial_no"], item["matched_by"], item["deleted"]) for item in items],
                         [("KH1", "统一社会信用代码", False), ("KH2", "名称", True)])


    async def test_official_status_codes_and_provider_list(self):
        self.assertEqual(qcc.QCC_STATUS["107"], "被禁止的IP或者签名错误")
        self.assertIn("白名单", qcc.qcc_error_message("107"))
        self.assertEqual(qcc.qcc_error_message("999"), "企查查返回 999：999")
        async with self.sessions() as db:
            await qcc.save_qcc_credentials(qcc.CredentialInput(key=FAKE_KEY, secret=FAKE_SECRET), ADMIN, db)
            listed = await qcc.external_credential_providers(ADMIN, db)
        self.assertEqual([item["id"] for item in listed["items"]], ["qcc"])
        self.assertTrue(listed["items"][0]["status"]["configured"])
        self.assertNotIn(FAKE_KEY, json.dumps(listed, ensure_ascii=False)); self.assertNotIn(FAKE_SECRET, json.dumps(listed, ensure_ascii=False))

    async def test_only_actual_system_admin(self):
        self.admin.stop()
        try:
            with self.assertRaises(HTTPException) as caught:
                qcc._require_admin({**LAWYER, "_user_action_keys": ["agent.global.manage"]})
            self.assertEqual(caught.exception.status_code, 403)
            qcc._require_admin(ADMIN)
        finally:
            self.admin.start()


if __name__ == "__main__":
    unittest.main()
