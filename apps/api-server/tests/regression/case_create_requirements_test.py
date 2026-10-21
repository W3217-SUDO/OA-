"""智能体新建案件：缺必填信息要在提交前就列出来，而不是生成待确认操作后才保存失败。"""
import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.agent_mcp.business_preflight import prepare_business_arguments
from app.areas.legal.router import create_case
from app.core.case_create_requirements import missing_case_create_fields

COUNSEL = {"title": "无印良品法律顾问案件", "case_type": "法律顾问", "handling_lawyers": ["张律师"],
           "counsel_type": "常年法律顾问", "counsel_start": "2026-01-01", "counsel_end": "2026-12-31"}


class MissingCaseCreateFieldsTest(unittest.TestCase):
    def test_counsel_case_lists_every_missing_item_at_once(self):
        body = {"title": "无印良品法律顾问案件", "case_type": "法律顾问", "handling_lawyers": []}
        self.assertEqual(missing_case_create_fields(body), ["顾问类型", "顾问期限（开始日期和结束日期都要填）", "经办律师"])

    def test_complete_counsel_case_passes_and_wrong_period_is_reported(self):
        self.assertEqual(missing_case_create_fields(COUNSEL), [])
        wrong = {**COUNSEL, "counsel_start": "2026-12-31", "counsel_end": "2026-01-01"}
        self.assertEqual(missing_case_create_fields(wrong), ["顾问期限有误：结束日期不能早于开始日期"])

    def test_litigation_case_needs_cause_position_and_lawyer(self):
        body = {"title": "合同纠纷", "case_type": "民事案件", "handling_lawyers": ["张律师"]}
        missing = missing_case_create_fields(body)
        self.assertEqual(missing[0], "案由或罪名")
        self.assertTrue(missing[1].startswith("客户诉讼地位（可选："))
        full = {**body, "cause_or_charge": "买卖合同纠纷", "client_position": "原告/申请人"}
        self.assertEqual(missing_case_create_fields(full), [])

    def test_counsel_fields_on_a_litigation_case_are_flagged(self):
        body = {"title": "x", "case_type": "民事案件", "cause_or_charge": "纠纷", "client_position": "原告/申请人",
                "handling_lawyers": ["张律师"], "counsel_type": "常年"}
        self.assertEqual(missing_case_create_fields(body), ["顾问类型和顾问期限只适用于法律顾问案件，请去掉"])

    def test_unknown_case_type_is_reported(self):
        self.assertTrue(missing_case_create_fields({"title": "x", "case_type": "其他", "handling_lawyers": ["a"]})[0].startswith("案件类型"))


class PreflightBeforeConfirmationTest(unittest.IsolatedAsyncioTestCase):
    async def test_prepare_stops_with_a_message_that_tells_the_agent_to_ask_the_user(self):
        spec = SimpleNamespace(_route=SimpleNamespace(endpoint=create_case))
        params = {"body": {"title": "无印良品法律顾问案件", "case_type": "法律顾问", "handling_lawyers": ["张律师"]}}
        with self.assertRaises(HTTPException) as caught:
            await prepare_business_arguments(spec, {"body": params["body"]}, params, {}, None)
        self.assertEqual(caught.exception.status_code, 422)
        self.assertIn("顾问类型", caught.exception.detail)
        self.assertIn("顾问期限", caught.exception.detail)
        self.assertIn("向用户询问", caught.exception.detail)

    async def test_complete_case_goes_through_unchanged(self):
        spec = SimpleNamespace(_route=SimpleNamespace(endpoint=create_case))
        arguments = {"body": dict(COUNSEL)}
        self.assertIs(await prepare_business_arguments(spec, arguments, {"body": dict(COUNSEL)}, {}, None), arguments)


if __name__ == "__main__":
    unittest.main()
