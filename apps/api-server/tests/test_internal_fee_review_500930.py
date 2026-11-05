"""500930（shenhe 11-05 选 A）：内部费用-待审核只留“内部费用”大类的非提成类费用。"""
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import internal_requests as module
from app.database import Base
from app.models import SystemParameter


class InternalFeeReview500930Test(unittest.IsolatedAsyncioTestCase):
    async def test_only_non_commission_internal_fee_types_stay(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, class_=AsyncSession)() as db:
            db.add_all([SystemParameter(category="fee_type", code=code, name=name, extra={"parent_code": parent}, is_active=active)
                        for code, name, parent, active in (("11040050", "翻译费", "INTERNAL", True), ("11040183", "服务费(文书)", "INTERNAL", True),
                                                           ("11040040", "开庭提成", "INTERNAL", True), ("1103010", "检索费", "OTHER", True),
                                                           ("11040099", "停用费", "INTERNAL", False))])
            await db.commit()
            allowed = await module.internal_non_commission_fee_names(db)
        await engine.dispose()
        self.assertEqual(allowed, {"翻译费", "服务费(文书)"})
        keep = lambda data: module.keep_in_internal_fee_review({"data": data}, allowed)
        self.assertTrue(keep({"fee_type": "内部费用", "fee_type_name": "翻译费"}))
        self.assertTrue(keep({"fee_type": "内部费用", "fee_type_name": "服务费（文书）"}), "全角括号也认")
        self.assertFalse(keep({"fee_type": "内部费用", "fee_type_name": "开庭提成", "legacy_kind": "internal_payment_line"}))
        self.assertFalse(keep({"fee_type": "其他费用", "fee_type_name": "检索费"}))
        self.assertFalse(keep({"fee_type": "代理费", "fee_type_name": "律师代理费"}))
        self.assertTrue(keep({"fee_type": "内部费用"}), "只选了内部费用、没写类型名称的仍留在这里")
        self.assertFalse(keep({"fee_type": "代理费"}))


if __name__ == "__main__":
    unittest.main()
