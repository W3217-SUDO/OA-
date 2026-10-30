"""BUG20261030004：专利年费 年费清单 / 年费监控 的日期与年费计算。"""

import unittest
from datetime import date

from app.areas.ipr import annual_fee_monitor as afm


class IprAnnualFeeMonitorTest(unittest.TestCase):
    def test_views_match_legacy_middle_column(self):
        views = afm._views(date(2026, 10, 30))
        self.assertEqual([item["label"] for item in views], [
            "2026年费", "26三季度", "26四季度", "27一季度", "27二季度",
            "6月内年费", "逾期1月", "逾期2月", "逾期3月", "逾期4月", "逾期5月", "逾期6月",
        ])
        by_key = {item["key"]: item for item in views}
        self.assertEqual((by_key["quarter-2027-1"]["start"], by_key["quarter-2027-1"]["end"]), (date(2027, 1, 1), date(2027, 3, 31)))
        self.assertEqual((by_key["within-6"]["start"], by_key["within-6"]["end"]), (date(2026, 10, 30), date(2027, 4, 29)))
        self.assertEqual((by_key["overdue-1"]["start"], by_key["overdue-1"]["end"]), (date(2026, 9, 30), date(2026, 10, 29)))
        self.assertEqual(by_key["overdue-6"]["start"], date(2026, 4, 30))

    def test_term_and_standard_fee(self):
        self.assertEqual(afm._term_years("发明", date(2015, 1, 1)), 20)
        self.assertEqual(afm._term_years("实用新型", date(2022, 1, 1)), 10)
        self.assertEqual(afm._term_years("外观设计", date(2021, 5, 31)), 10)
        self.assertEqual(afm._term_years("外观设计", date(2021, 6, 1)), 15)
        self.assertEqual(afm._standard_fee("发明", 3), 900)
        self.assertEqual(afm._standard_fee("发明", 16), 8000)
        self.assertEqual(afm._standard_fee("实用新型", 10), 2000)
        self.assertEqual(afm._standard_fee("外观设计", 11), 3000)

    def test_first_paid_year_and_leap_day(self):
        self.assertEqual(afm._first_paid_year_no({"first_annual_year": "3"}, date(2015, 5, 1)), 3)
        self.assertEqual(afm._first_paid_year_no({"authorization_date": "2016-04-30T00:00:00"}, date(2015, 5, 1)), 1)
        self.assertEqual(afm._first_paid_year_no({"authorization_date": "2016-05-01"}, date(2015, 5, 1)), 2)
        self.assertEqual(afm._add_months(date(2016, 2, 29), 12), date(2017, 2, 28))
        self.assertEqual(afm._patent_kind("国内实用新型专利"), "实用新型")


if __name__ == "__main__":
    unittest.main()
