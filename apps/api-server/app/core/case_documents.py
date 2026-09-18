"""案件文档按原始业务关系聚合，保留附件归属和访问权限。"""
import re

from sqlalchemy import String, cast, func, or_, select

from app.models import BusinessRecord, FileAttachment
from app.core.permissions import _ensure_record_module, _record_scope_conditions
from app.core.storage import _attachment_dict
from app.core.formatters import _person_display_name, _user_display_map


def _values(data, keys):
    values = []
    for key in keys:
        value = data.get(key)
        values.extend(value if isinstance(value, list) else re.split(r"[,，;；、|]+", str(value or "")))
    return {str(value).strip() for value in values if str(value or "").strip()}


def _ids(data, keys):
    return {int(value) for value in _values(data, keys) if value.isdigit() and int(value) > 0}


async def case_document_page(case_id, identity, db, page, page_size):
    case = await _ensure_record_module(case_id, "case", identity, db)
    data = case.data or {}
    scope = await _record_scope_conditions(identity, db)
    clue_ids = _ids(data, ("clue_id", "clue_record_id", "investigation_clue_id", "investigation_clue_ids"))
    clue_nos = _values(data, ("clue_no", "investigation_clue", "source_clue_no", "investigation_clue_nos"))
    # 明确的正向关联优先，避免历史反向关系将其他案件的线索混入。
    if clue_ids:
        relation = BusinessRecord.id.in_(clue_ids)
    elif clue_nos:
        relation = BusinessRecord.serial_no.in_(clue_nos)
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
    source_contracts = {str(source.get("data", {}).get("contract_no") or "") for source in data.get("merged_sources", [])}
    source_contracts.discard("")
    if source_contracts:
        contracts = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "contract", BusinessRecord.serial_no.in_(source_contracts),
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
    condition = FileAttachment.record_id.in_(records)
    total = await db.scalar(select(func.count()).select_from(FileAttachment).where(condition))
    files = list((await db.scalars(select(FileAttachment).where(condition)
        .order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc())
        .offset((page - 1) * page_size).limit(page_size))).all())
    users = await _user_display_map({item.uploader for item in files}, db)
    names = {key: _person_display_name(user.display_name, user.username)[0] for key, user in users.items()}
    items = []
    for item in files:
        source = records[item.record_id]
        category = item.category
        if source.module == "investigation":
            category = "鉴别资料"
        elif source.module == "contract":
            category = "合同文档"
        elif source.module == "evidence" or (source.module == "clue" and item.category in {"取证文件", "取证文档"}):
            category = "取证文档"
        elif source.module == "clue":
            category = "调查文档"
        items.append({**_attachment_dict(item, source, names), "document_category": category,
                      "source_module": source.module, "is_related_document": source.id != case.id})
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}
