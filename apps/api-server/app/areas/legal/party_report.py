"""当事人尽职调查报告（Word）的商务版式（501226，陶国南 11-04 要求参考商业尽调报告做得更商务、专业）。

结构：封面 → 目录 → 报告摘要（风险等级色块、可否作为被告、能否执行到、关键风险、律师建议）→ 八章正文 → 数据来源与免责声明。
只排版，不调接口；工商信息、风险数据、可诉性判断都由调用方传入。
"""
from datetime import date
from io import BytesIO

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from app.areas.legal import party_risk

FIRM = "上海沪知律师事务所"
FONT = "微软雅黑"
GREEN, GREEN_DARK, GREEN_LIGHT = "0B7A45", "075C33", "E8F5EE"
INK, GREY, LINE, STRIPE = "1F2A37", "6B7280", "D5DCE3", "F6F8FA"
LEVELS = {"高": "C0392B", "中": "D9822B", "低": "2E9E5B", "待评估": "8A94A6"}
CHAPTERS = ["企业基本信息", "股东与主要人员", "涉诉情况", "执行与信用", "经营风险", "可诉性分析", "执行可能性分析", "数据来源与声明"]
NUMBERS = "一二三四五六七八九十"


def _rgb(hex_color: str) -> RGBColor:
    return RGBColor.from_string(hex_color)


def _font(run, size: float | None = None, *, bold: bool | None = None, color: str | None = None) -> None:
    run.font.name = FONT
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONT)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color:
        run.font.color.rgb = _rgb(color)


