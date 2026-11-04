"""结算管理“导出结算清单”：按回款导出压缩包，每个案件一个文件夹（BUG20261102001，shenhe 11-02 确认）。

文件夹里放：
- 个案结算表：按 shenhe 给的“结算提成表”原件（settlement_sheet_template）填数；
  另附一份同名 PDF（横向一页、无页眉页脚），Excel 照样保留（fanyuxing 11-04，501225）；
- 法院文书：案件附件里文件名（或文件类型）是判决书、裁定书、调解书、和解协议的；
  另放本案全部诉讼费缴费凭证、有公证费的放公证费发票，不受“上次结算已放过”限制（BUG20261103011，fanyuxing 11-03）；
- 票据：诉讼费、保全费放缴费支付凭证（案件票据文件），公证费放公证处发票（案件发票/票据文件）；
  公证服务费、律师费发票不放。同一案件上一次回款之前已产生的成本，上一次结算已放过，不再放。
"""

import asyncio
import re
import tempfile
import zipfile
from copy import copy
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from io import BytesIO

import xlrd
import xlwt
from fastapi import HTTPException
from sqlalchemy import Text, select
from starlette.concurrency import run_in_threadpool

from app.areas.finance.excel_templates import copy_style
from app.areas.finance.settlement_sheet_template import TEMPLATE_XLS
from app.models import BusinessRecord, FileAttachment, IncomingPayment, SystemParameter

MAX_RECEIPTS = 30
MAX_TOTAL_BYTES = 500 * 1024 * 1024
DOWNLOAD_CONCURRENCY = 4
VOID_STATUSES = {"已作废", "已删除", "已取消", "已回收"}
COURT_DOCUMENT_PATTERN = re.compile(r"判决书|裁定书|调解书|和解协议")
LITIGATION_FEES = ("一审诉讼费", "二审诉讼费", "再审诉讼费", "诉讼费")
LITIGATION_VOUCHER_NAME = re.compile(r"诉讼费.*(收据|凭证|发票)|(收据|凭证|发票).*诉讼费")
NOTARY_INVOICE_NAME = re.compile(r"公证.*发票|发票.*公证")

# 个案结算表“发生成本/结案成本”九行：表上的名称 → 新系统费用名称
COST_ROWS = (
    ("诉讼费总额", ("一审诉讼费", "二审诉讼费", "再审诉讼费", "诉讼费")),
    ("公证费", ("公证费",)),
    ("公证费服务费", ("公证服务费",)),
    ("保全费", ("保全费",)),
    ("担保费", ("担保费",)),
    ("公告费", ("公告费",)),
    ("执行费", ("执行费",)),
    ("鉴定费", ("鉴定费",)),
    ("核定成本", ("核定成本",)),
)
RIGHTS_HOLDER_FEES = ("权利人分成", "权利人赔偿款")
# 放进“票据”文件夹的费用和附件类别
RECEIPT_RULES = {
    **{name: ("案件票据文件",) for name in ("一审诉讼费", "二审诉讼费", "再审诉讼费", "诉讼费", "保全费")},
    "公证费": ("案件发票文件", "案件票据文件"),
}

# 模板里要填值的单元格（行, 列）；其余单元格照抄模板的标签和样式
VALUE_CELLS = {
    "customer": (1, 1), "case_no": (2, 1), "archive_no": (2, 4), "evidence": (3, 1), "court_refund": (4, 1),
    "court_case_no": (5, 1), "defendants": (6, 1), "payer": (7, 1), "received_date": (7, 3), "bank": (7, 5),
    "receipt_amount": (8, 1), "case_amount": (8, 3), "rights_holder": (18, 2), "other_fee": (19, 2),
    "lawyer_fee": (20, 1), "lawyer_fee_refund": (20, 4), "platform_fee": (21, 1), "auditor": (22, 1), "audit_date": (22, 5),
}
COST_START_ROW = 9
MONEY_KEYS = {"court_refund", "receipt_amount", "case_amount", "rights_holder", "other_fee", "lawyer_fee", "lawyer_fee_refund", "platform_fee"}


