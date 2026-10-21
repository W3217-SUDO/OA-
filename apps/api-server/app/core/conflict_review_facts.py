"""利益冲突事实快照；只使用已有结构化字段，不把同名当成同一主体。"""

import hashlib
import json
import re
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, IprCaseCustomer, SystemConfig


def normalized_name(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "")).replace("（", "(").replace("）", ")").casefold()


def text_values(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if isinstance(item, (str, int)) and str(item).strip()]
    return [part.strip() for part in re.split(r"[、,，;；]", str(value or "")) if part.strip()]


def fingerprint(value: dict) -> str:
    content = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _positive_id(value: object) -> int | None:
    return int(value) if str(value or "").isdigit() and int(value) > 0 else None


async def related_conflict_sources(record: BusinessRecord, db: AsyncSession, *, strict: bool = True) -> list[BusinessRecord]:
    """用印和案件沿已验证的业务关联检查来源合同，避免只检查当前对象。"""
    result = [record]
    visited = {record.id}
    for current in result:
        data = current.data or {}
        references = []
        if current.module in {"case", "ipr_case", "seal"}:
            contract_id = _positive_id(data.get("contract_record_id") or data.get("contract_id"))
            numbers = text_values(data.get("contract_no"))
            references.extend(("contract", contract_id if index == 0 else None, number) for index, number in enumerate(numbers))
            if contract_id and not numbers:
                references.append(("contract", contract_id, ""))
        if current.module == "seal":
            references.append(("case", _positive_id(data.get("case_record_id") or data.get("case_id")), str(data.get("case_no") or "").strip()))
        for module, record_id, serial_no in references:
            if not record_id and not serial_no:
                continue
            condition = BusinessRecord.id == record_id if record_id else BusinessRecord.serial_no == serial_no
            linked = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == module, condition))
            if not linked or (record_id and serial_no and linked.serial_no != serial_no):
                if strict:
                    raise HTTPException(status_code=409, detail="利益冲突审查发现来源合同或案件关联失效，请先修正关联资料")
                continue
            if linked and linked.id not in visited:
                visited.add(linked.id)
                result.append(linked)
    return result


def _matter(record: BusinessRecord, customers: dict[int, BusinessRecord], ipr_links: dict[int, list[IprCaseCustomer]]) -> dict:
    data = record.data or {}
    links = ipr_links.get(record.id, []) if record.module == "ipr_case" else []
    primary = next((item.customer_record_id for item in links if item.is_primary), None)
    customer_id = primary or _positive_id(data.get("primary_customer_id") or data.get("customer_record_id") or data.get("customer_id"))
    customer = customers.get(customer_id) if customer_id else None
    customer_data = customer.data or {} if customer else {}
    own_name = str(customer.title if customer else record.customer or "").strip()
    party_identities = {}
    for key in ("plaintiff_identities", "defendant_identities", "third_party_identities"):
        for item in data.get(key) or []:
            if isinstance(item, dict) and item.get("name"):
                party_identities[normalized_name(item["name"])] = str(item.get("identity_no") or "").strip().upper()
    own_identity = str(customer_data.get("identity_no") or customer_data.get("credit_code") or party_identities.get(normalized_name(own_name)) or "").strip().upper()
    plaintiffs = text_values(data.get("plaintiffs") or data.get("plaintiff"))
    defendants = text_values(data.get("defendants") or data.get("defendant") or data.get("opponent"))
    third_parties = text_values(data.get("third_parties"))
    if record.module == "ipr_case":
        for item in data.get("litigation_parties") or []:
            if isinstance(item, dict) and str(item.get("name") or "").strip():
                target = plaintiffs if item.get("party_type") == "原告" else defendants if item.get("party_type") == "被告" else third_parties
                target.append(str(item["name"]).strip())
    own_in_defendants = normalized_name(own_name) in {normalized_name(item) for item in defendants}
    own_in_plaintiffs = normalized_name(own_name) in {normalized_name(item) for item in plaintiffs}
    opponents = plaintiffs if own_in_defendants and not own_in_plaintiffs else defendants
    opponents = [name for name in opponents if normalized_name(name) != normalized_name(own_name)]
    opponent_parties = [{"name": name, "identity": party_identities.get(normalized_name(name), "")} for name in sorted(set(opponents))]
    lawyers = sorted(set(text_values(data.get("handling_lawyer_usernames")) or text_values(data.get("handling_lawyers"))))
    if record.module == "ipr_case":
        lawyers = sorted(set(lawyers + text_values(data.get("case_manager") or data.get("case_officer")) + text_values(data.get("agent"))))
    court_numbers = sorted({str(data.get(key) or "").strip() for key in ("court_case_no", "first_court_case_no", "second_court_case_no", "retrial_court_case_no", "execution_court_case_no") if str(data.get(key) or "").strip()})
    case_type = str(data.get("case_type") or data.get("type") or "").strip()
    if record.module == "ipr_case":
        court_numbers = sorted(set(court_numbers) | {str(item.get("court_case_no") or "").strip() for item in data.get("litigation_courts") or [] if isinstance(item, dict) and str(item.get("court_case_no") or "").strip()})
        case_type = {"litigation": "知识产权诉讼", "non_litigation": "知识产权非诉"}.get(str(data.get("case_category") or ""), "知识产权案件")
    clients = [{"id": customer_id, "name": own_name, "identity": own_identity}]
    for link in links:
        linked_customer = customers.get(link.customer_record_id)
        if linked_customer and link.customer_record_id != customer_id:
            linked_data = linked_customer.data or {}
            clients.append({"id": linked_customer.id, "name": linked_customer.title, "identity": str(linked_data.get("identity_no") or linked_data.get("credit_code") or "").strip().upper()})
    merged = []
    for item in data.get("merged_sources") or []:
        if isinstance(item, dict) and item.get("id"):
            snapshot = BusinessRecord(id=int(item["id"]), module="case", serial_no=str(item.get("serial_no") or ""),
                                      customer=str(item.get("customer") or ""), status=str(item.get("status") or ""), data=dict(item.get("data") or {}))
            merged.append(_matter(snapshot, customers, ipr_links))
    return {
        "id": record.id, "module": record.module, "number": record.serial_no,
        "customer": own_name, "customer_identity": own_identity,
        "customer_id": customer_id, "clients": sorted(clients, key=lambda item: (item["id"] or 0, item["name"])), "opponents": opponent_parties,
        "plaintiffs": sorted(set(plaintiffs)), "defendants": sorted(set(defendants)), "third_parties": sorted(set(third_parties)),
        "lawyers": lawyers, "case_type": case_type,
        "case_kind": str(data.get("case_kind") or ""), "case_category": str(data.get("case_category") or ""),
        "client_position": str(data.get("client_position") or "").strip(),
        "court_numbers": court_numbers,
        "copy_root": _positive_id(data.get("copy_root_case_record_id") or data.get("reboot_source_case_id")) or (record.id if record.module in {"case", "ipr_case"} else None),
        "contract_id": _positive_id(data.get("contract_record_id") or data.get("contract_id")),
        "counsel_start": str(data.get("counsel_start") or ""),
        "counsel_end": str(data.get("counsel_end") or ""),
        "signed_at": str(data.get("signed_at") or ""),
        "terminated_at": str(data.get("terminated_at") or ""),
        "ended": record.status in {"已终止", "已解除", "已作废", "已撤回", "已删除", "已回收", "已归档", "亏损归档", "已结案"} or data.get("case_closed") is True or bool(data.get("case_closed_at")) or data.get("business_stage") == "结案",
        "agents": [dict(item) for key in ("plaintiff_agents", "defendant_agents", "third_party_agents") for item in data.get(key) or [] if isinstance(item, dict)],
        "merged_sources": merged,
    }


