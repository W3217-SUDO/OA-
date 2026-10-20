"""客户联系人、知识产权客户与案件阶段的实际页面投影。"""

from collections import defaultdict
from psycopg.types.json import Jsonb
from .common import connect, rows, save_report
from ..hz_field_maps import json_value, text, enabled, mapped_data
from .sql_projection import project, string, active, record_views, business_join, user_join, state


def customer_contacts(db, report):
    customers = {r["serial_no"]: r for r in db.execute("SELECT * FROM hz_records WHERE module='customer'").fetchall()}
    source_customers = {text(r["CustomerId"]): r for r in rows(db, "CRM_Customer")}
    by_customer = defaultdict(list)
    for row in rows(db, "CRM_Customer_Contacts"):
        source_parent = source_customers.get(text(row["CustomerId"]))
        parent_no = text(source_parent["CustomerNo"]) if source_parent else text(row["CustomerNo"])
        customer = customers.get(parent_no)
        if not customer:
            report["contacts_parent_missing"] = report.get("contacts_parent_missing", 0) + 1
            continue
        snapshot = {k: v for k, v in row.items() if "password" not in k.lower()}
        data = {
            **mapped_data("contact", snapshot),
            "legacy_record": json_value(snapshot),
            "id": text(row["ContactsGuid"]) or f"HZ-CONTACT-{row['ContactsId']}",
            "name": text(row["Contacts"]),
            "title": text(row["ContactsTitle"]),
            "mobile": text(row["Mobilephone"]),
            "phone": text(row["Mobilephone"]),
            "office_phone": text(row["OfficePhone"]),
            "home_phone": text(row["HomePhone"]),
            "email": text(row["Email"]),
            "address": text(row["ContactAddress"]),
            "postal_code": text(row["ContactZip"]),
            "fax": text(row["ContactFax"]),
            "is_primary": enabled(row["IsDefault"]),
            "position": text(row["ContactsTitle"]),
            "project_role": text(row["ProjectRole"]),
            "im_account": text(row["IM"]),
            "is_valid": enabled(row["IsActived"]),
            "is_active": enabled(row["IsActived"]),
            "is_contacted": enabled(row["IsContacted"]),
            "is_people_base": enabled(row["IsPeopleBASE"]),
            "is_received_email": enabled(row["IsReceivedEmail"]),
            "created_at": json_value(row["CreateTime"]),
            "updated_at": json_value(row["ChangeTime"]),
        }
        by_customer[customer["id"]].append(data)
    for customer_id, contacts in by_customer.items():
        db.execute(
            "UPDATE business_records SET data=(data::jsonb || %s)::json WHERE id=%s",
            (Jsonb({"contacts": contacts}), customer_id),
        )
    report["contacts_mapped"] = sum(map(len, by_customer.values()))
    db.commit()
    target = "legacy_customer_history_contacts"
    report[target] = project(
        db,
        target,
        "CRM_Customer_Contacts",
        {
            "source_primary_key": string("ContactsId"),
            "legacy_contact_guid": string("ContactsGuid"),
            "legacy_customer_id": string("CustomerId"),
            "legacy_customer_no": string("CustomerNo"),
            "customer_record_id": "r.id",
            "parent_mapping_status": state("r"),
            "orphan_reason": "CASE WHEN r.id IS NULL THEN 'source_customer_missing' ELSE '' END",
            "contact_name": string("Contacts"),
            "title": string("ContactsTitle"),
            "mobile_phone": string("Mobilephone"),
            "email": string("Email"),
            "is_active": active(),
            "photo_recovery_status": "CASE WHEN COALESCE(s.\"PhotoFileName\",'')='' THEN 'not_declared' ELSE 'physical_not_verified' END",
            "source_payload": "(to_jsonb(s)-'Password'-'OrgPassword')::json",
        },
        ["source_system", "source_table", "source_primary_key"],
        'LEFT JOIN "CRM_Customer" cc ON cc."CustomerId"=s."CustomerId" '
        'LEFT JOIN hz_records r ON r.module=\'customer\' AND r.serial_no=COALESCE(cc."CustomerNo",s."CustomerNo")',
    )