def _amount(value) -> Decimal:
    try:
        return Decimal(str(value)) if value not in (None, "") else Decimal(0)
    except Exception:
        return Decimal(0)


def _money(value: Decimal | None):
    return None if value is None or value == 0 else float(value)


def _text(value) -> str:
    if isinstance(value, (list, tuple)):
        return ",".join(str(item).strip() for item in value if str(item or "").strip())
    return str(value or "").strip()


def _safe_name(value: str) -> str:
    return re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", str(value or "").strip()) or "未命名"


@lru_cache(maxsize=1)
def _template():
    return xlrd.open_workbook(file_contents=TEMPLATE_XLS, formatting_info=True)


def render_case_sheet(values: dict, costs: list[tuple[Decimal | None, Decimal | None]]) -> bytes:
    """按原件逐格复制样式、合并区域、行高列宽，再把本案数据填进值单元格。"""
    source = _template()
    template = source.sheet_by_index(0)
    book = xlwt.Workbook(encoding="utf-8")
    for index, colour in source.colour_map.items():
        if 8 <= index <= 63 and colour:
            book.set_colour_RGB(index, *colour)
    sheet = book.add_sheet(template.name, cell_overwrite_ok=True)
    # 打印/转 PDF：横向、缩到一页、水平居中、不打页眉页脚（501225）
    sheet.portrait = False
    sheet.fit_num_pages = sheet.fit_width_to_pages = sheet.fit_height_to_pages = 1
    sheet.header_str = sheet.footer_str = b""
    sheet.print_centered_horz = True
    sheet.left_margin = sheet.right_margin = 0.4
    sheet.top_margin = sheet.bottom_margin = 0.5
    styles = {}
    money_styles = {}

    def style(row, column, money=False):
        index = template.cell_xf_index(row, column)
        if index not in styles:
            styles[index] = copy_style(source, index)
        if not money:
            return styles[index]
        if index not in money_styles:
            money_styles[index] = copy(styles[index])
            money_styles[index].num_format_str = "0.00"
        return money_styles[index]

    for index, info in template.colinfo_map.items():
        sheet.col(index).width = info.width
    for index, info in template.rowinfo_map.items():
        sheet.row(index).height = info.height
        sheet.row(index).height_mismatch = True
    cells = {position: key for key, position in VALUE_CELLS.items()}
    for offset, (planned, settled) in enumerate(costs):
        cells[(COST_START_ROW + offset, 2)] = ("cost", planned)
        cells[(COST_START_ROW + offset, 5)] = ("cost", settled)
    merged_tail = {(r, c) for r0, r1, c0, c1 in template.merged_cells for r in range(r0, r1) for c in range(c0, c1) if (r, c) != (r0, c0)}
    for row in range(template.nrows):
        for column in range(template.ncols):
            if (row, column) in merged_tail:
                continue
            target = cells.get((row, column))
            if target is None:
                value = template.cell_value(row, column)
                sheet.write(row, column, value, style(row, column))
            elif isinstance(target, tuple):
                sheet.write(row, column, _money(target[1]), style(row, column, money=True))
            else:
                value = values.get(target)
                money = target in MONEY_KEYS
                sheet.write(row, column, _money(value) if money else (value or ""), style(row, column, money=money))
    for r0, r1, c0, c1 in template.merged_cells:
        top_left = cells.get((r0, c0))
        if top_left is None:
            value = template.cell_value(r0, c0)
            cell_style = style(r0, c0)
        elif isinstance(top_left, tuple):
            value, cell_style = _money(top_left[1]), style(r0, c0, money=True)
        else:
            raw = values.get(top_left)
            money = top_left in MONEY_KEYS
            value, cell_style = (_money(raw) if money else (raw or "")), style(r0, c0, money=money)
        sheet.merge(r0, r1 - 1, c0, c1 - 1, cell_style)
        sheet.write(r0, c0, value, cell_style)
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def _dedupe_rights_holder(fees: list[BusinessRecord], attachment_names: dict[int, tuple]) -> list[BusinessRecord]:
    """同一案件两笔一模一样的权利人分成（同名称、同金额、同票据）按一笔计（shenhe 11-02 确认）。"""
    seen, kept = set(), []
    for fee in fees:
        key = (fee.title, str(_amount((fee.data or {}).get("amount"))), attachment_names.get(fee.id, ()))
        if key in seen:
            continue
        seen.add(key)
        kept.append(fee)
    return kept


