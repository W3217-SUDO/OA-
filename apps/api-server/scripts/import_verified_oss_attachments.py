"""从已验证对象清单幂等恢复附件关联，不读取或修改文件正文。"""

import argparse
import gzip
import hashlib
import json
import mimetypes
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from sqlalchemy.engine import make_url


SPECS = {
    "Legal_Case_File": ("case", "CaseNo", "Actived", "案件文档"),
    "IPR_Case_File": ("ipr_case", "CaseNo", "Actived", "知识产权案件文档"),
    "CRM_Customer_File": ("customer", "CustomerGuid", "IsActived", "客户文档"),
    "FCM_Contract_File": ("contract", "ContractGuid", "IsActived", "合同文档"),
    "Legal_Investigation_File": ("investigation", "InvestigationGuid", "IsActived", "鉴别资料"),
    "Legal_Investigation_Clue_File": ("clue", "ClueGuid", "IsActived", "调查文档"),
    "Legal_Investigation_Clue_Evidence_File": ("evidence", "EvidenceGuid", "IsActived", "取证文档"),
    "AWS_OfficialDocument_File": ("official_outgoing", "OfficialDocumentGuid", "IsActived", "发文附件"),
}


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def main(args):
    url = make_url(os.environ["DATABASE_URL"])
    check(url.get_backend_name() == "postgresql", "关联导入仅支持 PostgreSQL")
    with args.manifest.open("rb") as handle:
        check(hashlib.file_digest(handle, "sha256").hexdigest() == args.manifest_sha256, "关联清单校验失败")
    with gzip.open(args.manifest, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        check(header["database"] == url.database, "关联清单与目标数据库不一致")
        check(header["schema"] == 1 and header["rows"] > 0, "关联清单版本或数量无效")
        if args.apply:
            check(header["verification_complete"], "OSS 全量对象核对未完成，禁止写入")
            receipt = json.loads(args.backup_receipt.read_text(encoding="utf-8"))
            check(receipt["database"] == url.database and receipt["verified_off_server"], "缺少已校验的库外备份")
            check(
                set(receipt["table_counts"]) == {"file_attachments", "legacy_case_attachment_relations"},
                "备份表范围不完整",
            )
            check(len(receipt["backup_sha256"]) == 64 and receipt["backup_bytes"] > 0, "备份校验信息无效")
            check(receipt["manifest_sha256"] == args.manifest_sha256, "备份与关联清单不匹配")
            check(receipt["parent_rows"] > 0 and len(receipt["parent_sha256"]) == 64, "缺少父记录关系备份")
        with psycopg.connect(
            host=url.host,
            port=url.port or 5432,
            user=url.username,
            password=url.password,
            dbname=url.database,
            row_factory=dict_row,
        ) as db:
            db.execute("SET LOCAL lock_timeout='5s'")
            db.execute("SET LOCAL statement_timeout='180s'")
            db.execute("SET LOCAL work_mem='4MB'")
            db.execute("SET LOCAL max_parallel_workers_per_gather=0")
            db.execute("SET LOCAL jit=off")
            db.execute("SELECT pg_advisory_xact_lock(hashtext('verified-oss-attachment-import'))")
            db.execute("""CREATE TEMP TABLE oss_links (
                source_table text NOT NULL,file_id bigint NOT NULL,record_id bigint NOT NULL,
                object_key text NOT NULL,object_bytes bigint NOT NULL,etag text NOT NULL,
                PRIMARY KEY(source_table,file_id,record_id)) ON COMMIT DROP""")
            count = 0
            with db.cursor().copy("COPY oss_links FROM STDIN") as copier:
                for line in source:
                    row = json.loads(line)
                    check(row["source_table"] in SPECS, "清单含不受支持的旧表")
                    check(row["state"] == "verified_metadata" and row["http_status"] == 200, "对象尚未验证")
                    check(row["object_bytes"] == row["expected_bytes"] and row["etag"], "对象大小或标识未核实")
                    check(0 <= row["object_bytes"] <= 2147483647, "对象超出附件字段范围")
                    check(len("oss://" + header["bucket"] + "/" + row["object_key"]) <= 512, "OSS 路径过长")
                    check(
                        any(row["object_key"].startswith(prefix + "/") for prefix in header["prefixes"]),
                        "对象不在授权目录",
                    )
                    copier.write_row(
                        (
                            row["source_table"],
                            row["legacy_file_id"],
                            row["record_id"],
                            row["object_key"],
                            row["object_bytes"],
                            row["etag"],
                        )
                    )
                    count += 1
            check(count == header["rows"], "关联清单数量不一致")
            db.execute("ANALYZE oss_links")
            # 只读取所需旧身份字段，避免加载大型业务 JSON 到进程内存。
            db.execute("""CREATE TEMP TABLE oss_parents ON COMMIT DROP AS
                SELECT b.id,b.module,b.data->>'migration_source' source,
                jsonb_build_object('CaseNo',b.data->'legacy_record'->'CaseNo',
                    'CustomerGuid',b.data->'legacy_record'->'CustomerGuid',
                    'ContractGuid',b.data->'legacy_record'->'ContractGuid',
                    'InvestigationGuid',b.data->'legacy_record'->'InvestigationGuid',
                    'ClueGuid',b.data->'legacy_record'->'ClueGuid',
                    'EvidenceGuid',b.data->'legacy_record'->'EvidenceGuid',
                    'OfficialDocumentGuid',b.data->'legacy_record'->'OfficialDocumentGuid') legacy
                FROM business_records b JOIN (SELECT DISTINCT record_id FROM oss_links) p ON p.record_id=b.id""")
            db.execute("CREATE UNIQUE INDEX ON oss_parents(id)")
            db.execute("ANALYZE oss_parents")
            file_types = {"case": {}, "ipr_case": {}}
            for table in ("BAS_Case_FileType", "Legal_Case_FileType", "IPR_Case_FileType"):
                for row in db.execute(sql.SQL("SELECT to_jsonb(f) payload FROM {} f").format(sql.Identifier(table))):
                    item = row["payload"]
                    code = str(item.get("FileTypeId") or "")
                    if code and item.get("FileTypeName"):
                        modules = (
                            ("case", "ipr_case")
                            if table == "BAS_Case_FileType"
                            else ("ipr_case",)
                            if table == "IPR_Case_FileType"
                            else ("case",)
                        )
                        for module in modules:
                            file_types[module].setdefault(code, str(item["FileTypeName"]))
            db.execute("""CREATE TEMP TABLE oss_ready (
                record_id bigint,category text,file_type_code text,original_name text,stored_name text PRIMARY KEY,
                content_type text,size bigint,path text,uploader text,remark text,created_at timestamptz,
                is_license boolean,is_transmitted boolean,source_table text,file_id bigint) ON COMMIT DROP""")
            counts = Counter()
            for table, (module, parent, active, default_category) in SPECS.items():
                statement = sql.SQL("""SELECT l.*,to_jsonb(f) payload,p.legacy parent_payload,p.module,p.source
                    FROM oss_links l LEFT JOIN {} f ON f.{}=l.file_id
                    LEFT JOIN oss_parents p ON p.id=l.record_id
                    WHERE l.source_table=%s ORDER BY l.file_id,l.record_id""").format(
                    sql.Identifier(table), sql.Identifier("FileId")
                )
                with db.cursor(name="oss_source_rows") as reader:
                    reader.execute(statement, (table,))
                    while batch := reader.fetchmany(500):
                        prepared = []
                        for row in batch:
                            prepared.append(
                                prepare_attachment(
                                    row, table, module, parent, active, default_category, file_types, header
                                )
                            )
                            counts[table] += 1
                        with db.cursor().copy("COPY oss_ready FROM STDIN") as copier:
                            for values in prepared:
                                copier.write_row(values)
            check(sum(counts.values()) == count, "源附件核对未覆盖完整清单")
            mismatches = db.execute("""SELECT count(*) n FROM oss_ready r JOIN file_attachments f USING(stored_name)
                WHERE f.record_id<>r.record_id OR f.path<>r.path OR f.size<>r.size OR f.original_name<>r.original_name""").fetchone()[
                "n"
            ]
            check(mismatches == 0, "已有附件与导入清单冲突，禁止覆盖")
            expected_legal = counts["Legal_Case_File"]
            legal_matches = db.execute("""SELECT count(*) n FROM oss_ready r
                JOIN legacy_case_attachment_relations l ON l.legacy_file_id=r.file_id AND l.case_record_id=r.record_id
                WHERE r.source_table='Legal_Case_File'""").fetchone()["n"]
            check(legal_matches == expected_legal, "历史案件附件关系未完整对应")
            if args.apply:
                db.execute("LOCK TABLE file_attachments,legacy_case_attachment_relations IN SHARE ROW EXCLUSIVE MODE")
                check(
                    db.execute("SELECT count(*) n FROM file_attachments").fetchone()["n"]
                    == receipt["table_counts"]["file_attachments"],
                    "备份后附件数量发生变化",
                )
                check(
                    db.execute("SELECT count(*) n FROM legacy_case_attachment_relations").fetchone()["n"]
                    == receipt["table_counts"]["legacy_case_attachment_relations"],
                    "备份后历史关系数量发生变化",
                )
                inserted = db.execute("""INSERT INTO file_attachments
                    (record_id,category,file_type_code,original_name,stored_name,content_type,size,path,uploader,remark,created_at,
                     is_license,requires_transmission,is_transmitted,transmitted_by,is_locked,locked_by,word_editor_lock_token,word_editor_locked_by)
                    SELECT record_id,category,file_type_code,original_name,stored_name,content_type,size,path,uploader,remark,created_at,
                     is_license,false,is_transmitted,'',false,'','','' FROM oss_ready ON CONFLICT(stored_name) DO NOTHING""").rowcount
                updated = db.execute("""UPDATE legacy_case_attachment_relations l
                    SET attachment_id=f.id,source_path=f.path,source_available=true,mapping_state='oss_verified',updated_at=now()
                    FROM oss_ready r JOIN file_attachments f USING(stored_name)
                    WHERE r.source_table='Legal_Case_File' AND l.legacy_file_id=r.file_id AND l.case_record_id=r.record_id""").rowcount
                check(updated == expected_legal, "案件附件投影未完整对应，回滚整批")
                linked = db.execute(
                    "SELECT count(*) n FROM oss_ready r JOIN file_attachments f USING(stored_name)"
                ).fetchone()["n"]
                check(linked == count, "写入后关联数量不一致，回滚整批")
                db.commit()
            else:
                inserted = updated = 0
                db.rollback()
            print(
                json.dumps(
                    {
                        "apply": args.apply,
                        "database": url.database,
                        "verified_links": count,
                        "tables": dict(counts),
                        "inserted": inserted,
                        "case_relations_updated": updated,
                        "file_body_bytes": 0,
                    },
                    ensure_ascii=False,
                )
            )


def prepare_attachment(row, table, module, parent, active, default_category, file_types, header):
    raw = row["payload"]
    check(raw is not None and str(raw[active]).upper() in {"T", "Y", "TRUE", "1"}, "旧文件不存在或已停用")
    check(row["module"] == module and row["source"] == header["source"], "附件父记录来源或模块不一致")
    expected = str(raw.get(parent) or "").strip().casefold()
    actual = str((row["parent_payload"] or {}).get(parent) or "").strip().casefold()
    check(expected and expected == actual, "附件父键不匹配")
    if module == "evidence":
        check(
            str(raw.get("ClueGuid") or "").casefold() == str(row["parent_payload"].get("ClueGuid") or "").casefold(),
            "取证复合父键不匹配",
        )
    name = str(raw.get("FileName") or "")
    check(name and len(name) <= 255 and "/" not in name and "\\" not in name, "旧文件名无效")
    check(row["object_key"].rsplit("/", 1)[-1].casefold() == name.casefold(), "OSS 对象与旧文件名不一致")
    directory_key = raw.get("ClueGuid") if module == "evidence" else raw.get(parent)
    check(
        row["object_key"].rsplit("/", 2)[-2].strip().casefold() == str(directory_key).strip().casefold(),
        "OSS 对象目录与原父键不一致",
    )
    code = str(raw.get("FileTypeId") or raw.get("CaseFileTypeId") or "")
    category = file_types[module].get(code, code or default_category) if module in file_types else default_category
    check(len(category) <= 64, "原目录名称超出附件分类范围")
    stored = f"legacy-oss-{table}-{row['file_id']}-{row['record_id']}"
    uploaded = raw.get("UploadingTime") or raw.get("UploadTime") or raw.get("CreateTime")
    check(uploaded, "旧文件缺少上传日期，不能伪造当前日期")
    created = datetime.fromisoformat(uploaded)
    if created.tzinfo is None:
        created = created.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    uploader = str(
        raw.get("UploadingUser") or raw.get("UploadUser") or raw.get("Uploader") or raw.get("CreateUser") or ""
    )
    check(uploader and len(uploader) <= 64, "旧文件上传人缺失或无效")
    remark = json.dumps(
        {
            "source": header["source"],
            "legacy_table": table,
            "legacy_file_id": row["file_id"],
            "oss_etag": row["etag"],
            "legacy_declared_bytes": raw.get("FileSize"),
        },
        ensure_ascii=False,
    )
    return (
        row["record_id"],
        category,
        code,
        name,
        stored,
        mimetypes.guess_type(name)[0] or "application/octet-stream",
        row["object_bytes"],
        "oss://" + header["bucket"] + "/" + row["object_key"],
        uploader,
        remark,
        created,
        str(raw.get("IsLicense") or "").upper() in {"T", "Y", "1"},
        str(raw.get("IsTransmitted") or "").upper() in {"T", "Y", "1"},
        table,
        row["file_id"],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-receipt", type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    check(not args.apply or args.backup_receipt is not None, "写入必须提供库外备份回执")
    main(args)
