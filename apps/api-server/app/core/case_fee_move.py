"""案件费用“移到其他案子”（10.22 第8行，10.26 第11行调整）。

10.26 第11行用户要求只保留两条限制：
- 目标案件必须与当前案件属于同一客户（客户记录 ID → 客户编号 → 客户名称，取两案都有的最精确口径）；
- 一次只迁移一条费用（接口按单条费用操作）。
除此之外不再设其他限制：已有申请付款/开票/回款/退费等后续单据、案件归档或合并状态、费用提交人、
目标案件是否在当前账号可见范围内，都不再拦截。后续单据按费用 ID 关联，随费用一起出现在目标案件。
合同编号保留原值；原案、目标案、费用各记一条系统日志。

501337（fwl 11-04）：一条线索和它的证物（公证书号、仓库位置）、它的公证费/公证服务费是一体的，
移任何一项，整条线索这几样一起移到目标案件；不属于线索的费用仍只移这一笔。已移过的历史数据不动。
"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import or_, select

from app.models import BusinessRecord, WorkflowEvent

MOVABLE_FEE_SCOPES = {"律所", "平台"}


def _text(value) -> str:
    return str(value or "").strip()


def _fee_scope(fee: BusinessRecord) -> str:
    return _text((fee.data or {}).get("expense_scope")) or "律所"


def same_customer(source: BusinessRecord, target: BusinessRecord) -> bool:
    """客户记录 ID → 客户编号 → 客户名称，取两案都有的最精确口径比较。"""
    source_data, target_data = source.data or {}, target.data or {}
    for keys in (("customer_record_id", "customer_id"), ("customer_no",)):
        left = next((_text(source_data.get(key)) for key in keys if _text(source_data.get(key))), "")
        right = next((_text(target_data.get(key)) for key in keys if _text(target_data.get(key))), "")
        if left and right:
            return left == right
    return bool(_text(source.customer)) and _text(source.customer) == _text(target.customer)


CLUE_LINK_KEYS = ("investigation_clue_ids", "investigation_clue_nos", "investigation_clue_id", "investigation_clue",
                  "clue_record_id", "clue_id", "clue_no", "source_clue_no", "clue_nos")


async def clue_bundle(clue: BusinessRecord, source: BusinessRecord, db) -> tuple[list[BusinessRecord], list[BusinessRecord]]:
    """一条线索的证物和本案里属于这条线索的费用（数据库里粗筛，再逐条按线索 ID/GUID/证物 GUID 核对）。"""
    data = clue.data or {}
    clue_guid = _text(data.get("clue_guid"))
    evidence_conditions = [BusinessRecord.data["clue_record_id"].as_string() == str(clue.id),
                           BusinessRecord.data["clue_no"].as_string() == clue.serial_no]
    if clue_guid:
        evidence_conditions.append(BusinessRecord.data["clue_guid"].as_string() == clue_guid)
    evidences = [item for item in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "evidence", BusinessRecord.deleted_at.is_(None), or_(*evidence_conditions),
    ).order_by(BusinessRecord.id))).all() if _text((item.data or {}).get("clue_record_id")) == str(clue.id)
        or _text((item.data or {}).get("clue_no")) == clue.serial_no
        or (clue_guid and _text((item.data or {}).get("clue_guid")) == clue_guid)]
    evidence_guids = {_text((item.data or {}).get("evidence_guid")) for item in evidences} - {""}
    candidates = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.deleted_at.is_(None), BusinessRecord.status != "已删除",
        or_(BusinessRecord.data["case_no"].as_string() == source.serial_no,
            BusinessRecord.data["case_record_id"].as_string() == str(source.id)),
    ).order_by(BusinessRecord.id))).all()

    def belongs(fee: BusinessRecord) -> bool:
        fee_data = fee.data or {}
        return (_text(fee_data.get("clue_record_id")) == str(clue.id)
                or bool(clue_guid and _text(fee_data.get("clue_guid")) == clue_guid)
                or _text(fee_data.get("evidence_guid")) in evidence_guids)
    return evidences, [fee for fee in candidates if belongs(fee)]


def _clue_link_fields(clues: list[BusinessRecord]) -> dict:
    ids = [item.id for item in clues]
    nos = [item.serial_no for item in clues]
    return {
        "investigation_clue_ids": ids, "investigation_clue_nos": nos, "clue_nos": nos,
        "investigation_clue_id": ids[0] if ids else None, "clue_record_id": ids[0] if ids else None, "clue_id": ids[0] if ids else None,
        "investigation_clue": "、".join(nos), "clue_no": nos[0] if nos else "", "source_clue_no": nos[0] if nos else "",
    }


async def _case_clue_records(case: BusinessRecord, db) -> list[BusinessRecord]:
    from app.core.case_relations import case_clues
    return await case_clues(case, db)


async def _refresh_case_clue_fields(case: BusinessRecord, clues: list[BusinessRecord], db) -> None:
    """改案件的关联线索字段，并按线索重算调查员（保留个案另加的调查员，501293）。"""
    from app.core.cases import case_investigators_from_clues
    data = dict(case.data or {})
    extra = [(row.get("name") or "", row.get("username") or "") for row in data.get("investigator_clues") or [] if row.get("extra")]
    data.update(_clue_link_fields(clues))
    if clues or extra:
        data.update(await case_investigators_from_clues(clues, db, extra))
    case.data = data


def _point_to_case(record: BusinessRecord, source: BusinessRecord, target: BusinessRecord, moved: dict) -> None:
    data = dict(record.data or {})
    if str(data.get("converted_case_id") or "") == str(source.id):
        data["converted_case_id"] = target.id
    for key in ("converted_case_no", "linked_case_no"):
        if _text(data.get(key)) == source.serial_no:
            data[key] = target.serial_no
    record.data = {**data, "case_id": target.id, "case_record_id": target.id, "case_no": target.serial_no, **moved}


async def move_clue_bundle(clue: BusinessRecord, source: BusinessRecord, target: BusinessRecord, identity: dict, db,
                           *, extra_fee: BusinessRecord | None = None) -> dict:
    """把一条线索连同它的证物、费用移到目标案件（调用方已校验权限和同一客户；不提交事务）。"""
    evidences, fees = await clue_bundle(clue, source, db)
    if extra_fee is not None and all(item.id != extra_fee.id for item in fees):
        fees.append(extra_fee)
    moved = {"moved_from_case_id": source.id, "moved_from_case_no": source.serial_no,
             "moved_at": datetime.now().isoformat(timespec="seconds"), "moved_by": identity["username"]}
    for fee in fees:
        _point_to_case(fee, source, target, {**moved, "clue_record_id": clue.id})
    for evidence in evidences:
        _point_to_case(evidence, source, target, moved)
    _point_to_case(clue, source, target, {})
    source_clues = [item for item in await _case_clue_records(source, db) if item.id != clue.id]
    target_clues = [item for item in await _case_clue_records(target, db) if item.id != clue.id] + [clue]
    await _refresh_case_clue_fields(source, source_clues, db)
    await _refresh_case_clue_fields(target, target_clues, db)
    parts = [f"线索 {clue.serial_no}"]
    if evidences:
        parts.append("证物 " + "、".join(_text((item.data or {}).get("certificate_no")) or item.serial_no for item in evidences))
    if fees:
        parts.append("费用 " + "、".join(f"{item.serial_no}（{item.title}）" for item in fees))
    comment = f"{'；'.join(parts)} 由 {source.serial_no} 一起移到 {target.serial_no}"
    for record in (source, target, clue, *fees):
        db.add(WorkflowEvent(record_id=record.id, action="线索及证物、费用移到其他案件", from_status=record.status,
                             to_status=record.status, operator=identity["username"], comment=comment))
    return {"clue": clue.serial_no, "evidences": [item.serial_no for item in evidences], "fees": [item.serial_no for item in fees], "comment": comment}


async def _target_case(source: BusinessRecord, target_case_no: str, db) -> BusinessRecord:
    target_no = _text(target_case_no)
    if target_no == source.serial_no:
        raise HTTPException(status_code=422, detail="目标案件不能与当前案件相同")
    target = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.serial_no == target_no,
        BusinessRecord.status != "已删除", BusinessRecord.deleted_at.is_(None),
    ))
    if not target:
        raise HTTPException(status_code=404, detail="未找到目标案件，请核对案件编号")
    return target


async def fee_clue(fee: BusinessRecord, source: BusinessRecord, db, clue_id: int | None = None) -> BusinessRecord | None:
    """这笔费用属于本案哪条线索：费用里记了的按记录；没记的用操作人选的线索。"""
    clues = await _case_clue_records(source, db)
    data = fee.data or {}
    for clue in clues:
        if str(data.get("clue_record_id") or "") == str(clue.id) or (
                _text(data.get("clue_guid")) and _text(data.get("clue_guid")) == _text((clue.data or {}).get("clue_guid"))):
            return clue
        if _text(data.get("evidence_guid")):
            evidences, _ = await clue_bundle(clue, source, db)
            if any(_text((item.data or {}).get("evidence_guid")) == _text(data.get("evidence_guid")) for item in evidences):
                return clue
    if clue_id:
        chosen = next((clue for clue in clues if clue.id == clue_id), None)
        if chosen is None:
            raise HTTPException(status_code=422, detail="所选线索不属于当前案件")
        return chosen
    return None


async def move_case_fee(fee_id: int, target_case_no: str, identity: dict, db, clue_id: int | None = None) -> BusinessRecord:
    from app.core.cases import _case_action_granted
    from app.core.permissions import _ensure_record_module

    fee = await _ensure_record_module(fee_id, "finance", identity, db)
    if fee.status == "已删除":
        raise HTTPException(status_code=404, detail="费用记录不存在")
    if _fee_scope(fee) not in MOVABLE_FEE_SCOPES:
        raise HTTPException(status_code=422, detail="只有律所费用和平台费用可以移到其他案子")
    data = dict(fee.data or {})
    source_id = int(data.get("case_record_id") or data.get("case_id") or 0)
    source = await db.get(BusinessRecord, source_id) if source_id else None
    if not source or source.module != "case":
        raise HTTPException(status_code=409, detail="该费用没有关联有效案件，不能移到其他案子")
    if _text(data.get("case_no")) and _text(data.get("case_no")) != source.serial_no:
        raise HTTPException(status_code=409, detail="费用的案件 ID 与案件编号指向不同案件，请先修正关联")
    await _ensure_record_module(source.id, "case", identity, db)
    if not (await _case_action_granted(identity, db, "case.fee.move")
            or await _case_action_granted(identity, db, "case.fee.update")):
        raise HTTPException(status_code=403, detail="当前账号没有“移到其他案件”权限")
    target = await _target_case(source, target_case_no, db)
    for record in sorted((source, target, fee), key=lambda item: item.id):
        await db.refresh(record, with_for_update=True)
    if not same_customer(source, target):
        raise HTTPException(status_code=422, detail="目标案件与当前案件不属于同一客户，不允许迁移")
    clue = await fee_clue(fee, source, db, clue_id)
    if clue is not None:
        # 501337：属于线索的费用，整条线索（证物、同线索费用）一起移
        await db.refresh(clue, with_for_update=True)
        await move_clue_bundle(clue, source, target, identity, db, extra_fee=fee)
        await db.commit()
        await db.refresh(fee)
        return fee
    moved_at = datetime.now().isoformat(timespec="seconds")
    if str(data.get("converted_case_id") or "") == str(source.id):
        data["converted_case_id"] = target.id
    if _text(data.get("converted_case_no")) == source.serial_no:
        data["converted_case_no"] = target.serial_no
    # 合同字段保留原值（用户确认）；只改案件关联的 id 与案号两套字段。
    fee.data = {**data, "case_id": target.id, "case_record_id": target.id, "case_no": target.serial_no,
                "moved_from_case_id": source.id, "moved_from_case_no": source.serial_no,
                "moved_at": moved_at, "moved_by": identity["username"]}
    comment = f"费用 {fee.serial_no}（{fee.title}）由 {source.serial_no} 移到 {target.serial_no}"
    for record_id in (fee.id, source.id, target.id):
        record = fee if record_id == fee.id else source if record_id == source.id else target
        db.add(WorkflowEvent(record_id=record_id, action="案件费用移到其他案件", from_status=record.status,
                             to_status=record.status, operator=identity["username"], comment=comment))
    await db.commit()
    await db.refresh(fee)
    return fee


async def move_case_clue(case_id: int, clue_id: int, target_case_no: str, identity: dict, db) -> dict:
    """案件详情“线索信息”里把一条线索移到其他案子：线索、证物、该线索的费用一起移（501337）。"""
    from app.core.cases import _case_action_granted
    from app.core.permissions import _ensure_record_module

    source = await _ensure_record_module(case_id, "case", identity, db)
    if not (await _case_action_granted(identity, db, "case.fee.move")
            or await _case_action_granted(identity, db, "case.fee.update")
            or await _case_action_granted(identity, db, "case.detail.update")):
        raise HTTPException(status_code=403, detail="当前账号没有移动案件线索的权限")
    clue = next((item for item in await _case_clue_records(source, db) if item.id == clue_id), None)
    if clue is None:
        raise HTTPException(status_code=404, detail="这条线索不属于当前案件")
    target = await _target_case(source, target_case_no, db)
    for record in sorted((source, target, clue), key=lambda item: item.id):
        await db.refresh(record, with_for_update=True)
    if not same_customer(source, target):
        raise HTTPException(status_code=422, detail="目标案件与当前案件不属于同一客户，不允许迁移")
    result = await move_clue_bundle(clue, source, target, identity, db)
    await db.commit()
    return result


async def clue_bundle_preview(case_id: int, clue_id: int, identity: dict, db) -> dict:
    """移动前预览：这条线索会一起带走的证物和费用。"""
    from app.core.permissions import _ensure_record_module

    source = await _ensure_record_module(case_id, "case", identity, db)
    clue = next((item for item in await _case_clue_records(source, db) if item.id == clue_id), None)
    if clue is None:
        raise HTTPException(status_code=404, detail="这条线索不属于当前案件")
    evidences, fees = await clue_bundle(clue, source, db)
    return {
        "clue": {"id": clue.id, "serial_no": clue.serial_no, "title": clue.title},
        "evidences": [{"id": item.id, "serial_no": item.serial_no, "certificate_no": _text((item.data or {}).get("certificate_no")),
                       "location": _text((item.data or {}).get("storage_location_name") or (item.data or {}).get("storage_location"))} for item in evidences],
        "fees": [{"id": item.id, "serial_no": item.serial_no, "title": item.title, "amount": (item.data or {}).get("amount")} for item in fees],
    }


async def fee_clue_fields(clue_record_id: int | None, case_record: BusinessRecord | None, db) -> dict:
    """新增/修改费用时登记所属线索（501337 fwl 11-04）：只能选本案关联的线索；不传不改，0 清空。"""
    if clue_record_id is None:
        return {}
    if not clue_record_id:
        return {"clue_record_id": None}
    if case_record is None or all(item.id != clue_record_id for item in await _case_clue_records(case_record, db)):
        raise HTTPException(status_code=422, detail="所属线索不是本案关联的线索")
    return {"clue_record_id": clue_record_id}
