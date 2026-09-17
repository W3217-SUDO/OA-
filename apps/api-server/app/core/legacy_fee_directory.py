from fastapi import HTTPException


# 申浩旧系统 BAS_Case_FeeType 的启用目录；分组顺序来自旧页面 base.js。
LEGACY_FEE_GROUPS = (
    (1, "官费", ("一审诉讼费", "二审诉讼费", "再审诉讼费", "公证费", "调解金额", "判决金额", "保全费", "执行费", "核定成本")),
    (2, "代理费", ("律师代理费", "律师咨询费", "律师培训费", "律师见证费", "平台代理费", "律师代理费(退费)")),
    (3, "其他费用", ("案源介绍费", "权利人赔偿款", "投资人分成", "其他费用")),
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
                and (row["name"] == name or (name == "权利人赔偿款" and (row.get("extra") or {}).get("legacy_id") == 11030063))
            ]
            if not matches:
                raise HTTPException(status_code=409, detail=f"旧费用目录缺少项目：{group_name}/{name}")
            matches.sort(key=lambda row: (not bool((row.get("extra") or {}).get("legacy_id")), row["id"]))
            selected = matches[0]
            result.append({**selected, "name": name, "path": f"{group_name} / {name}", "is_active": True, "selectable": True})
            for row in catalog:
                if row["parent_code"] and row["base_fee_type"] == selected["base_fee_type"] and (row["name"] == name or row in matches):
                    if row["id"] != selected["id"]:
                        aliases[row["id"]] = selected["id"]
    return result, aliases
