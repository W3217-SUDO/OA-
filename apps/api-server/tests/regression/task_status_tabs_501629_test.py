"""501629（tgn 11-05 选 A）：任务页签按老系统分页面。

发起的任务 6 个：进行中、进行中-已完成、进行中-拒绝、进行中-已停止、进行中-已撤回、已验收；
接受的任务 4 个：待处理、处理中、已完成、已停止；协作的任务 2 个：处理中、已完成。
"""
import re
import unittest
from pathlib import Path

CONSTANTS = Path(__file__).resolve().parents[4] / "apps" / "admin-web" / "src" / "tp" / "constants.ts"


def _labels(name: str) -> list[str]:
    source = CONSTANTS.read_text(encoding="utf-8")
    block = re.search(rf"export const {name}: StatusTab\[\] = \[(.*?)\n\];", source, re.S)
    assert block, name
    return re.findall(r'label: "([^"]+)"', block.group(1))


class TaskStatusTabs501629Test(unittest.TestCase):
    def test_created_tabs_keep_legacy_six(self):
        self.assertEqual(_labels("createdTabs"), ["进行中", "进行中-已完成", "进行中-拒绝", "进行中-已停止", "进行中-已撤回", "已验收"])

    def test_received_tabs_use_legacy_names(self):
        self.assertEqual(_labels("receivedTabs"), ["待处理", "处理中", "已完成", "已停止"])

    def test_collaborating_tabs_use_legacy_names(self):
        self.assertEqual(_labels("collaboratingTabs"), ["处理中", "已完成"])


if __name__ == "__main__":
    unittest.main()
