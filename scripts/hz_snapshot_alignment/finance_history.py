"""财务原始状态和金额的只读账本投影，不触发新版付款审批。"""

from psycopg import sql
from .common import connect, enum_labels, save_report
from .sql_projection import project, string, active, record_views, business_join

HEADERS = [
    ("FAM_AR_CaseFee", "CaseFeeId", "case_fee", "CaseFeeStatus", "Amount", "FAM.AR.CaseFee.CaseFeeStatus"),
    ("FAM_AP_Payment", "PaymentId", "ap_payment", "PaymentStatus", "PaidAmount", "FAM.AP.Payment.PaymentStatus"),
    (
        "FAM_AR_Payment",
        "PaymentId",
        "ar_payment",
        "PaymentStatus",
        "CashedAmount",
        "FAM.AR.ReceivedPayment.PaymentStatus",
    ),
    ("FAM_Invoice", "InvoiceId", "invoice", "InvoiceStatus", "InvoiceAmount", "FAM.Invoice.InvoiceStatus"),
    ("FAM_InternalFee", "InternalFeeId", "internal_fee", None, "Amount", None),
    (
        "FAM_InternalFee_Payment",
        "PaymentId",
        "internal_payment",
        "PaymentStatus",
        "PaidAmount",
        "FAM.InternalFee.Payment.PaymentStatus",
    ),
]


def columns(db, table):
    return {
        r["column_name"]
        for r in db.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name=%s", (table,)
        ).fetchall()
    }


def status_label(db, enum, column):
    labels = enum_labels(enum)
    clauses = " ".join(
        "WHEN " + sql.Literal(code).as_string(db) + " THEN " + sql.Literal(label).as_string(db)
        for code, label in labels.items()
    )
    return f'CASE s."{column}"::text {clauses} ELSE CASE WHEN s."{column}" IS NULL THEN \'源状态未记录\' ELSE \'源状态\'||s."{column}"::text END END'


