"""501289（陶国南 11-03 21:56）：智能体改案件信息只查案件基本信息，不先读案件文档；规则写进提示词和工具说明。"""

import unittest

from fastapi.routing import APIRoute

from app.agent_mcp.operation_guidance import CASE_INFO_EDIT_PREREQUISITE, get_operation_guidance, is_case_info_edit
from app.case_agent import CASE_INFO_EDIT_RULES, build_case_model_messages
from app.config import settings
from app.harness_agent.runtime import oa_persona
from app.main import app


def route(name):
    return next(item for item in app.routes if isinstance(item, APIRoute) and item.endpoint.__name__ == name)


class CaseInfoEditRulesTest(unittest.TestCase):
    def test_case_info_edit_tools_say_basic_info_only(self):
        for name in ("update_normal_case_basic", "update_case_hearing_lawyer", "update_case_litigants", "update_case_court_info",
                     "update_case_notary_info", "update_case_settlement_amount", "update_case_phase", "create_case_reminder",
                     "create_case_event", "create_case_assisted_fee", "create_finance_fee", "update_finance_fee"):
            item = route(name)
            method = sorted(item.methods)[0]
            self.assertIn(CASE_INFO_EDIT_PREREQUISITE, get_operation_guidance(item, method)["prerequisites"], name)

    def test_document_and_archive_tools_unchanged(self):
        for method, path in (("POST", "/cases/{case_id}/ai-space/files"), ("POST", "/cases/{case_id}/attachments/move"),
                             ("POST", "/cases/{case_id}/documents/word-templates/{template_id}/generate"),
                             ("POST", "/cases/{case_id}/archive"), ("POST", "/cases/{case_id}/merge"), ("GET", "/cases/{case_id}"),
                             ("DELETE", "/finance/fees/{fee_id}")):
            self.assertFalse(is_case_info_edit(method, path), path)
        item = route("create_case_ai_draft")
        self.assertNotIn(CASE_INFO_EDIT_PREREQUISITE, get_operation_guidance(item, "POST")["prerequisites"])
        self.assertTrue(item.path.removeprefix(settings.api_prefix).startswith("/cases/"))

    def test_prompts_for_case_agent_and_shared_persona(self):
        prompt = build_case_model_messages({"case": {"id": 1}, "capabilities": {}}, [], None, [])[0]["content"]
        self.assertIn(CASE_INFO_EDIT_RULES, prompt)
        self.assertIn("不要读取案件文档", CASE_INFO_EDIT_RULES)
        self.assertIn("只查案件基本信息", oa_persona())


if __name__ == "__main__":
    unittest.main()


class CaseAskRules501634Test(__import__("unittest").TestCase):
    """501634（tgn 11-06 15:31 确认）：拿不准时用【追问】选项问题条，不写文字反问；确认在对话框下方点选。"""

    def test_case_agent_prompt_asks_with_options(self):
        from app import case_agent
        rules = case_agent.CASE_ASK_RULES
        self.assertIn("【追问】", rules)
        self.assertIn('{"questions":[{"question":"问题","options":["选项1","选项2"]}]}', rules)
        self.assertIn("信息齐全、对象唯一时不要追问，直接生成确认卡片", rules)
        self.assertIn("不要写“其他”选项", rules)
        self.assertNotIn("确认窗口", case_agent.CASE_INFO_EDIT_RULES)
        import inspect
        self.assertIn("{CASE_INFO_EDIT_RULES}{CASE_ASK_RULES}", inspect.getsource(case_agent))


class CaseAgentDecisionRace501634Test(__import__("unittest").IsolatedAsyncioTestCase):
    """501634（tgn 11-06 15:49）：执行期间页面刷新把卡片同步成“正在执行”，执行完回来仍要记下结果，不能报 409 卡住。"""

    async def test_executing_mcp_card_accepts_its_own_result(self):
        from contextlib import asynccontextmanager
        from app.case_agent import CaseAgentRuntime

        class Store:
            def __init__(self, values):
                self.values = values
            @asynccontextmanager
            async def operation(self, thread):
                yield
            async def write(self, thread, values):
                self.values = values

        def runtime(status, action_type="mcp.call"):
            item = CaseAgentRuntime.__new__(CaseAgentRuntime)
            item.store = Store({"pending_actions": [{"id": "a1", "type": action_type, "status": status}], "messages": []})
            item.error = ""
            async def ensure(*args, **kwargs):
                return item.store.values
            item._ensure_private_state = ensure
            item._public_state = lambda case_id, operator, values, *rest: values
            return item

        done = await runtime("executing").decide_action(case_id=1, action_id="a1", decision="approved", operator="tgn",
                                                        execution_result={"status": "succeeded"})
        self.assertEqual(done["pending_actions"][0]["status"], "approved")
        with self.assertRaises(ValueError):  # 没带执行结果（重复点击）仍拦下
            await runtime("executing").decide_action(case_id=1, action_id="a1", decision="approved", operator="tgn")
        with self.assertRaises(ValueError):  # 已处理完的不能再改
            await runtime("approved").decide_action(case_id=1, action_id="a1", decision="rejected", operator="tgn",
                                                    execution_result={"status": "rejected"})
