"""修复新版业务主表字段，保留记录编号、原始值和无法解析的关联。"""

from collections import Counter
from psycopg.types.json import Jsonb
from .common import SOURCE, audit_time, connect, enum_labels, keyed, rows, save_report
from .dictionaries import CASE_TYPES
from ..hz_field_maps import MAPS, enabled, json_value, mapped_data, split_people, text

SPECS = {
    "customer": ("CRM_Customer", "CustomerId", "CustomerNo", "CustomerName", "BusinessOwner"),
    "contract": ("FCM_Contract", "ContractId", "ContractNo", "ContractName", "BusinessOwner"),
    "case": ("Legal_Case", "CaseId", "CaseNo", "CaseName", "BusinessOwner"),
    "investigation": (
        "Legal_Investigation",
        "InvestigationId",
        "InvestigationNo",
        "InvestigationTitle",
        "BusinessOwner",
    ),
    "task": ("Legal_Investigation_Task", "TaskId", "TaskNo", "TaskName", "Investigator"),
    "clue": ("Legal_Investigation_Clue", "ClueId", "ClueNo", "StoreName", "CreateUser"),
    "evidence": ("Legal_Investigation_Clue_Evidence", "EvidenceId", None, "EvidenceNo", "CreateUser"),
    "ipr_case": ("IPR_Case", "CaseId", "CaseNo", "CaseName", "CaseOfficer"),
    "official_outgoing": (
        "AWS_OfficialDocument",
        "OfficialDocumentId",
        "OfficialDocumentNo",
        "OfficialDocumentName",
        "BusinessOwner",
    ),
}
ENUM_SPECS = {
    "contract": ("ContractStatus", "ContractStatus"),
    "task": ("TaskStatus", "InvestigationTaskStatus"),
    "clue": ("Status", "InvestigationClueStatus"),
    "evidence": ("EvidenceStatus", "InvestigationClueEvidenceStatus"),
    "official_outgoing": ("OfficialDocumentStatus", "OfficialDocumentStatus"),
}
STATUS_MAP = {
    "contract": {"1": "草稿", "2": "审批中", "3": "审批通过", "4": "已拒绝", "5": "已归档"},
    "task": {"10": "草稿", "20": "待审核", "30": "处理中", "40": "已拒绝", "50": "暂停", "60": "过期", "70": "已完成"},
    "clue": {
        "5": "草稿",
        "10": "待审批",
        "15": "待客户审核",
        "20": "待取证",
        "30": "已驳回",
        "40": "已撤回",
        "50": "已终止",
        "60": "已取证",
        "70": "未生成案件",
        "80": "已转案件",
    },
    "official_outgoing": {
        "5": "草稿",
        "10": "待审批",
        "20": "待用印",
        "30": "已拒绝",
        "40": "已撤回",
        "50": "已终止",
        "60": "已用印",
    },
}


