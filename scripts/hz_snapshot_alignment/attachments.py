"""只恢复附件元数据和原关联，不把未核实的 OSS 对象伪装成本地文件。"""

from .common import connect, save_report
from .sql_projection import project, string, active, record_views, business_join, user_join, state


def main():
    report = {}
    with connect() as db:
        record_views(db)
        report["customer_files"] = project(
            db,
            "legacy_customer_history_files",
            "CRM_Customer_File",
            {
                "source_primary_key": string("FileId"),
                "legacy_file_guid": string("FileGuid"),
                "legacy_customer_guid": string("CustomerGuid"),
                "customer_record_id": "r.id",
                "parent_mapping_status": state("r"),
                "orphan_reason": "CASE WHEN r.id IS NULL THEN 'source_customer_missing' ELSE '' END",
                "original_name": string("FileName"),
                "source_path": string("FilePath"),
                "declared_size_bytes": 'COALESCE(s."FileSize",0)',
                "is_license": active("IsLicense"),
                "is_active": active(),
                "uploader_username": string("UploadUser"),
                "mapped_user_id": "u.id",
                "user_mapping_status": state("u"),
                "uploaded_at": 's."UploadTime"',
                "physical_recovery_status": "'physical_not_verified'",
                "source_payload": "row_to_json(s)",
            },
            ["source_system", "source_table", "source_primary_key"],
            "LEFT JOIN hz_records r ON r.module='customer' AND r.data->>'customer_guid'=s.\"CustomerGuid\" "
            + user_join("UploadUser"),
        )
        report["case_files"] = project(
            db,
            "legacy_case_attachment_relations",
            "Legal_Case_File",
            {
                "legacy_file_id": 's."FileId"',
                "case_record_id": "r.id",
                "legacy_case_id": 's."CaseId"',
                "legacy_case_no": string("CaseNo"),
                "mapping_state": "CASE WHEN r.id IS NULL THEN 'source_case_missing' ELSE 'physical_not_verified' END",
                "source_path": string("FullPath"),
                "source_available": "FALSE",
                "source_snapshot": "row_to_json(s)",
            },
            ["legacy_file_id"],
            business_join("case", "CaseNo"),
        )
        specs = [
            ("FCM_Contract_File", "ContractGuid", "FilePath", "IsActived"),
            ("AWS_OfficialDocument_File", "OfficialDocumentGuid", "FilePath", "IsActived"),
            ("IPR_Case_File", "CaseNo", "FullPath", "Actived"),
            ("Legal_Investigation_Clue_File", "ClueGuid", "FullPath", "IsActived"),
            ("Legal_Investigation_Clue_Evidence_File", "EvidenceGuid", "FullPath", "IsActived"),
        ]
        for table, parent, path, flag in specs:
            fields = {
                r["column_name"]
                for r in db.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name=%s", (table,)
                ).fetchall()
            }
            if parent not in fields or path not in fields or flag not in fields:
                raise ValueError(f"{table} file schema is inconsistent with the audited mapping")
            mapping = {
                "source_system": "'legacy_crm'",
                "legacy_entity_type": repr(table),
                "legacy_file_id": 's."FileId"',
                "file_name": string("FileName"),
                "legacy_declared_size_bytes": 's."FileSize"',
                "legacy_file_path": string(path),
                "legacy_is_active": active(flag),
                "source_physical_exists": "FALSE",
                "source_recovery_status": "'physical_not_verified'",
                "source_payload": "row_to_json(s)",
                "legacy_parent_tuple": f"json_build_object('{parent}',s.\"{parent}\")",
            }
            if "FileGuid" in fields:
                mapping["legacy_file_guid"] = string("FileGuid")
            if parent.endswith("Guid"):
                mapping["legacy_parent_guid"] = string(parent)
            else:
                mapping["legacy_parent_no"] = string(parent)
            if "CaseId" in fields:
                mapping["legacy_parent_id"] = 's."CaseId"'
            report[table] = project(
                db,
                "legacy_historical_attachments",
                table,
                mapping,
                ["source_system", "legacy_entity_type", "legacy_file_id"],
            )
    save_report("attachment-report.json", report)


if __name__ == "__main__":
    main()
