"""501614（fwl 11-05）：专利非诉案件新建按旧系统弹窗的字段，写进旧系统迁来案件已有的键（分支3“我的案件”按这些键分组）。"""

import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException

from app.areas.ipr import patent_form


class PatentFormTest(unittest.IsolatedAsyncioTestCase):
    async def _apply(self, values, data=None):
        data = data if data is not None else {}

        async def names(db, usernames):
            return {"mengfei": "孟飞", "zy": "张一"}

        with patch.object(patent_form, "_display_names", names):
            await patent_form.apply_patent_form(data, values, None)
        return data

    async def test_people_written_with_legacy_aliases(self):
        data = await self._apply({"agent": "mengfei", "writer": "zy", "case_source": "mengfei", "case_manager": "zy"})
        self.assertEqual((data["agent"], data["procurator"], data["procurator_name"]), ("mengfei", "mengfei", "孟飞"))
        self.assertEqual((data["writer"], data["copywriter_name"]), ("zy", "张一"))
        self.assertEqual((data["case_source"], data["case_origin_people"], data["case_origin_people_name"]), ("mengfei", "mengfei", "孟飞"))
        self.assertEqual((data["business_owner"], data["business_owner_name"], data["case_officer"], data["case_officer_name"]), ("zy", "张一", "zy", "张一"))

    async def test_fields_flags_and_rate(self):
        data = await self._apply({"card_no": "91310000ABC", "inventor": "李四", "authorization_date": date(2026, 1, 2),
                                  "source_date": date(2026, 11, 5), "first_annual_year": 3, "cost_slow_rate": "0.85",
                                  "has_priority": True, "has_iu": False})
        self.assertEqual((data["card_no"], data["case_inventor"], data["authorization_date"], data["case_origin_date"]),
                         ("91310000ABC", "李四", "2026-01-02", "2026-11-05"))
        self.assertEqual((data["first_annual_year"], data["annual_fee_year"], data["cost_slow_rate"], data["rate"]), (3, 3, "0.85", 0.85))
        self.assertEqual((data["has_priority"], data["has_iu"]), ("T", "F"))

    async def test_card_no_and_rate_validation(self):
        with self.assertRaises(HTTPException):
            await self._apply({"card_no": "9131 0000"})
        with self.assertRaises(HTTPException):
            await self._apply({"cost_slow_rate": "0.50"})

    async def test_only_submitted_keys_change(self):
        data = await self._apply({"inventor": "王五"}, {"agent": "old", "has_relief": "T"})
        self.assertEqual((data["agent"], data["has_relief"], data["inventor"]), ("old", "T", "王五"))


if __name__ == "__main__":
    unittest.main()
