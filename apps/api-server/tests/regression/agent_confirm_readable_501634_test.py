"""501634（tgn 11-05）：确认窗口里的信息跟页面一致：编号换成案号、名称，不出现“其他信息”、内部编号。"""
import asyncio
import unittest
from types import SimpleNamespace

from app.agent_mcp.action_summary import summary_from_preview
from app.agent_mcp.display_labels import display_maps, record_display_maps, value_label

PARAMS = {"path": {"case_id": 501332}, "query": {}, "body": {
    "customer_record_id": 280154, "title": "10.30测试客户", "case_phase": "新案待分配", "cause_or_charge": "离婚纠纷",
    "handling_lawyers": ["System", "fanwl"], "assistant": "", "assistants": [], "business_owner": "范文玲玲", "investigator": "范文玲",
    "extra_investigators": [], "investigation_clue_ids": [280197], "right_type": "", "source_person": "范文玲玲",
    "comment": "案由由“侵害商标权纠纷”改为“离婚纠纷”"}}


class _FakeResult:
    def __init__(self, rows): self._rows = rows
    def all(self): return self._rows


class _FakeDb:
    async def execute(self, statement):
        sql = str(statement)
        if "FROM departments" in sql:
            return _FakeResult([SimpleNamespace(id=7, code="BJ-OFFICE", name="北京分所")])
        if "FROM users" in sql:
            return _FakeResult([SimpleNamespace(username="fanwl", display_name="范文玲")])
        if "business_records.owner" in sql and "business_records.serial_no" not in sql:
            return _FakeResult([])
        return _FakeResult([
            SimpleNamespace(id=501332, module="case", serial_no="HZMS2650002", title="某案"),
            SimpleNamespace(id=280154, module="customer", serial_no="KH001", title="10.30测试客户"),
            SimpleNamespace(id=280197, module="investigation_clue", serial_no="XS2026001", title="线索甲"),
        ])


def _preview(with_records=True):
    labels = display_maps(PARAMS)
    if with_records:
        records = asyncio.run(record_display_maps(PARAMS, _FakeDb()))
        labels = {"field_labels": {**labels["field_labels"], **records["field_labels"]},
                  "value_labels": {**labels["value_labels"], **records["value_labels"]}}
    return {"operation_name": "修改案件", "method": "PUT", "path_template": "/api/v1/cases/{case_id}/normal-basic",
            "params": PARAMS, **labels}


class AgentConfirmReadable501634Test(unittest.TestCase):
    def test_ids_become_case_no_and_names(self):
        preview = _preview()
        self.assertEqual(preview["field_labels"]["case_id"], "案号")
        self.assertEqual(preview["value_labels"]["case_id"]["501332"], "HZMS2650002")
        self.assertEqual(preview["field_labels"]["customer_record_id"], "客户")
        self.assertEqual(preview["value_labels"]["investigation_clue_ids"]["280197"], "线索甲")
        self.assertEqual(value_label("case_id", 501332, preview["value_labels"]), "HZMS2650002")

    def test_summary_has_case_no_and_no_internal_codes(self):
        summary = summary_from_preview(_preview())
        self.assertIn("案号：HZMS2650002", summary)
        self.assertNotIn("案件ID", summary)
        self.assertNotIn("其他信息", summary)
        self.assertNotIn("501332", summary)
        self.assertNotIn("280154", summary)

    def test_person_accounts_show_names_and_system(self):
        preview = _preview()
        self.assertEqual(preview["value_labels"]["handling_lawyers"], {"System": "系统", "fanwl": "范文玲"})
        self.assertEqual(value_label("handling_lawyers", "System", preview["value_labels"]), "系统")

    def test_department_codes_and_ids_show_names(self):
        maps = asyncio.run(record_display_maps({"body": {"department": "BJ-OFFICE", "department_id": 7}}, _FakeDb()))
        self.assertEqual(maps["value_labels"]["department"], {"BJ-OFFICE": "北京分所"})
        self.assertEqual(maps["value_labels"]["department_id"], {"7": "北京分所"})
        self.assertEqual(maps["field_labels"]["department_id"], "部门")

    def test_service_resolves_before_values_too(self):
        import inspect
        from app.agent_mcp import service
        self.assertIn('"before": {change["field"]: change.get("before") for change in changes}', inspect.getsource(service))

    def test_unresolved_ids_are_not_shown(self):
        summary = summary_from_preview(_preview(with_records=False))
        self.assertNotIn("501332", summary)
        self.assertNotIn("其他信息", summary)


if __name__ == "__main__":
    unittest.main()
