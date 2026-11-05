"""陶国南 11-05 09:14：新建公司客户一张“查企查查并新建客户”卡片；录费用多份合同时卡片上选合同。企查查只用假接口。"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.agent_mcp import business_tools
from app.agent_mcp.service import APPROVED_EXECUTION, apply_card_choice
from app.main import app


def _context():
    return SimpleNamespace(application=app, readonly=False, groups=None, write_allowed=True, username="u")


DETAIL = {"name": "上海假企业科技有限公司", "credit_code": "91310000FAKE00001X", "legal_representative": "假法人",
          "registered_address": "上海市假路1号", "organization_type": "公司企业", "roles": {"customers": [], "parties": []}}


async def _run(name, args, fake, *, confirm=False):
    with patch.object(business_tools, "get_auth_context", return_value=_context()):
        if confirm:
            token = APPROVED_EXECUTION.set(True)
            try:
                return await business_tools.run_business_tool(name, {**args, "confirm": True}, call=fake)
            finally:
                APPROVED_EXECUTION.reset(token)
        return await business_tools.run_business_tool(name, args, call=fake)


class CustomerEnterpriseCardTest(unittest.IsolatedAsyncioTestCase):
    def _fake(self, calls, library=()):
        async def fake(name, args):
            calls.append((name, args))
            if name == "oa_list_company_library_get":
                return {"items": list(library)}
            if name == "oa_lookup_company_library_post":
                return DETAIL
            if name == "oa_create_customer_post":
                return {"id": 9, "serial_no": "KH1", "title": args["body"]["title"]}
            return {"items": []}
        return fake

    async def test_not_in_library_plans_one_card_with_paid_lookup(self):
        calls = []
        plan = await _run("biz_customer_create", {"title": DETAIL["name"], "customer_managers": ["admin"]}, self._fake(calls))
        writes = [step["tool"] for step in plan["steps"] if step["kind"] == "写"]
        self.assertEqual(writes, ["oa_lookup_company_library_post", "oa_create_customer_post"])
        self.assertTrue(any("扣一次企查查查询" in item for item in plan["changes"]))
        self.assertNotIn("oa_lookup_company_library_post", [name for name, _ in calls], "计划阶段不真的查企查查")

    async def test_execution_fills_customer_from_lookup(self):
        calls = []
        await _run("biz_customer_create", {"title": DETAIL["name"], "customer_managers": ["admin"]}, self._fake(calls), confirm=True)
        body = next(args for name, args in calls if name == "oa_create_customer_post")["body"]
        self.assertEqual((body["credit_code"], body["legal_representative"], body["taxpayer_id"]), (DETAIL["credit_code"], "假法人", DETAIL["credit_code"]))
        self.assertEqual([name for name, _ in calls].count("oa_lookup_company_library_post"), 1, "点一次只查一次")

    async def test_library_hit_does_not_charge(self):
        calls = []
        plan = await _run("biz_customer_create", {"title": DETAIL["name"], "customer_managers": ["admin"]}, self._fake(calls, [DETAIL]))
        self.assertNotIn("oa_lookup_company_library_post", [step["tool"] for step in plan["steps"]])
        self.assertTrue(any("不扣企查查次数" in item for item in plan["changes"]))

    async def test_individual_skips_enterprise_lookup(self):
        calls = []
        plan = await _run("biz_customer_create", {"title": "张三", "organization_type": "个人", "customer_managers": ["admin"]}, self._fake(calls))
        self.assertNotIn("oa_list_company_library_get", [step["tool"] for step in plan["steps"]])


class FeeContractChoiceTest(unittest.IsolatedAsyncioTestCase):
    def _fake(self, contracts):
        async def fake(name, args):
            if name in ("oa_get_record_get", "oa_search_ordinary_cases_post"):
                return {"id": 1, "serial_no": "HZMS1", "customer": "甲公司", "data": {}}
            if name == "oa_list_case_fee_contracts_get":
                return {"items": contracts}
            return {"id": 5}
        return fake

    ARGS = {"case_id": 1, "expense_scope": "律所", "fee_type": "官费", "title": "一审诉讼费", "amount": 100, "handler": "admin"}
    TWO = [{"id": 11, "serial_no": "HT1", "title": "常年法律顾问合同", "data": {"signed_at": "2026-01-02"}},
           {"id": 12, "serial_no": "HT2", "title": "专项代理合同", "data": {"signed_at": "2026-03-04"}}]

    async def test_two_contracts_put_choice_on_card(self):
        plan = await _run("biz_case_fee_create_and_request_payment", self.ARGS, self._fake(self.TWO))
        self.assertEqual([item["value"] for item in plan["choice"]["options"]], [11, 12])
        self.assertIn("常年法律顾问合同", plan["choice"]["options"][0]["label"])
        self.assertIn("2026-01-02", plan["choice"]["options"][0]["label"])
        self.assertFalse(any(step.get("problem") for step in plan["steps"]))

    async def test_one_contract_is_default(self):
        plan = await _run("biz_case_fee_create_and_request_payment", self.ARGS, self._fake(self.TWO[:1]))
        self.assertNotIn("choice", plan)
        body = next(step for step in plan["steps"] if step["tool"] == "oa_create_finance_fee_post")["arguments"]["body"]
        self.assertEqual(body["contract_record_id"], 11)

    async def test_execution_without_choice_is_refused(self):
        with self.assertRaises(HTTPException) as caught:
            await _run("biz_case_fee_create_and_request_payment", self.ARGS, self._fake(self.TWO), confirm=True)
        self.assertEqual(caught.exception.status_code, 409)

    def test_choice_must_be_an_offered_option(self):
        data = {"arguments": dict(self.ARGS), "preview": {"choice": {"field": "contract_record_id", "label": "费用归属合同",
                                                                    "options": [{"value": 11, "label": "A"}, {"value": 12, "label": "B"}]}}}
        with self.assertRaises(HTTPException):
            apply_card_choice(dict(data), None)
        with self.assertRaises(HTTPException):
            apply_card_choice(dict(data), {"contract_record_id": 99})
        apply_card_choice(data, {"contract_record_id": "12"})
        self.assertEqual(data["arguments"]["contract_record_id"], 12)


if __name__ == "__main__":
    unittest.main()
