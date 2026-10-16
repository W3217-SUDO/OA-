"""历史和现代结算导出共用列表读取边界，不接受历史键办理写操作。"""

from datetime import date
from inspect import signature

from fastapi import HTTPException

from app.core.imported_settlement_projection import NORMAL_STATES, read_imported_settlement_page


async def query_export_rows(reader, request, identity, db):
    parameters = signature(reader).parameters
    values = {}
    for key, value in (request.query_params.items() if request is not None else ()):
        name = "application_status" if key == "status" else key
        if name not in parameters or name in {"identity", "db", "page", "page_size"}:
            continue
        if name.endswith(("_from", "_to")):
            try:
                value = date.fromisoformat(value)
            except ValueError as exc:
                raise HTTPException(422, "导出日期格式无效") from exc
        values[name] = value
    if "application_status" in parameters:
        values.setdefault("application_status", "待审批")
    result = await reader(**values, identity=identity, db=db, page=1, page_size=2147483647)
    return result["items"]


async def append_imported_export_rows(rows, projection_ids, identity, db, *, mode):
    if not projection_ids.strip():
        return rows
    keys = {value.strip() for value in projection_ids.split(",") if value.strip()}
    prefix = "legacy-normal:" if mode == "normal" else "legacy-archive:"
    if not keys or any(not key.startswith(prefix) or not key[len(prefix):].isdigit()
                       or int(key[len(prefix):]) <= 0 for key in keys):
        raise HTTPException(422, "历史结算投影键无效")
    result = await read_imported_settlement_page(rows, identity, db, mode=mode, statuses=set(NORMAL_STATES.values()),
                                                projection_ids=keys)
    return result["items"]


async def enrich_general_export_rows(rows, identity, db, kind):
    from app.areas.finance.export_projection import enrich_settlement_exports

    modern = [row for row in rows if not row.get("read_only")]
    if modern:
        await enrich_settlement_exports(modern, identity, db, include_invoice_fields=kind == "receipt")
    for row in rows:
        if row.get("read_only"):
            details = row["data"].get("allocation_details") or []
            if kind != "case" and any(detail.get("kind") is None for detail in details):
                raise HTTPException(409, "历史结算费用类别缺少唯一来源，不能静默省略到账分类导出")
    return rows


def _provenance_rows(rows):
    historical = [row for row in rows if row.get("amount_basis") == "legacy_snapshot"]
    if not historical:
        return []
    columns = ("投影标识", "金额口径", "来源说明", "原始来源表", "原始主键", "原始状态值", "财务中心", "本地分配操作")
    values = [columns]
    for row in historical:
        source = row.get("provenance") or {}
        values.append((row["id"], "legacy_snapshot", row["source_label"], source.get("source_table"),
            source.get("legacy_id"), row.get("source_status"), row["data"].get("finance_scope"),
            "已发生本地分配操作" if row.get("has_local_allocation_activity") else "无本地分配摘要"))
    return values


def append_settlement_provenance(workbook, rows):
    values = _provenance_rows(rows)
    if not values:
        return
    sheet = workbook.book.add_sheet("来源说明")
    for index, parts in enumerate(values):
        for column, value in enumerate(parts):
            sheet.write(index, column, value)
            sheet.col(column).width = 7000


def settlement_provenance_xml(rows):
    from xml.etree.ElementTree import Element, SubElement, tostring

    values = _provenance_rows(rows)
    if not values:
        return ""
    sheet = Element("Worksheet", {"ss:Name": "来源说明"})
    table = SubElement(sheet, "Table")
    for parts in values:
        row = SubElement(table, "Row")
        for value in parts:
            cell = SubElement(row, "Cell")
            SubElement(cell, "Data", {"ss:Type": "String"}).text = str(value) if value is not None else ""
    return tostring(sheet, encoding="unicode")


def render_archive_settlement_export(template_id, values, rows):
    from app.areas.finance.excel_templates import FinanceWorkbook

    workbook = FinanceWorkbook(template_id)
    workbook.header()
    for index, value in enumerate(values, 1):
        workbook.row(index, value)
    append_settlement_provenance(workbook, rows)
    return workbook.content()
