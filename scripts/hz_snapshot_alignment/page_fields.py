"""仅补前端契约明确的源字段别名，不重跑主表导入或覆盖已补的历史关联。"""

from collections import Counter
from psycopg.types.json import Jsonb
from .common import SOURCE, connect, enum_labels, save_report
from ..hz_field_maps import MAPS, json_value, text, enabled
from .business import SPECS


def main():
    report = Counter()
    with connect() as db:
        target = db.execute(
            "SELECT id,module,data FROM business_records WHERE data->>'migration_source'=%s", (SOURCE,)
        ).fetchall()
        customer_types = enum_labels("CRM.Customer.CustomerTypeId")
        contract_types = enum_labels("ContractType")
        charging_types = enum_labels("ChargingType")
        execution_states = enum_labels("ExecutionStatus")
        for record in target:
            module = record["module"]
            data = record["data"] or {}
            source = data.get("legacy_record")
            if not isinstance(source, dict) or module not in SPECS:
                continue
            patch = {key: source[column] for key, column in MAPS.get(module, {}).items() if column in source}
            if module == "customer":
                patch.update(
                    customer_type=customer_types.get(text(source.get("CustomerType")), "源类型未记录"),
                    legacy_customer_type_name=source.get("CustomerTypeName"),
                    organization_type="",
                )
                # 原脚本把“申请人”的数字误用作“个人”，未知组织类型必须保留未知。
                nature = text(source.get("CustomerTypeName"))
                if nature in {"个人", "个体工商户", "事业单位", "机关团体", "公司企业", "其他"}:
                    patch["organization_type"] = nature
                patch["organization_type_mapping_state"] = (
                    "mapped" if patch["organization_type"] else "source_kind_unresolved"
                )
            if module == "contract":
                patch.update(
                    type=contract_types.get(text(source.get("ContractType")), ""),
                    fee_type=charging_types.get(text(source.get("ChargingType")), ""),
                    external_contract_numbers=[text(source["RefContractNo"])]
                    if text(source.get("RefContractNo"))
                    else [],
                )
            if module == "case":
                patch.update(execution_status=execution_states.get(text(source.get("ExecutionStatus")), ""))
                if not text(source.get("CustomerNo")) or not text(source.get("ContractNo")):
                    patch["source_required_parent_missing"] = [
                        key for key in ("CustomerNo", "ContractNo") if not text(source.get(key))
                    ]
            if module == "clue":
                patch["has_product"] = enabled(source.get("HasProduct"))
            if module == "evidence":
                patch["storage_state"] = data.get("legacy_status_label", "")
            patch["page_mapping_revision"] = "page-contract-v2"
            db.execute(
                "UPDATE business_records SET data=(data::jsonb||%s)::json WHERE id=%s",
                (Jsonb(json_value(patch)), record["id"]),
            )
            report[module + "_updated"] += 1
            report["aliases_written"] += len(patch)
        db.commit()
    save_report("page-fields-report.json", dict(report))


if __name__ == "__main__":
    main()
