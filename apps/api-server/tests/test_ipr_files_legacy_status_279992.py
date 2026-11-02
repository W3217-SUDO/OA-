"""BUG20261028020（高勤兰 11-02）：迁移专利案件的状态是老系统阶段名，上传、标记已转、删除文档不能因为不是“在办”被挡住。"""
import unittest

from app.core.permissions import IPR_FILE_LOCKED_STATUSES, ipr_case_files_writable


class IprFilesLegacyStatusTest(unittest.TestCase):
    def test_legacy_stages_and_active_cases_can_maintain_files(self):
        for status in ("在办", "答复审查意见", "年费监控", "实质审查", "受理", "失效"):
            self.assertTrue(ipr_case_files_writable(status), status)

    def test_new_workflow_draft_pending_rejected_closed_stay_locked(self):
        for status in ("草稿", "待审批", "已驳回", "已结案", "", None):
            self.assertFalse(ipr_case_files_writable(status), status)
        self.assertEqual(IPR_FILE_LOCKED_STATUSES, {"草稿", "待审批", "已驳回", "已结案"})


if __name__ == "__main__":
    unittest.main()