class Alignment:
    def __init__(self, db):
        self.db = db
        self.report = Counter()
        self.tables = {module: rows(db, spec[0]) for module, spec in SPECS.items()}
        self.source_ids = {module: keyed(items, SPECS[module][1]) for module, items in self.tables.items()}
        self.source_no = {
            module: keyed(items, SPECS[module][2]) for module, items in self.tables.items() if SPECS[module][2]
        }
        self.existing = keyed(db.execute("SELECT * FROM business_records").fetchall(), "serial_no")
        self.ids = {module: {} for module in SPECS}
        for no, item in self.existing.items():
            if item["module"] in self.ids and (item["data"] or {}).get("migration_source") == SOURCE:
                self.ids[item["module"]][no] = item["id"]
        self.users = keyed(rows(db, "users"), "username")
        self.departments = {text(r["DepartmentId"]): text(r["DepartmentName"]) for r in rows(db, "HR_Department")}
        self.ipr_people = {text(r["UserName"]).lower(): text(r["EmployeeName"]) for r in rows(db, "IPR_User")}
        self.case_phases = {text(r["CasePhaseId"]): text(r["CasePhaseName"]) for r in rows(db, "BAS_Case_Phase")}
        self.ipr_phases = {text(r["CasePhaseId"]): text(r["CasePhaseName"]) for r in rows(db, "IPR_CasePhase")}
        self.ipr_types = {text(r["CaseTypeId"]): text(r["CaseTypeName"]) for r in rows(db, "IPR_CaseType")}
        self.parameter_ids = {(r["category"], r["code"]): r["id"] for r in rows(db, "system_parameters")}
        self.enums = {module: enum_labels(value[1]) for module, value in ENUM_SPECS.items()}
        self.contract_types = enum_labels("ContractType")
        self.charging_types = enum_labels("ChargingType")
        self.archive_states = enum_labels("CaseArchiveStatus")
        self.clues_by_guid = {text(r["ClueGuid"]): r for r in self.tables["clue"]}

    def relation(self, data, kind, no):
        no = text(no)
        if not no:
            return
        record_id = self.ids[kind].get(no)
        data[kind + "_no"] = no
        if record_id:
            data[kind + "_record_id"] = record_id
            data[kind + "_id"] = record_id
        else:
            data.setdefault("unresolved_source_relations", []).append(
                {"type": kind, "no": no, "reason": "源快照中找不到父记录"}
            )
            self.report[kind + "_unresolved_references"] += 1

    def status(self, module, row, data):
        if module in ENUM_SPECS:
            field = ENUM_SPECS[module][0]
            code = text(row.get(field))
            label = self.enums[module].get(code, "")
            data.update({"legacy_status_code": code, "legacy_status_label": label})
            if not label:
                self.report[module + "_unknown_status"] += 1
                return f"源状态{code}" if code else "源状态未记录"
            return STATUS_MAP.get(module, {}).get(code, label)
        if module in {"case", "ipr_case"}:
            labels = self.case_phases if module == "case" else self.ipr_phases
            phase = labels.get(text(row.get("CasePhaseId")), "")
            data["case_phase"] = phase
            category = "case_phase" if module == "case" else "ipr_case_phase"
            data["case_phase_parameter_id"] = self.parameter_ids.get((category, text(row.get("CasePhaseId"))))
            return phase or "源阶段未记录"
        if module == "customer":
            return text(row.get("CustomerStatus")) or "源状态未记录"
        data["legacy_status_code"] = text(row.get("Status"))
        return f"源状态{text(row['Status'])}" if row.get("Status") is not None else "源状态未记录"

    def normalize(self, module, row):
        table, identifier, no_field, title_field, owner_field = SPECS[module]
        no = text(row[no_field]) if no_field else f"HZ-EV-{row[identifier]}"
        existing = self.existing.get(no)
        if existing and (existing["module"] != module or (existing["data"] or {}).get("migration_source") != SOURCE):
            raise ValueError(f"{module} target identity is occupied by unrelated data")
        original = existing["data"] if existing else {}
        # 旧脚本生成的归一化占位值可以修正；新增的业务字段原样保留。
        data = {
            **(original or {}),
            **mapped_data(module, row),
            "migration_source": SOURCE,
            "alignment_revision": "full-fields-v1",
            "source_table": table,
            "legacy_record": json_value(row),
            "source_active": enabled(row.get("IsActived")) if "IsActived" in row else None,
            "unresolved_source_relations": [],
        }
        data["legacy_" + ("ipr_case" if module == "ipr_case" else module) + "_id"] = row[identifier]
        owner = text(row.get(owner_field))
        if module != "investigation":
            data["source_owner"] = owner
        customer_no = text(row.get("CustomerNo"))
        contract_no = text(row.get("ContractNo"))
        if module == "customer":
            data.update(
                {
                    "customer_no": no,
                    "customer_manager": text(row.get("CustomerOwner")),
                    "holder": text(row.get("Holder")),
                    "business_owner": owner,
                    "organization_type": "",
                    "legacy_customer_type_name": row.get("CustomerTypeName"),
                    "customer_type": enum_labels("CRM.Customer.CustomerTypeId").get(
                        text(row.get("CustomerType")), "源类型未记录"
                    ),
                }
            )
        if module == "contract":
            data.update(
                {
                    "contract_no": no,
                    "contract_type": self.contract_types.get(text(row.get("ContractType")), ""),
                    "charging_type": self.charging_types.get(text(row.get("ChargingType")), ""),
                    "type": self.contract_types.get(text(row.get("ContractType")), ""),
                    "fee_type": self.charging_types.get(text(row.get("ChargingType")), ""),
                }
            )
        if module == "ipr_case":
            parent = self.source_ids["customer"].get(text(row.get("CustomerId")))
            customer_no = text(parent.get("CustomerNo")) if parent else ""
            contract = self.source_ids["contract"].get(text(row.get("ContractId")))
            contract_no = text(contract.get("ContractNo")) if contract else ""
            type_name = self.ipr_types.get(text(row.get("CaseTypeId")), "")
            data.update(
                {
                    "legacy_customer_id": row.get("CustomerId"),
                    "legacy_contract_id": row.get("ContractId"),
                    "case_type": type_name,
                    "case_type_name": type_name,
                    "case_kind": "商标"
                    if "商标" in type_name
                    else "专利"
                    if any(k in type_name for k in ("专利", "PCT", "实用新型", "外观设计"))
                    else type_name,
                }
            )
            for key, column in [
                ("case_officer_name", "CaseOfficer"),
                ("case_origin_people_name", "CaseOriginPeople"),
                ("procurator_name", "Procurator"),
                ("copywriter_name", "Copywriter"),
                ("case_submitter_name", "CaseSubmitter"),
            ]:
                username = text(row.get(column)).lower()
                user = self.users.get(username)
                data[key] = self.ipr_people.get(username) or (user["display_name"] if user else "")
                if username in self.ipr_people and user and self.ipr_people[username] != user["display_name"]:
                    data.setdefault("person_identity_conflicts", []).append(
                        {"field": column, "source_username": username}
                    )
                    self.report["ipr_person_namespace_conflicts"] += 1
        if module == "case":
            data["case_type"] = CASE_TYPES.get(row.get("CaseTypeId"), "")
            data["archive_status"] = self.archive_states.get(text(row.get("ArchiveStatus")), "")
            data["legacy_archive_status_code"] = row.get("ArchiveStatus")
            data["case_team_usernames"] = list(
                dict.fromkeys(split_people(row.get("CaseLawyer")) + split_people(row.get("CaseAssistant")))
            )
        if module in {"task", "clue"}:
            investigation_no = text(row.get("InvestigationNo"))
            self.relation(data, "investigation", investigation_no)
            parent = self.source_no["investigation"].get(investigation_no)
            contract_no = text(parent.get("ContractNo")) if parent else ""
            if module == "clue":
                task_no = text(row.get("InvestigationTaskNo"))
                task_id = self.ids["task"].get(task_no)
                data.update(
                    {
                        "source_task_no": task_no,
                        "source_task_id": task_id,
                        "source_task_record_id": task_id,
                        "investigator_usernames": split_people(row.get("Investigators")),
                        "investigators": split_people(row.get("InvestigatorNames")),
                    }
                )
        if module in {"investigation", "task", "clue"}:
            contract = self.source_no["contract"].get(contract_no)
            customer_no = text(contract.get("CustomerNo")) if contract else ""
        if module == "evidence":
            clue = self.clues_by_guid.get(text(row.get("ClueGuid")))
            if clue:
                clue_no = text(clue["ClueNo"])
                self.relation(data, "clue", clue_no)
                parent = self.source_no["investigation"].get(text(clue.get("InvestigationNo")))
                contract_no = text(parent.get("ContractNo")) if parent else ""
                contract = self.source_no["contract"].get(contract_no)
                customer_no = text(contract.get("CustomerNo")) if contract else ""
            data["evidence_date"] = json_value(row.get("EvidenceDate"))
            data["evidence_type"] = text(row.get("EvidenceType"))
        if module != "customer":
            self.relation(data, "customer", customer_no)
        if module != "contract":
            self.relation(data, "contract", contract_no)
        parent = self.source_no["customer"].get(customer_no)
        customer = (
            text(parent.get("CustomerName"))
            if parent
            else text(row.get("ApplicantName"))
            if module == "ipr_case"
            else ""
        )
        if module == "contract" and parent:
            data["customer_manager"] = text(parent.get("CustomerOwner"))
        status = self.status(module, row, data)
        data["status"] = status
        title = text(row.get(title_field))
        if module == "clue" and not title:
            title = text(row.get("Indictee"))
        if module == "evidence" and not title:
            title = no
        department = self.departments.get(text(row.get("DepartmentId")), "")
        if not department and owner in self.users:
            department = self.users[owner]["department"]
        values = (
            title,
            customer,
            status,
            owner,
            department,
            text(row.get("Remark")),
            Jsonb(data),
            audit_time(row.get("CreateTime")),
            audit_time(row.get("ChangeTime") or row.get("CreateTime")),
        )
        if existing:
            self.db.execute(
                "UPDATE business_records SET title=%s,customer=%s,status=%s,owner=%s,department=%s,description=%s,data=%s,created_at=COALESCE(%s,created_at),updated_at=COALESCE(%s,updated_at) WHERE id=%s",
                values + (existing["id"],),
            )
            record_id = existing["id"]
            self.report[module + "_updated"] += 1
        else:
            record_id = self.db.execute(
                "INSERT INTO business_records(title,customer,status,owner,department,description,data,created_at,updated_at,module,serial_no) VALUES(%s,%s,%s,%s,%s,%s,%s,COALESCE(%s,now()),COALESCE(%s,now()),%s,%s) RETURNING id",
                values + (module, no),
            ).fetchone()["id"]
            self.report[module + "_created"] += 1
        self.ids[module][no] = record_id
        if module == "evidence":
            self.db.execute(
                "UPDATE investigation_evidences SET evidence_type=%s,evidence_date=%s,status=%s,source_snapshot=%s WHERE record_id=%s",
                (text(row.get("EvidenceType")), row.get("EvidenceDate"), status, Jsonb(json_value(row)), record_id),
            )
        for key, column in MAPS.get(module, {}).items():
            if column in row and data.get(key) != json_value(row[column]):
                # 布尔、人员和来源标识在上述逻辑中有明确的语义转换。
                if key not in {"customer_guid", "source_owner", "has_product", "product"}:
                    raise ValueError(f"{module} explicit field mapping mismatch: {key}")
        self.report["source_fields_mapped"] += len(row)


def main():
    with connect() as db:
        alignment = Alignment(db)
        # 源字段长度超过原通用主表上限，扩容而不是截断历史内容。
        db.execute("ALTER TABLE business_records ALTER COLUMN title TYPE text, ALTER COLUMN customer TYPE text")
        for module in SPECS:
            for row in alignment.tables[module]:
                alignment.normalize(module, row)
            db.commit()
            print(f"{module}: {len(alignment.tables[module])} aligned", flush=True)
        save_report("business-report.json", dict(alignment.report))


if __name__ == "__main__":
    main()
