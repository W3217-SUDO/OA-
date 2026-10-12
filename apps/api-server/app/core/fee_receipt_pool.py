"""本次授权费用池的轻量收款关联，不携带金额或展示快照。"""
from dataclasses import dataclass


def unique_legacy_fee_ids(entries):
    candidates = {}
    for fee_id, values in entries:
        for value in values:
            try:
                legacy_id = int(value or 0)
            except (TypeError, ValueError):
                legacy_id = 0
            if legacy_id:
                candidates.setdefault(legacy_id, set()).add(fee_id)
    return {key: next(iter(ids)) for key, ids in candidates.items() if len(ids) == 1}


@dataclass
class FeeReceiptBinding:
    fee_ids: set
    legacy_fee_ids: dict
    case_ids: set
    case_nos: set
    case_ids_by_fee: dict
    case_nos_by_fee: dict

    def group_by_case(self, cases_by_id, cases_by_no):
        grouped = {}
        for fee_id, number in self.case_nos_by_fee.items():
            case = cases_by_id.get(self.case_ids_by_fee[fee_id]) or cases_by_no.get(number)
            linked_no = case.serial_no if case else number
            if linked_no:
                grouped.setdefault(linked_no, []).append(fee_id)
        return grouped


@dataclass
class FeeReceiptPool:
    rows: list
    all_record_ids: set

    @classmethod
    def from_rows(cls, rows):
        rows = list(rows)
        return cls(rows, {row.id for row in rows})

    def with_rows(self, rows):
        # 合并行为与原 finances_by_id.update 一致，既有位置不变，补读追加。
        merged = {row.id: row for row in self.rows}
        merged.update((row.id, row) for row in rows)
        return type(self).from_rows(merged.values())

    def receipt_binding(self):
        active = [row for row in self.rows if row.status != "已删除"]
        case_ids, case_nos = set(), set()
        case_ids_by_fee, case_nos_by_fee = {}, {}
        for row in active:
            raw_id, raw_no = row.links[0], row.links[2]
            # 保留原来的 int 异常，不将损坏的案件编号吞成零。
            case_id = int(raw_id or 0)
            case_no = str(raw_no or "")
            case_ids_by_fee[row.id] = case_id
            case_nos_by_fee[row.id] = case_no
            if raw_id:
                case_ids.add(case_id)
            if raw_no:
                case_nos.add(case_no)
        return FeeReceiptBinding(
            {row.id for row in active},
            unique_legacy_fee_ids((row.id, row.links[6:8]) for row in active),
            case_ids, case_nos, case_ids_by_fee, case_nos_by_fee,
        )
