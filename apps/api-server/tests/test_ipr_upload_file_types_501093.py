"""BUG20261102005（高勤兰 11-02）：案件里上传文档的类型名单和老系统一致——按案件类型取，分官文 / 非官文 / 转文。"""
import unittest
from types import SimpleNamespace

from app.core.ipr import ipr_file_type_applies, ipr_file_type_group, ipr_record_file_type_case_type


def file_type(code, name, case_type="1", official="F", transformed="F", **extra):
    legacy = {"CaseTypeId": int(case_type), "IsOfficeFileType": official, "IsTransformed": transformed} if case_type else {}
    return SimpleNamespace(code=code, name=name, extra={
        "case_type_code": case_type, "is_official": official == "T", "legacy_record": legacy, **extra})


def case(case_type_id=None, case_kind="专利"):
    return SimpleNamespace(data={"case_type_id": case_type_id, "case_kind": case_kind})


class IprUploadFileTypesTest(unittest.TestCase):
    def test_patent_cases_share_the_invention_patent_list(self):
        for code in ("1", "2", "3", "14", "15", "16", "17"):
            self.assertEqual(ipr_record_file_type_case_type(case(code)), "1", code)
        self.assertEqual(ipr_record_file_type_case_type(case("4", "商标")), "4")
        self.assertEqual(ipr_record_file_type_case_type(case("18")), "18")
        self.assertEqual(ipr_record_file_type_case_type(case(None, "商标")), "4")

    def test_only_the_case_type_list_applies(self):
        patent = file_type("100001", "权利要求书", official="T")
        trademark = file_type("420001", "商标注册申请受理通知书", case_type="4", official="T")
        utility_model = case("2")
        self.assertTrue(ipr_file_type_applies(patent, utility_model))
        self.assertFalse(ipr_file_type_applies(trademark, utility_model))
        self.assertTrue(ipr_file_type_applies(trademark, case("4", "商标")))

    def test_generic_new_system_types_are_not_offered_in_a_case(self):
        generic = SimpleNamespace(code="IPR-OTHER", name="普通知识产权案件文档", extra={"case_kinds": ["专利", "商标"]})
        self.assertFalse(ipr_file_type_applies(generic, case("2")))
        added = SimpleNamespace(code="NEW-1", name="管理员新增", extra={"case_kinds": ["专利"]})
        self.assertTrue(ipr_file_type_applies(added, case("2")))
        self.assertFalse(ipr_file_type_applies(added, case("4", "商标")))

    def test_groups_follow_the_legacy_flags(self):
        self.assertEqual(ipr_file_type_group(file_type("100001", "权利要求书", official="T")), "官文")
        self.assertEqual(ipr_file_type_group(file_type("200912", "复审决定书", official="T", transformed="T")), "官文")
        self.assertEqual(ipr_file_type_group(file_type("3200021", "转费用减缓审批通知书", transformed="T")), "转文")
        self.assertEqual(ipr_file_type_group(file_type("3310072", "其他")), "非官文")
        self.assertEqual(ipr_file_type_group(SimpleNamespace(code="X", name="x", extra={"requires_transmission": True})), "转文")


if __name__ == "__main__":
    unittest.main()
