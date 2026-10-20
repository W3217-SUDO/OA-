"""使用来源主键登记日志投影，重复运行不会重复生成新版流水。"""

from .common import connect, save_report
from .sql_projection import project, string, record_views, business_join


def materialize(db, table, key, target, joins, record_id, mapping, date_field, where="TRUE"):
    db.execute("DROP TABLE IF EXISTS pg_temp.hz_event_batch")
    db.execute(f'''CREATE TEMP TABLE hz_event_batch AS
        SELECT s.*, {record_id} AS migration_record_id,
               nextval(pg_get_serial_sequence('{target}','id')) AS migration_event_id
        FROM "{table}" s {joins}
        WHERE {record_id} IS NOT NULL AND {date_field} IS NOT NULL AND ({where})
        AND NOT EXISTS(SELECT 1 FROM hz_alignment_event_links l
          WHERE l.source_table='{table}' AND l.source_id=s."{key}"::text)''')
    mapping = {
        "id": "s.migration_event_id",
        "record_id" if target == "workflow_events" else "contract_record_id": "s.migration_record_id",
        **mapping,
    }
    count = project(db, target, "hz_event_batch", mapping, ["id"])
    db.execute(f'''INSERT INTO hz_alignment_event_links(source_table,source_id,target_table,target_id,record_id)
        SELECT '{table}',"{key}"::text,'{target}',migration_event_id,migration_record_id FROM hz_event_batch
        ON CONFLICT(source_table,source_id) DO NOTHING''')
    db.commit()
    return count


def main():
    report = {}
    with connect() as db:
        record_views(db)
        db.execute("""CREATE TABLE IF NOT EXISTS hz_alignment_event_links(
            source_table varchar(96) NOT NULL,source_id varchar(128) NOT NULL,
            target_table varchar(96) NOT NULL,target_id bigint NOT NULL,record_id bigint NOT NULL,
            PRIMARY KEY(source_table,source_id))""")
        db.execute("ALTER TABLE workflow_events ALTER COLUMN from_status TYPE text,ALTER COLUMN to_status TYPE text")
        for table, key, module in [("Legal_Case_Log", "LogId", "case"), ("IPR_Case_Log", "LogId", "ipr_case")]:
            fields = {
                r["column_name"]
                for r in db.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name=%s", (table,)
                ).fetchall()
            }
            where = "UPPER(COALESCE(s.\"IsActived\",'')) IN ('Y','T','1')" if "IsActived" in fields else "TRUE"
            report[table] = materialize(
                db,
                table,
                key,
                "workflow_events",
                business_join(module, "CaseNo"),
                "r.id",
                {
                    "action": "'旧系统操作记录'",
                    "from_status": "''",
                    "to_status": "''",
                    "operator": string("CreateUser"),
                    "comment": string("Content"),
                    "created_at": "s.\"CreateTime\" AT TIME ZONE 'Asia/Shanghai'",
                },
                's."CreateTime"',
                where,
            )
        report["case_log_projection"] = project(
            db,
            "legacy_case_log_projections",
            "Legal_Case_Log",
            {
                "legacy_log_id": 's."LogId"',
                "case_record_id": "r.id",
                "workflow_event_id": "l.target_id",
                "mapping_state": "CASE WHEN r.id IS NULL THEN 'source_case_missing' WHEN l.target_id IS NULL THEN 'inactive_source' ELSE 'mapped' END",
                "source_snapshot": "row_to_json(s)",
            },
            ["legacy_log_id"],
            business_join("case", "CaseNo")
            + " LEFT JOIN hz_alignment_event_links l ON l.source_table='Legal_Case_Log' AND l.source_id=s.\"LogId\"::text",
        )
        joins = 'JOIN "IPR_Case" c ON c."CaseId"=s."CaseId" JOIN hz_records r ON r.module=\'ipr_case\' AND r.serial_no=c."CaseNo" LEFT JOIN "IPR_CasePhase" p ON p."CasePhaseId"=s."CurrentPhaseId" LEFT JOIN "IPR_CasePhase" lp ON lp."CasePhaseId"=s."LastPhaseId"'
        # 阶段名称使用来源字典，不把旧状态数字套到新版通用状态上。
        db.execute("DROP TABLE IF EXISTS pg_temp.hz_event_batch")
        db.execute(
            """CREATE TEMP TABLE hz_event_batch AS SELECT s.*,r.id AS migration_record_id,
            COALESCE(p."CasePhaseName",'') AS migration_phase,COALESCE(lp."CasePhaseName",'') AS migration_last_phase,
            nextval(pg_get_serial_sequence('workflow_events','id')) AS migration_event_id
            FROM "IPR_Case_Pahses" s """
            + joins
            + """ WHERE s."CreateTime" IS NOT NULL AND NOT EXISTS(
            SELECT 1 FROM hz_alignment_event_links l WHERE l.source_table='IPR_Case_Pahses' AND l.source_id=s."Id"::text)"""
        )
        report["ipr_phases"] = project(
            db,
            "workflow_events",
            "hz_event_batch",
            {
                "id": "s.migration_event_id",
                "record_id": "s.migration_record_id",
                "action": "'旧系统阶段变更'",
                "from_status": "s.migration_last_phase",
                "to_status": "s.migration_phase",
                "operator": string("CreateUser"),
                "comment": string("Content"),
                "created_at": "s.\"CreateTime\" AT TIME ZONE 'Asia/Shanghai'",
            },
            ["id"],
        )
        db.execute(
            "INSERT INTO hz_alignment_event_links(source_table,source_id,target_table,target_id,record_id) SELECT 'IPR_Case_Pahses',\"Id\"::text,'workflow_events',migration_event_id,migration_record_id FROM hz_event_batch ON CONFLICT DO NOTHING"
        )
        db.commit()
        joins = "LEFT JOIN hz_records r ON r.module='contract' AND r.data->>'contract_guid'=s.\"ContractGuid\""
        report["contract_events"] = materialize(
            db,
            "FCM_Contract_Event",
            "EventId",
            "contract_events",
            joins,
            "r.id",
            {
                "content": string("Content"),
                "operator": string("Operator"),
                "created_at": 'COALESCE(s."OperateTime",s."CreateTime") AT TIME ZONE \'Asia/Shanghai\'',
            },
            'COALESCE(s."OperateTime",s."CreateTime")',
            "UPPER(COALESCE(s.\"IsActived\",'')) IN ('Y','T','1')",
        )
    save_report("event-report.json", report)


if __name__ == "__main__":
    main()
