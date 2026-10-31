"""把 HD 知识产权库（PRD_IPR_HD_20180929）导入新版 OA。默认只演练（整体回滚），加 --apply 才提交。

源数据由旧服务器只读导出为 JSONL 目录：每表一个 <表名>.jsonl，另有 _schema.json（{表名: [[列名, SQL类型], ...]}）。

- 原样副本：HD 表写进单独的 schema legacy_ipr_hd（与上海/沪知副本同名且 CaseId 撞号），每次整表刷新。
- 客户：只导案件用到的；按来源键 ipr_hd:<CustomerId> 幂等。信用代码（LicenseNo/OrganizationCode 中 18 位的）或
  规范化全名与新系统已有客户相同的只列进报告，不自动合并，一律新建；编号被占用时加 HD- 前缀。
- 案件：按 (legacy_source=ipr_hd, legacy_ipr_case_id) 幂等新建或更新；案号被其他记录占用时不覆盖，列为冲突。
- 案件日志：IPR_Case_Log 投影为 workflow_events，经 hz_alignment_event_links 去重。
- 案件文件：IPR_Case_File（有效的）按 --oss-keys 清单对上 OSS 对象 HD.IPR/HD.IPR.WEB/CaseFiles/CaseFiles/<案号>/<文件名>，
  写 file_attachments（path=oss://...，大小、ETag 取 OSS）；OSS 上没有的只列进报告。remark 用 hd_file_id，不用 legacy_file_id，
  避免案件文件列表拿 HD 的 FileId 去查上海副本表（撞号）。

所有新记录带 migration_source=<--batch>，回滚按批次号逻辑删除。
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import psycopg  # noqa: E402
from psycopg import sql  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402
from psycopg.types.json import Jsonb  # noqa: E402
from hz_field_maps import enabled, json_value, mapped_data, text  # noqa: E402

LEGACY_SOURCE = "ipr_hd"
SCHEMA = "legacy_ipr_hd"
ACTOR = "ipr-hd-import"
OSS_BUCKET = "oabeifen3217"
OSS_CASE_FILE_PREFIX = "HD.IPR/HD.IPR.WEB/CaseFiles/CaseFiles/"
STORED_NAME_PREFIX = "legacy-oss-hd-IPR_Case_File-"
LOCAL_TZ = timezone(timedelta(hours=8))
# 导出目录里的表全部进副本（以 _schema.json 为准）；以下几张是导入逻辑必需的。
REQUIRED_TABLES = ("IPR_Case", "IPR_CaseType", "IPR_CasePhase", "IPR_Case_Customer", "CRM_Customer", "HR_Staff")
PEOPLE_COLUMNS = (
    ("case_officer_name", "CaseOfficer"), ("case_origin_people_name", "CaseOriginPeople"),
    ("procurator_name", "Procurator"), ("copywriter_name", "Copywriter"), ("case_submitter_name", "CaseSubmitter"),
)
_SQL_TYPES = {
    "int": "integer", "smallint": "integer", "tinyint": "integer", "bigint": "bigint", "bit": "boolean",
    "decimal": "numeric", "numeric": "numeric", "money": "numeric", "smallmoney": "numeric",
    "float": "double precision", "real": "double precision", "date": "date",
    "datetime": "timestamp", "datetime2": "timestamp", "smalldatetime": "timestamp",
}


def same_json(a, b) -> bool:
    """按写进 jsonb 后的样子比较（键顺序、数字写法不影响）。"""
    dump = lambda v: json.dumps(json.loads(json.dumps(v, default=str, ensure_ascii=False)), sort_keys=True, ensure_ascii=False)  # noqa: E731
    return dump(a) == dump(b)


def without_recomputed_deadline(data: dict) -> dict:
    """HD 旧系统每晚重算 IPR_Case.Deadline（不改 ChangeTime）；只有这一项不同不算案件有改动。"""
    legacy = {k: v for k, v in (data.get("legacy_record") or {}).items() if k != "Deadline"}
    return {**{k: v for k, v in data.items() if k != "deadline"}, "legacy_record": legacy}


def pg_type(sql_type: str) -> str:
    return _SQL_TYPES.get(re.sub(r"\(.*", "", sql_type.strip().lower()), "text")


def normalized_name(value) -> str:
    name = unicodedata.normalize("NFKC", text(value)).replace(" ", "")
    return name.replace("(", "（").replace(")", "）")


def credit_code(row: dict) -> str:
    for column in ("LicenseNo", "OrganizationCode"):
        value = re.sub(r"\s", "", text(row.get(column))).upper()
        if len(value) == 18:
            return value
    return ""


def audit_time(value):
    if not value:
        return None
    moment = datetime.fromisoformat(str(value))
    return moment.replace(tzinfo=LOCAL_TZ) if moment.tzinfo is None else moment


class HdImport:
    def __init__(self, db, source: Path, batch: str, oss_keys: Path | None = None, exclude: set[str] | None = None):
        self.db, self.source, self.batch, self.oss_keys = db, source, batch, oss_keys
        self.exclude = exclude or set()
        self.report = Counter()
        self.lists: dict[str, list] = {
            "customer_name_or_code_matches": [], "case_serial_conflicts": [], "customer_serial_prefixed": [],
            "unknown_case_types": [], "unresolved_people": [], "files_missing_in_oss": [], "case_update_diffs": [],
        }
        self.schema = json.loads((source / "_schema.json").read_text(encoding="utf-8"))
        missing = [table for table in REQUIRED_TABLES if table not in self.schema]
        if missing:
            raise SystemExit(f"导出目录缺少必需的表：{missing}")
        self.tables: dict[str, list[dict]] = {}

    def load(self, table: str) -> list[dict]:
        if table not in self.tables:
            path = self.source / f"{table}.jsonl"
            self.tables[table] = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
        return self.tables[table]

    def import_cases(self) -> list[dict]:
        """要导入的案件：去掉 --exclude-case-no 指定的（副本表照样完整保留）。"""
        return [r for r in self.load("IPR_Case") if text(r.get("CaseNo")) not in self.exclude]

    # ---------- 原样副本 ----------
    def mirror(self) -> None:
        self.db.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(SCHEMA)))
        for table in sorted(self.schema):
            columns = self.schema.get(table)
            if not columns:
                self.report[f"mirror_missing:{table}"] += 1
                continue
            name = sql.Identifier(SCHEMA, table)
            self.db.execute(sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
                name, sql.SQL(", ").join(sql.SQL("{} {}").format(sql.Identifier(col), sql.SQL(pg_type(kind))) for col, kind in columns)))
            existing = {r["column_name"] for r in self.db.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s", (SCHEMA, table)).fetchall()}
            for col, kind in columns:
                if col not in existing:
                    self.db.execute(sql.SQL("ALTER TABLE {} ADD COLUMN {} {}").format(name, sql.Identifier(col), sql.SQL(pg_type(kind))))
            # 副本是旧库的只读镜像，按整表刷新保持与源一致；不属于业务数据的逻辑删除范围。
            self.db.execute(sql.SQL("TRUNCATE {}").format(name))
            names = [col for col, _ in columns]
            with self.db.cursor().copy(sql.SQL("COPY {} ({}) FROM STDIN").format(name, sql.SQL(", ").join(map(sql.Identifier, names)))) as copy:
                for row in self.load(table):
                    copy.write_row([row.get(col) for col in names])
            self.report[f"mirror_rows:{table}"] = len(self.load(table))

    # ---------- 客户 ----------
    def customers(self) -> dict[str, int]:
        cases = self.import_cases()
        kept = {text(r["CaseId"]) for r in cases}
        used = {text(r.get("CustomerId")) for r in cases} | {
            text(r.get("CustomerId")) for r in self.load("IPR_Case_Customer") if text(r.get("CaseId")) in kept}
        used.discard("")
        source = {text(r["CustomerId"]): r for r in self.load("CRM_Customer")}
        contacts: dict[str, list] = {}
        for row in self.load("CRM_Customer_Contacts"):
            contacts.setdefault(text(row.get("CustomerNo")), []).append(row)
        existing = self.db.execute(
            "SELECT id, serial_no, title, data FROM business_records WHERE module='customer' AND deleted_at IS NULL").fetchall()
        by_key = {(r["data"] or {}).get("legacy_source_key"): r for r in existing if (r["data"] or {}).get("legacy_source_key")}
        by_name: dict[str, list] = {}
        by_code: dict[str, list] = {}
        for r in existing:
            by_name.setdefault(normalized_name(r["title"]), []).append(r)
            data = r["data"] or {}
            for value in (data.get("credit_code"), data.get("organization_code"), data.get("taxpayer_id")):
                code = re.sub(r"\s", "", text(value)).upper()
                if len(code) == 18:
                    by_code.setdefault(code, []).append(r)
        taken = {r["serial_no"] for r in existing}
        ids: dict[str, int] = {}
        for customer_id in sorted(used, key=lambda v: int(v) if v.isdigit() else 0):
            row = source.get(customer_id)
            if not row:
                self.report["customer_missing_in_source"] += 1
                continue
            key = f"{LEGACY_SOURCE}:{customer_id}"
            name, code = text(row.get("CustomerName")), credit_code(row)
            if key not in by_key:
                matches = {m["id"]: m for m in by_name.get(normalized_name(name), []) + (by_code.get(code, []) if code else [])}
                if matches:
                    self.lists["customer_name_or_code_matches"].append({
                        "hd_customer_id": customer_id, "hd_customer_no": text(row.get("CustomerNo")), "hd_name": name, "credit_code": code,
                        "existing": [{"id": m["id"], "serial_no": m["serial_no"], "title": m["title"]} for m in matches.values()],
                    })
            data = {
                **mapped_data("customer", row),
                "migration_source": self.batch, "legacy_source": LEGACY_SOURCE, "legacy_source_key": key,
                "legacy_customer_id": row.get("CustomerId"), "customer_no": text(row.get("CustomerNo")),
                "credit_code": code or text(row.get("LicenseNo")), "source_table": f"{SCHEMA}.CRM_Customer",
                "legacy_record": json_value(row),
                "contacts": [
                    {"id": f"ipr-hd-{c.get('ContactsId')}", "name": text(c.get("Contacts")), "position": text(c.get("ContactsTitle")),
                     "email": text(c.get("Email")), "office_phone": text(c.get("OfficePhone")), "phone": text(c.get("Mobilephone")),
                     "is_primary": enabled(c.get("IsDefault")), "is_valid": enabled(c.get("IsActived")) if c.get("IsActived") is not None else True}
                    for c in contacts.get(text(row.get("CustomerNo")), [])
                ],
            }
            status = "历史数据" if row.get("IsActived") is None or enabled(row.get("IsActived")) else "已回收"
            if key in by_key:
                current = by_key[key]
                # 更新时保留首次导入的批次号：回滚某一轮同步只删那一轮新建的，不能连带删掉首次导入的客户。
                merged = {**data, **{k: v for k, v in (current["data"] or {}).items() if k not in data or k == "migration_source"}}
                ids[customer_id] = current["id"]
                if same_json(merged, current["data"] or {}) and (name or current["title"]) == current["title"]:
                    self.report["customer_unchanged"] += 1
                    continue
                self.db.execute("UPDATE business_records SET title=%s, data=%s WHERE id=%s", (name or current["title"], Jsonb(merged), current["id"]))
                self.report["customer_updated"] += 1
                continue
            serial = text(row.get("CustomerNo")) or f"HD-C{customer_id}"
            if serial in taken:
                self.lists["customer_serial_prefixed"].append({"hd_customer_no": serial, "name": name})
                serial = f"HD-{serial}"
            if serial in taken:
                serial = f"HD-C{customer_id}"
            taken.add(serial)
            ids[customer_id] = self.db.execute(
                """INSERT INTO business_records (module, serial_no, title, customer, status, owner, department, description, data, created_at, updated_at)
                   VALUES ('customer', %s, %s, '', %s, 'admin', 'HD', '', %s, COALESCE(%s, now()), COALESCE(%s, now())) RETURNING id""",
                (serial, name or serial, status, Jsonb(data), audit_time(row.get("CreateTime")), audit_time(row.get("ChangeTime") or row.get("CreateTime"))),
            ).fetchone()["id"]
            self.report["customer_created"] += 1
        return ids

    # ---------- 案件 ----------
    def cases(self, customer_ids: dict[str, int]) -> dict[str, int]:
        types = {text(r["CaseTypeId"]): text(r["CaseTypeName"]) for r in self.load("IPR_CaseType")}
        phases = {text(r["CasePhaseId"]): text(r["CasePhaseName"]) for r in self.load("IPR_CasePhase")}
        # HD 员工表：StaffName 是账号，StaffChName 是姓名。
        people = {text(r.get("StaffName")).lower(): text(r.get("StaffChName")) for r in self.load("HR_Staff")}
        users = {r["username"]: r["display_name"] for r in self.db.execute("SELECT username, display_name FROM users").fetchall()}
        customers = {text(r["CustomerId"]): r for r in self.load("CRM_Customer")}
        monitored = {text(r.get("CaseId")) for r in self.load("IPR_Case_Monitoring") if text(r.get("IsActived")).upper() == "T"}
        type_params = {r["name"]: r["id"] for r in self.db.execute(
            "SELECT id, name FROM system_parameters WHERE category='ipr_case_type' AND deleted_at IS NULL").fetchall()}
        phase_params = {r["name"]: r["id"] for r in self.db.execute(
            "SELECT id, name FROM system_parameters WHERE category='ipr_case_phase' AND deleted_at IS NULL").fetchall()}
        existing = self.db.execute(
            "SELECT id, serial_no, title, customer, status, description, data FROM business_records WHERE module='ipr_case' AND deleted_at IS NULL").fetchall()
        by_legacy = {text((r["data"] or {}).get("legacy_ipr_case_id")): r for r in existing if (r["data"] or {}).get("legacy_source") == LEGACY_SOURCE}
        taken = {r["serial_no"]: r for r in self.db.execute("SELECT id, serial_no, module FROM business_records WHERE deleted_at IS NULL").fetchall()}
        ids: dict[str, int] = {}
        self.report["ipr_case_excluded"] = len(self.load("IPR_Case")) - len(self.import_cases())
        for row in self.import_cases():
            case_id, no = text(row["CaseId"]), text(row.get("CaseNo"))
            if not no:
                self.report["ipr_case_missing_no"] += 1
                continue
            type_name = types.get(text(row.get("CaseTypeId")), "")
            if type_name and type_name not in type_params:
                self.lists["unknown_case_types"].append({"case_no": no, "case_type": type_name})
            phase = phases.get(text(row.get("CasePhaseId")), "")
            customer_row = customers.get(text(row.get("CustomerId")))
            customer_record_id = customer_ids.get(text(row.get("CustomerId")))
            data = {
                **mapped_data("ipr_case", row),
                "migration_source": self.batch, "legacy_source": LEGACY_SOURCE, "source_table": f"{SCHEMA}.IPR_Case",
                "legacy_record": json_value(row), "legacy_ipr_case_id": row["CaseId"],
                "legacy_customer_id": row.get("CustomerId"), "legacy_contract_id": row.get("ContractId"),
                "case_type": type_name, "case_type_name": type_name,
                "case_kind": "商标" if "商标" in type_name else "专利" if any(k in type_name for k in ("专利", "PCT", "实用新型", "外观设计")) else type_name,
                "case_phase": phase, "case_phase_parameter_id": phase_params.get(phase), "status": phase or "源阶段未记录",
                "customer_no": text(customer_row.get("CustomerNo")) if customer_row else "",
            }
            if customer_record_id:
                data.update({"customer_record_id": customer_record_id, "customer_id": customer_record_id, "primary_customer_id": customer_record_id})
            if text(row.get("ContractId")) not in {"", "0"}:
                data["unresolved_source_relations"] = [{"type": "contract", "legacy_id": row.get("ContractId"), "reason": "HD 合同不在新系统"}]
            for key, column in PEOPLE_COLUMNS:
                username = text(row.get(column)).lower()
                data[key] = people.get(username) or users.get(username, "")
                if username and not data[key]:
                    self.lists["unresolved_people"].append({"case_no": no, "field": column, "username": username})
            customer_name = text(customer_row.get("CustomerName")) if customer_row else text(row.get("ApplicantName"))
            values = (text(row.get("CaseName")) or no, customer_name, phase or "源阶段未记录", text(row.get("Remark")))
            current = by_legacy.get(case_id)
            if current:
                # 新系统里改过的字段（案件日志里有人工“修改案件信息”）以新系统为准，本脚本只补源字段。
                # 首次导入的批次号保留（同步轮次回滚不能删掉首次导入的案件）；旧系统没变的案件不重写。
                kept = {k: v for k, v in (current["data"] or {}).items()
                        if k not in data or k in {"annual_fee_monitoring", "first_annual_year", "cost_slow_rate", "writer", "migration_source"}}
                merged = {**data, **kept}
                ids[case_id] = current["id"]
                if (same_json(without_recomputed_deadline(merged), without_recomputed_deadline(current["data"] or {}))
                        and values == (current["title"], current["customer"], current["status"], current["description"])):
                    self.report["ipr_case_unchanged"] += 1
                else:
                    if len(self.lists["case_update_diffs"]) < 20:
                        before = current["data"] or {}
                        self.lists["case_update_diffs"].append({
                            "case_no": no, "keys": sorted(k for k in set(before) | set(merged) if not same_json(before.get(k), merged.get(k)))[:10],
                            "columns": [n for n, a, b in zip(("title", "customer", "status", "description"), values,
                                                              (current["title"], current["customer"], current["status"], current["description"])) if a != b]})
                    self.db.execute("UPDATE business_records SET title=%s, customer=%s, status=%s, description=%s, data=%s WHERE id=%s",
                                    values + (Jsonb(merged), current["id"]))
                    self.report["ipr_case_updated"] += 1
            elif no in taken:
                self.lists["case_serial_conflicts"].append({"case_no": no, "existing_record_id": taken[no]["id"], "existing_module": taken[no]["module"]})
                self.report["ipr_case_conflict_skipped"] += 1
                continue
            else:
                if case_id in monitored:
                    data["annual_fee_monitoring"] = True
                ids[case_id] = self.db.execute(
                    """INSERT INTO business_records (module, serial_no, title, customer, status, owner, department, description, data, created_at, updated_at)
                       VALUES ('ipr_case', %s, %s, %s, %s, 'admin', 'HD', %s, %s, COALESCE(%s, now()), COALESCE(%s, now())) RETURNING id""",
                    (no, *values, Jsonb(data), audit_time(row.get("CreateTime")), audit_time(row.get("ChangeTime") or row.get("CreateTime"))),
                ).fetchone()["id"]
                taken[no] = {"id": ids[case_id], "module": "ipr_case"}
                self.report["ipr_case_created"] += 1
            if type_name in type_params:
                self.db.execute(
                    """INSERT INTO ipr_case_type_assignments (case_record_id, case_type_id, assigned_at, assigned_by)
                       SELECT %s, %s, now(), %s WHERE NOT EXISTS (SELECT 1 FROM ipr_case_type_assignments WHERE case_record_id=%s AND deleted_at IS NULL)""",
                    (ids[case_id], type_params[type_name], ACTOR, ids[case_id]))
        return ids

    def case_customers(self, case_ids: dict[str, int], customer_ids: dict[str, int]) -> None:
        primary = {text(r["CaseId"]): text(r.get("CustomerId")) for r in self.load("IPR_Case")}
        links = [(text(r["CaseId"]), text(r.get("CustomerId")), r.get("SortingIndex")) for r in self.load("IPR_Case_Customer")]
        links += [(case, customer, 0) for case, customer in primary.items() if customer]
        for case, customer, sorting in links:
            if case not in case_ids or customer not in customer_ids:
                continue
            inserted = self.db.execute(
                """INSERT INTO ipr_case_customers (case_record_id, customer_record_id, is_primary, sorting_index, created_by, created_at)
                   VALUES (%s, %s, %s, %s, %s, now()) ON CONFLICT (case_record_id, customer_record_id) WHERE deleted_at IS NULL DO NOTHING""",
                (case_ids[case], customer_ids[customer], primary.get(case) == customer, sorting or 0, ACTOR)).rowcount
            self.report["ipr_case_customer_linked"] += inserted

    def logs(self, case_ids: dict[str, int]) -> None:
        self.db.execute("""CREATE TABLE IF NOT EXISTS hz_alignment_event_links(
            source_table varchar(96) NOT NULL, source_id varchar(128) NOT NULL,
            target_table varchar(96) NOT NULL, target_id bigint NOT NULL, record_id bigint NOT NULL,
            PRIMARY KEY(source_table, source_id))""")
        # 回滚只逻辑删除日志、不删对应关系；已删的允许重新导入（换绑到新日志）。
        links = {r["source_id"]: r["live"] for r in self.db.execute(
            """SELECT l.source_id, (e.deleted_at IS NULL) AS live FROM hz_alignment_event_links l
               LEFT JOIN workflow_events e ON e.id = l.target_id WHERE l.source_table=%s""", (f"{SCHEMA}.IPR_Case_Log",)).fetchall()}
        for row in self.load("IPR_Case_Log"):
            log_id, case = text(row.get("LogId")), text(row.get("CaseId"))
            if links.get(log_id) or case not in case_ids or ("IsActived" in row and not enabled(row.get("IsActived"))):
                continue
            event_id = self.db.execute(
                """INSERT INTO workflow_events (record_id, action, from_status, to_status, operator, comment, created_at)
                   VALUES (%s, '旧系统操作记录', '', '', %s, %s, COALESCE(%s, now())) RETURNING id""",
                (case_ids[case], text(row.get("CreateUser"))[:64], text(row.get("Content")), audit_time(row.get("CreateTime"))),
            ).fetchone()["id"]
            self.db.execute(
                """INSERT INTO hz_alignment_event_links VALUES (%s, %s, 'workflow_events', %s, %s)
                   ON CONFLICT (source_table, source_id) DO UPDATE SET target_id=EXCLUDED.target_id, record_id=EXCLUDED.record_id""",
                (f"{SCHEMA}.IPR_Case_Log", log_id, event_id, case_ids[case]))
            self.report["workflow_events_created"] += 1

    def files(self, case_ids: dict[str, int]) -> None:
        if not self.oss_keys:
            self.report["files_skipped_no_oss_listing"] = 1
            return
        objects: dict[str, tuple[str, int]] = {}
        for line in self.oss_keys.read_text(encoding="utf-8").splitlines():
            if line.strip():
                key, etag, size = json.loads(line)
                if key.startswith(OSS_CASE_FILE_PREFIX) and not key.endswith("/"):
                    objects[key] = (etag, int(size))
        lowered = {key.lower(): key for key in objects}
        types = {text(r["FileTypeId"]): text(r["FileTypeName"]) for r in self.load("IPR_Case_FileType")}
        done = {r["stored_name"] for r in self.db.execute(
            "SELECT stored_name FROM file_attachments WHERE stored_name LIKE %s AND deleted_at IS NULL", (STORED_NAME_PREFIX + "%",)).fetchall()}
        for row in self.load("IPR_Case_File"):
            file_id, case = text(row.get("FileId")), text(row.get("CaseId"))
            if text(row.get("Actived")).upper() != "T" or case not in case_ids:
                continue
            stored_name = f"{STORED_NAME_PREFIX}{file_id}"
            if stored_name in done:
                continue
            name = text(row.get("FullPath"))
            candidates = [f"{OSS_CASE_FILE_PREFIX}{text(row.get('CaseNo'))}/{value}" for value in (name, name.strip()) if value]
            key = None
            for candidate in candidates:  # 先原样，再忽略大小写（Windows 文件名不区分大小写）
                key = candidate if candidate in objects else lowered.get(candidate.lower())
                if key:
                    break
            if not key:
                self.lists["files_missing_in_oss"].append({"case_no": text(row.get("CaseNo")), "file_id": file_id, "full_path": name})
                continue
            etag, size = objects[key]
            uploaded = audit_time(row.get("UploadingTime") or row.get("CreateTime"))
            original_name = text(row.get("FileName")) or key.rsplit("/", 1)[-1]
            self.db.execute(
                """INSERT INTO file_attachments (record_id, category, file_type_code, original_name, stored_name, content_type, size, path,
                       uploader, remark, document_date, is_license, requires_transmission, is_transmitted, transmitted_by,
                       is_locked, locked_by, word_editor_lock_token, word_editor_locked_by, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, false, %s, '', false, '', '', '', COALESCE(%s, now()))""",
                (case_ids[case], types.get(text(row.get("FileTypeId"))) or "其他", text(row.get("FileTypeId")), original_name, stored_name,
                 mimetypes.guess_type(original_name)[0] or "application/octet-stream", size, f"oss://{OSS_BUCKET}/{key}",
                 text(row.get("UploadingUser"))[:64], json.dumps({
                     "source": self.batch, "legacy_source": LEGACY_SOURCE, "legacy_table": f"{SCHEMA}.IPR_Case_File",
                     "hd_file_id": row.get("FileId"), "oss_etag": etag, "legacy_declared_bytes": row.get("FileSize")}, ensure_ascii=False),
                 uploaded.date() if uploaded else None, text(row.get("IsTransmitted")).upper() == "T", uploaded))
            self.report["file_attachments_created"] += 1

    def run(self) -> dict:
        timings = {}
        for name, step in (("mirror", self.mirror), ("customers", None), ("cases", None), ("case_customers", None), ("logs", None), ("files", None)):
            started = time.monotonic()
            if name == "mirror":
                step()
            elif name == "customers":
                self.customer_ids = self.customers()
            elif name == "cases":
                self.case_ids = self.cases(self.customer_ids)
            elif name == "case_customers":
                self.case_customers(self.case_ids, self.customer_ids)
            elif name == "logs":
                self.logs(self.case_ids)
            else:
                self.files(self.case_ids)
            timings[name] = round(time.monotonic() - started, 1)
        self.report["source_files"] = len(self.load("IPR_Case_File"))
        return {"batch": self.batch, "counts": dict(self.report), "timings_seconds": timings,
                **{key: value for key, value in self.lists.items()}}


def rollback(db, batch: str) -> dict:
    """按批次逻辑删除本次导入新建的客户、案件及其关联（附件文件不涉及）；legacy_ipr_hd 副本另行 DROP SCHEMA。"""
    stamp = {"actor": f"{ACTOR}-rollback"}
    records = [r["id"] for r in db.execute(
        "SELECT id FROM business_records WHERE data->>'migration_source'=%s AND deleted_at IS NULL", (batch,)).fetchall()]
    result = {"business_records": len(records)}
    if records:
        result["ipr_case_customers"] = db.execute(
            "UPDATE ipr_case_customers SET deleted_at=now(), deleted_by=%(actor)s WHERE deleted_at IS NULL AND created_by=%(created)s "
            "AND (case_record_id = ANY(%(ids)s) OR customer_record_id = ANY(%(ids)s))", {**stamp, "created": ACTOR, "ids": records}).rowcount
        result["ipr_case_type_assignments"] = db.execute(
            "UPDATE ipr_case_type_assignments SET deleted_at=now(), deleted_by=%(actor)s WHERE deleted_at IS NULL AND assigned_by=%(by)s "
            "AND case_record_id = ANY(%(ids)s)", {**stamp, "by": ACTOR, "ids": records}).rowcount
        result["file_attachments"] = db.execute(
            "UPDATE file_attachments SET deleted_at=now(), deleted_by=%(actor)s WHERE deleted_at IS NULL AND stored_name LIKE %(prefix)s "
            "AND record_id = ANY(%(ids)s)", {**stamp, "prefix": STORED_NAME_PREFIX + "%", "ids": records}).rowcount
        result["workflow_events"] = db.execute(
            "UPDATE workflow_events SET deleted_at=now(), deleted_by=%(actor)s WHERE deleted_at IS NULL AND id IN "
            "(SELECT target_id FROM hz_alignment_event_links WHERE source_table=%(table)s AND record_id = ANY(%(ids)s))",
            {**stamp, "table": f"{SCHEMA}.IPR_Case_Log", "ids": records}).rowcount
        db.execute("UPDATE business_records SET deleted_at=now(), deleted_by=%(actor)s WHERE id = ANY(%(ids)s)", {**stamp, "ids": records})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", help="HD 导出 JSONL 目录")
    parser.add_argument("--oss-keys", help="HD.IPR 的 OSS 对象清单（每行 [key, etag, size] 的 JSONL）；不给就不写附件")
    parser.add_argument("--exclude-case-no", default="", help="不导入的案号，逗号分隔（如非知识产权的劳动纠纷、占位案件）")
    parser.add_argument("--rollback", action="store_true", help="按 --batch 逻辑删除该批次（配合 --apply 才提交）")
    parser.add_argument("--batch", default=f"ipr_hd_{datetime.now():%Y%m%d}", help="迁移批次号，写入 migration_source")
    parser.add_argument("--report", required=True, help="报告输出文件（仓库外）")
    parser.add_argument("--apply", action="store_true", help="提交写入；不加只演练并回滚")
    args = parser.parse_args()
    report_path = Path(args.report).expanduser().resolve()
    if report_path.is_relative_to(Path(__file__).resolve().parents[1]):
        raise SystemExit("报告必须写在仓库外")
    with psycopg.connect(os.environ["HD_POSTGRES_DSN"], row_factory=dict_row, autocommit=False) as db:
        db.execute("SET TIME ZONE 'Asia/Shanghai'")
        db.execute("SET LOCAL statement_timeout = 0")
        if args.rollback:
            result = {"batch": args.batch, "counts": rollback(db, args.batch), "timings_seconds": {}}
        elif args.source:
            result = HdImport(db, Path(args.source).expanduser(), args.batch,
                                                Path(args.oss_keys).expanduser() if args.oss_keys else None,
                                                {v.strip() for v in args.exclude_case_no.split(",") if v.strip()}).run()
        else:
            raise SystemExit("请指定 --source 或 --rollback")
        if args.apply:
            db.commit()
        else:
            db.rollback()
    result["applied"] = args.apply
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"applied": args.apply, "counts": result["counts"], "timings_seconds": result["timings_seconds"]}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
