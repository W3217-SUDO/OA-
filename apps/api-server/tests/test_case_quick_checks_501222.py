"""501222（陶国南 11-03 12:50）：“归纳案件情况 / 优先待办事项”的固定检查。"""
import unittest
from datetime import date

from app.case_quick_checks import QUICK_COMMAND_RULES, build_case_check
from app.case_workflow_rules import build_case_workflow_guide

TODAY = date(2026, 11, 3)


def context(**overrides):
    base = {
        "case": {"status": "新案待分配", "data": {"cause_or_charge": "买卖合同纠纷", "plaintiff": "甲公司", "defendant": "乙公司",
                                                  "handling_lawyers": ["思法汇成"], "hearing_lawyer": "chenjiugen", "assistant": "chenjiugen",
                                                  "court": "苏州中院", "court_case_no": "(2026)苏05民初1号"}},
        "people": [{"role": "经办律师", "name": "思法汇成"}, {"role": "开庭律师", "name": "陈久根"}, {"role": "律师助理", "name": "陈久根"}],
        "contracts": [{"id": 1, "data": {"contract_type": "争议解决合同"}}],
        "finances": {"fees": [{"data": {"fee_type": "代理费"}}], "invoices": [{"id": 1}]},
        "documents": [{"name": "授权委托书.pdf"}],
        "tasks": [],
    }
    base.update(overrides)
    base["standard_workflow"] = build_case_workflow_guide(base, reference_date=TODAY)
    return base


class CaseQuickChecksTest(unittest.TestCase):
    def test_a_missing_elements_and_stage_mismatch(self):
        ctx = context(case={"status": "文书准备", "data": {}}, people=[], documents=[{"name": "一审判决书.pdf"}])
        check = build_case_check(ctx, today=TODAY)
        self.assertEqual(check["a_case_elements"]["missing"], ["案件当事人", "案由", "经办律师", "开庭律师", "律师助理"], "文书准备阶段不查法院信息")
        self.assertIn("已上传判决书", check["a_case_elements"]["stage_document_mismatch"][0])
        early = build_case_check(context(case={"status": "等待公证书", "data": {}}, people=[]), today=TODAY)
        self.assertNotIn("法院信息", early["a_case_elements"]["missing"], "立案前不查法院信息、法院案号")
        self.assertNotIn("法院案号", early["a_case_elements"]["missing"])
        filed = build_case_check(context(case={"status": "已立案", "data": {}}, people=[]), today=TODAY)
        self.assertIn("法院案号", filed["a_case_elements"]["missing"])
        complete = build_case_check(context(), case_last_activity="2026-11-01", today=TODAY)
        self.assertEqual(complete["issue_count"], 0, "全部没问题时只给一句结论")
        self.assertGreater(check["issue_count"], 0)
        self.assertEqual(complete["a_case_elements"]["missing"], [])
        self.assertEqual(complete["a_case_elements"]["stage_document_mismatch"], [])

    def test_b_urgent_stale_and_postponed_tasks(self):
        tasks = [{"id": 1, "title": "提交证据", "status": "待处理", "deadline": "2026-11-04"},
                 {"id": 2, "title": "联系客户", "status": "处理中", "deadline": "2026-12-30"},
                 {"id": 3, "title": "补材料", "status": "待处理", "deadline": "2026-12-01"},
                 {"id": 4, "title": "已办完", "status": "已完成", "deadline": "2026-10-01"}]
        check = build_case_check(context(tasks=tasks), postpones={2: 2, 3: 3}, case_last_activity="2026-10-01", today=TODAY)
        self.assertEqual([item["id"] for item in check["b_tasks"]["urgent"]], [1])
        self.assertEqual([(item["id"], item["postpone_count"]) for item in check["b_tasks"]["postponed"]], [(3, 3)], "延期 3 次及以上才算多次延期")
        self.assertIsNone(check["b_tasks"]["case_idle"], "60 日内有记录不提醒")
        idle = build_case_check(context(), case_last_activity="2026-09-01T10:00:00", today=TODAY)["b_tasks"]["case_idle"]
        self.assertEqual(idle["message"], "案件 63 日未有状态变化")

    def test_c_contract_fees_framework_and_after_judgment(self):
        bare = build_case_check(context(contracts=[], finances={"fees": [], "invoices": []}, documents=[]), today=TODAY)
        self.assertEqual(bare["c_contract_and_fees"], ["没有关联合同，请确认是否已签订合同", "没有上传授权委托书", "还没有新建律师费（代理费）"])
        framework = context(contracts=[{"data": {"contract_type": "框架合作合同"}}], finances={"fees": [], "invoices": []})
        self.assertEqual(build_case_check(framework, today=TODAY)["c_contract_and_fees"], [], "框架合作合同前期不提醒建费用")
        judged = context(contracts=[{"data": {"contract_type": "框架合作合同"}}], finances={"fees": [], "invoices": []},
                         documents=[{"name": "授权委托书.pdf"}, {"name": "民事判决书.pdf"}])
        self.assertIn("已判决：请及时申请执行；符合收费条件的及时催收律师费", build_case_check(judged, today=TODAY)["c_contract_and_fees"])
        uninvoiced = context(finances={"fees": [{"data": {"fee_type": "代理费"}}], "invoices": []})
        self.assertIn("律师费已新建，还没有开具发票", build_case_check(uninvoiced, today=TODAY)["c_contract_and_fees"])

    def test_d_lawyer_license_only_when_submitting_to_court(self):
        self.assertEqual(build_case_check(context(), today=TODAY)["d_lawyer_license"], [], "文书准备阶段不提醒")
        filing = context(case={"status": "已立案", "data": context()["case"]["data"]})
        self.assertEqual(build_case_check(filing, today=TODAY)["d_lawyer_license"], ["提交法院（立案、开庭）时请把律师证一并提交法院"])
        guide = context()["standard_workflow"]
        self.assertFalse(next(item for item in guide["materials"] if item["code"] == "lawyer-license")["required"], "律师证不是必备项")

    def test_rules_only_report_found_problems(self):
        self.assertIn("查过没问题的项一律不写", QUICK_COMMAND_RULES)
        self.assertIn("未发现需要处理的问题", QUICK_COMMAND_RULES)
        self.assertNotIn("写“无”。", QUICK_COMMAND_RULES)


if __name__ == "__main__":
    unittest.main()
