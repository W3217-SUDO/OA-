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

    def test_relief_rate_and_filters(self):
        self.assertEqual(afm._relief_rate({"cost_slow_rate": "0.85"}), 0.85)
        self.assertEqual(afm._relief_rate({"cost_slow_rate": "1.00"}), 0.0)
        self.assertEqual(afm._relief_rate({}), 0.0)
        rows = [
            {"serial_no": "SHPU1910840", "application_no": "2019224588808", "applicant": "上海汉欣", "application_date": date(2019, 12, 31)},
            {"serial_no": "SHPI1500668", "application_no": "2015108778345", "applicant": "上海语路", "application_date": date(2015, 12, 4)},
        ]
        self.assertEqual([row["serial_no"] for row in afm._filter_rows(rows, {"case_no": "2015108"}, None, None)], ["SHPI1500668"])
        self.assertEqual([row["serial_no"] for row in afm._filter_rows(rows, {"applicant": "汉欣"}, date(2019, 1, 1), None)], ["SHPU1910840"])

    def test_monitor_and_amount_rules(self):
        base = {"paid": False, "monitor_blocked": False, "informed": False, "inform_amount": 0, "gained_amount": 0, "bill_amount": 0}
        self.assertFalse(afm._out_of_monitor(base))
        self.assertTrue(afm._out_of_monitor({**base, "paid": True}))
        self.assertTrue(afm._out_of_monitor({**base, "monitor_blocked": True}))
        self.assertEqual(afm._amounts_text(base), "未通知")
        self.assertEqual(afm._amounts_text({**base, "informed": True, "inform_amount": 180, "bill_amount": 180}), "180/0/180")
        self.assertEqual(afm._legacy_source({}), "ipr_sh")
        self.assertEqual(afm._legacy_source({"legacy_source": "ipr_hd"}), "ipr_hd")

    def test_late_fee_first_month_free(self):
        row = {"due_date": date(2026, 6, 10), "annual_fee": 2000}
        self.assertEqual(afm._late_fee(row, date(2026, 6, 10)), 0)
        self.assertEqual(afm._late_fee(row, date(2026, 7, 10)), 0)
        self.assertEqual(afm._late_fee(row, date(2026, 7, 11)), 100)
        self.assertEqual(afm._late_fee(row, date(2026, 10, 29)), 400)

    def test_notice_template_placeholders_filled(self):
        import io
        from docx import Document
        from app.areas.ipr.annual_fee_notice_template import annual_fee_notice_template
        document = Document(io.BytesIO(annual_fee_notice_template()))
        values = {"$CUSTOMERNAME": "甲公司", "$CONTRACTNAME": "张三", "$ZIP": "200000", "$ADDRESS": "上海", "$TEL": "1", "$FAX": "",
                  "$FWR": "2026-10-30", "$1": "2026-11-01", "$2": "300", "$3": "100", "$4": "400"}
        ordered = dict(sorted(values.items(), key=lambda item: -len(item[0])))
        paragraphs = list(document.paragraphs) + [p for t in document.tables for r in t.rows for c in r.cells for p in c.paragraphs]
        for paragraph in paragraphs:
            if "$" in paragraph.text:
                afm._fill_placeholders(paragraph, ordered)
        text = "\n".join(p.text for p in paragraphs)
        self.assertNotIn("$", text)
        self.assertIn("总计为：400", "".join(text.split()))
        self.assertEqual([c.text for c in document.tables[-1].rows[0].cells][:3], ["序号", "案件编号", "案件名称"])

    def test_notice_template_uses_confirmed_bank_account(self):
        # 高勤兰 11-02 确认（BUG20261030004）：收款账户改为中信银行古北支行。
        import re
        import zipfile
        from io import BytesIO
        from app.areas.ipr.annual_fee_notice_template import annual_fee_notice_template
        xml = zipfile.ZipFile(BytesIO(annual_fee_notice_template())).read("word/document.xml").decode("utf-8")
        text = re.sub(r"<[^>]+>", "", xml)
        for expected in ("名称：上海申浩律师事务所", "账号：8110201012400029679", "中信银行古北支行"):
            self.assertIn(expected, text)
        self.assertNotIn("452075880439", text)
        self.assertNotIn("中国银行上海市交大徐汇校区支行", text)

    def test_first_paid_year_and_leap_day(self):
        self.assertEqual(afm._first_paid_year_no({"first_annual_year": "3"}, date(2015, 5, 1)), 3)
        self.assertEqual(afm._first_paid_year_no({"authorization_date": "2016-04-30T00:00:00"}, date(2015, 5, 1)), 1)
        self.assertEqual(afm._first_paid_year_no({"authorization_date": "2016-05-01"}, date(2015, 5, 1)), 2)
        self.assertEqual(afm._add_months(date(2016, 2, 29), 12), date(2017, 2, 28))
        self.assertEqual(afm._patent_kind("国内实用新型专利"), "实用新型")


if __name__ == "__main__":
    unittest.main()