def court_folder_extras(case_attachments: list, fees: list, attachments_by_record: dict) -> list[tuple[str, object]]:
    """“法院文书”文件夹里另放的诉讼费缴费凭证和公证费发票：（文件名, 附件）。"""
    out: list[tuple[str, object]] = []
    seen: set[int] = set()

    def add(name: str, item) -> None:
        if item.id not in seen:
            seen.add(item.id)
            out.append((name, item))

    has_notary = any(fee.title == "公证费" for fee in fees)
    for fee in fees:
        for item in attachments_by_record.get(fee.id, []):
            if fee.title in LITIGATION_FEES and item.category in ("案件票据文件", "案件发票文件"):
                add(f"诉讼费凭证_{_safe_name(fee.title)}_{_safe_name(item.original_name)}", item)
            elif fee.title == "公证费" and item.category == "案件发票文件":
                add(f"公证费发票_{_safe_name(item.original_name)}", item)
    for item in case_attachments:
        name = item.original_name or ""
        if LITIGATION_VOUCHER_NAME.search(name) and "通知书" not in name:
            add(f"诉讼费凭证_{_safe_name(name)}", item)
        elif has_notary and NOTARY_INVOICE_NAME.search(name):
            add(f"公证费发票_{_safe_name(name)}", item)
    return out


async def _previous_receipt_dates(db, case_nos: set[str]) -> dict[str, list[date]]:
    """每个案件所有回款的到账日期（用来判断哪些成本上一次结算已经放过票据）。"""
    out: dict[str, list[date]] = {}
    for case_no in case_nos:
        rows = (await db.execute(select(IncomingPayment.received_date).where(
            IncomingPayment.allocations.cast(Text).contains(f'"case_no": "{case_no}"'),
        ))).scalars().all()
        out[case_no] = sorted({value for value in rows if value})
    return out


