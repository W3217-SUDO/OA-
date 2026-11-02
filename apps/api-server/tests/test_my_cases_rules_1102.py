"""陶国南 11-02 定“我的案件”按旧系统（1A，a-A，b-A，c-A）：
1A 客户账号看自己公司的案件（客户 contact_accounts，即旧系统客户协作人 TypeId=2，不分大小写），绝不看别的客户；a-A 上传过文件不算；
b-A 迁移过来的案件参与人不算；c-A 待退费的本人范围不按出庭律师算。"""
import unittest

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.main  # noqa: F401  注册全部模型
from app.core.permissions import _case_mine_scope_condition, _coordinated_case_condition
from app.database import Base
from app.models import BusinessRecord, FileAttachment


class MyCasesRules1102Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(id=1, module="customer", serial_no="KH1", title="甲公司", status="T", owner="mgr", data={"contact_accounts": ["JIAKEHU"]}),
                BusinessRecord(id=2, module="customer", serial_no="KH2", title="乙公司", status="T", owner="mgr", data={}),
                BusinessRecord(id=11, module="case", serial_no="AJ1", title="甲公司案件", status="文书准备", owner="mgr", data={"customer_record_id": 1}),
                BusinessRecord(id=12, module="case", serial_no="AJ2", title="乙公司案件", status="文书准备", owner="mgr", data={"customer_record_id": 2}),
                BusinessRecord(id=21, module="case", serial_no="AJ21", title="只上传过文件", status="文书准备", owner="other",
                               data={"case_team_usernames": ["other"]}),
                BusinessRecord(id=22, module="case", serial_no="AJ22", title="迁移参与人", status="文书准备", owner="other",
                               data={"case_team_usernames": ["other"], "legacy_participants": [{"staff_name": "lawyer"}]}),
                BusinessRecord(id=23, module="case", serial_no="AJ23", title="出庭律师", status="文书准备", owner="other",
                               data={"case_team_usernames": ["other"], "court_lawyer_username": "lawyer"}),
                BusinessRecord(id=24, module="case", serial_no="AJ24", title="案源人", status="文书准备", owner="other",
                               data={"case_team_usernames": ["other"], "business_owner": "lawyer"}),
                BusinessRecord(id=25, module="case", serial_no="AJ25", title="大写账号的经办律师", status="文书准备", owner="other",
                               data={"case_team_usernames": ["LAWYER"], "handling_lawyer_usernames": ["LAWYER"]}),
            ])
            await db.flush()
            db.add(FileAttachment(record_id=21, category="案件文件", original_name="a.pdf", stored_name="a.pdf", content_type="application/pdf",
                                  size=1, path="x/a.pdf", uploader="lawyer"))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def ids(self, username, **kwargs):
        async with self.sessions() as db:
            mine = await _case_mine_scope_condition({"username": username}, db, **kwargs)
            condition = or_(mine, _coordinated_case_condition(username, db.get_bind().dialect.name))
            return set((await db.scalars(select(BusinessRecord.id).where(BusinessRecord.module == "case", condition))).all())

    async def test_client_account_sees_only_its_own_customer_cases(self):
        self.assertEqual(await self.ids("jiakehu"), {11})  # 迁移数据存大写账号，不分大小写比；乙公司没挂这个账号，看不到

    async def test_client_account_rows_are_tagged_own_customer(self):
        from app.core.permissions import mark_coordinated_cases
        async with self.sessions() as db:
            items = await mark_coordinated_cases([{"id": 11, "data": {"customer_record_id": 1}}], {"username": "jiakehu"}, db)
        self.assertEqual(items[0]["data"]["my_case_relation"], "本客户")

    async def test_client_account_official_fee_customers(self):
        from unittest.mock import patch
        from app.core import customer_fee_balance
        seen = {}

        async def balances(db, customers):
            seen["ids"] = {row.id for row in customers}
            return {}

        with patch.object(customer_fee_balance, "customer_fee_balances", balances):
            async with self.sessions() as db:
                await customer_fee_balance.managed_customers_official_unreceived(db, "jiakehu")
        self.assertEqual(seen["ids"], {1})

    async def test_upload_and_migrated_participant_are_not_mine_court_lawyer_is_except_refund(self):
        self.assertEqual(await self.ids("lawyer"), {23, 24, 25})  # 上传文件（21）、迁移参与人（22）不再算；大写账号照算
        self.assertEqual(await self.ids("lawyer", court_lawyer=False), {24, 25})  # 待退费不按出庭律师算
