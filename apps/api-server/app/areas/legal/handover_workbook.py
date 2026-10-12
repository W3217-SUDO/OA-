"""保持交接清单标题、十六列和一式两份签收区的 BIFF 工作簿。"""

from io import BytesIO

import xlwt

from app.areas.legal.case_export_projection import HANDOVER_HEADERS


def handover_workbook(rows: list[list]) -> bytes:
    workbook = xlwt.Workbook(encoding="utf-8")
    sheet = workbook.add_sheet("归档交接清单(一式二份)")
    border = "borders: left thin, right thin, top thin, bottom thin;"
    title = xlwt.easyxf("font: name 微软雅黑, height 320, bold on; align: horiz center, vert center;" + border)
    body = xlwt.easyxf("font: name 微软雅黑, height 240; align: horiz center, vert center, wrap on;" + border)
    note = xlwt.easyxf("font: name 微软雅黑, height 200; align: horiz left, vert center, wrap on;" + border)
    sheet.write_merge(0, 0, 0, 14, "上海沪知律师事务所知产中心案卷交接表", title)
    sheet.row(0).height = 480
    for column, name in enumerate(HANDOVER_HEADERS):
        sheet.col(column).width = 4608
        sheet.write(1, column, name, body)
    for row_index, values in enumerate(rows, 2):
        sheet.row(row_index).height = 1800
        for column, value in enumerate(values):
            sheet.write(row_index, column, value, body)
    footer = len(rows) + 2
    sheet.row(footer).height = 900
    sheet.write_merge(footer, footer, 0, 3, "注:本交接表由中心档案提交人与律师事务所档案接收人，\n交接案卷时当场签收，签收只代表案卷已经交接，\n不代表档案已审核通过，审核情况，以中心案件管理系统审批为准", note)
    sheet.write_merge(footer, footer, 4, 6, "送卷人签名：\n日期：  年   月   日", note)
    sheet.write_merge(footer, footer, 7, 10, "档案接收人签名：\n日期：  年   月   日", note)
    sheet.write_merge(footer, footer, 11, 14, "本表一式2份，提交人、接收人各执一份", note)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
