"""将 AI 回复中的 Markdown 表格转换为可打开的 XLSX 工作簿。"""

from __future__ import annotations

from html import escape
from io import BytesIO
import re
from zipfile import ZIP_DEFLATED, ZipFile


_SEPARATOR_CELL = r":?-{1,}:?"


def _cell_text(value: str) -> str:
    return escape(str(value).strip(), quote=False)


def _split_row(line: str) -> list[str]:
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|") and not value.endswith("\\|"):
        value = value[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in value:
        if char == "\\" and not escaped:
            escaped = True
            current.append(char)
            continue
        if char == "|" and not escaped:
            cells.append("".join(current).replace("\\|", "|").strip())
            current = []
        else:
            current.append(char)
        escaped = False
    cells.append("".join(current).replace("\\|", "|").strip())
    return cells


def _is_separator(line: str) -> bool:
    cells = _split_row(line)
    return bool(cells) and all(re.fullmatch(_SEPARATOR_CELL, cell.replace(" ", "")) for cell in cells)


def markdown_table_rows(content: str) -> list[list[str]]:
    """Extract the first complete Markdown table from an assistant response."""
    lines = [line.strip() for line in str(content or "").splitlines()]
    for index in range(len(lines) - 1):
        if "|" not in lines[index] or not _is_separator(lines[index + 1]):
            continue
        rows: list[list[str]] = [_split_row(lines[index])]
        cursor = index + 2
        while cursor < len(lines) and "|" in lines[cursor] and lines[cursor].strip():
            if not _is_separator(lines[cursor]):
                rows.append(_split_row(lines[cursor]))
            cursor += 1
        width = max((len(row) for row in rows), default=0)
        if width < 1 or len(rows) < 2:
            continue
        return [row + [""] * (width - len(row)) for row in rows]
    return []


def has_markdown_table(content: str) -> bool:
    return bool(markdown_table_rows(content))


def _worksheet_xml(rows: list[list[str]]) -> str:
    body = []
    for row in rows:
        cells = "".join(f'<c t="inlineStr"><is><t>{_cell_text(value)}</t></is></c>' for value in row)
        body.append(f"<row>{cells}</row>")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheetData>{''.join(body)}</sheetData></worksheet>")


def markdown_table_xlsx(content: str) -> bytes:
    rows = markdown_table_rows(content)
    if not rows:
        raise ValueError("回答中没有可保存的 Markdown 表格")
    files = {
        "[Content_Types].xml": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'),
        "_rels/.rels": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'),
        "xl/workbook.xml": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="AI表格" sheetId="1" r:id="rId1"/></sheets></workbook>'),
        "xl/_rels/workbook.xml.rels": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'),
        "xl/worksheets/sheet1.xml": _worksheet_xml(rows),
    }
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path, value in files.items():
            archive.writestr(path, value.encode("utf-8"))
    return output.getvalue()
