import unittest
from pathlib import Path


class HrEmployeeBatchDeleteRouteOrderTest(unittest.TestCase):
    def test_batch_delete_route_is_registered_before_employee_id_delete_route(self):
        source = Path("app/main.py").read_text(encoding="utf-8")
        batch_route = '@app.api_route(f"{settings.api_prefix}/hr/employees/batch", methods=["DELETE"])'
        employee_route = '@app.delete(f"{settings.api_prefix}/hr/employees/{{employee_id}}"'
        self.assertIn(batch_route, source)
        self.assertIn(employee_route, source)
        self.assertLess(
            source.index(batch_route),
            source.index(employee_route),
            "FastAPI checks routes in registration order; /hr/employees/batch must not be parsed as employee_id",
        )


if __name__ == "__main__":
    unittest.main()
