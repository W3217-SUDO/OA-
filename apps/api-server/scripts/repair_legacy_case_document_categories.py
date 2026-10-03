"""按旧案件目录修复已导入的 OSS 附件分类，先导出限定范围备份。"""

import argparse
import hashlib
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from sqlalchemy.engine import make_url


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) + "\n").encode("utf-8")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def build_plan(db):
    old_types = {}
    for table in ("BAS_Case_FileType", "Legal_Case_FileType"):
        for row in db.execute(sql.SQL('SELECT "FileTypeId","FileTypeName" FROM {}').format(sql.Identifier(table))):
            if row["FileTypeId"] and row["FileTypeName"]:
                old_types.setdefault(str(row["FileTypeId"]), row["FileTypeName"])
    plan = []
    skipped = {"missing_folder": 0, "changed_category": 0, "parent_mismatch": 0}
    query = '''SELECT a.id,a.record_id,a.stored_name,a.path,a.category,a.remark,
        r."FileId" file_id,r."CaseNo" case_no,r."FileTypeId" old_type_id,
        r."CaseFileTypeId" folder_id,t."FileTypeName" new_category,b.serial_no
        FROM legacy_case_attachment_relations l
        JOIN file_attachments a ON a.id=l.attachment_id AND a.record_id=l.case_record_id
        JOIN "Legal_Case_File" r ON r."FileId"=l.legacy_file_id
        JOIN business_records b ON b.id=a.record_id AND b.module='case'
        LEFT JOIN "Legal_Case_FileType" t
          ON t."FileTypeId"=r."CaseFileTypeId" AND t."CaseNo"=r."CaseNo"
        WHERE l.mapping_state='oss_verified' AND r."CaseFileTypeId">0
        AND a.stored_name='legacy-oss-Legal_Case_File-'||r."FileId"::text||'-'||a.record_id::text
        ORDER BY a.id'''
    with db.cursor(name="category_plan") as cursor:
        cursor.execute(query)
        for row in cursor:
            if row["serial_no"] != row["case_no"] or json.loads(row["remark"])["source"] != "hz_crm_20260930":
                skipped["parent_mismatch"] += 1
                continue
            if not row["new_category"]:
                skipped["missing_folder"] += 1
                continue
            if row["category"] == row["new_category"]:
                continue
            code = str(row["old_type_id"] or row["folder_id"] or "")
            if row["category"] != old_types.get(code, code or "案件文档"):
                skipped["changed_category"] += 1
                continue
            require(len(row["new_category"]) <= 64, "原目录名称超过分类长度，禁止截断")
            plan.append({key: row[key] for key in (
                "id", "record_id", "stored_name", "path", "category", "new_category", "file_id", "folder_id", "case_no"
            )})
    return plan, skipped


