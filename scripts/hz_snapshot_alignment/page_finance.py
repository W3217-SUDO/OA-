"""从原财务主键及分配明细建立当前费用、到账和发票页面投影。"""

from collections import Counter, defaultdict
from decimal import Decimal
from psycopg.types.json import Jsonb
from .common import SOURCE, audit_time, connect, enum_labels, rows, save_report
from ..hz_field_maps import enabled, json_value, mapped_data, text


def money(value):
    return float(value) if value is not None else None


def total(values):
    return sum((Decimal(str(v)) for v in values if v is not None), Decimal(0))


def main():
    report = Counter()
    with connect() as db:
        records = db.execute(
            "SELECT id,module,serial_no,title,customer,owner,department,data->>'migration_source' AS source FROM business_records"
        ).fetchall()
        index = {(r["module"], r["serial_no"]): r for r in records}
        params = {(r["category"], r["code"]): r for r in rows(db, "system_parameters")}
        fee_types = {r["FeeTypeId"]: r for r in rows(db, "BAS_Case_FeeType")}
        fee_status = enum_labels("FAM.AR.CaseFee.CaseFeeStatus")
        invoice_status = enum_labels("FAM.Invoice.InvoiceStatus")
        refund_status = enum_labels("BAS.Type.RefundStatus")
        bases = {1: "官方费用", 2: "代理费", 3: "其他费用", 4: "内部费用", 5: "其他费用", 6: "代理费"}

        def link(data, module, number):
            number = text(number)
            if not number:
                return None
            parent = index.get((module, number))
            if not parent or parent["source"] != SOURCE:
                raise RuntimeError(f"Financial {module} parent is not uniquely mapped")
            data.update(
                {
                    module + "_id": parent["id"],
                    module + "_record_id": parent["id"],
                    module + "_no": number,
                    module + "_title": parent["title"],
                }
            )
            return parent

        def store(module, serial, row, data, title, status, owner, department, customer):
            old = index.get((module, serial))
            if old and old["source"] != SOURCE:
                raise RuntimeError("Financial destination identity is occupied")
            values = (
                title,
                customer,
                status,
                owner,
                department,
                text(row.get("Remark")),
                Jsonb(json_value(data)),
                audit_time(row["CreateTime"]),
                audit_time(row["ChangeTime"] or row["CreateTime"]),
            )
            if old:
                db.execute(
                    "UPDATE business_records SET title=%s,customer=%s,status=%s,owner=%s,department=%s,description=%s,data=%s,created_at=%s,updated_at=%s WHERE id=%s",
                    values + (old["id"],),
                )
                identity = old["id"]
            else:
                identity = db.execute(
                    "INSERT INTO business_records(title,customer,status,owner,department,description,data,created_at,updated_at,module,serial_no) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    values + (module, serial),
                ).fetchone()["id"]
            index[(module, serial)] = {"id": identity, "source": SOURCE}
            return identity

        fees = {}
        for row in rows(db, "FAM_AR_CaseFee"):
            if row["Amount"] is None:
                report["fee_source_amount_missing"] += 1
                continue
            kind = fee_types[row["CaseFeeTypeId"]]
            category = params[("fee_type", text(kind["FeeTypeId"]))]
            base = bases[kind["TypeId"]]
            db.execute(
                "UPDATE system_parameters SET extra=(extra::jsonb||%s)::json WHERE id=%s",
                (Jsonb({"base_fee_type": base, "legacy_source": SOURCE}), category["id"]),
            )
            data = {
                **mapped_data("finance", row),
                "migration_source": SOURCE,
                "legacy_source": SOURCE,
                "source_table": "FAM_AR_CaseFee",
                "legacy_kind": "ar_case_fee",
                "legacy_record": json_value(row),
                "legacy_case_fee_id": row["CaseFeeId"],
                "legacy_case_fee_guid": text(row["CaseFeeGuid"]),
                "source_active": enabled(row["IsActived"]),
                "amount": money(row["Amount"]),
                "fee_type": base,
                "fee_type_id": category["id"],
                "fee_type_code": text(kind["FeeTypeId"]),
                "expense_subtype": kind["FeeTypeName"],
                "expense_scope": "平台" if kind["TypeId"] == 6 else "律所",
                "paid_amount": money(row["PaidAmount"]),
                "received_amount": money(row["CashedAmount"]),
                "invoiced_amount": money(row["InvoicedAmount"]),
                "refund_amount": money(row["RefundAmount"]),
                "refund_requested_amount": money(row["RefundAmount"]),
                "refunded_amount": money(row["RefundedAmount"]),
                "refund_status_label": refund_status.get(text(row["RefundStatus"]), "源状态未记录"),
                "submitted_by": text(row["RequestUser"]),
                "submitted_at": json_value(row["InformDate"]),
                "legacy_status_code": row["CaseFeeStatus"],
            }
            case = link(data, "case", row["CaseNo"])
            if not case:
                raise RuntimeError("Financial case parent is missing")
            link(data, "contract", row["ContractNo"])
            customer = link(data, "customer", row["CustomerNo"])
            status = fee_status.get(text(row["CaseFeeStatus"]), "源状态未记录") if data["source_active"] else "已删除"
            identity = store(
                "finance",
                f"HZ-FEE-{row['CaseFeeId']}",
                row,
                data,
                kind["FeeTypeName"],
                status,
                text(row["RequestUser"]),
                case["department"],
                customer["title"] if customer else case["customer"],
            )
            fees[row["CaseFeeId"]] = {"id": identity, "row": row, "data": data, "title": kind["FeeTypeName"]}
            report["fees_mapped"] += 1
            if data["source_active"]:
                report["fees_active"] += 1

        payment_objects = defaultdict(list)
        for row in rows(db, "FAM_AR_Payment_Object"):
            if enabled(row["IsActived"]):
                payment_objects[row["PaymentId"]].append(row)
        receipt_amounts = defaultdict(Decimal)
        for row in rows(db, "FAM_AR_Payment"):
            if not enabled(row["IsActived"]):
                report["receipts_inactive_preserved_in_history"] += 1
                continue
            allocations = []
            for obj in payment_objects[row["PaymentId"]]:
                fee = fees.get(obj["CaseFeeId"])
                if not fee or text(obj["CaseNo"]) != text(fee["row"]["CaseNo"]):
                    raise RuntimeError("Receipt allocation source fee/case is inconsistent")
                amount = obj["CashedAmount"]
                allocations.append(
                    {
                        "fee_id": fee["id"],
                        "finance_record_id": fee["id"],
                        "case_fee_id": fee["id"],
                        "case_id": fee["data"]["case_id"],
                        "case_no": obj["CaseNo"],
                        "contract_no": fee["data"].get("contract_no", ""),
                        "fee_type": fee["data"]["fee_type"],
                        "amount": money(amount),
                        "payment_method": row["PaymentModeName"],
                        "is_refund": enabled(obj["IsRefund"]),
                        "source_object": json_value(obj),
                    }
                )
                receipt_amounts[obj["CaseFeeId"]] += Decimal(str(amount))
            allocated = total(a["amount"] for a in allocations)
            if row["AppliedAmount"] is None:
                if allocations:
                    raise RuntimeError("Receipt allocation header is missing but detail rows exist")
                report["receipt_source_allocation_not_recorded"] += 1
            elif allocated != Decimal(str(row["AppliedAmount"])):
                raise RuntimeError("Receipt allocation total differs from source header")
            header = {
                "migration_source": SOURCE,
                "source_table": "FAM_AR_Payment",
                "legacy_payment_id": row["PaymentId"],
                "legacy_receipt_no": row["SequenceNo"],
                "source_payload": json_value(row),
            }
            if allocations:
                allocations[0]["source_header"] = header
            else:
                allocations.append({"amount": 0, "source_header": header})
            customer = index.get(("customer", text(row["CustomerNo"])))
            contract = index.get(("contract", text(row["ContractNo"])))
            serial = f"HZ-RCPT-{row['PaymentId']}"
            old = db.execute("SELECT id,source_kind FROM incoming_payments WHERE receipt_no=%s", (serial,)).fetchone()
            if old and old["source_kind"] != SOURCE:
                raise RuntimeError("Receipt destination identity is occupied")
            values = (
                SOURCE,
                serial,
                row["CashedDate"].date(),
                money(row["CashedAmount"]),
                text(row["PayerName"]),
                "源状态未记录",
                customer["title"] if customer else "",
                contract["id"] if contract else None,
                text(row["ContractNo"]),
                "",
                text(row["PaymentModeName"]),
                text(row["Receiver"]),
                float(allocated),
                Jsonb(allocations),
                text(row["Registrant"]),
                text(row["Remark"]),
                audit_time(row["CreateTime"]),
                audit_time(row["ChangeTime"] or row["CreateTime"]),
            )
            db.execute(
                "INSERT INTO incoming_payments(source_kind,receipt_no,received_date,amount,payer_name,status,claimed_customer,contract_record_id,contract_no,case_no,bank_source,claimant,allocated_amount,allocations,operator,remark,created_at,updated_at) VALUES("
                + ",".join(["%s"] * len(values))
                + ") ON CONFLICT(receipt_no) DO UPDATE SET amount=excluded.amount,allocations=excluded.allocations,allocated_amount=excluded.allocated_amount",
                values,
            )
            report["receipts_mapped"] += 1
            report["receipt_allocations_mapped"] += len(payment_objects[row["PaymentId"]])
        for fee_id, fee in fees.items():
            if (
                fee["data"]["source_active"]
                and Decimal(str(fee["row"]["CashedAmount"] or 0)) != receipt_amounts[fee_id]
            ):
                raise RuntimeError("Current fee receipt total differs from original source")

        invoice_objects = defaultdict(list)
        for row in rows(db, "FAM_Invoice_Object"):
            invoice_objects[row["InvoiceId"]].append(row)
        invoice_amounts = defaultdict(Decimal)
        for row in rows(db, "FAM_Invoice"):
            allocations = []
            case_ids = set()
            for obj in invoice_objects[row["InvoiceId"]]:
                if not enabled(obj["IsActived"]):
                    continue
                fee = fees.get(obj["CaseFeeId"])
                if not fee or text(obj["CaseNo"]) != text(fee["row"]["CaseNo"]):
                    raise RuntimeError("Invoice allocation source fee/case is inconsistent")
                allocations.append(
                    {
                        "fee_id": fee["id"],
                        "amount": money(obj["InvoicedAmount"]),
                        "case_id": fee["data"]["case_id"],
                        "case_no": obj["CaseNo"],
                        "source_object_id": obj["SeqId"],
                    }
                )
                case_ids.add(fee["data"]["case_id"])
                if row["InvoiceStatus"] == 5:
                    invoice_amounts[obj["CaseFeeId"]] += Decimal(str(obj["InvoicedAmount"]))
            data = {
                **mapped_data("invoice", row),
                "migration_source": SOURCE,
                "legacy_source": SOURCE,
                "source_table": "FAM_Invoice",
                "legacy_record": json_value(row),
                "legacy_invoice_id": row["InvoiceId"],
                "amount": money(row["InvoiceAmount"]),
                "invoice_no": row["InvoiceNo"],
                "case_fee_ids": list(dict.fromkeys(a["fee_id"] for a in allocations)),
                "case_fee_allocations": allocations,
                "case_ids": sorted(case_ids),
                "invoice_title": row["InvoiceName"],
                "invoice_type": row["InvoiceType"],
                "application_no": row["InvoiceApplicationNo"],
                "application_date": json_value(row["InvoiceApplicationDate"]),
                "applicant": row["InvoiceApplicant"],
                "handler": row["InvoiceResponser"],
                "taxpayer_id": row["CustomerCompanyCode"],
                "invoice_address": row["CustomerBusinessAddress"],
                "invoice_phone": row["CustomerPhone"],
                "bank_name": row["CustomerBankName"],
                "bank_account": row["CustomerBankAccount"],
                "legacy_objects": json_value(invoice_objects[row["InvoiceId"]]),
            }
            link(data, "customer", row["CustomerNo"])
            allocated = total(a["amount"] for a in allocations)
            if allocated != Decimal(str(row["InvoiceAmount"])):
                data["allocation_mapping_state"] = "source_header_allocation_difference"
                report["invoice_source_header_allocation_difference"] += 1
            store(
                "invoice",
                f"HZ-INV-{row['InvoiceId']}",
                row,
                data,
                text(row["InvoiceName"]),
                invoice_status[text(row["InvoiceStatus"])],
                text(row["InvoiceApplicant"]),
                "",
                text(row["CustomerName"]),
            )
            report["invoices_mapped"] += 1
            report["invoice_allocations_mapped"] += len(allocations)
        for fee_id, fee in fees.items():
            if (
                fee["data"]["source_active"]
                and Decimal(str(fee["row"]["InvoicedAmount"] or 0)) != invoice_amounts[fee_id]
            ):
                db.execute(
                    "UPDATE business_records SET data=(data::jsonb||%s)::json WHERE id=%s",
                    (
                        Jsonb(
                            {
                                "invoice_mapping_state": "source_summary_allocation_difference",
                                "verified_invoice_allocation_amount": str(invoice_amounts[fee_id]),
                            }
                        ),
                        fee["id"],
                    ),
                )
                report["fee_source_invoice_summary_difference"] += 1
        db.commit()
    save_report("page-finance-report.json", dict(report))


if __name__ == "__main__":
    main()
