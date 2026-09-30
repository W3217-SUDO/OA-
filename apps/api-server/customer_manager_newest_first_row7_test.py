import unittest

from app.core.crm import _prioritize_new_customer_managers


class CustomerManagerNewestFirstRow7Test(unittest.TestCase):
    def test_latest_added_manager_is_first(self):
        self.assertEqual(
            _prioritize_new_customer_managers(["taowei", "fanwenlin"], ["manager3", "taowei", "fanwenlin"]),
            ["manager3", "taowei", "fanwenlin"],
        )

    def test_multiple_additions_follow_stack_order_and_removals_stay_removed(self):
        self.assertEqual(
            _prioritize_new_customer_managers(["old1", "old2"], ["new2", "new1", "old2"]),
            ["new2", "new1", "old2"],
        )

    def test_repeated_save_without_additions_keeps_order(self):
        self.assertEqual(
            _prioritize_new_customer_managers(["latest", "old1", "old2"], ["latest", "old1", "old2"]),
            ["latest", "old1", "old2"],
        )


if __name__ == "__main__":
    unittest.main()
