"""一般结算按用户原件生成到账、案件及双区块清单。"""

from decimal import Decimal

from app.areas.finance.excel_templates import FinanceWorkbook


def amount_sum(details, key):
    values = [detail.get(key) for detail in details]
    return None if any(value is None for value in values) else float(sum((Decimal(str(value)) for value in values), Decimal(0)))


def case_values(detail):
    values = [detail.get(key) for key in ("case_no", "case_stage", "fee_type", "fee_total_amount", "fee_allocated_amount",
        "current_amount", "allocated_at", "settlement_amount", "archive_fee", "customer", "hearing_lawyer", "assistant", "contract_no")]
    if values[6]:
        values[6] = str(values[6])[:10]
    return values


def render_general_settlement_export(kind, records, export_date):
    template_id = {"receipt": "F51", "case": "F53", "settlement": "F55"}.get(kind)
    if template_id is None:
        raise ValueError(f"不支持的结算导出模板: {kind}")
    workbook = FinanceWorkbook(template_id)
    index = 0
    if kind != "settlement":
        workbook.header()
        index = 1
    for record in records:
        data = record["data"]
        details = data.get("allocation_details") or []
        if kind == "case":
            for detail in details:
                workbook.row(index, case_values(detail))
                index += 1
        elif kind == "receipt":
            payment_start = index
            cases = {}
            for detail in details:
                cases.setdefault(str(detail.get("case_id") or detail.get("case_no")), []).append(detail)
            for case_details in cases.values():
                case_start = index
                detail = case_details[0]
                for fee_kind, label in (("official", "代收代付（官费）"), ("agency", "收入（代理费）"), ("other", "代收代付（其他费用）")):
                    group = [item for item in case_details if item.get("kind") == fee_kind]
                    if not group:
                        continue
                    values = [data.get("received_date"), label, amount_sum(group, "current_amount"), data.get("receipt_amount"),
                        data.get("bank_source"), data.get("payer_name"), detail.get("court_case_no"), detail.get("case_no"),
                        detail.get("source_person"), detail.get("hearing_lawyer"), detail.get("assistant"), detail.get("file_no"),
                        detail.get("archive_no"), amount_sum(case_details, "archive_fee"), detail.get("customer"), detail.get("invoice_dates"),
                        detail.get("invoice_titles"), detail.get("invoice_numbers"), detail.get("invoice_amount"), detail.get("invoice_extra_amount"), ""]
                    workbook.row(index, values)
                    index += 1
                if index > case_start:
                    workbook.merge(case_start, index - 1, tuple(range(8, 21)), values)
            if index > payment_start:
                workbook.merge(payment_start, index - 1, (0, 3, 4), values)
        else:
            workbook.header(index)
            index += 1
            groups = {}
            for detail in details:
                groups.setdefault(str(detail.get("case_id") or detail.get("case_no")), []).append(detail)
            for group in groups.values():
                start = index
                detail = group[0]
                common = [data.get("received_date"), None, "知产中心", data.get("payer_name"), data.get("receipt_amount"), None,
                    detail.get("court_case_no"), detail.get("case_no"), detail.get("assistant"), "", "", "", ""]
                for fee_kind, label in (("official", "代收代付（官费）"), ("agency", "收入（代理费）"), ("other", "权利人分成（其他）")):
                    values = list(common)
                    values[1] = label
                    values[5] = amount_sum([item for item in group if item.get("kind") == fee_kind], "current_amount") if data["amount_visible"] else None
                    workbook.row(index, values, 1 + index - start)
                    index += 1
                workbook.merge(start, index - 1, (0, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12), common)
            workbook.header(index, 4)
            index += 1
            for detail in details:
                workbook.row(index, case_values(detail), 5)
                index += 1
    names = {"receipt": "到账清单", "case": "案件清单", "settlement": "结算清单"}
    return workbook.content(), f"{names[kind]}-{export_date}.xls", workbook.template.name
