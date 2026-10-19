"""回款页面“无实际筛选”判定必须与 matches_incoming_filters 的跳过规则一致。"""

from datetime import date
from types import SimpleNamespace
from unittest import TestCase

from app.areas.finance.incoming_query import has_effective_incoming_filters, matches_incoming_filters


def _payment(**overrides):
    values = {
        "received_date": date(2025, 5, 6), "bank_reference": "REF-1", "claimed_customer": "客户甲",
        "payer_name": "付款方", "status": "已分配", "contract_no": "HT-1", "allocations": [],
        "source_kind": "manual", "remark": "", "payment_method": "", "legacy_payment_method": None,
        "local_allocation_summary": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class EffectiveIncomingFiltersTest(TestCase):
    def test_empty_and_placeholder_values_are_not_effective(self):
        for view in ("finance-receipts-manage", "finance-receipts-claim", "finance-receipts-query", "finance-receipts-icbc"):
            for filters in ({}, {"routeField1": ""}, {"routeField1": None}, {"routeField1": "请选择"}, {"routeField1": "全部"}):
                self.assertFalse(has_effective_incoming_filters(view, filters), (view, filters))

    def test_empty_date_range_is_not_effective_on_each_view_date_column(self):
        for view, key in (("finance-receipts-manage", "routeField0"), ("finance-receipts-icbc", "routeField2"),
                          ("finance-receipts-query", "routeField9")):
            self.assertFalse(has_effective_incoming_filters(view, {key: [None, None]}))
            self.assertFalse(has_effective_incoming_filters(view, {key: ["", ""]}))
            self.assertTrue(has_effective_incoming_filters(view, {key: ["2025-01-01", None]}))

    def test_query_fee_type_list(self):
        view = "finance-receipts-query"
        self.assertFalse(has_effective_incoming_filters(view, {"routeField10": []}))
        self.assertFalse(has_effective_incoming_filters(view, {"routeField10": ["全部"]}))
        self.assertTrue(has_effective_incoming_filters(view, {"routeField10": ["官费"]}))
        self.assertTrue(has_effective_incoming_filters(view, {"routeField10": "官费"}))

    def test_real_text_filter_is_effective(self):
        self.assertTrue(has_effective_incoming_filters("finance-receipts-manage", {"routeField2": "客户"}))
        self.assertTrue(has_effective_incoming_filters("finance-receipts-query", {"routeField11": "已分配"}))

    def test_non_effective_filters_never_exclude_a_row(self):
        """判定为无实际筛选的条件，逐行匹配时也必须全部通过。"""
        cases = [
            ("finance-receipts-manage", {"routeField0": [None, None], "routeField1": "", "routeField2": "请选择"}),
            ("finance-receipts-query", {"routeField8": "全部", "routeField11": "全部", "routeField10": [], "routeField9": ["", ""]}),
            ("finance-receipts-icbc", {"routeField2": [None, None], "routeField3": "请选择"}),
        ]
        rows = [_payment(), _payment(received_date=None, payer_name=None, status="待认领")]
        for view, filters in cases:
            self.assertFalse(has_effective_incoming_filters(view, filters))
            for row in rows:
                self.assertTrue(matches_incoming_filters(row, view, filters, {}, {}), (view, filters))
