"""智能体调用工具缺必填参数：一次列出全部缺项，并提示先问用户。"""
import unittest

from fastapi import HTTPException

from app.agent_mcp.catalog import _require_all, _strict_objects


class MissingRequiredTest(unittest.TestCase):
    def test_all_missing_required_names_are_listed_in_one_error(self):
        schema = {"type": "object", "required": ["title", "case_type", "handling_lawyers"],
                  "properties": {"title": {"type": "string"}, "case_type": {"type": "string"}, "handling_lawyers": {"type": "array"}}}
        with self.assertRaises(HTTPException) as caught:
            _strict_objects({"title": "x"}, schema, {}, ("body",))
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual([item["loc"] for item in caught.exception.detail], [["body", "case_type"], ["body", "handling_lawyers"]])
        self.assertTrue(all("请先向用户询问" in item["msg"] and item["type"] == "missing" for item in caught.exception.detail))

    def test_nothing_missing_is_not_an_error(self):
        _require_all(("query",), ["a", "b"], {"a": 1, "b": 2})
        _strict_objects({"a": 1}, {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}}, {}, ())

    def test_group_level_required_parameters_are_listed_together(self):
        with self.assertRaises(HTTPException) as caught:
            _require_all(("path",), ["case_id", "task_id"], {})
        self.assertEqual([item["loc"] for item in caught.exception.detail], [["path", "case_id"], ["path", "task_id"]])


if __name__ == "__main__":
    unittest.main()
