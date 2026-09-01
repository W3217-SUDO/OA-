import ast
from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("app") / "main.py"
module = ast.parse(SOURCE.read_text(encoding="utf-8"))
function_node = next(
    node for node in module.body
    if isinstance(node, ast.FunctionDef) and node.name == "_prioritize_new_customer_managers"
)
namespace = {}
exec(compile(ast.Module(body=[function_node], type_ignores=[]), str(SOURCE), "exec"), namespace)
_prioritize_new_customer_managers = namespace["_prioritize_new_customer_managers"]


class CustomerManagerNewestFirstRow7Test(unittest.TestCase):
    def test_latest_added_manager_is_first(self):
        self.assertEqual(
            _prioritize_new_customer_managers(["taowei", "fanwenlin"], ["taowei", "fanwenlin", "manager3"]),
            ["manager3", "taowei", "fanwenlin"],
        )

    def test_multiple_additions_follow_stack_order_and_removals_stay_removed(self):
        self.assertEqual(
            _prioritize_new_customer_managers(["old1", "old2"], ["old2", "new1", "new2"]),
            ["new2", "new1", "old2"],
        )

    def test_repeated_save_without_additions_keeps_order(self):
        self.assertEqual(
            _prioritize_new_customer_managers(["latest", "old1", "old2"], ["latest", "old1", "old2"]),
            ["latest", "old1", "old2"],
        )


if __name__ == "__main__":
    unittest.main()
