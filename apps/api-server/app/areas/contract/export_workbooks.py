"""合同及案件阶段导出的工作簿模板渲染。"""
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import xlrd
import xlwt
from fastapi import HTTPException, Response


TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "templates" / "exports"


def _template_style(book, index):
    """保留模板单元格的字体、颜色、边框、对齐与数字格式。"""
    source = book.xf_list[index]
    font = book.font_list[source.font_index]
    style = xlwt.XFStyle()
    for attribute in ("name", "height", "bold", "italic", "colour_index", "underline_type"):
        setattr(style.font, attribute, getattr(font, attribute))
    style.alignment.horz = source.alignment.hor_align
    style.alignment.vert = source.alignment.vert_align
    style.alignment.wrap = source.alignment.text_wrapped
    for side in ("left", "right", "top", "bottom"):
        setattr(style.borders, side, getattr(source.border, f"{side}_line_style"))
        setattr(style.borders, f"{side}_colour", getattr(source.border, f"{side}_colour_index"))
    style.pattern.pattern = source.background.fill_pattern
    style.pattern.pattern_fore_colour = source.background.pattern_colour_index
    style.pattern.pattern_back_colour = source.background.background_colour_index
    style.num_format_str = book.format_map[source.format_key].format_str
    return style


def render_workbook(template: str, rows: list[list], *, summary: float | None = None,
                    groups: list[tuple[int, int, int]] | None = None) -> Response:
    """只加载空白模板，复制格式后写入本次已授权数据。"""
    source = xlrd.open_workbook(str(TEMPLATE_ROOT / f"{template}.xls"), formatting_info=True)
    sheet = source.sheet_by_index(0)
    if sheet.nrows + len(rows) > 65536:
        raise HTTPException(422, "导出行数超过 XLS 上限，请缩小查询范围")
    book = xlwt.Workbook(encoding="utf-8")
    output = book.add_sheet(sheet.name, cell_overwrite_ok=True)
    body_style = xlwt.easyxf("font: name SimSun, height 200; borders: left thin, right thin, top thin, bottom thin; alignment: vert center, wrap on")
    styles = {index: _template_style(source, index) for index in {
        sheet.cell_xf_index(row, column) for row in range(sheet.nrows) for column in range(sheet.ncols)
    }}
    number_style = xlwt.easyxf("font: name SimSun, height 200; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right, vert center", num_format_str="0.00")
    count_style = xlwt.easyxf("font: name SimSun, height 200; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right, vert center", num_format_str="0")
    for column in range(sheet.ncols):
        output.col(column).width = sheet.colinfo_map[column].width
    template_merged = {(row, column) for start, end, left, right in sheet.merged_cells
                       for row in range(start, end) for column in range(left, right)}
    for row in range(sheet.nrows):
        output.row(row).height = sheet.rowinfo_map[row].height
        for column in range(sheet.ncols):
            if (row, column) not in template_merged:
                output.write(row, column, sheet.cell_value(row, column), styles[sheet.cell_xf_index(row, column)])
    for start, end, left, right in sheet.merged_cells:
        output.write_merge(start, end - 1, left, right - 1, sheet.cell_value(start, left), styles[sheet.cell_xf_index(start, left)])
    if summary is not None:
        summary_column = 6 if template == "contract-receivable-detail" else 5
        output.write(0, summary_column, summary, number_style)
    offset = sheet.nrows
    merged = {(row, column) for start, end, column in groups or [] for row in range(start, end + 1)}
    for index, values in enumerate(rows):
        output.row(offset + index).height = 360
        for column, value in enumerate(values):
            if (index, column) not in merged:
                numeric_style = count_style if template == "case-stage-statistics" else number_style
                output.write(offset + index, column, "" if value is None else value,
                             numeric_style if isinstance(value, (int, float)) else body_style)
    for start, end, column in groups or []:
        value = rows[start][column]
        output.write_merge(offset + start, offset + end, column, column,
                           "" if value is None else value,
                           number_style if isinstance(value, (int, float)) else body_style)
    output.set_panes_frozen(True)
    output.set_horz_split_pos(offset)
    output.set_portrait(False)
    output.fit_width_to_pages = 1
    stream = BytesIO()
    book.save(stream)
    filename = f"{sheet.name}.xls"
    return Response(stream.getvalue(), media_type="application/vnd.ms-excel",
                    headers={"Content-Disposition": f"attachment; filename=export.xls; filename*=UTF-8''{quote(filename)}"})
