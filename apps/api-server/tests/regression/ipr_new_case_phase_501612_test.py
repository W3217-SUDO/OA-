"""501612（fwl 11-05）：新建知识产权案件时可选案件阶段，照旧系统按申请类型给选项，默认“申请立案”。"""

import unittest

from app.api_schemas.ipr import IprCaseCreateInput
from app.main import app


class IprNewCasePhaseTest(unittest.TestCase):
    def test_create_defaults_to_application_filing(self):
        body = IprCaseCreateInput(case_kind="专利", title="t", customer="c")
        self.assertEqual(body.case_phase, "申请立案")
        self.assertEqual(IprCaseCreateInput(case_kind="专利", title="t", customer="c", case_phase="受理").case_phase, "受理")

    def test_annual_fee_phase_turns_on_monitoring_at_create(self):
        import inspect
        from app.areas.ipr import router as ipr_router
        source = inspect.getsource(ipr_router)
        self.assertIn('"annual_fee_monitoring": (body.case_phase.strip() == "年费监控")', source)

    def test_phase_options_route_registered(self):
        paths = {(route.path, tuple(sorted(getattr(route, "methods", []) or []))) for route in app.routes}
        self.assertIn(("/api/v1/ipr/phase-options", ("GET",)), paths)
        self.assertIn(("/api/v1/ipr/cases/{case_id}/phase-options", ("GET",)), paths)


if __name__ == "__main__":
    unittest.main()