def _shade(cell, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


def _borders(table, color: str = LINE, size: int = 4, inside: bool = True) -> None:
    properties = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single" if inside or edge in ("top", "left", "bottom", "right") else "nil")
        element.set(qn("w:sz"), str(size))
        element.set(qn("w:color"), color)
        borders.append(element)
    properties.append(borders)


def _cell_text(cell, text: str, *, size: float = 9, bold: bool = False, color: str = INK, align=None) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(2)
    if align is not None:
        paragraph.alignment = align
    _font(paragraph.add_run(text), size, bold=bold, color=color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def _widths(table, widths_cm: list[float]) -> None:
    """固定表格总宽和列宽（tblW + tblLayout fixed + tblGrid），WPS、手机预览才不会按内容挤窄。"""
    table.autofit = False
    properties = table._tbl.tblPr
    for tag in ("w:tblW", "w:tblLayout"):
        for old in properties.findall(qn(tag)):
            properties.remove(old)
    total = OxmlElement("w:tblW")
    total.set(qn("w:w"), str(int(sum(widths_cm) * 567)))
    total.set(qn("w:type"), "dxa")
    properties.append(total)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    properties.append(layout)
    for column, width in zip(table._tbl.tblGrid.findall(qn("w:gridCol")), widths_cm):
        column.set(qn("w:w"), str(int(width * 567)))
    for row in table.rows:
        for cell, width in zip(row.cells, widths_cm):
            cell.width = Cm(width)


def _field(paragraph, instruction: str, placeholder: str = "1") -> None:
    """页码等 Word 域：begin / instrText / separate / 占位 / end。"""
    def char(kind: str):
        run = paragraph.add_run()
        element = OxmlElement("w:fldChar")
        element.set(qn("w:fldCharType"), kind)
        run._element.append(element)
        return run

    char("begin")
    run = paragraph.add_run()
    text = OxmlElement("w:instrText")
    text.set(qn("xml:space"), "preserve")
    text.text = instruction
    run._element.append(text)
    char("separate")
    _font(paragraph.add_run(placeholder), 8.5, color=GREY)
    char("end")


class Report:
    WIDTH = 16.6  # A4 减左右边距 2.2cm

    def __init__(self):
        self.document = Document()
        section = self.document.sections[0]
        section.page_width, section.page_height = Cm(21), Cm(29.7)
        section.left_margin = section.right_margin = Cm(2.2)
        section.top_margin, section.bottom_margin = Cm(2.4), Cm(2.2)
        normal = self.document.styles["Normal"]
        normal.font.name = FONT
        normal.font.size = Pt(10)
        normal.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONT)
        normal.paragraph_format.line_spacing = 1.35
        normal.paragraph_format.space_after = Pt(4)
        for level, (size, color) in {1: (15, GREEN_DARK), 2: (11.5, INK)}.items():
            style = self.document.styles[f"Heading {level}"]
            style.font.name, style.font.size, style.font.bold = FONT, Pt(size), True
            style.font.color.rgb = _rgb(color)
            style.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONT)
            style.paragraph_format.space_before = Pt(16 if level == 1 else 10)
            style.paragraph_format.space_after = Pt(8 if level == 1 else 4)
            style.paragraph_format.keep_with_next = True

    # ---------- 基本元素 ----------
    def text(self, value: str, *, size: float = 10, bold: bool = False, color: str = INK, align=None, after: float = 4, style: str | None = None):
        paragraph = self.document.add_paragraph(style=style)
        paragraph.paragraph_format.space_after = Pt(after)
        if align is not None:
            paragraph.alignment = align
        _font(paragraph.add_run(value), size, bold=bold, color=color)
        return paragraph

    def bullet(self, value: str, *, color: str = INK, bold_prefix: str = "") -> None:
        paragraph = self.document.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(3)
        if bold_prefix:
            _font(paragraph.add_run(bold_prefix), 10, bold=True, color=color)
        _font(paragraph.add_run(value), 10, color=color)

    def heading(self, value: str, level: int = 1) -> None:
        paragraph = self.document.add_heading(level=level)
        _font(paragraph.add_run(value), 15 if level == 1 else 11.5, bold=True, color=GREEN_DARK if level == 1 else INK)
        if level == 1:  # 章标题下加一条绿色细线
            properties = paragraph._p.get_or_add_pPr()
            border = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            for key, value_ in (("val", "single"), ("sz", "8"), ("space", "4"), ("color", GREEN)):
                bottom.set(qn(f"w:{key}"), value_)
            border.append(bottom)
            properties.append(border)

    def chapter(self, index: int) -> None:
        self.heading(f"{NUMBERS[index]}、{CHAPTERS[index]}")

    def note(self, value: str, *, fill: str = GREEN_LIGHT, color: str = GREEN_DARK, label: str = "小结") -> None:
        """章节小结：浅绿底色的一行框。"""
        table = self.document.add_table(rows=1, cols=1)
        _borders(table, GREEN, 4)
        cell = table.rows[0].cells[0]
        _shade(cell, fill)
        cell.text = ""
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_before = Pt(3)
        paragraph.paragraph_format.space_after = Pt(3)
        _font(paragraph.add_run(f"{label}："), 9.5, bold=True, color=color)
        _font(paragraph.add_run(value), 9.5, color=INK)
        _widths(table, [self.WIDTH])
        self.text("", after=2)

    def grid(self, headers: list[str], rows: list[list[str]], widths: list[float] | None = None, *, size: float = 8.5) -> None:
        """规范表格：绿色表头白字、浅灰细线、隔行底色。"""
        table = self.document.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _borders(table)
        for cell, header in zip(table.rows[0].cells, headers):
            _shade(cell, GREEN)
            _cell_text(cell, header, size=size, bold=True, color="FFFFFF")
        header_row = table.rows[0]._tr.get_or_add_trPr()
        repeat = OxmlElement("w:tblHeader")
        repeat.set(qn("w:val"), "true")
        header_row.append(repeat)
        for number, values in enumerate(rows):
            cells = table.add_row().cells
            for cell, value in zip(cells, values):
                _cell_text(cell, value, size=size)
                if number % 2:
                    _shade(cell, STRIPE)
        _widths(table, widths or self.column_widths(headers))
        self.text("", after=2)

    def column_widths(self, headers: list[str]) -> list[float]:
        """按表头估列宽：日期、身份、状态窄，金额中等，标题、原因、对方等文字列平分剩下的宽度。"""
        fixed = []
        for header in headers:
            if any(word in header for word in ("日期", "时间")):
                fixed.append(2.3)
            elif any(word in header for word in ("身份", "状态", "税种", "移出", "持股")):
                fixed.append(1.7)
            elif "(元)" in header or "股权" in header:
                fixed.append(2.6)
            else:
                fixed.append(0)
        flexible = [index for index, width in enumerate(fixed) if not width]
        rest = max(self.WIDTH - sum(fixed), 2.5 * len(flexible))
        widths = [width or rest / len(flexible) for width in fixed] if flexible else fixed
        scale = self.WIDTH / sum(widths)
        return [width * scale for width in widths]

    def pairs(self, rows: list[tuple[str, str]], *, columns: int = 2) -> None:
        """键值表：每行 columns 组“标签｜值”，标签列浅绿底。"""
        rows = [row for row in rows if row[1]]
        table = self.document.add_table(rows=0, cols=columns * 2)
        _borders(table)
        long_rows = [row for row in rows if len(row[1]) > 40]
        short_rows = [row for row in rows if len(row[1]) <= 40]
        for start in range(0, len(short_rows), columns):
            cells = table.add_row().cells
            for offset, (label, value) in enumerate(short_rows[start:start + columns]):
                _shade(cells[offset * 2], GREEN_LIGHT)
                _cell_text(cells[offset * 2], label, size=9, bold=True, color=GREEN_DARK)
                _cell_text(cells[offset * 2 + 1], value, size=9)
        for label, value in long_rows:  # 长内容（经营范围、地址）独占一行
            cells = table.add_row().cells
            merged = cells[1].merge(cells[-1])
            _shade(cells[0], GREEN_LIGHT)
            _cell_text(cells[0], label, size=9, bold=True, color=GREEN_DARK)
            _cell_text(merged, value, size=9)
        label_width, value_width = 2.6, self.WIDTH / columns - 2.6
        _widths(table, [label_width, value_width] * columns)
        self.text("", after=2)

    def page_break(self) -> None:
        self.document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def save(self) -> bytes:
        buffer = BytesIO()
        self.document.save(buffer)
        return buffer.getvalue()


