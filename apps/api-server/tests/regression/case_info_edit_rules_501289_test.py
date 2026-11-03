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
