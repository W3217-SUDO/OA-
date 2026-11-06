"""公证书号仓库信息导入（501692/501694，fwl 11-06）：读上传的 Excel（.xlsx/.xls）或 UTF-8 CSV，返回 [(行号, {列名: 值})]；
并按线索号 / 公证书号找到要更新的证物（旧系统迁来的公证书号、仓库、发票号都在证物上）。"""

from __future__ import annotations

import csv
from datetime import date, datetime
import io

from fastapi import HTTPException

SUFFIXES = (".xlsx", ".xls", ".csv")
# 表头所在行：含“线索号/线索编号”或“公证书号/证书号”的第一行（模板上方可能有标题行）。
HEADER_KEYS = {"线索号", "线索编号", "公证书号", "证书号", "clue_no", "certificate_no"}


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def _from_matrix(matrix: list[list[str]]) -> list[tuple[int, dict]]:
    header_index = next((index for index, row in enumerate(matrix[:10]) if HEADER_KEYS & {cell.strip() for cell in row}), None)
    if header_index is None:
        raise HTTPException(status_code=422, detail="没有找到表头：第一行应包含“线索号”或“公证书号”列")
    header = [cell.strip() for cell in matrix[header_index]]
    rows = []
    for offset, values in enumerate(matrix[header_index + 1:], start=header_index + 2):
        row = {name: (values[index] if index < len(values) else "") for index, name in enumerate(header) if name}
        if any(value for value in row.values()):
            rows.append((offset, row))
    return rows


def read_rows(filename: str, raw: bytes) -> list[tuple[int, dict]]:
    name = (filename or "").lower()
    if not name.endswith(SUFFIXES):
        raise HTTPException(status_code=422, detail="仅支持 Excel（.xlsx / .xls）或 UTF-8 CSV 文件")
    if name.endswith(".csv"):
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail="CSV 必须使用 UTF-8 编码；也可以直接上传 Excel") from exc
        return _from_matrix([[cell.strip() for cell in row] for row in csv.reader(io.StringIO(content))])
    try:
        if name.endswith(".xlsx"):
            from openpyxl import load_workbook
            sheet = load_workbook(io.BytesIO(raw), read_only=True, data_only=True).worksheets[0]
            matrix = [[_cell(value) for value in row] for row in sheet.iter_rows(values_only=True)]
        else:
            import xlrd
            book = xlrd.open_workbook(file_contents=raw)
            sheet = book.sheet_by_index(0)
            matrix = []
            for index in range(sheet.nrows):
                values = []
                for cell in sheet.row(index):
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        values.append(_cell(xlrd.xldate.xldate_as_datetime(cell.value, book.datemode)))
                    else:
                        values.append(_cell(cell.value))
                matrix.append(values)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Excel 文件无法读取，请确认文件没有损坏、没有加密") from exc
    return _from_matrix(matrix)


def evidence_certificate(data: dict) -> str:
    return str(data.get("certificate_no") or data.get("notarial_no") or data.get("notary_no") or "").strip()


def pick_evidence(candidates: list, certificate_no: str):
    """同一线索下只有一个证物就是它；有多个时按公证书号对上唯一一个，对不上返回错误说明。"""
    if len(candidates) == 1:
        return candidates[0], ""
    if not candidates:
        return None, ""
    if certificate_no:
        matched = [item for item in candidates if evidence_certificate(item.data or {}).casefold() == certificate_no.casefold()]
        if len(matched) == 1:
            return matched[0], ""
    return None, f"该线索下有 {len(candidates)} 个证物，请填写与其中一个证物一致的公证书号"
