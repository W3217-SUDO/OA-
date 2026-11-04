"""501325（fwl 11-04）：公证号模板先用公证处设置里维护的，没维护的旧系统公证处用旧系统模板；只在返回时补，不写库。"""

import unittest

from app.core.system import _system_parameter_dict, notary_number_template
from app.models import SystemParameter


def office(extra):
    return SystemParameter(id=1, category="notary_office", code="24", name="上海市徐汇公证处", extra=extra, sort_order=0, is_active=True)


class NotaryNumberTemplateTest(unittest.TestCase):
    def test_own_template_wins(self):
        item = office({"number_template": "（{year}）沪徐证经字第{serial}号", "legacy_record": {"TemplateName": "(yyyy)沪徐证经字第xxxxx号"}})
        self.assertEqual(notary_number_template(item), "（{year}）沪徐证经字第{serial}号")

    def test_legacy_template_fallback_without_writing(self):
        extra = {"legacy_record": {"TemplateName": "(yyyy)沪徐证经字第xxxxx号"}}
        item = office(extra)
        self.assertEqual(_system_parameter_dict(item)["extra"]["number_template"], "(yyyy)沪徐证经字第xxxxx号")
        self.assertNotIn("number_template", item.extra)

    def test_other_categories_untouched(self):
        item = SystemParameter(id=2, category="fee_type", code="F", name="公证费", extra={"a": 1}, sort_order=0, is_active=True)
        self.assertEqual(_system_parameter_dict(item)["extra"], {"a": 1})


class NotaryOptionsEndpointTest(unittest.TestCase):
    def test_options_endpoint_returns_template(self):
        import inspect
        from app.areas.system.router import autocomplete_system_causes, list_system_parameter_options
        self.assertIn("notary_number_template", inspect.getsource(list_system_parameter_options))
        self.assertNotIn("notary_number_template", inspect.getsource(autocomplete_system_causes))


if __name__ == "__main__":
    unittest.main()
