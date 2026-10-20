"""恢复页面真正读取的字典及类型关系，只转换源表明确声明的关联。"""

from collections import Counter
from .common import connect, rows, enum_labels, ACTOR, save_report
from .dictionaries import upsert
from ..hz_field_maps import text, enabled, json_value, split_people
from .sql_projection import project, record_views


def main():
    report = Counter()
    with connect() as db:
        for code, label in enum_labels("CRM.Customer.CustomerTypeId").items():
            upsert(db, "customer_type", code, label, {"legacy_id": code, "source_enum": "CustomerTypeId"})
        specs = [
            ("case_file_type", "BAS_Case_FileType", "FileTypeId", "FileTypeName"),
            ("fee_type", "BAS_Case_FeeType", "FeeTypeId", "FeeTypeName"),
            ("ipr_case_file_type", "IPR_Case_FileType", "FileTypeId", "FileTypeName"),
            ("ipr_fee_type", "IPR_Case_FeeType", "FeeTypeId", "FeeTypeName"),
            ("notary_office", "BAS_NotaryOffice", "NotaryOfficeId", "NotaryOfficeName"),
            ("court_officer", "BAS_Court_Officer", "OfficerId", "OfficerName"),
        ]
        fee_labels = enum_labels("CaseFeeTypeId")
        for category, table, key, label in specs:
            for row in rows(db, table):
                extra = {"legacy_id": row[key], "source_table": table, "legacy_record": json_value(row)}
                if "FileType" in table:
                    extra.update(
                        is_official=enabled(row.get("IsOfficeFileType")),
                        allow_repeat=enabled(row.get("CanRepeatUpload")),
                        can_batch_upload=enabled(row.get("CanBatchUpload")),
                        hedging_file_type_codes=split_people(row.get("HedgingFileTypeId")),
                        hedging_fee_type_codes=split_people(row.get("HedgingFeeTypeId")),
                        case_type_code=text(row.get("CaseTypeId")),
                    )
                if "FeeType" in table:
                    extra.update(
                        legacy_group_code=text(row.get("TypeId")),
                        fee_group=fee_labels.get(text(row.get("TypeId")), ""),
                        case_type_code=text(row.get("CaseTypeId")),
                        is_invoiced=enabled(row.get("IsInvoiced")),
                    )
                if category == "notary_office":
                    extra.update(address=row.get("Address"), phone=row.get("Telphone"))
                if category == "court_officer":
                    extra.update(
                        court_code=text(row.get("CourtNo")),
                        email=row.get("Email"),
                        phone=row.get("Phone"),
                        role_mapping_state="source_role_not_recorded",
                    )
                upsert(
                    db, category, text(row[key]), text(row[label]), extra, int(row[key]), enabled(row.get("IsActived"))
                )
                report[category] += 1
            db.commit()
        parameters = {(r["category"], r["code"]): r["id"] for r in rows(db, "system_parameters")}

        def link(target, keys, values):
            if any(v is None for v in values):
                report[target + "_unresolved"] += 1
                return
            db.execute(
                "INSERT INTO "
                + target
                + " ("
                + ",".join(keys)
                + ",created_by,updated_by) VALUES ("
                + ",".join(["%s"] * (len(keys) + 2))
                + ") ON CONFLICT ("
                + ",".join(keys)
                + ") DO NOTHING",
                (*values, ACTOR, ACTOR),
            )
            report[target] += 1

        for row in rows(db, "BAS_Case_Phase"):
            link(
                "case_type_case_phase_relations",
                ("case_type_id", "case_phase_id"),
                (
                    parameters.get(("case_type", text(row["CaseTypeId"]))),
                    parameters.get(("case_phase", text(row["CasePhaseId"]))),
                ),
            )
        for row in rows(db, "BAS_Case_FileType"):
            if row["CaseTypeId"] is not None:
                link(
                    "case_type_file_type_relations",
                    ("case_type_id", "file_type_id"),
                    (
                        parameters.get(("case_type", text(row["CaseTypeId"]))),
                        parameters.get(("case_file_type", text(row["FileTypeId"]))),
                    ),
                )
            for fee in split_people(row["HedgingFeeTypeId"]):
                link(
                    "case_file_type_fee_type_relations",
                    ("file_type_id", "fee_type_id"),
                    (parameters.get(("case_file_type", text(row["FileTypeId"]))), parameters.get(("fee_type", fee))),
                )
        for row in rows(db, "IPR_CaseType_CaseFileType_CaseFeeType"):
            values = (
                parameters.get(("ipr_case_type", text(row["CaseTypeId"]))),
                parameters.get(("ipr_case_file_type", text(row["CaseFileTypeId"]))),
                parameters.get(("ipr_fee_type", text(row["CaseFeeTypeId"]))),
            )
            if all(v is not None for v in values):
                link("ipr_case_type_file_fee_type_rules", ("case_type_id", "file_type_id", "fee_type_id"), values)
            else:
                report["ipr_rule_unresolved"] += 1
        db.commit()
        record_views(db)
        report["ipr_type_assignments"] = project(
            db,
            "ipr_case_type_assignments",
            "IPR_Case",
            {
                "case_record_id": "r.id",
                "case_type_id": "p.id",
                "assigned_by": "COALESCE(s.\"CreateUser\",'')",
                "assigned_at": 's."CreateTime"',
            },
            ["case_record_id"],
            "JOIN hz_records r ON r.module='ipr_case' AND r.serial_no=s.\"CaseNo\" JOIN system_parameters p ON p.category='ipr_case_type' AND p.code=s.\"CaseTypeId\"::text",
            's."CreateTime" IS NOT NULL',
        )
    save_report("page-dictionary-report.json", dict(report))


if __name__ == "__main__":
    main()
