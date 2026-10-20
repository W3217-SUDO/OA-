"""保留历史 IPR 合同关系，撤销放入普通案件标的表的错误投影。"""

from collections import defaultdict
from psycopg.types.json import Jsonb
from .common import SOURCE, connect, save_report
from ..hz_field_maps import json_value


def main():
    with connect() as db:
        invalid = db.execute(
            "SELECT o.*,c.data->>'migration_source' AS contract_source,r.data->>'migration_source' AS case_source,r.data->>'contract_record_id' AS ipr_contract_id,r.serial_no AS ipr_case_no FROM contract_objects o JOIN business_records r ON r.id=o.case_record_id JOIN business_records c ON c.id=o.contract_record_id WHERE r.module='ipr_case' FOR UPDATE OF o"
        ).fetchall()
        recovered = defaultdict(list)
        for item in invalid:
            if not (
                item["created_by"] == item["updated_by"] == "legacy-import"
                and item["amount"] == 0
                and item["fee_type"] == ""
                and item["remark"] == "沪知历史知识产权案件关联"
                and item["contract_source"] == item["case_source"] == SOURCE
                and int(item["ipr_contract_id"]) == item["contract_record_id"]
            ):
                raise ValueError("非原始迁移产生的错误标的，停止清理")
            for table in ("contract_object_logs", "contract_payment_lines"):
                if db.execute(
                    f"SELECT count(*) AS n FROM {table} WHERE contract_object_id=%s", (item["id"],)
                ).fetchone()["n"]:
                    raise ValueError("错误投影已关联后续业务，不能自动清理")
            recovered[item["contract_record_id"]].append(json_value(item))
        for contract_id, items in recovered.items():
            record = db.execute("SELECT data FROM business_records WHERE id=%s FOR UPDATE", (contract_id,)).fetchone()
            previous = record["data"].get("legacy_ipr_contract_object_imports", [])
            keys = {item["id"] for item in previous}
            patch = {
                "legacy_ipr_contract_object_imports": previous + [item for item in items if item["id"] not in keys],
                "ipr_contract_object_mapping_state": "preserved_outside_legal_case_subjects",
            }
            db.execute(
                "UPDATE business_records SET data=(data::jsonb||%s)::json WHERE id=%s", (Jsonb(patch), contract_id)
            )
        if invalid:
            db.execute("DELETE FROM contract_objects WHERE id=ANY(%s)", ([item["id"] for item in invalid],))
        remaining = db.execute(
            "SELECT count(*) AS n FROM contract_objects o JOIN business_records r ON r.id=o.case_record_id WHERE r.module<>'case'"
        ).fetchone()["n"]
        if remaining:
            raise ValueError("合同标的仍有不符合当前模型的案件")
        db.commit()
    save_report(
        "page-contract-cleanup-report.json",
        {
            "invalid_imports_preserved_and_removed": len(invalid),
            "affected_contracts": len(recovered),
            "remaining_invalid_native_subjects": remaining,
        },
    )


if __name__ == "__main__":
    main()
