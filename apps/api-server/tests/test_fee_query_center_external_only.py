"""财务中心/平台财务中心的费用查询按老系统只列外部费用，内部费用不混进来（陶国南 2026-11-02）。"""
import unittest
from unittest.mock import AsyncMock, patch

from app.areas.finance import router as finance_router


def fact(fee_id, internal):
    return {"id": fee_id, "is_internal": internal, "refund_requested_amount": None,
            "payment_status": "", "unpaid_official": False, "amount": 100}


class FeeQueryCenterExternalOnlyTest(unittest.IsolatedAsyncioTestCase):
    async def query(self, identity):
        facts = [fact(1, False), fact(2, True), fact(3, False)]
        with patch("app.core.dashboard_scope.dashboard_request_identity", AsyncMock(return_value=identity)), \
                patch("app.core.fee_list_facts.fee_query_facts", AsyncMock(return_value=facts)), \
                patch("app.core.finance.invoice_fee_row_filter", AsyncMock(return_value=lambda row: True)), \
                patch("app.core.system._allowed_field_keys", AsyncMock(return_value={"finance.amount"})), \
                patch("app.core.finance._fee_query_rows", AsyncMock(side_effect=lambda *a, ids=None, **k: [{"id": i} for i in sorted(ids or [])])), \
                patch.object(finance_router, "filter_rows_by_center", AsyncMock(side_effect=lambda rows, *a, **k: list(rows))):
            return await finance_router.query_finance_fees(
                scope="company", unpaid_official=False, external_only=False, case_no="", court_case_no="", notary_no="",
                refund_amount_from=None, refund_amount_to=None, customer="", paid_organization="", payment_status="",
                paid_from=None, paid_to=None, hearing_lawyer="", assistant="", case_stages="", fee_types="",
                page=1, page_size=15, dashboard_queue="", identity=identity, db=None,
            )

    async def test_firm_and_platform_center_hide_internal_fees(self):
        for scope in ("firm", "platform"):
            result = await self.query({"_finance_scope": scope})
            self.assertEqual([row["id"] for row in result["items"]], [1, 3])
            self.assertEqual(result["total"], 2)

    async def test_without_center_keeps_internal_fees(self):
        result = await self.query({})
        self.assertEqual(result["total"], 3)


if __name__ == "__main__":
    unittest.main()
