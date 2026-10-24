import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.core import fee_list_facts as facts_cache
from app.core.finance import invoice_fee_row_filter, refund_case_fee_row_passes


FACTS = {
    "id": 7, "case_no": "HD2025-01", "court_case_no": "(2025)沪0101民初1号", "certificate_no": "",
    "invoiced_amount": 100.0, "remaining_invoice_amount": 0.0, "has_issued_invoice": True,
    "invoice_status": "已开票", "invoice_date": "2026-09-30", "customer": "上海某科技有限公司",
    "paid_organization": "黄浦法院", "hearing_lawyer": "王律师", "assistant": "李助理", "case_stage": "一审",
    "paid_date": "2026-10-01", "fee_type_id": "", "fee_type_code": "", "fee_type_name": "",
    "base_fee_type": "官方费用", "display_fee_type": "诉讼费", "received_payer_name": "", "cashed_date": "",
}


class FeeListFactsTest(unittest.IsolatedAsyncioTestCase):
    def test_columns_round_trip_keeps_order_and_values(self):
        rows = [dict(FACTS, id=index) for index in range(3)]
        self.assertEqual(facts_cache._rows(facts_cache._columns(rows)), rows)
        self.assertEqual(facts_cache._rows(facts_cache._columns([])), [])
        with self.assertRaises(ValueError):
            facts_cache._columns([{"id": 1}, {"other": 2}])

    def test_compressed_entry_round_trips_and_rejects_corruption(self):
        rows = [{"id": 1, "nested": {"a": [1, 2]}}, {"id": 2, "nested": {}}]
        payload = facts_cache._encode("10:20:", rows)
        self.assertEqual(facts_cache._decode(payload), {"snapshot": "10:20:", "result": rows})
        with self.assertRaises(HTTPException):
            facts_cache._decode(b"not-zlib")
        with patch.object(facts_cache.settings, "fee_facts_cache_max_payload_bytes", 8):
            self.assertIsNone(facts_cache._encode("10:20:", [{"id": index} for index in range(1000)]))

    async def test_same_payload_is_decoded_once_per_process(self):
        payloads = {"k:data": facts_cache._encode("1:2:", [{"id": 1}])}
        client = SimpleNamespace(get=AsyncMock(side_effect=lambda key: payloads.get(key)))
        facts_cache._decoded.clear()
        with patch.object(facts_cache.shared, "client", return_value=client), \
             patch.object(facts_cache, "_decode", wraps=facts_cache._decode) as decode:
            first = await facts_cache._read("k")
            self.assertIs(await facts_cache._read("k"), first)
            self.assertEqual(decode.call_count, 1)
            payloads["k:data"] = facts_cache._encode("1:3:", [{"id": 2}])
            self.assertEqual((await facts_cache._read("k"))["result"], [{"id": 2}])
            self.assertEqual(decode.call_count, 2)
            self.assertIsNone(await facts_cache._read("missing"))
        facts_cache._decoded.clear()

    async def test_publish_skips_oversize_and_memory_pressure(self):
        client = SimpleNamespace(eval=AsyncMock(return_value=1))
        with patch.object(facts_cache.shared, "client", return_value=client), \
             patch.object(facts_cache.store, "_memory_allows_publish", AsyncMock(return_value=False)):
            await facts_cache._publish("key", "owner", "1:2:", [])
        client.eval.assert_not_awaited()
        with patch.object(facts_cache.shared, "client", return_value=client), \
             patch.object(facts_cache.store, "_memory_allows_publish", AsyncMock(return_value=True)):
            await facts_cache._publish("key", "owner", "1:2:", [])
        self.assertEqual(client.eval.await_args.args[2:4], ("key:lock", "key:data"))

    async def test_dashboard_scoped_identity_is_refused(self):
        with self.assertRaises(ValueError):
            await facts_cache.fee_query_facts({"_dashboard_fee_ids": {1}}, None, scope="company")
        with self.assertRaises(ValueError):
            await facts_cache.refund_pending_base({"_dashboard_fee_ids": {1}}, None)

    async def test_row_filter_matches_text_dates_and_invoice_status(self):
        db = SimpleNamespace()
        with patch("app.core.finance._fee_type_filter_values", AsyncMock(return_value=(set(), set(), set(), set(), set()))):
            async def passes(**filters):
                return (await invoice_fee_row_filter(db, **filters))(FACTS)

            self.assertTrue(await passes())
            self.assertTrue(await passes(customer=" 科技 ", case_no="hd2025", paid_organization="黄浦"))
            self.assertFalse(await passes(customer="北京"))
            self.assertTrue(await passes(paid_from=date(2026, 10, 1), paid_to=date(2026, 10, 1)))
            self.assertFalse(await passes(paid_from=date(2026, 10, 2)))
            self.assertFalse(await passes(cashed_from=date(2026, 1, 1)))  # 无到账日期不满足日期下限
            self.assertFalse(await passes(invoice_status="未开票"))
            self.assertTrue(await passes(invoice_status="已开票", invoice_from=date(2026, 9, 30)))
            self.assertTrue(await passes(case_stages="二审,一审"))
            self.assertFalse(await passes(case_stages="二审"))
            self.assertTrue(await passes(fee_types="官费"))
            self.assertTrue(await passes(fee_types="诉讼费"))
            self.assertFalse(await passes(fee_types="代理费"))

    def test_fee_query_and_refund_row_conditions(self):
        row = {"is_internal": False, "refund_requested_amount": None, "payment_status": "已付款", "unpaid_official": False}
        kwargs = dict(external_only=False, refund_amount_from=None, refund_amount_to=None, payment_status="", unpaid_official=False)
        self.assertTrue(facts_cache.fee_query_row_passes(row, **kwargs))
        # 金额被遮蔽（None）时设了退费下限即不满足，与原逻辑一致
        self.assertFalse(facts_cache.fee_query_row_passes(row, **{**kwargs, "refund_amount_from": 0}))
        self.assertFalse(facts_cache.fee_query_row_passes(row, **{**kwargs, "payment_status": "待审批"}))
        self.assertFalse(facts_cache.fee_query_row_passes(row, **{**kwargs, "unpaid_official": True}))
        self.assertFalse(facts_cache.fee_query_row_passes({**row, "is_internal": True}, **{**kwargs, "external_only": True}))
        data = {"court_name": "上海市黄浦区人民法院"}
        self.assertTrue(refund_case_fee_row_passes(data, 200, "R20", "退费中", refund_status="退费中", court_name="黄浦"))
        self.assertFalse(refund_case_fee_row_passes(data, 200, "R20", "退费中", refund_status="R10"))
        self.assertFalse(refund_case_fee_row_passes(data, 200, "R20", "退费中", refund_amount_from=201))
        self.assertTrue(refund_case_fee_row_passes(data, 200, "R20", "退费中", refund_amount_to=200))


if __name__ == "__main__":
    unittest.main()
