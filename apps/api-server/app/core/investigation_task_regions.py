"""校验调查子任务的多选区域并生成展示字段。"""

import re

from fastapi import HTTPException


def _region_tokens(value: object) -> set[str]:
    return {part for part in re.split(r"[、,，;；\s]+", str(value or "")) if part}


def scalar_investigation_task_regions(province: str, city: str) -> list[list[str]]:
    """将旧单值省市参数转换为同一套受授权校验的区域路径。"""
    province = province.strip()
    city = city.strip()
    if not province or any(mark in province + city for mark in ",，、;；"):
        raise HTTPException(status_code=422, detail="请提交明确的调查省市；多地域请使用调查区域列表")
    return [[province, city] if city else [province]]


def investigation_regions_cover_country(
    paths: list[list[str]], cities_by_province: dict[str, list[str]],
) -> bool:
    """判断已验证的调查路径是否覆盖所有省市，保留全国授权语义。"""
    selected = {tuple(path) for path in paths}
    return all(
        (province,) in selected or all((province, city) in selected for city in cities)
        for province, cities in cities_by_province.items()
    )


def normalize_investigation_task_regions(
    paths: list[list[str]], authorization: dict, cities_by_province: dict[str, list[str]],
) -> tuple[list[list[str]], str, str, str]:
    if not paths or len(paths) > 500:
        raise HTTPException(status_code=422, detail="请至少选择一个调查区域，最多选择500处")

    normalized: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for path in paths:
        if not isinstance(path, list) or len(path) not in {1, 2} or any(not isinstance(part, str) for part in path):
            raise HTTPException(status_code=422, detail="调查区域必须按省、市层级选择")
        parts = tuple(part.strip() for part in path)
        province = parts[0]
        if not province or province not in cities_by_province or (len(parts) == 2 and parts[1] not in cities_by_province[province]):
            raise HTTPException(status_code=422, detail="调查区域不存在或省市不匹配")
        if parts in seen:
            raise HTTPException(status_code=422, detail="调查区域不能重复选择")
        seen.add(parts)
        normalized.append(list(parts))

    whole_provinces = {path[0] for path in normalized if len(path) == 1}
    if any(len(path) == 2 and path[0] in whole_provinces for path in normalized):
        raise HTTPException(status_code=422, detail="同一省份不能同时选择整省和所属城市")

    scope = str(authorization.get("authorization_scope") or "").strip()
    scope_type = str(authorization.get("authorization_scope_type") or "").strip()
    if scope_type != "N" and scope not in {"全国", "全国范围"}:
        authorized_regions = authorization.get("authorization_regions") or []
        authorized_paths = {
            tuple(part.strip() for part in path)
            for path in authorized_regions
            if isinstance(path, list) and 1 <= len(path) <= 2 and all(isinstance(part, str) for part in path)
        }
        if not authorized_paths:
            provinces = _region_tokens(authorization.get("province")) | _region_tokens(scope)
            cities = _region_tokens(authorization.get("city")) | _region_tokens(scope)
            authorized_paths = {
                (province,) for province in cities_by_province if province in provinces
            } | {
                (province, city)
                for province, known_cities in cities_by_province.items()
                for city in known_cities if city in cities
            }
        if not authorized_paths:
            raise HTTPException(status_code=422, detail="父调查任务的授权区域不明确，请先完善授权范围")
        if any(
            not any(
                selected[0] == allowed[0] and (
                    len(allowed) == 1 or (len(selected) == 2 and selected[1] == allowed[1])
                )
                for allowed in authorized_paths
            )
            for selected in normalized
        ):
            raise HTTPException(status_code=422, detail="调查区域不能超出父任务授权范围")

    provinces = list(dict.fromkeys(path[0] for path in normalized))
    cities = list(dict.fromkeys(path[1] for path in normalized if len(path) == 2))
    summary = "、".join(" ".join(path) for path in normalized)
    return normalized, summary, ",".join(provinces), ",".join(cities)
