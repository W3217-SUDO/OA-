"""文书、客户端案件里的法院显示全称，不显示“冀01”这类代号（501149 全站排查）。"""
import unittest

from app.areas.crm.router import _portal_case_dict
from app.areas.legal.template_documents import case_template_values
from app.models import BusinessRecord

NAMES = {"冀01": "河北省石家庄市中级人民法院"}


def case(court):
    return BusinessRecord(id=1, module="case", serial_no="GD1", title="GD1", customer="上海某科技有限公司", status="一审",
                          owner="admin", department="上海", data={"court": court, "first_instance_court": court})


class CourtNamesSitewideTest(unittest.TestCase):
    def test_documents_print_court_name(self):
        values = case_template_values(case("冀01"), "first-instance-lawyer-letter", {"court_names": NAMES})
        self.assertEqual(values["court"], "河北省石家庄市中级人民法院")
        self.assertEqual(case_template_values(case("黄浦法院"), "first-instance-lawyer-letter", {"court_names": NAMES})["court"], "黄浦法院")

    def test_customer_portal_case_has_court_display(self):
        result = _portal_case_dict(case("冀01"), NAMES)
        self.assertEqual(result["data"]["court_displays"]["court"]["name"], "河北省石家庄市中级人民法院")
        self.assertEqual(_portal_case_dict(case("X99"), NAMES)["data"]["court_displays"]["court"]["status"], "unresolved")


if __name__ == "__main__":
    unittest.main()
