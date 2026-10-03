"""案件文档按原始业务关系聚合，保留附件归属和访问权限。"""
import re

from sqlalchemy import String, cast, func, or_, select

from app.models import BusinessRecord, FileAttachment
from fastapi import HTTPException

from app.core.permissions import _can_search_all_cases_from_global_search, _ensure_case_read_module, _record_scope_conditions
from app.core.storage import _attachment_dict
from app.core.formatters import _person_display_name, _user_display_map
from app.core.case_document_sources import case_document_sources
from app.core.legacy_case_document_folders import legacy_attachment_folder_keys


def _values(data, keys):
    values = []
    for key in keys:
        value = data.get(key)
        values.extend(value if isinstance(value, list) else re.split(r"[,，;；、|]+", str(value or "")))
    return {str(value).strip() for value in values if str(value or "").strip()}


def _ids(data, keys):
    return {int(value) for value in _values(data, keys) if value.isdigit() and int(value) > 0}


def _case_read_identity(identity):
    if not identity.get("_page_menu_capability"):
        return identity
    return {**identity, "role": identity["_actual_role"], "role_ids": identity["_actual_role_ids"],
            "_page_menu_capability": False}


async def case_document_records(case, identity, db):
    """解析已授权案件的真实关联文档父记录；普通账号保留原关联范围。"""
    identity = _case_read_identity(identity)
    sources = case_document_sources(case)
    scope = [] if await _can_search_all_cases_from_global_search(identity, db) else await _record_scope_conditions(identity, db)
    clue_relations = []
    for source in sources:
        source_data = source.get("data") or {}
        clue_ids = _ids(source_data, ("clue_id", "clue_record_id", "investigation_clue_id", "investigation_clue_ids"))
        clue_nos = _values(source_data, ("clue_no", "investigation_clue", "source_clue_no", "investigation_clue_nos"))
        # 每个来源分别优先使用明确ID，避免其他来源的ID遮蔽仅有编号的历史关系。
        if clue_ids:
            clue_relations.append(BusinessRecord.id.in_(clue_ids))
        elif clue_nos:
            clue_relations.append(BusinessRecord.serial_no.in_(clue_nos))
    if clue_relations:
        relation = or_(*clue_relations)
    else:
        relation = or_(
            *[cast(BusinessRecord.data[key].as_string(), String) == str(case.id)
              for key in ("case_id", "case_record_id", "converted_case_id")],
            *[BusinessRecord.data[key].as_string() == case.serial_no
              for key in ("case_no", "converted_case_no")],
        )
    clues = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "clue", relation, *scope,
    ))).all())
    records = {case.id: case, **{clue.id: clue for clue in clues}}
    source_cases = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.id.in_([source["id"] for source in sources[1:]]),
        *scope,
    ))).all()
    records.update({source.id: source for source in source_cases})
    customer_ids, customer_nos = set(), set()
    for source in sources:
        source_data = source.get("data") or {}
        customer_ids.update(_ids(source_data, ("customer_id", "customer_record_id")))
        customer_nos.update(_values(source_data, ("customer_no",)))
    if customer_ids or customer_nos:
        customers = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "customer",
            or_(BusinessRecord.id.in_(customer_ids), BusinessRecord.serial_no.in_(customer_nos)),
            *scope,
        ))).all()
        records.update({customer.id: customer for customer in customers})
    contract_ids, contract_nos = set(), set()
    for source in sources:
        contract_ids.update(_ids(source.get("data") or {}, ("contract_id", "contract_record_id")))
        contract_nos.update(_values(source.get("data") or {}, ("contract_no",)))
    if contract_ids or contract_nos:
        contracts = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "contract", or_(BusinessRecord.id.in_(contract_ids), BusinessRecord.serial_no.in_(contract_nos)),
            BusinessRecord.customer == case.customer, *scope,
        ))).all()
        records.update({contract.id: contract for contract in contracts})
    if clues:
        evidence_ids, investigation_ids, task_ids = set(), set(), set()
        investigation_nos = set()
        for clue in clues:
            item = clue.data or {}
            evidence_ids.update(_ids(item, ("evidence_ids", "collection_evidence_record_id")))
            investigation_ids.update(_ids(item, ("investigation_id", "investigation_record_id")))
            investigation_nos.update(_values(item, ("investigation_no",)))
            task_ids.update(_ids(item, ("source_task_id",)))
        if task_ids:
            tasks = (await db.scalars(select(BusinessRecord).where(
                BusinessRecord.id.in_(task_ids), BusinessRecord.module.in_(["task", "investigation"]), *scope,
            ))).all()
            for task in tasks:
                if task.module == "investigation":
                    investigation_ids.add(task.id)
                investigation_ids.update(_ids(task.data or {}, ("investigation_id", "investigation_record_id")))
                investigation_nos.update(_values(task.data or {}, ("investigation_no",)))
        clue_id_strings = [str(clue.id) for clue in clues]
        evidence_relation = or_(
            BusinessRecord.id.in_(evidence_ids),
            *[cast(BusinessRecord.data[key].as_string(), String).in_(clue_id_strings)
              for key in ("clue_id", "clue_record_id")],
            BusinessRecord.data["clue_no"].as_string().in_([clue.serial_no for clue in clues]),
        )
        related = (await db.scalars(select(BusinessRecord).where(or_(
            (BusinessRecord.module == "evidence") & evidence_relation,
            (BusinessRecord.module == "investigation") & or_(
                BusinessRecord.id.in_(investigation_ids), BusinessRecord.serial_no.in_(investigation_nos),
            ),
        ), *scope))).all()
        records.update({record.id: record for record in related})
    return records


async def case_attachment_parent(case_id, record_id, identity, db):
    """只按目标案件及真实来源关系授权附件父记录，避免扩大独立业务入口。"""
    identity = _case_read_identity(identity)
    case = await _ensure_case_read_module(case_id, identity, db)
    record = (await case_document_records(case, identity, db)).get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="附件不属于该案件或无权访问")
    return record


async def case_document_page(case_id, identity, db, page, page_size):
    identity = _case_read_identity(identity)
    case = await _ensure_case_read_module(case_id, identity, db)
    records = await case_document_records(case, identity, db)
    condition = FileAttachment.record_id.in_(records)
    total = await db.scalar(select(func.count()).select_from(FileAttachment).where(condition))
    files = list((await db.scalars(select(FileAttachment).where(condition)
        .order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc())
        .offset((page - 1) * page_size).limit(page_size))).all())
    users = await _user_display_map({item.uploader for item in files}, db)
    names = {key: _person_display_name(user.display_name, user.username)[0] for key, user in users.items()}
    items = []
    legacy_folder_keys = await legacy_attachment_folder_keys(files, records, db)
    for item in files:
        source = records[item.record_id]
        category = item.category
        if source.module == "investigation":
            category = "鉴别资料"
        elif source.module == "customer":
            category = "客户文档"
        elif source.module == "contract":
            category = "合同文档"
        elif source.module == "evidence" or (source.module == "clue" and item.category in {"取证文件", "取证文档"}):
            category = "取证文档"
        elif source.module == "clue":
            category = "调查文档"
        items.append({**_attachment_dict(item, source, names), "document_category": category,
                      "source_module": source.module, "is_related_document": source.id != case.id,
                      "legacy_document_folder_key": legacy_folder_keys.get(item.id)})
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}
