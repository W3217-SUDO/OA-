"""Structured case litigant-agent API compatibility contract."""

from __future__ import annotations

import unittest

from case_litigant_detail_row16_test import API, CaseLitigantDetailRow16Test
from app.main import CaseLitigantsInput, _clean_case_litigant_agents, _legacy_case_list
from app.models import BusinessRecord


class CaseLitigantAgentsStructuredTest(unittest.IsolatedAsyncioTestCase):
    _customer = staticmethod(CaseLitigantDetailRow16Test._customer)
    _case = staticmethod(CaseLitigantDetailRow16Test._case)

    async def asyncSetUp(self) -> None:
        await CaseLitigantDetailRow16Test.asyncSetUp(self)

    async def asyncTearDown(self) -> None:
        await CaseLitigantDetailRow16Test.asyncTearDown(self)

    async def override_db(self):
        async for db in CaseLitigantDetailRow16Test.override_db(self):
            yield db

    @staticmethod
    def _payload() -> dict:
        return {
            "plaintiffs": ["CODEX 原告"],
            "plaintiff_agents": [{"name": "原告代理人甲", "law_firm": "申浩律师事务所", "position": "合伙人", "phone": "13800000001", "authority": "特别授权"}],
            "defendants": ["CODEX 被告"],
            "defendant_agents": [{"name": "被告代理人乙", "law_firm": "乙律师事务所", "position": "律师", "phone": "13800000002", "authority": "一般授权"}],
            "third_parties": ["CODEX 第三人"],
            "third_party_agents": [{"name": "第三人代理人丙", "law_firm": "丙律师事务所", "position": "法务", "phone": "13800000003", "authority": "特别授权"}],
            "comment": "CODEX structured litigant agents",
        }

    async def test_detailed_agents_round_trip_for_all_roles(self) -> None:
        payload = self._payload()
        response = await self.client.put(f"{API}/cases/{self.edit_case_id}/litigants-detail", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        for field in ("plaintiff_agents", "defendant_agents", "third_party_agents"):
            self.assertEqual(data[field], payload[field])
        self.assertEqual(_legacy_case_list(data["plaintiff_agents"]), "原告代理人甲")
        async with self.sessions() as db:
            persisted = await db.get(BusinessRecord, self.edit_case_id)
            self.assertEqual(persisted.data["plaintiff_agents"], payload["plaintiff_agents"])
            self.assertEqual(persisted.data["defendant_agents"], payload["defendant_agents"])
            self.assertEqual(persisted.data["third_party_agents"], payload["third_party_agents"])

        changed = self._payload()
        changed["plaintiff_agents"][0]["authority"] = "修改后的特别授权"
        changed["defendant_agents"] = []
        response = await self.client.put(f"{API}/cases/{self.edit_case_id}/litigants-detail", json=changed)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["plaintiff_agents"], changed["plaintiff_agents"])
        self.assertEqual(response.json()["data"]["defendant_agents"], [])
        async with self.sessions() as db:
            persisted = await db.get(BusinessRecord, self.edit_case_id)
            self.assertEqual(persisted.data["plaintiff_agents"], changed["plaintiff_agents"])
            self.assertEqual(persisted.data["defendant_agents"], [])

    def test_name_only_agents_are_preserved_as_structured_records(self) -> None:
        body = CaseLitigantsInput(plaintiff_agents=["历史代理人"])
        self.assertEqual(
            _clean_case_litigant_agents(body.plaintiff_agents),
            [{"name": "历史代理人", "law_firm": "", "position": "", "phone": "", "authority": ""}],
        )

    def test_whitespace_agent_name_is_rejected(self) -> None:
        body = CaseLitigantsInput(plaintiff_agents=[{"name": "   "}])
        with self.assertRaisesRegex(Exception, "代理人姓名不能为空"):
            _clean_case_litigant_agents(body.plaintiff_agents)


if __name__ == "__main__":
    unittest.main()