def histories(db, report):
    report["coordinators"] = project(
        db,
        "legacy_customer_history_coordinators",
        "CRM_Customer_Coordinator",
        {
            "source_primary_key": string("CoordinatorId"),
            "legacy_customer_id": string("CustomerId"),
            "legacy_customer_no": string("CustomerNo"),
            "customer_record_id": "r.id",
            "parent_mapping_status": state("r"),
            "source_username": string("StaffName"),
            "mapped_user_id": "u.id",
            "user_mapping_status": state("u"),
            "relation_type_id": string("TypeId"),
            "source_payload": "row_to_json(s)",
        },
        ["source_system", "source_table", "source_primary_key"],
        business_join("customer", "CustomerNo") + " " + user_join("StaffName"),
    )
    report["customer_events"] = project(
        db,
        "legacy_customer_history_events",
        "CRM_Customer_Event",
        {
            "source_primary_key": string("EventId"),
            "legacy_customer_guid": string("CustomerGuid"),
            "customer_record_id": "r.id",
            "parent_mapping_status": state("r"),
            "operator_username": string("Operator"),
            "mapped_user_id": "u.id",
            "user_mapping_status": state("u"),
            "operated_at": 's."OperateTime"',
            "content": string("Content"),
            "is_active": active(),
            "source_payload": "row_to_json(s)",
        },
        ["source_system", "source_table", "source_primary_key"],
        "LEFT JOIN hz_records r ON r.module='customer' AND r.data->>'customer_guid'=s.\"CustomerGuid\" "
        + user_join("Operator"),
    )
    report["case_phases"] = project(
        db,
        "legacy_case_phase_histories",
        "Legal_Case_Phase",
        {
            "legacy_phase_id": 's."Id"',
            "case_record_id": "r.id",
            "legacy_case_id": 's."CaseId"',
            "legacy_case_no": string("CaseNo"),
            "legacy_last_phase_id": 's."LastPhaseId"',
            "legacy_phase_code": string("PhaseId"),
            "phase_parameter_id": "p.id",
            "case_mapping_state": state("r"),
            "phase_mapping_state": state("p"),
            "content": string("Content"),
            "is_active": string("IsActived"),
            "created_by": string("CreateUser"),
            "legacy_created_at": 's."CreateTime"',
            "legacy_updated_at": 's."ChangeTime"',
            "source_snapshot": "row_to_json(s)",
        },
        ["legacy_phase_id"],
        business_join("case", "CaseNo")
        + " LEFT JOIN system_parameters p ON p.category='case_phase' AND p.code=s.\"PhaseId\"::text",
    )
    report["case_participants"] = project(
        db,
        "legacy_case_participant_relations",
        "Legal_Case_Participant",
        {
            "case_record_id": "r.id",
            "user_id": "u.id",
            "legacy_case_no": string("CaseNo"),
            "legacy_staff_name": string("StaffName"),
            "case_mapping_state": state("r"),
            "user_mapping_state": state("u"),
            "source_snapshot": "row_to_json(s)",
        },
        ["legacy_case_no", "legacy_staff_name"],
        business_join("case", "CaseNo") + " " + user_join("StaffName"),
    )


def ipr_customers(db, report):
    joins = (
        'JOIN "IPR_Case" c ON c."CaseId"=s."CaseId" JOIN "CRM_Customer" cc ON cc."CustomerId"=s."CustomerId" '
        + "JOIN hz_records r ON r.module='ipr_case' AND r.serial_no=c.\"CaseNo\" JOIN hz_records cr ON cr.module='customer' AND cr.serial_no=cc.\"CustomerNo\""
    )
    report["ipr_customer_links"] = project(
        db,
        "ipr_case_customers",
        "IPR_Case_Customer",
        {
            "case_record_id": "r.id",
            "customer_record_id": "cr.id",
            "is_primary": 'c."CustomerId"=s."CustomerId"',
            "sorting_index": 's."SortingIndex"',
            "created_by": string("CreateUser"),
            "created_at": 'COALESCE(s."CreateTime",r.created_at)',
        },
        ["case_record_id", "customer_record_id"],
        joins,
    )
    report["ipr_links_source_unresolved"] = db.execute(
        'SELECT count(*) AS n FROM "IPR_Case_Customer" s LEFT JOIN "CRM_Customer" c ON c."CustomerId"=s."CustomerId" LEFT JOIN "IPR_Case" ic ON ic."CaseId"=s."CaseId" WHERE c."CustomerId" IS NULL OR ic."CaseId" IS NULL'
    ).fetchone()["n"]


def official(db, report):
    joins = (
        "JOIN hz_records r ON r.module='official_outgoing' AND r.serial_no=s.\"OfficialDocumentNo\" "
        + business_join("case", "CaseNo", "ca")
        + " "
        + business_join("contract", "ContractNo", "co")
    )
    report["official_documents"] = project(
        db,
        "official_outgoing_documents",
        "AWS_OfficialDocument",
        {
            "record_id": "r.id",
            "official_no": string("OfficialDocumentNo"),
            "source_type": "CASE WHEN ca.id IS NOT NULL THEN 'case' WHEN co.id IS NOT NULL THEN 'contract' ELSE '' END",
            "source_record_id": "COALESCE(ca.id,co.id)",
            "created_by": string("CreateUser"),
            "created_at": 'COALESCE(s."CreateTime",r.created_at)',
        },
        ["record_id"],
        joins,
    )


def main():
    report = {}
    with connect() as db:
        record_views(db)
        customer_contacts(db, report)
        histories(db, report)
        ipr_customers(db, report)
        official(db, report)
    save_report("relations-report.json", report)


if __name__ == "__main__":
    main()
