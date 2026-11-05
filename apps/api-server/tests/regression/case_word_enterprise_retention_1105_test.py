"""陶国南 11-05：办案小结保管期限按案件类型自动带；文书里单位当事人缺法定代表人等时先查企业信息库，没有再查企查查（只用假接口）。"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.areas.legal import case_word_templates as cwt


class RetentionTest(unittest.TestCase):
    def test_by_case_type(self):
        record = lambda serial: SimpleNamespace(serial_no=serial)
        self.assertEqual(cwt.retention_period(record("GDMS2300327"), {"case_type": "民事争议"}), "20年")
        self.assertEqual(cwt.retention_period(record("GD201000648"), {"case_type": "行政案件及国家赔偿"}), "20年")
        self.assertEqual(cwt.retention_period(record("GDXS2100643"), {"case_type": "刑事案件"}), "长期")
        self.assertEqual(cwt.retention_period(record("GD201000617"), {"case_type": "仲裁"}), "")
        self.assertEqual(cwt.retention_period(record("HZMS2600442"), {}), "20年", "没填案件类型按案号")

    def test_case_summary_has_auto_retention_and_choices(self):
        item = next(item for item in cwt.BUILTIN_TEMPLATES if item["id"] == "case-summary")
        self.assertEqual(item["options"]["保管期限"], ["20年", "长期"])
        self.assertIn("保管期限", cwt.AUTO_FIELDS)


LIBRARY = {"name": "上海假甲科技有限公司", "credit_code": "91310000FAKEA0001X", "legal_representative": "库里法人", "registered_address": "上海市库里路1号"}
QCC = {"name": "上海假乙科技有限公司", "credit_code": "91310000FAKEB0002X", "legal_representative": "企查查法人", "registered_address": "上海市查询路2号", "cached": False}


class EnterpriseCompletionTest(unittest.IsolatedAsyncioTestCase):
    async def _complete(self, name, profile, *, charge, library=None, qcc=None, error=None):
        calls = []

        async def fake_profile(db, *keywords):
            return library

        async def fake_lookup(keyword, username, db, **kwargs):
            calls.append(keyword)
            if error:
                raise HTTPException(429, error)
            return qcc

        state = {"charge": charge, "username": "admin"}
        token = cwt.ENTERPRISE_LOOKUP.set(state)
        try:
            with patch("app.areas.crm.company_lookup.company_profile", fake_profile), patch("app.areas.crm.company_lookup.lookup_company", fake_lookup):
                result = await cwt._complete_enterprise(name, profile, None)
                again = await cwt._complete_enterprise(name, profile, None)
        finally:
            cwt.ENTERPRISE_LOOKUP.reset(token)
        return result, again, calls, state

    async def test_library_first_no_charge(self):
        result, _, calls, state = await self._complete(LIBRARY["name"], {}, charge=True, library=LIBRARY)
        self.assertEqual((result["legal_representative"], result["credit_code"]), ("库里法人", LIBRARY["credit_code"]))
        self.assertEqual(calls, [])

    async def test_preview_lists_pending_without_charge(self):
        result, _, calls, state = await self._complete(QCC["name"], {}, charge=False)
        self.assertEqual(calls, [])
        self.assertEqual(state["pending"], [QCC["name"]])
        self.assertIn("扣一次企查查次数", cwt.enterprise_notice(state)["message"])

    async def test_generate_queries_once_and_fills(self):
        result, again, calls, state = await self._complete(QCC["name"], {"legal_representative": "档案法人"}, charge=True, qcc=QCC)
        self.assertEqual(calls, [QCC["name"]], "同一次生成里同一家只查一次")
        self.assertEqual(result["legal_representative"], "档案法人", "档案里已有的不覆盖")
        self.assertEqual(result["credit_code"], QCC["credit_code"])
        self.assertEqual(result["registered_address"], "上海市查询路2号")
        self.assertIn("已查企查查补全", cwt.enterprise_notice(state)["message"])

    async def test_person_not_queried(self):
        result, _, calls, state = await self._complete("张三", {}, charge=True, qcc=QCC)
        self.assertEqual(calls, [])
        self.assertEqual(result, {})

    async def test_complete_profile_not_queried(self):
        full = {"credit_code": "91310000FULL00001X", "legal_representative": "甲", "registered_address": "某地"}
        _, _, calls, _ = await self._complete("上海全信息有限公司", full, charge=True, qcc=QCC)
        self.assertEqual(calls, [])

    async def test_lookup_failure_left_blank_with_note(self):
        result, _, _, state = await self._complete(QCC["name"], {}, charge=True, error="今日企查查次数已用完")
        self.assertEqual(result, {})
        self.assertIn("今日企查查次数已用完", cwt.enterprise_notice(state)["message"])

    async def test_outside_template_render_does_nothing(self):
        self.assertEqual(await cwt._complete_enterprise(QCC["name"], {}, None), {})


class OnlyUsedFieldsTest(unittest.TestCase):
    """模板里没用到的当事人信息不算，也不会为它查企查查（11-05 发现：生成撤诉申请书等也会为各方当事人查企查查）。"""

    def test_wanted_follows_template_fields(self):
        token = cwt.ENTERPRISE_LOOKUP.set({"charge": True, "username": "admin", "fields": {"法院", "案由"}})
        try:
            self.assertFalse(cwt._wanted("被告信息"))
            self.assertTrue(cwt._wanted("案由"))
        finally:
            cwt.ENTERPRISE_LOOKUP.reset(token)
        self.assertTrue(cwt._wanted("被告信息"), "不在生成模板时照常算")


if __name__ == "__main__":
    unittest.main()
