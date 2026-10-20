"""补齐仓库主数据与证据位置，重复业务键只使用唯一的完整匹配。"""

from collections import Counter, defaultdict
from psycopg import sql
from psycopg.types.json import Jsonb
from .common import ACTOR, SOURCE, audit_time, connect, keyed, rows, save_report
from ..hz_field_maps import enabled, json_value, text


def put(db, table, values, identity):
    keys = tuple(values)
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT ({}) DO UPDATE SET {} RETURNING id").format(
        sql.Identifier(table),
        sql.SQL(",").join(map(sql.Identifier, keys)),
        sql.SQL(",").join(sql.Placeholder() for _ in keys),
        sql.Identifier(identity),
        sql.SQL(",").join(
            sql.SQL("{}=EXCLUDED.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in keys if k != identity
        ),
    )
    return db.execute(
        statement, tuple(Jsonb(json_value(v)) if isinstance(v, dict) else v for v in values.values())
    ).fetchone()["id"]


def master_values(source, identifier, no, name):
    return {
        identifier: source[no[0]],
        no[1]: text(source[no[2]]),
        "name": text(source[name]),
        "address": text(source["Address"]),
        "is_active": enabled(source["IsActived"]),
        "sort_order": int(source["SortingIndex"] or 0),
        "created_by": text(source["CreateUser"]),
        "updated_by": text(source["ChangeUser"]),
        "legacy_created_at": audit_time(source["CreateTime"]),
        "legacy_updated_at": audit_time(source["ChangeTime"]),
    }


def main():
    report = Counter()
    with connect() as db:
        for item in rows(db, "warehouse_legacy_evidence_mappings"):
            if (item["source_snapshot"] or {}).get("migration_source") != SOURCE:
                raise ValueError("仓库映射已存在其他来源，停止合并")
        warehouses = keyed(rows(db, "BAS_Warehouse"), "WarehouseNo")
        warehouse_ids = {}
        for no, source in warehouses.items():
            values = master_values(
                source, "legacy_warehouse_id", ("WarehouseId", "warehouse_no", "WarehouseNo"), "WarehouseName"
            )
            warehouse_ids[no] = put(db, "warehouses", values, "legacy_warehouse_id")
            report["warehouses_mapped"] += 1
        locations = defaultdict(list)
        location_ids = {}
        for source in rows(db, "BAS_Warehouse_StorageLocation"):
            warehouse_no = text(source["WarehouseNo"])
            if warehouse_no not in warehouse_ids:
                raise ValueError("源货位所属仓库缺失")
            values = master_values(
                source,
                "legacy_storage_location_id",
                ("StorageLocationId", "storage_location_no", "StorageLocationNo"),
                "StorageLocationName",
            )
            values["warehouse_id"] = warehouse_ids[warehouse_no]
            location_ids[source["StorageLocationId"]] = put(
                db, "warehouse_storage_locations", values, "legacy_storage_location_id"
            )
            locations[(warehouse_no, text(source["StorageLocationNo"]))].append(source)
            report["storage_locations_mapped"] += 1
        targets = keyed(
            db.execute(
                "SELECT * FROM business_records WHERE module='evidence' AND data->>'migration_source'=%s", (SOURCE,)
            ).fetchall(),
            "serial_no",
        )
        clues = defaultdict(list)
        for clue in rows(db, "Legal_Investigation_Clue"):
            clues[text(clue["ClueGuid"])].append(clue)
        investigations = keyed(rows(db, "Legal_Investigation"), "InvestigationNo")
        for source in rows(db, "Legal_Investigation_Clue_Evidence"):
            record = targets[f"HZ-EV-{source['EvidenceId']}"]
            data = record["data"] or {}
            warehouse_no, location_no = text(source["WarehouseNo"]), text(source["StorageLocationNo"])
            candidates = locations.get((warehouse_no, location_no), [])
            if len(candidates) > 1:
                candidates = [
                    r for r in candidates if text(r["StorageLocationName"]) == text(source["StorageLocationName"])
                ]
            location = candidates[0] if len(candidates) == 1 else None
            mapping_state = (
                "mapped"
                if location
                else "ambiguous_location"
                if len(candidates) > 1
                else "source_location_not_recorded"
                if not warehouse_no or not location_no
                else "source_location_missing"
            )
            warehouse_id = warehouse_ids.get(warehouse_no)
            location_id = location_ids[location["StorageLocationId"]] if location else None
            clue_candidates = clues.get(text(source["ClueGuid"]), [])
            clue = clue_candidates[0] if len(clue_candidates) == 1 else None
            if len(clue_candidates) > 1:
                report["source_clue_guid_ambiguous"] += 1
            investigation = investigations.get(text(clue["InvestigationNo"])) if clue else None
            patch = {
                "legacy_evidence_no": source["EvidenceNo"],
                "evidence_status": data.get("legacy_status_label") or "源状态未记录",
                "storage_state": data.get("legacy_status_label") or "源状态未记录",
                "warehouse_mapping_state": mapping_state,
                "notarization_no": source["NotarialNo"],
                "notary_no": source["NotarialNo"],
                "notary_office": source["NotaryOrganization"],
                "evidence_date": source["EvidenceDate"],
            }
            if clue:
                patch.update(
                    clue_no=clue["ClueNo"],
                    shop_name=clue["StoreName"],
                    investigator=clue["InvestigatorNames"],
                    case_no=clue["CaseNo"],
                )
            if investigation:
                patch["rights_holder"] = investigation["IndicterName"]
            if location:
                patch.update(
                    warehouse_id=warehouse_id,
                    warehouse_no=warehouse_no,
                    warehouse=warehouses[warehouse_no]["WarehouseName"],
                    storage_location_id=location_id,
                    storage_location_no=location_no,
                    location=location["StorageLocationName"],
                )
                put(
                    db,
                    "warehouse_evidence_locations",
                    {
                        "record_id": record["id"],
                        "warehouse_id": warehouse_id,
                        "storage_location_id": location_id,
                        "assigned_by": ACTOR,
                    },
                    "record_id",
                )
            db.execute(
                "UPDATE business_records SET data=(data::jsonb||%s)::json WHERE id=%s",
                (Jsonb(json_value(patch)), record["id"]),
            )
            put(
                db,
                "warehouse_legacy_evidence_mappings",
                {
                    "legacy_evidence_id": source["EvidenceId"],
                    "legacy_evidence_guid": text(source["EvidenceGuid"]),
                    "record_id": record["id"],
                    "warehouse_id": warehouse_id,
                    "storage_location_id": location_id,
                    "mapping_status": mapping_state,
                    "reason": "" if location else "源位置缺失或业务键重复，不猜测货位",
                    "source_snapshot": {"migration_source": SOURCE, "record": json_value(source)},
                },
                "legacy_evidence_id",
            )
            report[mapping_state] += 1
        invalid = db.execute(
            "SELECT count(*) AS n FROM warehouse_evidence_locations b JOIN warehouse_storage_locations l ON l.id=b.storage_location_id WHERE b.warehouse_id<>l.warehouse_id"
        ).fetchone()["n"]
        if invalid:
            raise ValueError("仓库与货位外键不一致")
        db.commit()
    save_report("page-warehouse-report.json", dict(report))


if __name__ == "__main__":
    main()