def export_scope(db, plan, summary):
    entries = {}
    with zipfile.ZipFile(sys.stdout.buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        def write_rows(name, rows):
            digest = hashlib.sha256()
            count = 0
            with archive.open(name, "w") as handle:
                for row in rows:
                    payload = encode(row)
                    handle.write(payload)
                    digest.update(payload)
                    count += 1
            entries[name] = {"rows": count, "sha256": digest.hexdigest()}

        write_rows("plan.jsonl", plan)
        ids = [row["id"] for row in plan]
        parents = sorted({row["record_id"] for row in plan})
        folders = sorted({row["folder_id"] for row in plan})
        files = [row["file_id"] for row in plan]
        queries = {
            "file_attachments.jsonl": ("SELECT * FROM file_attachments WHERE id=ANY(%s) ORDER BY id", ids),
            "parents.jsonl": ('''SELECT id,module,serial_no,data->>'migration_source' source,
                data->'legacy_record'->>'CaseNo' legacy_case_no FROM business_records WHERE id=ANY(%s) ORDER BY id''', parents),
            "legacy_files.jsonl": ('''SELECT "FileId","CaseNo","FileTypeId","CaseFileTypeId","Actived"
                FROM "Legal_Case_File" WHERE "FileId"=ANY(%s) ORDER BY "FileId"''', files),
            "legacy_folders.jsonl": ('''SELECT * FROM "Legal_Case_FileType" WHERE "FileTypeId"=ANY(%s) ORDER BY "FileTypeId"''', folders),
        }
        for name, (query, keys) in queries.items():
            with db.cursor(name="scope_export") as cursor:
                cursor.execute(query, (keys,))
                write_rows(name, cursor)
        require(entries["file_attachments.jsonl"]["rows"] == len(plan), "备份附件数量不一致")
        archive.writestr("manifest.json", encode({**summary, "entries": entries}))


def main(args, before_commit=None):
    url = make_url(os.environ["DATABASE_URL"])
    with psycopg.connect(host=url.host, port=url.port or 5432, user=url.username,
                         password=url.password, dbname=url.database, row_factory=dict_row, connect_timeout=10) as db:
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ" + (" READ ONLY" if not args.apply else ""))
        db.execute("SET LOCAL statement_timeout='120s'")
        db.execute("SET LOCAL lock_timeout='5s'")
        db.execute("SET LOCAL work_mem='2MB'")
        db.execute("SET LOCAL max_parallel_workers_per_gather=0")
        db.execute("SET LOCAL jit=off")
        plan, skipped = build_plan(db)
        plan_sha = hashlib.sha256(b"".join(encode(row) for row in plan)).hexdigest()
        summary = {"database": url.database, "snapshot_at": datetime.now(timezone.utc).isoformat(),
                   "affected_attachments": len(plan), "affected_cases": len({row["record_id"] for row in plan}),
                   "skipped": skipped, "plan_sha256": plan_sha}
        if args.export:
            require(plan, "没有需要修正的分类")
            export_scope(db, plan, summary)
            return
        if args.apply:
            receipt = json.loads(args.backup_receipt.read_text(encoding="utf-8"))
            require(receipt["verified_off_server"] and receipt["database"] == url.database, "库外备份未验证")
            require(receipt["plan_sha256"] == plan_sha and receipt["affected_attachments"] == len(plan), "备份后分类范围变化")
            require(len(receipt["backup_sha256"]) == 64 and receipt["backup_bytes"] > 0, "备份校验信息缺失")
            require(set(receipt["entries"]) == {"plan.jsonl", "file_attachments.jsonl", "parents.jsonl", "legacy_files.jsonl", "legacy_folders.jsonl"}, "关系备份不完整")
            require((datetime.now(timezone.utc) - datetime.fromisoformat(receipt["snapshot_at"])).total_seconds() < 900, "备份快照已过期")
            db.execute("SELECT pg_advisory_xact_lock(hashtext('verified-oss-attachment-import'))")
            db.execute("CREATE TEMP TABLE category_patch (id bigint PRIMARY KEY,record_id bigint,stored_name text,path text,old_category text,new_category text) ON COMMIT DROP")
            with db.cursor().copy("COPY category_patch FROM STDIN") as copier:
                for row in plan:
                    copier.write_row(tuple(row[key] for key in ("id", "record_id", "stored_name", "path", "category", "new_category")))
            updated = db.execute('''UPDATE file_attachments a SET category=p.new_category FROM category_patch p
                WHERE a.id=p.id AND a.record_id=p.record_id AND a.stored_name=p.stored_name
                AND a.path=p.path AND a.category=p.old_category''').rowcount
            require(updated == len(plan), "写入前附件发生变化，回滚整批")
            require(db.execute('''SELECT count(*) n FROM file_attachments a JOIN category_patch p ON p.id=a.id
                WHERE a.category=p.new_category AND a.path=p.path AND a.record_id=p.record_id''').fetchone()["n"] == updated,
                    "分类修正完整性校验失败")
            if before_commit is not None:
                before_commit()
            db.commit()
            summary["updated"] = updated
        print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--export", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-receipt", type=Path)
    args = parser.parse_args()
    require(not args.apply or args.backup_receipt, "修正分类前必须提供库外备份回执")
    main(args)
