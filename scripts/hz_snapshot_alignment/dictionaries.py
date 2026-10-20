"""把源字典同步到新版参数，保留源编码和父子关系。"""

from psycopg.types.json import Jsonb
from .common import ACTOR, SOURCE, connect, rows, enum_labels, save_report
from ..hz_field_maps import enabled, json_value, text

CASE_TYPES = {110: "民事争议", 120: "刑事案件", 130: "行政案件及国家赔偿", 140: "法律顾问", 150: "仲裁"}


def upsert(db, category, code, name, extra, order=0, active=True):
    existing = db.execute(
        "SELECT id FROM system_parameters WHERE category=%s AND code=%s ORDER BY id", (category, code)
    ).fetchall()
    if len(existing) > 1:
        raise RuntimeError(f"Duplicate system parameter: {category}/{code}")
    extra = {**extra, "migration_source": SOURCE}
    if existing:
        db.execute(
            "UPDATE system_parameters SET name=%s,extra=%s,sort_order=%s,is_active=%s,updated_by=%s WHERE id=%s",
            (name, Jsonb(extra), order, active, ACTOR, existing[0]["id"]),
        )
        return existing[0]["id"]
    return db.execute(
        "INSERT INTO system_parameters(category,code,name,extra,sort_order,is_active,created_by,updated_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (category, code, name, Jsonb(extra), order, active, ACTOR, ACTOR),
    ).fetchone()["id"]


def main():
    report = {}
    with connect() as db:
        for value, name in CASE_TYPES.items():
            upsert(db, "case_type", str(value), name, {"legacy_id": value}, value)
        report["case_type"] = len(CASE_TYPES)
        for category, enum in [("contract_type", "ContractType"), ("charging_type", "ChargingType")]:
            labels = enum_labels(enum)
            for code, name in labels.items():
                upsert(db, category, code, name, {"legacy_id": int(code)}, int(code))
            report[category] = len(labels)
        specs = [
            ("case_phase", "BAS_Case_Phase", "CasePhaseId", "CasePhaseName"),
            ("ipr_case_type", "IPR_CaseType", "CaseTypeId", "CaseTypeName"),
            ("ipr_case_phase", "IPR_CasePhase", "CasePhaseId", "CasePhaseName"),
            ("court", "BAS_Court", "CourtId", "CourtName"),
            ("cause", "BAS_Causes", "CauseId", "CauseName"),
        ]
        for category, table, identifier, label in specs:
            source = rows(db, table)
            for row in source:
                code = text(row[identifier])
                extra = {"legacy_id": row[identifier], "source_table": table, "legacy_record": json_value(row)}
                if category == "case_phase":
                    parent = row.get("ParentPhaseId")
                    extra.update(
                        {
                            "parent_code": str(parent) if parent and parent > 0 else "",
                            "case_type": CASE_TYPES.get(row.get("CaseTypeId"), ""),
                            "case_type_id": row.get("CaseTypeId"),
                        }
                    )
                if category == "cause":
                    parent = row.get("ParentCauseId")
                    extra["parent_code"] = str(parent) if parent and parent > 0 else ""
                if category == "ipr_case_type":
                    name = text(row[label])
                    extra["case_kind"] = (
                        "商标"
                        if "商标" in name
                        else "专利"
                        if any(v in name for v in ("专利", "PCT", "实用新型", "外观设计"))
                        else name
                    )
                    extra["short_code"] = row.get("CaseTypeShortCode")
                if category == "court":
                    code = text(row.get("CourtCode")) or code
                    extra.update(
                        {
                            "province_city": row.get("DistrictName"),
                            "address": row.get("Address"),
                            "phone": row.get("Telphone"),
                        }
                    )
                upsert(
                    db,
                    category,
                    code,
                    text(row[label]),
                    extra,
                    int(row.get("SortingIndex") or row[identifier]),
                    enabled(row["IsActived"]) if "IsActived" in row else True,
                )
            report[category] = len(source)
    save_report("dictionary-report.json", report)


if __name__ == "__main__":
    main()
