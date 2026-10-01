import ast
import pathlib
import unittest


API_SOURCE = (pathlib.Path(__file__).resolve().parents[2] / "app" / "areas" / "legal" / "router.py").read_text(encoding="utf-8")


class CaseCapabilityBatchContractTest(unittest.TestCase):
    def test_batch_route_precedes_dynamic_case_route(self):
        batch_route = '@router.get(f"{settings.api_prefix}/cases/action-capabilities")'
        detail_route = '@router.get(f"{settings.api_prefix}/cases/{{case_id}}/action-capabilities")'
        self.assertIn(batch_route, API_SOURCE)
        self.assertIn(detail_route, API_SOURCE)
        self.assertLess(API_SOURCE.index(batch_route), API_SOURCE.index(detail_route))
        from app.main import app

        paths = [route.path for route in app.routes if "GET" in getattr(route, "methods", ())]
        self.assertLess(paths.index("/api/v1/cases/action-capabilities"), paths.index("/api/v1/cases/{case_id}/action-capabilities"))

    def test_batch_route_is_scoped_and_bounded(self):
        for token in (
            "async def case_list_action_capabilities(",
            "if len(requested_ids) > 100:",
            'BusinessRecord.module == "case"',
            "*(await _record_scope_conditions(identity, db))",
            "await _case_detail_action_capabilities(record, identity, db)",
        ):
            self.assertIn(token, API_SOURCE)

    def test_backend_source_parses(self):
        ast.parse(API_SOURCE)


if __name__ == "__main__":
    unittest.main()
