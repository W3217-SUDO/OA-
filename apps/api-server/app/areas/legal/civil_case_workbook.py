"""民事案件列表按原模板的二十三列表头、边框与交替底色输出。"""

from io import BytesIO

import xlwt

from app.areas.legal.case_export_projection import CIVIL_HEADERS


def civil_case_workbook(rows: list[list[str]]) -> bytes:
    workbook = xlwt.Workbook(encoding="utf-8")
    workbook.set_colour_RGB(xlwt.Style.colour_map["gray50"], 153, 153, 153)
    workbook.set_colour_RGB(xlwt.Style.colour_map["gray40"], 170, 170, 170)
    workbook.set_colour_RGB(xlwt.Style.colour_map["gray25"], 245, 245, 245)
    borders = "borders: left thin, right thin, top thin, bottom thin, left_colour gray40, right_colour gray40, top_colour gray40, bottom_colour gray40;"
    header = xlwt.easyxf("font: name 宋体, height 200, colour white; pattern: pattern solid, fore_colour gray50; align: horiz center, vert center, wrap on;" + borders)
    normal = xlwt.easyxf("font: name 宋体, height 200; align: vert top, wrap on;" + borders)
    shaded = xlwt.easyxf("font: name 宋体, height 200; pattern: pattern solid, fore_colour gray25; align: vert top, wrap on;" + borders)
    # BIFF 每张工作表最多65536行，超过时续表仍使用同一模板，不能截掉全量查询结果。
    for sheet_index, start in enumerate(range(0, max(len(rows), 1), 65535), 1):
        sheet = workbook.add_sheet("案件列表" if sheet_index == 1 else f"案件列表{sheet_index}")
        for column, title in enumerate(CIVIL_HEADERS):
            sheet.write(0, column, title, header)
            sheet.col(column).width = (32 if column in {1, 2, 3, 5, 13, 15, 17, 20} else 20) * 256
        sheet.row(0).height = 400
        for row_index, row in enumerate(rows[start:start + 65535], 1):
            for column, value in enumerate(row):
                sheet.write(row_index, column, value, shaded if row_index % 2 else normal)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
