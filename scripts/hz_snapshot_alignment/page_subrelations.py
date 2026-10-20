"""补投影资助办理记录，并撤销源 GUID 歧义造成的错误证据父关系。"""

from collections import Counter, defaultdict
from datetime import datetime
from psycopg.types.json import Jsonb
from .common import SOURCE, audit_time, connect, keyed, rows, save_report
from ..hz_field_maps import json_value, text


def main():
    report = Counter()
    with connect() as db:
        clues = defaultdict(list)
        for clue in rows(db, "Legal_Investigation_Clue"):
            clues[text(clue["ClueGuid"])].append(clue)
        evidence = keyed(
            db.execute(
                "SELECT * FROM business_records WHERE module='evidence' AND data->>'migration_source'=%s", (SOURCE,)
            ).fetchall(),
            "serial_no",
        )
        for source in rows(db, "Legal_Investigation_Clue_Evidence"):
            guid = text(source["ClueGuid"])
            if len(clues.get(guid, [])) <= 1:
                continue
            record = evidence[f"HZ-EV-{source['EvidenceId']}"]
            reference = db.execute(
                "INSERT INTO investigation_historical_references(entity_type,legacy_key,source_table,reason,source_snapshot) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(entity_type,legacy_key) DO UPDATE SET reason=EXCLUDED.reason,source_snapshot=EXCLUDED.source_snapshot RETURNING id",
                (
                    "clue",
                    guid,
                    "Legal_Investigation_Clue",
                    "源 ClueGuid 对应多条线索，无法确认唯一父记录",
                    Jsonb({"migration_source": SOURCE, "candidate_legacy_ids": [r["ClueId"] for r in clues[guid]]}),
                ),
            ).fetchone()["id"]
            db.execute(
                "UPDATE investigation_evidences SET clue_record_id=NULL,missing_clue_reference_id=%s WHERE record_id=%s",
                (reference, record["id"]),
            )
            keys = [
                "clue_record_id",
                "clue_id",
                "clue_no",
                "contract_record_id",
                "contract_id",
                "contract_no",
                "customer_record_id",
                "customer_id",
                "customer_no",
                "case_no",
                "shop_name",
                "investigator",
                "rights_holder",
            ]
            previous = {k: record["data"][k] for k in keys if k in record["data"]}
            patch = {
                "clue_mapping_state": "ambiguous_source_guid",
                "missing_clue_reference_id": reference,
                "ambiguous_previous_links": record["data"].get("ambiguous_previous_links") or previous,
            }
            db.execute(
                "UPDATE business_records SET customer='',data=((data::jsonb-%s::text[])||%s)::json WHERE id=%s",
                (keys, Jsonb(patch), record["id"]),
            )
            report["ambiguous_evidence_links_removed"] += 1

        source_cases = keyed(rows(db, "IPR_Case"), "CaseId")
        target_cases = keyed(
            db.execute(
                "SELECT * FROM business_records WHERE module='ipr_case' AND data->>'migration_source'=%s", (SOURCE,)
            ).fetchall(),
            "serial_no",
        )
        fee_types = keyed(rows(db, "IPR_Case_AssistedFeeType"), "AssistedFeeTypeId")
        people = {text(r["UserName"]).lower(): text(r["EmployeeName"]) for r in rows(db, "IPR_User")}
        mappings = defaultdict(list)
        for source in rows(db, "IPR_Case_AssistedFee"):
            case = source_cases.get(text(source["CaseId"]))
            if not case:
                report["assisted_missing_source_case"] += 1
                continue
            if text(case["CaseNo"]) != text(source["CaseNo"]):
                raise ValueError("源资助记录 CaseId 与 CaseNo 不一致")
            record = target_cases[text(case["CaseNo"])]
            fee_type = fee_types[text(source["AssistedFeeTypeId"])]
            previous = [
                m
                for m in record["data"].get("legacy_assisted_fee_mappings", [])
                if m["legacy_id"] == source["AssistedFeeId"]
            ]
            request_date = (
                source["RequestDate"].date() if isinstance(source["RequestDate"], datetime) else source["RequestDate"]
            )
            response_date = (
                source["ResponseDate"].date()
                if isinstance(source["ResponseDate"], datetime)
                else source["ResponseDate"]
            )
            if not request_date or not text(fee_type["AssistedFeeTypeName"]):
                raise ValueError("资助记录缺少必填日期或已证实的资助类别")
            values = {
                "case_record_id": record["id"],
                "assisted_type": fee_type["AssistedFeeTypeName"],
                "status": "已办理" if response_date else "源状态未记录",
                "request_date": request_date,
                "request_user": people.get(text(source["RequestUser"]).lower(), text(source["RequestUser"])),
                "response_date": response_date,
                "response_user": people.get(text(source["ResponseUser"]).lower(), text(source["ResponseUser"])),
                "remark": "历史记录；源回执文件尚未恢复" if text(source["FileFullPath"]) else "历史记录",
            }
            if previous:
                native_id = previous[0]["native_id"]
                current = db.execute("SELECT * FROM ipr_case_assisted_fees WHERE id=%s", (native_id,)).fetchone()
                if not current or any(current[key] != value for key, value in values.items()):
                    raise ValueError("既有资助投影已被修改，停止覆盖")
            else:
                native_id = db.execute(
                    "INSERT INTO ipr_case_assisted_fees(case_record_id,assisted_type,status,request_date,request_user,response_date,response_user,remark,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,COALESCE(%s,now()),COALESCE(%s,now())) RETURNING id",
                    tuple(values.values()) + (audit_time(source["CreateTime"]), audit_time(source["ChangeTime"])),
                ).fetchone()["id"]
            mappings[record["id"]].append(
                {
                    "legacy_id": source["AssistedFeeId"],
                    "native_id": native_id,
                    "source_table": "IPR_Case_AssistedFee",
                    "source_snapshot": json_value(source),
                    "receipt_recovery_state": "unverified" if text(source["FileFullPath"]) else "source_not_recorded",
                }
            )
            report["assisted_records_mapped"] += 1
            if text(source["FileFullPath"]):
                report["assisted_receipts_unverified"] += 1
        for record_id, values in mappings.items():
            db.execute(
                "UPDATE business_records SET data=(data::jsonb||%s)::json WHERE id=%s",
                (Jsonb({"legacy_assisted_fee_mappings": values}), record_id),
            )
        db.commit()
    save_report("page-subrelations-report.json", dict(report))


if __name__ == "__main__":
    main()