async def build_settlement_package(rows: list[dict], identity: dict, db, export_date: date) -> tuple[str, str]:
    """生成压缩包，返回（临时文件路径, 下载文件名）。调用方负责发送后删除临时文件。"""
    from app.core.storage import ensure_attachment_local

    if len(rows) > MAX_RECEIPTS:
        raise HTTPException(422, f"一次最多导出 {MAX_RECEIPTS} 笔回款的结算单压缩包，请筛选或勾选后再导出")
    plans = []
    case_ids, case_nos = set(), set()
    for row in rows:
        data = row.get("data") or {}
        by_case: dict[str, list[dict]] = {}
        for detail in data.get("allocation_details") or []:
            case_no = str(detail.get("case_no") or "").strip()
            if not case_no:
                continue
            by_case.setdefault(case_no, []).append(detail)
            case_nos.add(case_no)
            if detail.get("case_id"):
                case_ids.add(int(detail["case_id"]))
        plans.append((row, data, by_case))
    if not case_nos:
        raise HTTPException(422, "所选回款没有分配到案件，无法生成结算单")

    cases = {item.serial_no: item for item in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.deleted_at.is_(None), BusinessRecord.serial_no.in_(case_nos),
    ))).all()}
    fees_by_case: dict[str, list[BusinessRecord]] = {}
    for fee in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.deleted_at.is_(None),
        BusinessRecord.data["case_no"].as_string().in_(case_nos),
        BusinessRecord.data["legacy_kind"].as_string().is_distinct_from("internal_payment_line"),
    ))).all():
        if fee.status in VOID_STATUSES:
            continue
        fees_by_case.setdefault(str((fee.data or {}).get("case_no") or "").strip(), []).append(fee)
    fee_ids = [fee.id for fees in fees_by_case.values() for fee in fees]
    case_record_ids = [item.id for item in cases.values()]
    attachments_by_record: dict[int, list[FileAttachment]] = {}
    if fee_ids or case_record_ids:
        for item in (await db.scalars(select(FileAttachment).where(
            FileAttachment.deleted_at.is_(None), FileAttachment.record_id.in_(fee_ids + case_record_ids),
        ).order_by(FileAttachment.id))).all():
            attachments_by_record.setdefault(item.record_id, []).append(item)
    court_codes = {code for code, name in (await db.execute(select(SystemParameter.code, SystemParameter.name).where(
        SystemParameter.category == "case_file_type", SystemParameter.deleted_at.is_(None),
    ))).all() if COURT_DOCUMENT_PATTERN.search(str(name or ""))}
    evidence_by_case: dict[str, list[BusinessRecord]] = {}
    for item in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "evidence", BusinessRecord.deleted_at.is_(None),
        BusinessRecord.data["case_no"].as_string().in_(case_nos),
    ))).all():
        evidence_by_case.setdefault(str((item.data or {}).get("case_no") or "").strip(), []).append(item)
    receipt_dates = await _previous_receipt_dates(db, case_nos)
    auditor = str(identity.get("display_name") or identity.get("username") or "")

    entries: list[tuple[str, object]] = []  # (压缩包内路径, bytes 或 FileAttachment)
    used_folders: set[str] = set()
    for row, data, by_case in plans:
        received = str(data.get("received_date") or "")[:10]
        try:
            received_day = date.fromisoformat(received) if received else None
        except ValueError:
            received_day = None
        for case_no, details in by_case.items():
            case = cases.get(case_no)
            case_data = (case.data if case else None) or {}
            folder = _safe_name(case_no)
            if folder in used_folders:
                folder = _safe_name(f"{case_no}_{row.get('serial_no') or row.get('id')}")
            used_folders.add(folder)
            fees = fees_by_case.get(case_no, [])
            names = {fee.id: tuple(sorted(a.original_name for a in attachments_by_record.get(fee.id, []))) for fee in fees}
            totals: dict[str, Decimal] = {}
            rights = _dedupe_rights_holder([fee for fee in fees if fee.title in RIGHTS_HOLDER_FEES], names)
            for fee in fees:
                if fee.title in RIGHTS_HOLDER_FEES:
                    continue
                totals[fee.title] = totals.get(fee.title, Decimal(0)) + _amount((fee.data or {}).get("amount"))
            costs = []
            for _label, titles in COST_ROWS:
                total = sum((totals.get(title, Decimal(0)) for title in titles), Decimal(0))
                costs.append((total or None, total or None))
            evidence = [
                f"{_text((item.data or {}).get('notary_no')) or item.serial_no}({_text((item.data or {}).get('warehouse_status')) or item.status})"
                for item in evidence_by_case.get(case_no, [])
            ]
            values = {
                "customer": case.customer if case else _text(details[0].get("customer")),
                "case_no": case_no,
                "archive_no": _text(case_data.get("archive_no") or case_data.get("file_no") or details[0].get("archive_no") or details[0].get("file_no")),
                "evidence": ",".join(evidence),
                "court_refund": _amount(case_data.get("court_refund_amount")) or None,
                "court_case_no": _text(case_data.get("court_case_no") or details[0].get("court_case_no")),
                "defendants": _text(case_data.get("defendants") or case_data.get("defendant")),
                "payer": _text(data.get("payer_name")),
                "received_date": received,
                "bank": _text(data.get("payment_method") or data.get("bank_name")),
                "receipt_amount": _amount(data.get("receipt_amount")) or None,
                "case_amount": sum((_amount(item.get("current_amount")) for item in details), Decimal(0)) or None,
                "rights_holder": sum((_amount((fee.data or {}).get("amount")) for fee in rights), Decimal(0)) or None,
                "other_fee": totals.get("其他费用") or None,
                "lawyer_fee": totals.get("律师代理费") or None,
                "lawyer_fee_refund": totals.get("律师代理费(退费)") or None,
                "platform_fee": totals.get("平台代理费") or None,
                "auditor": auditor,
                "audit_date": export_date.isoformat(),
            }
            sheet = await run_in_threadpool(render_case_sheet, values, costs)
            entries.append((f"{folder}/{_safe_name(case_no)}_个案结算表.xls", sheet))
            for item in attachments_by_record.get(case.id, []) if case else []:
                if COURT_DOCUMENT_PATTERN.search(item.original_name or "") or (item.file_type_code and item.file_type_code in court_codes):
                    entries.append((f"{folder}/法院文书/{_safe_name(item.original_name)}", item))
            for name, item in court_folder_extras(attachments_by_record.get(case.id, []) if case else [], fees, attachments_by_record):
                entries.append((f"{folder}/法院文书/{name}", item))
            # 上一次回款（到账日期早于本次）之前已产生的成本，上次结算已放过票据
            earlier = [day for day in receipt_dates.get(case_no, []) if received_day and day < received_day]
            cutoff = max(earlier) if earlier else None
            for fee in fees:
                categories = RECEIPT_RULES.get(fee.title)
                if not categories:
                    continue
                if cutoff and fee.created_at and fee.created_at.date() <= cutoff:
                    continue
                for item in attachments_by_record.get(fee.id, []):
                    if item.category in categories:
                        entries.append((f"{folder}/票据/{_safe_name(fee.title)}_{_safe_name(item.original_name)}", item))

    semaphore = asyncio.Semaphore(DOWNLOAD_CONCURRENCY)
    missing: dict[str, list[str]] = {}
    # 个案结算表另附 PDF：整批一次转换；转不成的写进该案件“缺失文件.txt”，不影响 Excel 下载
    from app.core.pdf_conversion import convert_many_to_pdf
    sheets = {path: item for path, item in entries if isinstance(item, bytes) and path.endswith("_个案结算表.xls")}
    pdfs = await convert_many_to_pdf(sheets, ".xls")
    for path in sheets if pdfs is not None else ():
        pdf_path = path[:-len(".xls")] + ".pdf"
        if path in pdfs:
            entries.append((pdf_path, pdfs[path]))
        else:
            missing.setdefault(path.split("/", 1)[0], []).append(pdf_path.split("/", 1)[-1] + "（PDF 转换失败，请用 Excel 版）")

    async def local(path: str, item: FileAttachment):
        async with semaphore:
            try:
                return path, await ensure_attachment_local(item)
            except Exception:
                missing.setdefault(path.split("/", 1)[0], []).append(item.original_name)
                return path, None

    files = await asyncio.gather(*(local(path, item) for path, item in entries if isinstance(item, FileAttachment)))
    total = sum(len(item) for _path, item in entries if isinstance(item, bytes))
    total += sum(path.stat().st_size for _name, path in files if path is not None)
    if total > MAX_TOTAL_BYTES:
        raise HTTPException(422, "结算单压缩包超过 500MB，请少选几笔回款后再导出")

    def write_zip() -> str:
        handle = tempfile.NamedTemporaryFile(prefix="settlement-", suffix=".zip", delete=False)
        handle.close()
        used: set[str] = set()

        def unique(name: str) -> str:
            if name not in used:
                used.add(name)
                return name
            stem, dot, ext = name.rpartition(".")
            for index in range(2, 1000):
                candidate = f"{stem}({index}).{ext}" if dot else f"{name}({index})"
                if candidate not in used:
                    used.add(candidate)
                    return candidate
            return name
        with zipfile.ZipFile(handle.name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, item in entries:
                if isinstance(item, bytes):
                    archive.writestr(unique(name), item)
            for name, path in files:
                if path is not None:
                    archive.write(path, unique(name))
            for folder, names in missing.items():
                archive.writestr(f"{folder}/缺失文件.txt", "以下文件读取失败，未能放入压缩包：\n" + "\n".join(names))
        return handle.name

    path = await run_in_threadpool(write_zip)
    first = plans[0][0]
    label = str(first.get("serial_no") or first.get("id")) if len(plans) == 1 else export_date.strftime("%Y%m%d")
    return path, f"结算单_{label}_{datetime.now():%Y%m%d%H%M%S}.zip"
