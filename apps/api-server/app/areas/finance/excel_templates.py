"""财务 Excel 模板的 BIFF 版式读取和真实数据渲染。"""

from datetime import date, datetime
from copy import copy
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import xlrd
import xlwt


TEMPLATE_DIRECTORY = Path(__file__).with_name("export_templates")
MONEY_COLUMNS = {
    "F21": {9}, "F27": {12, 14, 18, 21}, "F31": {12, 14, 18, 21}, "F57": {12, 14, 18, 21},
    "F29": {10, 11, 12, 13, 23}, "F33": {10, 11, 12, 13, 23},
    "F35": {10, 12}, "F37": {10, 12}, "F39": {10, 12}, "F51": {2, 3, 13, 18, 19},
    "F53": {3, 4, 5, 7, 8},
}


def copy_style(book, index):
    """复制原件单元格样式，不复制业务值。"""
    xf = book.xf_list[index]
    source = book.font_list[xf.font_index]
    style = xlwt.XFStyle()
    for name in ("name", "height", "bold", "italic", "colour_index", "underline_type", "struck_out", "outline", "shadow", "escapement", "family", "character_set"):
        setattr(style.font, name if name != "character_set" else "charset", getattr(source, name))
    style.num_format_str = book.format_map[xf.format_key].format_str
    alignment = xf.alignment
    for target, origin in (("horz", "hor_align"), ("vert", "vert_align"), ("wrap", "text_wrapped"), ("rota", "rotation"), ("indent", "indent_level"), ("shri", "shrink_to_fit"), ("dire", "text_direction")):
        setattr(style.alignment, target, getattr(alignment, origin))
    border = xf.border
    for edge in ("left", "right", "top", "bottom"):
        setattr(style.borders, edge, getattr(border, edge + "_line_style"))
        setattr(style.borders, edge + "_colour", getattr(border, edge + "_colour_index"))
    style.pattern.pattern = xf.background.fill_pattern
    style.pattern.pattern_fore_colour = xf.background.pattern_colour_index
    style.pattern.pattern_back_colour = xf.background.background_colour_index
    return style


@lru_cache(maxsize=12)
def read_template(template_id):
    return xlrd.open_workbook(str(TEMPLATE_DIRECTORY / (template_id + ".xls")), formatting_info=True)


class FinanceWorkbook:
    """数据和动态合并区域由业务渲染器提供，字体、列宽和行高来自原模板。"""

    def __init__(self, template_id):
        self.template_id = template_id
        self.source = read_template(template_id)
        self.template = self.source.sheet_by_index(0)
        self.book = xlwt.Workbook(encoding="utf-8")
        for index, colour in self.source.colour_map.items():
            if 8 <= index <= 63 and colour:
                self.book.set_colour_RGB(index, *colour)
        self.sheet = self.book.add_sheet(self.template.name, cell_overwrite_ok=True)
        self.styles = {index: copy_style(self.source, index) for index in range(len(self.source.xf_list))}
        self.money_styles = {}
        for index, info in self.template.colinfo_map.items():
            self.sheet.col(index).width = info.width
            self.sheet.col(index).hidden = info.hidden

    def style(self, source_row, column):
        index = self.template.cell_xf_index(source_row, column)
        columns = ({3, 4, 5, 7, 8} if source_row == 5 else {4, 5}) if self.template_id == "F55" else MONEY_COLUMNS[self.template_id]
        if source_row not in (0, 4) and column in columns:
            if index not in self.money_styles:
                style = copy(self.styles[index])
                style.num_format_str = "#,##0.00" if self.template_id in {"F29", "F33", "F35", "F37", "F39"} else "0.00"
                self.money_styles[index] = style
            return self.money_styles[index]
        return self.styles[index]

    def row(self, index, values, style_row=1):
        if len(values) != self.template.ncols:
            raise ValueError("导出列数与原模板不一致")
        source_row = min(style_row, self.template.nrows - 1)
        info = self.template.rowinfo_map.get(source_row)
        if info:
            self.sheet.row(index).height = info.height
            self.sheet.row(index).height_mismatch = info.height_mismatch
        for column, value in enumerate(values):
            if isinstance(value, (date, datetime)):
                value = value.isoformat()[:10]
            elif isinstance(value, (tuple, list)):
                value = "、".join(str(part) for part in value)
            self.sheet.write(index, column, value, self.style(source_row, column))

    def header(self, index=0, template_row=0):
        self.row(index, self.template.row_values(template_row), template_row)

    def merge(self, start, end, columns, values, style_row=1):
        if start > end:
            return
        for column in columns:
            style = self.style(style_row, column)
            self.sheet.write_merge(start, end, column, column, values[column], style)

    def content(self):
        target = BytesIO()
        self.book.save(target)
        return target.getvalue()


def render_rows(template_id, values):
    workbook = FinanceWorkbook(template_id)
    workbook.header()
    for index, row in enumerate(values, 1):
        workbook.row(index, row)
    return workbook.content()