def risk_level(subject_ok: bool, cancelled: bool, risk: dict | None, *, abnormal: bool = False) -> str:
    """高：已注销，或有终本、失信、破产；中：吊销等登记异常，或有被执行、限高、欠税、设押、经营异常；低：都没有；没查风险数据为待评估。"""
    if cancelled:
        return "高"
    if risk is None:
        return "中" if abnormal else "待评估"
    sections, flags = risk.get("sections") or {}, risk.get("flags") or {}
    count = lambda key: (sections.get(key) or {}).get("count", 0)  # noqa: E731
    if count("bankruptcy") or count("dishonest") or count("end_execution") or flags.get("失信"):
        return "高"
    if (count("restricted") or count("executed") or count("own_tax") or count("mortgage") or count("abnormal") or count("serious_illegal")
            or any("无效" not in str(item.get("status")) for item in (sections.get("pledge") or {}).get("items", [])) or not subject_ok or abnormal):
        return "中"
    return "低"


def advice(level: str, detail: dict, risk: dict | None, subject_notes: list[str], cancelled: bool) -> list[str]:
    """律师建议：按风险等级和命中的风险给出可操作的几条。"""
    sections = (risk or {}).get("sections") or {}
    items = []
    if cancelled:
        items.append("被调查主体已注销，建议改列清算义务人、股东或投资人为被告，并调取注销清算材料核实清算责任。")
    if level == "高":
        items.append("起诉前先做财产调查：申请律师调查令或通过法院查询银行账户、不动产、车辆、股权等财产线索。")
        items.append("同步申请诉前或诉讼财产保全，防止财产转移；评估诉讼成本与预计回收，必要时调整诉讼策略。")
        items.append("核查股东出资（认缴未实缴、抽逃出资）及人格混同情形，评估追加股东或关联方承担责任的可能。")
    elif level == "中":
        items.append("建议起诉时一并申请财产保全，并关注被告其他案件的执行进展，必要时申请参与分配。")
    elif level == "低":
        items.append("公开数据未见重大风险，可按正常程序起诉；如标的较大，仍建议申请财产保全。")
    else:
        items.append("尚未查询风险数据，建议在立案前补查被告涉诉、被执行和失信情况后再定诉讼策略。")
    if (sections.get("end_execution") or {}).get("count"):
        items.append("已有终本案件，可留意其他债权人恢复执行的情况；如被告资不抵债，可考虑申请破产或参与破产分配。")
    if (sections.get("own_tax") or {}).get("count") or (sections.get("mortgage") or {}).get("count"):
        items.append("欠税和抵押债权在受偿顺序上优先于普通债权，估算可回收金额时应予扣除。")
    if any("个体工商户" in note for note in subject_notes):
        items.append("被告为个体工商户，起诉状中应列明字号并写明经营者身份信息。")
    if any("不一致" in note for note in subject_notes):
        items.append("案件登记的名称与现登记名称不一致，起诉时以现登记名称为准并注明曾用名。")
    return items[:6]


