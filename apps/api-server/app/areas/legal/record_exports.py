"""通用业务记录导出。"""
from fastapi import APIRouter
from app.core.dependencies import AsyncSession, BusinessRecord, Depends, Query, Response, csv, current_identity, date, get_db, io, json, select, settings

router = APIRouter()


@router.get(f"{settings.api_prefix}/records/export")
async def export_records(
    module: str = Query(min_length=1, max_length=32),
    title: str = "", serial_no: str = "", record_type: str = Query("", alias="type"),
    customer: str = "", case_no: str = "", fee_type: str = "", contract_body: str = "",
    source_person: str = "", signed_at_start: str = "", signed_at_end: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    await _require_record_module_menu(module, identity, db, action="导出")
    conditions = [BusinessRecord.module == module, *(await _record_scope_conditions(identity, db))]
    records = list((await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.created_at))).all())
    def contains(value: object, needle: str) -> bool:
        return not needle or needle.lower() in str(value or "").lower()
    def matches(item: BusinessRecord) -> bool:
        data = item.data or {}
        if not contains(item.title, title) or not contains(item.serial_no, serial_no): return False
        if record_type and data.get("type") != record_type: return False
        if not contains(item.customer, customer) or not contains(data.get("case_no"), case_no): return False
        if fee_type and data.get("fee_type") != fee_type: return False
        if contract_body and data.get("contract_body") != contract_body: return False
        if source_person and not contains(data.get("source_person") or item.owner, source_person): return False
        signed = str(data.get("signed_at") or "")[:10]
        if signed_at_start and (not signed or signed < signed_at_start): return False
        if signed_at_end and (not signed or signed > signed_at_end): return False
        return True
    records = [item for item in records if matches(item)]
    allowed_fields = await _allowed_field_keys(identity, db)
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(["业务编号", "标题", "客户/主体", "状态", "负责人", "部门", "说明", "扩展数据", "创建时间", "更新时间"])
    for item in records:
        visible = _record_dict(item, allowed_fields)
        writer.writerow([visible["serial_no"], visible["title"], visible["customer"], visible["status"], visible["owner"], visible["department"], visible["description"], json.dumps(visible.get("data") or {}, ensure_ascii=False), visible["created_at"], visible["updated_at"]])
    content = "\ufeff" + output.getvalue()
    return Response(content=content.encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{module}-{date.today()}.csv"'})

@router.get(f"{settings.api_prefix}/records/export-excel")
async def export_records_excel(
    module: str = Query(min_length=1, max_length=32),
    title: str = "", serial_no: str = "", record_type: str = Query("", alias="type"),
    customer: str = "", case_no: str = "", fee_type: str = "", contract_body: str = "",
    source_person: str = "", signed_at_start: str = "", signed_at_end: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """按可见范围导出兼容既有 Excel 格式的工作簿。"""
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys, _excel_response, _record_dict,
    )
    await _require_record_module_menu(module, identity, db, action="导出")
    conditions = [BusinessRecord.module == module, *(await _record_scope_conditions(identity, db))]
    records = list((await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.created_at))).all())
    def contains(value: object, needle: str) -> bool:
        return not needle or needle.lower() in str(value or "").lower()
    def matches(item: BusinessRecord) -> bool:
        data = item.data or {}
        if not contains(item.title, title) or not contains(item.serial_no, serial_no): return False
        if record_type and data.get("type") != record_type: return False
        if not contains(item.customer, customer) or not contains(data.get("case_no"), case_no): return False
        if fee_type and data.get("fee_type") != fee_type: return False
        if contract_body and data.get("contract_body") != contract_body: return False
        if source_person and not contains(data.get("source_person") or item.owner, source_person): return False
        signed = str(data.get("signed_at") or "")[:10]
        if signed_at_start and (not signed or signed < signed_at_start): return False
        if signed_at_end and (not signed or signed > signed_at_end): return False
        return True
    records = [item for item in records if matches(item)]
    allowed_fields = await _allowed_field_keys(identity, db)
    headers = ["业务编号", "标题", "客户/主体", "状态", "负责人", "部门", "说明", "扩展数据", "创建时间", "更新时间"]
    rows = []
    for item in records:
        visible = _record_dict(item, allowed_fields)
        rows.append([
            visible["serial_no"], visible["title"], visible["customer"], visible["status"],
            visible["owner"], visible["department"], visible["description"],
            json.dumps(visible.get("data") or {}, ensure_ascii=False), visible["created_at"], visible["updated_at"],
        ])
    return _excel_response(f"{module}-{date.today()}.xls", headers, rows)
