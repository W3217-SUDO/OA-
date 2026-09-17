import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, update

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, engine
from app.models import SystemParameter
from app.core.finance import _fee_type_catalog, _fee_type_catalog_aliases

from fastapi import HTTPException


# 启用目录来自旧表；入口名称以用户确认的旧页面为准，分组顺序来自 base.js。
LEGACY_FEE_GROUPS = (
    (1, "官费", ("一审诉讼费", "二审诉讼费", "再审诉讼费", "公证费", "调解金额", "判决金额", "保全费", "执行费", "核定成本")),
    (2, "代理费", ("律师代理费", "律师咨询费", "律师培训费", "律师见证费", "平台代理费", "律师代理费(退费)")),
    (3, "其他费用", ("案源介绍费", "权利人分成", "投资人分成", "其他费用")),
    (4, "内部费用", ("产品购买费", "案源提成", "案源固定提成", "文书提成", "文书固定提成", "文书退费提成", "开庭提成", "开庭固定提成", "翻译费", "投资提成", "调查提成", "调查固定提成", "调档费", "品牌管理费", "品牌固定管理费", "手续服务费", "任务逾期扣款", "服务费(调查)", "服务费(开庭)", "服务费(案源)", "服务费(文书)", "服务费(品管)")),
    (5, "第三方费用", ("检索费", "公告费", "担保费", "鉴定费", "公证服务费")),
)


def legacy_fee_filter_catalog(catalog: list[dict]) -> tuple[list[dict], dict[int, int]]:
    roots = {
        int(row["extra"]["legacy_group_id"]): row
        for row in catalog
        if not row["parent_code"] and (row.get("extra") or {}).get("legacy_group_id")
    }
    if not roots:
        return catalog, {}
    result: list[dict] = []
    aliases: dict[int, int] = {}
    for group_id, group_name, names in LEGACY_FEE_GROUPS:
        if group_id not in roots:
            raise HTTPException(status_code=409, detail=f"旧费用目录缺少分组：{group_name}")
        root = roots[group_id]
        result.append({**root, "name": group_name, "path": group_name, "has_children": True, "selectable": False})
        for name in names:
            matches = [
                row for row in catalog
                if row["parent_code"] == root["code"]
                and (row["name"] == name or (name == "权利人分成" and (row["name"] == "权利人赔偿款" or (row.get("extra") or {}).get("legacy_id") == 11030063)))
            ]
            if not matches:
                raise HTTPException(status_code=409, detail=f"旧费用目录缺少项目：{group_name}/{name}")
            matches.sort(key=lambda row: (not bool((row.get("extra") or {}).get("legacy_id")), row["id"]))
            selected = matches[0]
            result.append({**selected, "name": name, "path": f"{group_name} / {name}", "is_active": True, "selectable": True,
                           "historical_names": list(dict.fromkeys(row["name"] for row in matches))})
            for row in catalog:
                if row["parent_code"] and row["base_fee_type"] == selected["base_fee_type"] and (row["name"] == name or row in matches):
                    if row["id"] != selected["id"]:
                        aliases[row["id"]] = selected["id"]
    return result, aliases


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["export", "apply", "restore"])
    parser.add_argument("--snapshot")
    args = parser.parse_args()
    async with SessionLocal() as db:
        rows = list((await db.scalars(select(SystemParameter).where(SystemParameter.category == "fee_type").order_by(SystemParameter.sort_order, SystemParameter.id))).all())
        if args.mode == "export":
            parameters = [{column.name: getattr(row, column.name) for column in SystemParameter.__table__.columns} for row in rows]
            ids = [row.id for row in rows]
            related = {}
            from app.database import Base
            for table in Base.metadata.sorted_tables:
                columns = [column for column in table.columns if any(fk.target_fullname == "system_parameters.id" for fk in column.foreign_keys)]
                if columns:
                    from sqlalchemy import or_
                    records = (await db.execute(select(table).where(or_(*(column.in_(ids) for column in columns))))).mappings().all()
                    related[table.name] = [dict(row) for row in records]
            print(json.dumps({"scope": "fee_type parameters and unchanged foreign-key relations", "parameters": parameters, "related": related}, default=str, ensure_ascii=True))
        elif args.mode == "restore":
            snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8-sig"))
            for row in snapshot["parameters"]:
                values = {key: row[key] for key in ("name", "extra", "sort_order", "is_active", "updated_by")}
                values["updated_at"] = datetime.fromisoformat(row["updated_at"])
                await db.execute(update(SystemParameter).where(SystemParameter.id == row["id"], SystemParameter.category == "fee_type").values(**values))
            await db.commit()
            print("RESTORED", len(snapshot["parameters"]))
        else:
            if any((row.extra or {}).get("catalog_alignment") == "fee-master-v1" for row in rows):
                print("ALREADY_APPLIED")
                return
            catalog = _fee_type_catalog(rows, include_inactive=True)
            projected, aliases = legacy_fee_filter_catalog(catalog)
            aliases = {**_fee_type_catalog_aliases(rows), **aliases}
            by_id = {row.id: row for row in rows}
            selected = {row["id"]: row for row in projected}
            for row in rows:
                extra = dict(row.extra or {})
                if row.id in selected:
                    expected = selected[row.id]
                    history = list(dict.fromkeys([*extra.get("historical_names", []), row.name, *expected.get("historical_names", [])]))
                    extra.update(parent_code=expected["parent_code"], historical_names=history, catalog_alignment="fee-master-v1")
                    if not expected["parent_code"]:
                        extra["fee_group"] = {1: "official", 2: "agency", 3: "other", 4: "internal", 5: "third-party"}[int(extra["legacy_group_id"])]
                    extra["platform_agency"] = expected["name"] == "平台代理费"
                    row.name = expected["name"]
                    row.sort_order = projected.index(expected) + 1
                    row.is_active = True
                else:
                    row.is_active = False
                    if row.id in aliases:
                        extra["alias_of"] = by_id[aliases[row.id]].code
                    elif not extra.get("legacy_id") or int(extra["legacy_id"]) < 0:
                        extra["catalog_retired"] = True
                row.extra = extra
                row.updated_by = "fee-master-v1"
            await db.flush()
            rows = list((await db.scalars(select(SystemParameter).where(SystemParameter.category == "fee_type")
                        .order_by(SystemParameter.sort_order, SystemParameter.id)
                        .execution_options(populate_existing=True))).all())
            active = _fee_type_catalog(rows)
            if len(active) != 51 or sum(bool(row["parent_code"]) for row in active) != 46:
                raise RuntimeError("费用参数校准数量不符，事务取消")
            await db.commit()
            print("APPLIED roots=5 leaves=46 retained_ids=" + str(len(rows)))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