def render_due_diligence(record, name: str, role: str, detail: dict, risk: dict | None, *, risk_note: str,
                         subject: str, subject_notes: list[str], business_rows: list[dict], business_risks: list[str],
                         not_covered: list[str], business_source: str = "", today: date | None = None) -> bytes:
    today = today or date.today()
    report = Report()
    document = report.document
    status = str(detail.get("status") or "")
    cancelled = bool(detail.get("cancel_date")) or ("注销" in status and "未注销" not in status)
    level = risk_level("可以作为被告" in subject, cancelled, risk, abnormal=bool(detail.get("abnormal") or detail.get("revoke_date")))
    execution, reasons = party_risk.enforceability(risk) if risk else ("", [])
    sections = (risk or {}).get("sections") or {}
    report_no = f"沪知尽调-{record.serial_no}-{today:%Y%m%d}"
    business_source = business_source or (f"企查查企业工商信息（{str(detail.get('queried_at') or '')[:10]} 查询）"
                                          if detail.get("queried_at") else "企查查企业工商信息")

    # ---------- 封面：律所 logo（标志加名称）放左上，下面一条绿线 ----------
    from app.areas.legal.report_logo import FULL, MARK

    logo = document.add_paragraph()
    logo.paragraph_format.space_after = Pt(4)
    logo.add_run().add_picture(BytesIO(FULL), width=Cm(5.2))
    rule = report.text("", after=0)
    properties = rule._p.get_or_add_pPr()
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for key, value in (("val", "single"), ("sz", "12"), ("space", "1"), ("color", GREEN)):
        bottom.set(qn(f"w:{key}"), value)
    border.append(bottom)
    properties.append(border)
    for _ in range(4):
        report.text("", after=10)
    report.text(f"{role}尽职调查报告", size=28, bold=True, color=GREEN_DARK, after=6)
    report.text("Due Diligence Report", size=12, color=GREY, after=30)
    report.text(name, size=18, bold=True, color=INK, after=40)
    cover = document.add_table(rows=0, cols=2)
    _borders(cover, LINE, 4, inside=True)
    for label, value in (("被调查企业", name), ("统一社会信用代码", detail.get("credit_code") or ""),
                         ("所属案件", f"{record.serial_no}  {record.title}"), ("出具单位", FIRM),
                         ("出具日期", f"{today.year} 年 {today.month} 月 {today.day} 日"), ("报告编号", report_no), ("报告性质", "仅供内部参考")):
        cells = cover.add_row().cells
        _shade(cells[0], GREEN_LIGHT)
        _cell_text(cells[0], label, size=10, bold=True, color=GREEN_DARK)
        _cell_text(cells[1], value, size=10, bold=label == "报告性质", color="C0392B" if label == "报告性质" else INK)
    _widths(cover, [4.2, Report.WIDTH - 4.2])
    for _ in range(4):
        report.text("", after=10)
    report.text("本报告依据公开数据由系统生成，仅供本所承办律师内部参考，未经许可不得对外提供。", size=8.5, color=GREY,
                align=WD_ALIGN_PARAGRAPH.CENTER)

    # 正文另起一节：封面不带页眉页脚，正文页眉页脚和页码从 1 开始。
    body = document.add_section(WD_SECTION.NEW_PAGE)
    body.header.is_linked_to_previous = False
    body.footer.is_linked_to_previous = False
    page_numbers = body._sectPr.find(qn("w:pgNumType"))
    if page_numbers is None:
        page_numbers = OxmlElement("w:pgNumType")
        body._sectPr.append(page_numbers)
    page_numbers.set(qn("w:start"), "1")
    header = body.header.paragraphs[0]
    header.paragraph_format.tab_stops.add_tab_stop(Cm(Report.WIDTH), WD_TAB_ALIGNMENT.RIGHT)
    header.add_run().add_picture(BytesIO(MARK), height=Cm(0.55))
    _font(header.add_run(f"  {FIRM}  |  {role}尽职调查报告"), 8.5, color=GREEN_DARK, bold=True)
    _font(header.add_run(f"\t{name}  ·  仅供内部参考"), 8.5, color=GREY)
    properties = header._p.get_or_add_pPr()
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for key, value in (("val", "single"), ("sz", "6"), ("space", "4"), ("color", GREEN)):
        bottom.set(qn(f"w:{key}"), value)
    border.append(bottom)
    properties.append(border)
    footer = body.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(footer.add_run(f"报告编号 {report_no}    第 "), 8.5, color=GREY)
    _field(footer, "PAGE")
    _font(footer.add_run(" 页"), 8.5, color=GREY)

    # ---------- 目录（静态，手机上也能看；章节固定） ----------
    report.text("目  录", size=16, bold=True, color=GREEN_DARK, align=WD_ALIGN_PARAGRAPH.CENTER, after=14)
    for index, title in enumerate(["报告摘要"] + [f"{NUMBERS[i]}、{chapter}" for i, chapter in enumerate(CHAPTERS)]):
        paragraph = report.text("", after=6)
        _font(paragraph.add_run(title), 10.5, bold=index == 0, color=INK)
    report.page_break()

    # ---------- 报告摘要 ----------
    report.heading("报告摘要")
    summary = document.add_table(rows=1, cols=2)
    _borders(summary, LINE)
    level_cell, text_cell = summary.rows[0].cells
    _shade(level_cell, LEVELS[level])
    level_cell.text = ""
    paragraph = level_cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(paragraph.add_run("综合风险等级\n"), 9, color="FFFFFF")
    _font(paragraph.add_run(level), 26 if len(level) == 1 else 16, bold=True, color="FFFFFF")
    level_cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    text_cell.text = ""
    for label, value in (("可否作为被告", subject), ("能否执行到", execution or f"{risk_note}，暂未判断。")):
        line = text_cell.add_paragraph() if text_cell.paragraphs[0].text else text_cell.paragraphs[0]
        line.paragraph_format.space_after = Pt(4)
        _font(line.add_run(f"{label}："), 9.5, bold=True, color=GREEN_DARK)
        _font(line.add_run(value), 9.5, color=INK)
    _widths(summary, [3.4, Report.WIDTH - 3.4])
    report.text("", after=4)
    report.heading("关键风险", 2)
    key_risks = (business_risks + reasons)[:5]
    if key_risks:
        for item in key_risks:
            report.bullet(item, color="A93226")
    else:
        report.text("公开数据中未发现需要特别提示的风险。" if risk else f"{risk_note}，仅核查了工商登记，未发现注销、吊销等异常。")
    report.heading("律师建议", 2)
    for item in advice(level, detail, risk, subject_notes, cancelled):
        report.bullet(item)
    report.heading("风险数据概览", 2)
    overview = []
    for label, keys in (("涉诉情况", party_risk.LITIGATION), ("执行与信用", party_risk.ENFORCEMENT), ("经营风险", party_risk.OPERATION)):
        counted = [(party_risk.SECTIONS[key][0], sections[key]["count"]) for key in keys if key in sections]
        overview.append([label, "、".join(f"{title} {number} 条" for title, number in counted) if counted else ("未发现记录" if risk else "未查询")])
    report.grid(["维度", "命中情况"], overview, [3.2, Report.WIDTH - 3.2], size=9)
    report.page_break()

    # ---------- 一、企业基本信息 ----------
    report.chapter(0)
    established = detail.get("established_date") or ""
    report.note("、".join(part for part in (f"登记状态：{status or '—'}", established and f"成立于 {established}",
                                           detail.get("registered_capital") and f"注册资本 {detail['registered_capital']}",
                                           detail.get("legal_representative") and f"法定代表人 {detail['legal_representative']}") if part) + "。")
    report.pairs([(row["label"], row["value"]) for row in business_rows], columns=2)

    # ---------- 二、股东与主要人员 ----------
    report.chapter(1)
    if "partners" in sections or "employees" in sections:
        report.note(f"股东 {(sections.get('partners') or {}).get('count', 0)} 名，主要人员 {(sections.get('employees') or {}).get('count', 0)} 名。")
        for key in ("partners", "employees"):
            if key in sections:
                report.heading(party_risk.SECTIONS[key][0], 2)
                report.grid([header for _f, header in party_risk.SECTIONS[key][1]],
                            [party_risk.item_text(key, item) for item in sections[key]["items"]])
    else:
        report.note("本报告数据源未覆盖股东及主要人员，需另行核查（调取工商内档，或开通企查查企业风险扫描）。", fill="FDF3E7", color="9A5B13", label="未核查")
        if detail.get("legal_representative"):
            report.pairs([("法定代表人", detail["legal_representative"])], columns=1)

    def risk_chapter(index: int, keys: tuple, empty: str) -> None:
        report.chapter(index)
        if not risk:
            report.note(f"{risk_note}，本章未核查。", fill="FDF3E7", color="9A5B13", label="未核查")
            return
        hit = [key for key in keys if key in sections]
        if not hit:
            report.note(empty)
            return
        parts = []
        for key in hit:
            section = sections[key]
            amount = f"（{party_risk._yuan(section['amount'])}）" if section.get("amount") else ""
            parts.append(f"{party_risk.SECTIONS[key][0]} {section['count']} 条{amount}")
        report.note("、".join(parts) + "。")
        for key in hit:
            label, columns = party_risk.SECTIONS[key]
            section = sections[key]
            shown = min(10, len(section["items"]))
            suffix = f"（共 {section['count']} 条，列最新 {shown} 条）" if section["count"] > shown else f"（共 {section['count']} 条）"
            report.heading(f"{label}{suffix}", 2)
            report.grid([header for _f, header in columns], [party_risk.item_text(key, item) for item in section["items"][:10]])

    risk_chapter(2, party_risk.LITIGATION, "未发现立案、开庭公告和裁判文书记录。")
    risk_chapter(3, party_risk.ENFORCEMENT, "未发现被执行、失信、限制高消费、终本、破产和司法拍卖记录。")
    risk_chapter(4, party_risk.OPERATION, "未发现经营异常、行政处罚、欠税、严重违法、股权出质、动产抵押和清算记录。")

    # ---------- 六、可诉性分析 ----------
    report.chapter(5)
    report.note(subject, label="结论")
    for note in subject_notes:
        report.bullet(note)
    report.text("依据：被告应为依法存续、具有诉讼主体资格的民事主体；已注销的法人、非法人组织诉讼主体资格消灭，"
                "相应责任由清算义务人、股东等承担；个体工商户以营业执照登记的字号为当事人，并注明经营者信息。", size=9, color=GREY)

    # ---------- 七、执行可能性分析 ----------
    report.chapter(6)
    if risk:
        report.note(execution, label="结论", fill={"高": "FBEAEA", "中": "FDF3E7"}.get(level, GREEN_LIGHT),
                    color={"高": "A93226", "中": "9A5B13"}.get(level, GREEN_DARK))
        for reason in reasons:
            report.bullet(reason)
    else:
        report.note(f"{risk_note}，暂未判断被告有没有财产、能不能执行到。", fill="FDF3E7", color="9A5B13", label="未核查")
    report.text("说明：以上依据公开的执行、失信和经营风险数据判断，不代表被告的全部财产状况；管辖、诉讼时效、证据是否充分，请承办律师结合案情判断。",
                size=9, color=GREY)

    # ---------- 八、数据来源与声明 ----------
    report.chapter(7)
    report.grid(["数据项", "来源", "查询时间"], [
        ["工商登记信息", business_source, str(detail.get("queried_at") or "")[:10] or "—"],
        ["涉诉、执行、经营风险", risk["source_label"] if risk else risk_note, str((risk or {}).get("queried_at") or "")[:10] or "—"],
    ], [3.6, 9.4, 3.6], size=9)
    if not_covered:
        report.heading("本报告未核查的事项", 2)
        for item in not_covered:
            report.bullet(item)
    report.heading("免责声明", 2)
    for item in ("本报告依据第三方数据服务商提供的公开数据，由系统按固定模板生成，数据以国家企业信用信息公示系统、中国执行信息公开网、"
                 "中国裁判文书网等官方公示为准。",
                 "公开数据存在更新延迟和遗漏的可能，本所不对数据的完整性、及时性作出保证。",
                 "本报告仅供本所承办律师内部参考，不构成法律意见，未经许可不得对外提供或引用。"):
        report.bullet(item, color=GREY)
    report.text(f"{FIRM}", size=10, bold=True, color=GREEN_DARK, align=WD_ALIGN_PARAGRAPH.RIGHT, after=0)
    report.text(f"{today.year} 年 {today.month} 月 {today.day} 日", size=10, color=INK, align=WD_ALIGN_PARAGRAPH.RIGHT)
    return report.save()
