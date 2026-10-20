"""把真实来源关系接到新版页面键，冲突和孤儿记录单独登记。"""

from collections import Counter, defaultdict
from psycopg.types.json import Jsonb
from .common import SOURCE, connect, rows, save_report
from ..hz_field_maps import enabled, json_value, split_people, text


def main():
    report = Counter()
    with connect() as db:
        records = db.execute(
            "SELECT id,module,serial_no,data FROM business_records WHERE data->>'migration_source'=%s", (SOURCE,)
        ).fetchall()
        by_module = defaultdict(dict)
        for r in records:
            by_module[r["module"]][r["serial_no"]] = r
        changes = defaultdict(dict)

        def patch(r, **values):
            changes[r["id"]].update(values)

        coordinators = defaultdict(lambda: defaultdict(list))
        for s in rows(db, "CRM_Customer_Coordinator"):
            if text(s["StaffName"]):
                coordinators[text(s["CustomerNo"])][s["TypeId"]].append(text(s["StaffName"]))
        for no, r in by_module["customer"].items():
            source = r["data"]["legacy_record"]
            groups = coordinators[no]
            managers = list(dict.fromkeys(groups[0] + split_people(source.get("CustomerOwner"))))
            patch(
                r,
                customer_managers=managers,
                coordinators=list(dict.fromkeys(groups[1])),
                contact_accounts=list(dict.fromkeys(groups[2])),
                source_person=text(source.get("BusinessOwner")),
                source_customer_source_type=source.get("CustomerSourceType"),
                customer_source=text(source.get("BusinessOwner")),
            )
        participants = defaultdict(list)
        for s in rows(db, "Legal_Case_Participant"):
            participants[text(s["CaseNo"])].append(
                {"staff_name": text(s["StaffName"]), "source_table": "Legal_Case_Participant"}
            )
        claims = defaultdict(set)
        for no, r in by_module["case"].items():
            source = r["data"]["legacy_record"]
            numbers = split_people(source.get("InvestigationClueNos"))
            for number in numbers:
                claims[number].add(no)
            patch(r, legacy_participants=participants[no], investigation_clue_nos=numbers)
            original = by_module["case"].get(text(source.get("OriginalCaseNo")))
            if original and original["id"] != r["id"]:
                patch(r, original_case_id=original["id"])
        valid_edges = defaultdict(list)
        for no, clue in by_module["clue"].items():
            reverse = text(clue["data"]["legacy_record"].get("CaseNo"))
            forward = claims[no]
            if reverse and forward and forward != {reverse}:
                patch(clue, case_relation_mapping_state="source_bidirectional_conflict")
                report["case_clue_source_conflicts"] += 1
                continue
            target = reverse if reverse else next(iter(forward)) if len(forward) == 1 else ""
            case = by_module["case"].get(target)
            if not case:
                if target or forward:
                    report["case_clue_source_parent_missing"] += 1
                continue
            valid_edges[case["id"]].append(clue)
            patch(
                clue,
                case_id=case["id"],
                case_record_id=case["id"],
                converted_case_id=case["id"],
                converted_case_no=target,
                linked_case_no=target,
                case_no=target,
                case_relation_mapping_state="mapped",
            )
            report["case_clue_bidirectional_edges"] += 1
        for case in by_module["case"].values():
            linked = valid_edges[case["id"]]
            if linked:
                patch(
                    case,
                    investigation_clue_ids=[c["id"] for c in linked],
                    investigation_clue_id=linked[0]["id"],
                    clue_record_id=linked[0]["id"],
                    clue_no=linked[0]["serial_no"],
                )
        products = defaultdict(list)
        producers = defaultdict(list)
        indictees = defaultdict(list)
        for table, bucket in [
            ("Legal_Investigation_Clue_Product", products),
            ("Legal_Investigation_Clue_Producer", producers),
            ("Legal_Investigation_Clue_Indictee", indictees),
        ]:
            for s in rows(db, table):
                if enabled(s.get("IsActived")):
                    bucket[text(s["ClueGuid"])].append(s)
        for clue in by_module["clue"].values():
            source = clue["data"]["legacy_record"]
            guid = text(source["ClueGuid"])
            actual_products = products[guid]
            subjects = [
                {
                    "name": s["IndicteeName"],
                    "nature_code": s["BusinessNatureType"],
                    "identity_no": s["IndicteeLicenseNo"],
                    "legal_representative": s["LegalRepresentative"],
                    "region": [s["ProvinceZh"], s["CityZh"], s["DistrictZh"]],
                    "business_address": s["Address"],
                    "source_id": s["IndicteeId"],
                    "source_record": json_value(s),
                }
                for s in indictees[guid]
            ]
            names = list(dict.fromkeys(text(s["ProductName"]) for s in actual_products if text(s["ProductName"])))
            patch(
                clue,
                product="、".join(names),
                product_url="、".join(
                    dict.fromkeys(text(s["ProductUrl"]) for s in actual_products if text(s["ProductUrl"]))
                ),
                sale_num="、".join(text(s["SaleNum"]) for s in actual_products if s["SaleNum"] is not None),
                source_products=json_value(actual_products),
                producers=[text(s["ProducerName"]) for s in producers[guid]],
                source_producers=json_value(producers[guid]),
                indictees=subjects,
            )
            task = by_module["task"].get(text(source.get("InvestigationTaskNo")))
            investigation = by_module["investigation"].get(text(source.get("InvestigationNo")))
            if task:
                td = task["data"]
                patch(
                    clue,
                    parent_task_no=task["serial_no"],
                    source_task_start_date=td.get("start_date"),
                    source_task_end_date=td.get("end_date"),
                    source_task_assigner=td.get("publisher"),
                    investigation_assistant=td.get("assistant"),
                    assigner=td.get("publisher"),
                )
            if investigation:
                patch(
                    clue,
                    source_owner=investigation["data"].get("source_owner"),
                    authorized_from=investigation["data"].get("authorized_from"),
                    authorized_to=investigation["data"].get("authorized_to"),
                )
            report["clue_products_mapped"] += len(actual_products)
            report["clue_subjects_mapped"] += len(subjects)
        for r in records:
            customer = by_module["customer"].get(text(r["data"].get("customer_no")))
            if r["module"] != "customer" and customer:
                groups = changes[customer["id"]].get("customer_managers", [])
                patch(r, customer_managers=groups, customer_manager=groups[0] if groups else "")
            if r["module"] == "ipr_case" and customer:
                patch(r, primary_customer_id=customer["id"])
        for record_id, values in changes.items():
            db.execute(
                "UPDATE business_records SET data=(data::jsonb||%s)::json WHERE id=%s",
                (Jsonb(json_value(values)), record_id),
            )
        report["records_updated"] = len(changes)
        db.commit()
    save_report("page-relations-report.json", dict(report))


if __name__ == "__main__":
    main()