async def collect_conflict_facts(record: BusinessRecord, db: AsyncSession) -> dict:
    sources = await related_conflict_sources(record, db)
    source_ids = {item.id for item in sources}
    rows = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(["case", "ipr_case", "contract", "customer", "hr"]),
    ).order_by(BusinessRecord.id))).all())
    customers = {row.id: row for row in rows if row.module == "customer"}
    ipr_links: dict[int, list[IprCaseCustomer]] = {}
    for link in (await db.scalars(select(IprCaseCustomer).order_by(IprCaseCustomer.id))).all():
        ipr_links.setdefault(link.case_record_id, []).append(link)
    matters = [_matter(row, customers, ipr_links) for row in rows if row.module in {"case", "ipr_case", "contract"} and row.id not in source_ids]
    subject = [_matter(row, customers, ipr_links) for row in sources]
    people = []
    for row in rows:
        if row.module != "hr" or row.status in {"离职", "停用", "已删除", "已回收"}:
            continue
        data = row.data or {}
        people.append({"id": row.id, "name": row.title, "username": str(data.get("username") or row.owner or ""), "identity": str(data.get("id_no") or "").strip().upper()})
    config = await db.scalar(select(SystemConfig).where(SystemConfig.key == "company_profile"))
    company_name = str((config.value or {}).get("name") or "") if config else ""
    # 审查业务状态及审查投影不参与自身指纹，避免提交审批后立即把结论变为过期。
    for item in subject:
        item.pop("ended", None)
    return {"subjects": subject, "matters": matters, "people": people, "company_name": company_name}


def party_matches(party: dict, name: str, identity: str) -> bool:
    if party.get("identity") and identity:
        return party["identity"] == identity
    return bool(normalized_name(party.get("name")) and normalized_name(party.get("name")) == normalized_name(name))


def current_counsel(matter: dict) -> bool:
    if "顾问" not in matter["case_type"] or matter.get("ended"):
        return False
    start, end = matter["counsel_start"], matter["counsel_end"]
    if not start or not end:
        return False
    try:
        return date.fromisoformat(start) <= date.today() <= date.fromisoformat(end)
    except ValueError:
        return False
