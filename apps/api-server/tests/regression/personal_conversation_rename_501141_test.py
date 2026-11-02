"""501141：历史会话可以改名，改名后不再被首句自动标题覆盖。"""

import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from app.areas.personal_agent import conversations


class ConversationRenameTest(unittest.IsolatedAsyncioTestCase):
    async def test_rename_keeps_title_after_first_message(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            created = await conversations.create_conversation(directory)
            conversation_id = created["state"]["conversation_id"]
            renamed = await conversations.rename_conversation(directory, conversation_id, "  客户 甲公司  签约  ")
            self.assertEqual(next(item["title"] for item in renamed["items"] if item["id"] == conversation_id), "客户 甲公司 签约")
            state = conversations.read_state(directory, conversation_id)
            state["messages"] = [{"role": "user", "content": "帮我新建一个客户，生成一个合同"}]
            await conversations.save_state(directory, state)
            self.assertEqual(conversations.read_state(directory, conversation_id)["conversation_title"], "客户 甲公司 签约")
            with self.assertRaises(HTTPException) as caught:
                await conversations.rename_conversation(directory, conversation_id, "   ")
            self.assertEqual(caught.exception.status_code, 422)

    async def test_unrenamed_conversation_still_titles_from_first_message(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            created = await conversations.create_conversation(directory)
            state = conversations.read_state(directory, created["state"]["conversation_id"])
            state["messages"] = [{"role": "user", "content": "查一下曹志刚律师名下的案件"}]
            await conversations.save_state(directory, state)
            self.assertEqual(conversations.read_state(directory, state["conversation_id"])["conversation_title"], "查一下曹志刚律师名下的案件")


if __name__ == "__main__":
    unittest.main()
