"""分类案件主体的只读名录；历史未分类资料只登记待复核。"""

import hashlib

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.core.dependencies import AsyncSession, current_identity, get_db, settings
from app.core.case_parties import party_label
from app.models import BusinessRecord

router = APIRouter()


@router.get(f"{settings.api_prefix}/customers/party-directory/check")
async def check_client_opponents(name: str = Query(min_length=1, max_length=256), credit_code: str = "",
                                 identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.conflict_review_facts import normalized_name
    from app.core.permissions import _require_record_module_menu

    await _require_record_module_menu("customer", identity, db, action="查看")

    matches, pending = 0, 0
    # 只返回风险提示，不把全所案件明细或其他账号资料暴露到客户录入页面。
    statement = select(BusinessRecord.data["case_parties"], BusinessRecord.data["case_party_schema_version"]).where(
        BusinessRecord.module == "case", BusinessRecord.status.not_in(["已删除", "已回收"]),
    ).execution_options(yield_per=200)
    async for parties, version in await db.stream(statement):
        if version != 1:
            pending += 1
            continue
        for party in parties or []:
            if party["party_standpoint"] != "对方":
                continue
            code = str(party.get("credit_code") or "").strip().upper()
            matched = code == credit_code.strip().upper() if code and credit_code.strip() else normalized_name(party["name"]) == normalized_name(name)
            if matched:
                matches += 1
    return {"matched": matches > 0, "historical_pending": pending > 0,
            "message": "存在对手方身份匹配，须按利益冲突审查流程核实" if matches else "已分类对手方中未发现匹配"}


@router.get(f"{settings.api_prefix}/customers/party-directory/clients")
async def party_client_choices(keyword: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import _record_scope_conditions, _record_dict_for_identity, _require_record_module_menu

    identity = {key: value for key, value in identity.items() if key != "_page_menu_capability"}
    await _require_record_module_menu("case", identity, db, action="查看")

    conditions = [BusinessRecord.module == "customer", BusinessRecord.status.not_in(["已回收", "已删除"]),
                  func.coalesce(BusinessRecord.data["customer_type"].as_string(), "客户").in_(["客户", "委托客户"]), *(await _record_scope_conditions(identity, db))]
    if keyword.strip():
        conditions.append(BusinessRecord.title.ilike(f"%{keyword.strip()}%"))
    rows = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.title, BusinessRecord.id).limit(50))).all()
    items = []
    for row in rows:
        visible = await _record_dict_for_identity(row, identity, db)
        items.append({"id": row.id, "name": row.title, "number": row.serial_no,
                      "credit_code": visible["data"].get("identity_no" if visible["data"].get("organization_type") == "个人" else "credit_code", ""), "organization_type": visible["data"].get("organization_type", "")})
    return {"items": items, "limit": 50}


@router.get(f"{settings.api_prefix}/customers/party-directory")
async def list_party_directory(keyword: str = "", scope: str = Query("opponents", pattern="^(opponents|all|review)$"),
                               page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=100),
                               identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import _record_scope_conditions, _require_record_module_menu
    from app.core.system import _allowed_field_keys

    identity = {key: value for key, value in identity.items() if key != "_page_menu_capability"}
    await _require_record_module_menu("case", identity, db, action="查看")

    allowed_fields = await _allowed_field_keys(identity, db)
    identity_visible = allowed_fields is None or "customer.legal" in allowed_fields
    # 名录只展示当前账号原本可见的案件；全所利冲运算仍由现有审查服务执行。
    statement = select(BusinessRecord.id, BusinessRecord.serial_no, BusinessRecord.data["case_parties"],
                       BusinessRecord.data["case_party_schema_version"], BusinessRecord.data["plaintiffs"], BusinessRecord.data["defendants"], BusinessRecord.data["third_parties"], BusinessRecord.data["unclassified_case_parties"], BusinessRecord.data["opponent"]).where(
        BusinessRecord.module == "case", BusinessRecord.status.not_in(["已删除", "已回收"]), *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.id).execution_options(yield_per=200)
    groups, unclassified, review = {}, 0, []
    async for case_id, case_no, parties, version, plaintiffs, defendants, thirds, source_parties, opponent in await db.stream(statement):
        if version != 1:
            unclassified += 1
            names = [str(name) for values in (plaintiffs, defendants, thirds) if isinstance(values, list) for name in values]
            names.extend(str(item.get("name") or "") for item in source_parties or [] if isinstance(item, dict))
            if opponent:
                names.append(str(opponent))
            if not keyword.strip() or keyword.strip().casefold() in " ".join([case_no, *names]).casefold():
                review.append({"id": str(case_id), "name": "、".join(dict.fromkeys(names)) or "尚未录入主体", "subject_kind": "待人工确认", "credit_code": "", "classifications": ["未分类"], "cases": [{"id": case_id, "number": case_no}]})
            continue
        for party in parties or []:
            if scope == "opponents" and party["party_standpoint"] != "对方":
                continue
            if keyword.strip() and keyword.strip().casefold() not in " ".join([party["name"], party.get("credit_code", ""), case_no]).casefold():
                continue
            # 无证件的同名主体不自动合并，留给人工核对。
            key = (party["subject_kind"], party["credit_code"]) if party.get("credit_code") else (case_id, party["id"])
            item = groups.setdefault(key, {"id": hashlib.sha256(repr(key).encode("utf-8")).hexdigest(), "name": party["name"], "subject_kind": party["subject_kind"], "credit_code": party.get("credit_code", "") if identity_visible else None, "classifications": [], "cases": []})
            label = party_label(party)
            if label not in item["classifications"]:
                item["classifications"].append(label)
            if not any(case["id"] == case_id for case in item["cases"]):
                item["cases"].append({"id": case_id, "number": case_no})
    items = list(groups.values()) if scope != "review" else review
    return {"items": items[(page - 1) * page_size:page * page_size], "total": len(items), "page": page, "page_size": page_size,
            "unclassified_case_count": unclassified, "scope": "当前账号可见案件"}
