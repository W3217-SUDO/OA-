"""将已保存的费用分类元数据转换为业务表单使用的标识。"""

from app.data_models.parameters import SystemParameter


FEE_GROUP_BASES = {
    "official": "官方费用",
    "agency": "代理费",
    "other": "其他费用",
    "internal": "内部费用",
    "third-party": "其他费用",
    "platform": "其他费用",
}
LEGACY_FEE_GROUPS = {
    "1": "official", "2": "agency", "3": "other",
    "4": "internal", "5": "third-party", "6": "platform",
}
FEE_GROUP_LABELS = {
    "官费": "official", "官方费用": "official", "代理费": "agency",
    "其他费用": "other", "内部费用": "internal", "内部提成": "internal",
    "第三方费用": "third-party", "平台费用": "platform",
}
INITIAL_FEE_GROUPS = {
    "OFFICIAL": "official", "AGENCY": "agency",
    "OTHER": "other", "INTERNAL": "internal",
    # 初始化目录将第三方项目放在其他费用根下，业务入口仍需独立分类。
    "1103010": "third-party", "1103020": "third-party", "1103030": "third-party",
    "1103040": "third-party", "1103050": "third-party",
}


def fee_type_group(item: SystemParameter) -> str:
    """兼容已校准目录、两种旧库迁移元数据及初始化目录。"""
    extra = item.extra or {}
    configured = str(extra.get("fee_group") or "").strip()
    if configured in FEE_GROUP_BASES:
        return configured
    legacy_group = str(extra.get("legacy_group_id") or extra.get("legacy_group_code") or "").strip()
    if legacy_group in LEGACY_FEE_GROUPS:
        return LEGACY_FEE_GROUPS[legacy_group]
    if configured in FEE_GROUP_LABELS:
        return FEE_GROUP_LABELS[configured]
    return INITIAL_FEE_GROUPS.get(item.code, "")


def is_platform_agency_fee(item: SystemParameter) -> bool:
    """保留显式配置，识别旧库及初始化目录中已定义的平台代理费。"""
    extra = item.extra or {}
    if "platform_agency" in extra:
        return bool(extra["platform_agency"])
    return str(extra.get("legacy_id") or "") == "11020050" or item.code == "1102050"
