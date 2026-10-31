"""陶威 10-31：旧沪知系统仍在用并持续同步，新系统自编号从各自号段起，不再和旧系统撞号。"""
import unittest

from app.core.serial_ranges import NEW_SYSTEM_SERIAL_START, next_in_range


class NewSystemSerialRangeTest(unittest.TestCase):
    def test_starts(self):
        self.assertEqual(NEW_SYSTEM_SERIAL_START, {"customer": 50001, "contract": 50001, "case": 50001, "clue": 8001})

    def test_legacy_numbers_below_range_are_ignored(self):
        self.assertEqual(next_in_range([10664, 10665], "customer"), 50001)
        self.assertEqual(next_in_range([10665, 50001, 50007], "customer"), 50008)
        self.assertEqual(next_in_range([3996], "clue"), 8001)
        self.assertEqual(next_in_range([], "case"), 50001)


if __name__ == "__main__":
    unittest.main()