def main():
    report = {}
    with connect() as db:
        record_views(db)
        for table, identifier, kind, status, amount, enum in HEADERS:
            fields = columns(db, table)
            mapping = {
                "source_table": repr(table),
                "legacy_id": string(identifier),
                "record_kind": repr(kind),
                "status_code": string(status) if status else "''",
                "status_label": status_label(db, enum, status) if enum else "'源表未设状态字段'",
                "primary_amount": f'COALESCE(s."{amount}",0)',
                "is_active": active(),
                "source_payload": "row_to_json(s)",
                "mapping_status": "CASE WHEN c.id IS NOT NULL OR ca.id IS NOT NULL OR co.id IS NOT NULL THEN 'mapped' ELSE 'source_parent_missing' END",
            }
            joins = []
            for module, source, alias in [
                ("customer", "CustomerNo", "c"),
                ("case", "CaseNo", "ca"),
                ("contract", "ContractNo", "co"),
            ]:
                if source in fields:
                    joins.append(business_join(module, source, alias))
                    mapping["legacy_" + module + "_no"] = string(source)
                    mapping[module + "_record_id"] = alias + ".id"
                else:
                    joins.append(f"LEFT JOIN hz_records {alias} ON FALSE")
            report[table] = project(
                db, "legacy_finance_records", table, mapping, ["source_table", "legacy_id"], " ".join(joins)
            )
        specs = [
            ("FAM_AP_Payment_Object", "FAM_AP_Payment", "PaymentId", "PaidAmount", "ap_payment"),
            ("FAM_AR_Payment_Object", "FAM_AR_Payment", "PaymentId", "CashedAmount", "ar_payment"),
            ("FAM_Invoice_Object", "FAM_Invoice", "InvoiceId", "InvoicedAmount", "invoice"),
            (
                "FAM_InternalFee_Payment_Object",
                "FAM_InternalFee_Payment",
                "PaymentId",
                "PaidAmount",
                "internal_payment",
            ),
        ]
        for table, parent, parent_id, amount, kind in specs:
            fields = columns(db, table)
            mapping = {
                "source_table": repr(table),
                "legacy_key": string("SeqId"),
                "parent_source_table": repr(parent),
                "parent_legacy_id": string(parent_id),
                "legacy_finance_record_id": "p.id",
                "orphan_reason": "CASE WHEN p.id IS NULL THEN 'source_header_missing' ELSE '' END",
                "allocation_kind": repr(kind),
                "legacy_case_id": string("CaseId"),
                "legacy_case_no": string("CaseNo"),
                "legacy_case_fee_id": string("CaseFeeId") if "CaseFeeId" in fields else "''",
                "case_record_id": "r.id",
                "mapping_status": "CASE WHEN r.id IS NULL THEN 'source_case_missing' ELSE 'mapped' END",
                "amount": f'COALESCE(s."{amount}",0)',
                "is_active": active(),
                "source_payload": "row_to_json(s)",
            }
            for key, column in [
                ("prepaid_amount", "PrePaidAmount"),
                ("settlement_amount", "SettlementAmount"),
                ("archive_amount", "ArchiveAmount"),
            ]:
                if column in fields:
                    mapping[key] = f'COALESCE(s."{column}",0)'
            if "IsRefund" in fields:
                mapping["is_refund"] = active("IsRefund")
            joins = (
                f"LEFT JOIN legacy_finance_records p ON p.source_table='{parent}' AND p.legacy_id=s.\"{parent_id}\"::text "
                + business_join("case", "CaseNo")
            )
            report[table] = project(
                db, "legacy_finance_allocations", table, mapping, ["source_table", "legacy_key"], joins
            )
        for table, parent, parent_id, kind in [
            ("FAM_AP_Payment_Audit", "FAM_AP_Payment", "PaymentId", "ap_payment"),
            ("FAM_InternalFee_Payment_Audit", "FAM_InternalFee_Payment", "PaymentId", "internal_payment"),
            ("FAM_Invoice_Audit", "FAM_Invoice", "InvoiceId", "invoice"),
        ]:
            mapping = {
                "source_table": repr(table),
                "legacy_id": string("AuditId"),
                "parent_source_table": repr(parent),
                "parent_legacy_id": string(parent_id),
                "legacy_finance_record_id": "p.id",
                "audit_kind": repr(kind),
                "orphan_reason": "CASE WHEN p.id IS NULL THEN 'source_header_missing' ELSE '' END",
                "audit_status_code": string("AuditStatus"),
                "audit_flow_id": string("AuditFlowId"),
                "audit_flow_node_id": string("AuditFlowNodeId"),
                "audit_round_id": string("AuditRoundId"),
                "auditor": string("Auditor"),
                "audit_date": 's."AuditDate"',
                "audit_content": string("AuditContent"),
                "source_payload": "row_to_json(s)",
            }
            joins = f"LEFT JOIN legacy_finance_records p ON p.source_table='{parent}' AND p.legacy_id=s.\"{parent_id}\"::text"
            report[table] = project(db, "legacy_finance_audits", table, mapping, ["source_table", "legacy_id"], joins)
        # 此源表没有独立主键；相同原行按稳定序号分别保留，不能合并丢行。
        db.execute(
            'CREATE TEMP VIEW hz_invoice_files AS SELECT f.*,md5(to_jsonb(f)::text)||\':\'||row_number() OVER(PARTITION BY to_jsonb(f)::text ORDER BY "InvoiceId")::text AS migration_row_key FROM "FAM_Invoice_File" f'
        )
        mapping = {
            "legacy_finance_record_id": "p.id",
            "parent_legacy_id": string("InvoiceId"),
            "legacy_key": "s.migration_row_key",
            "orphan_reason": "CASE WHEN p.id IS NULL THEN 'source_header_missing' ELSE '' END",
            "legacy_case_fee_id": string("CaseFeeId"),
            "filename": string("InvoiceFileName"),
            "size_bytes": 'COALESCE(s."InvoiceFileSize",0)',
            "file_amount": 'COALESCE(s."InvoiceAmount",0)',
            "invoice_date": 's."InvoiceDate"',
            "is_active": active(),
            "physical_file_verified": "FALSE",
            "source_payload": "(to_jsonb(s)-'migration_row_key')::json",
        }
        report["invoice_files"] = project(
            db,
            "legacy_finance_files",
            "hz_invoice_files",
            mapping,
            ["legacy_finance_record_id", "legacy_key"],
            "LEFT JOIN legacy_finance_records p ON p.source_table='FAM_Invoice' AND p.legacy_id=s.\"InvoiceId\"::text",
        )
    save_report("finance-history-report.json", report)


if __name__ == "__main__":
    main()
