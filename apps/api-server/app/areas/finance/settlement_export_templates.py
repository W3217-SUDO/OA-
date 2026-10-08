"""一般结算导出模板。

模板定义与路由、查询逻辑分离，便于各公司后续替换列顺序、标题和取值规则，
避免在 API 路由中拼接临时 XML 表格。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape
from typing import Any, Callable, Iterable


ValueReader = Callable[[dict[str, Any], dict[str, Any] | None], Any]


@dataclass(frozen=True)
class SettlementExportColumn:
    """结算导出模板的一列。"""

    title: str
    read: ValueReader
    number: bool = False


@dataclass(frozen=True)
class SettlementExportTemplate:
    """结算清单/到账清单/案件清单的可维护模板定义。"""

    kind: str
    sheet_name: str
    filename_prefix: str
    columns: tuple[SettlementExportColumn, ...]
    expand_details: bool = False

    def rows(self, records: Iterable[dict[str, Any]]) -> list[list[Any]]:
        values: list[list[Any]] = []
        for record in records:
            details = list((record.get("data") or {}).get("allocation_details") or [])
            if self.expand_details:
                for detail in details:
                    values.append([column.read(record, detail) for column in self.columns])
            else:
                values.append([column.read(record, None) for column in self.columns])
        return values


def _record_value(key: str) -> ValueReader:
    return lambda record, _detail: (record.get("data") or {}).get(key)


def _detail_value(key: str) -> ValueReader:
    return lambda _record, detail: (detail or {}).get(key)


def _record_serial(record: dict[str, Any], _detail: dict[str, Any] | None) -> Any:
    return record.get("serial_no")


def _record_customer(record: dict[str, Any], _detail: dict[str, Any] | None) -> Any:
    return record.get("customer")


def _detail_customer(record: dict[str, Any], detail: dict[str, Any] | None) -> Any:
    return (detail or {}).get("customer") or record.get("customer")


GENERAL_SETTLEMENT_EXPORT_TEMPLATES: dict[str, SettlementExportTemplate] = {
    "receipt": SettlementExportTemplate(
        kind="receipt",
        sheet_name="到账清单",
        filename_prefix="到账清单",
        columns=(
            SettlementExportColumn("回款编号", _record_serial),
            SettlementExportColumn("客户名称", _record_customer),
            SettlementExportColumn("回款单位", _record_value("payer_name")),
            SettlementExportColumn("回款日期", _record_value("received_date")),
            SettlementExportColumn("回款金额", _record_value("receipt_amount"), True),
            SettlementExportColumn("已分金额", _record_value("allocated_amount"), True),
            SettlementExportColumn("未分金额", _record_value("remaining_amount"), True),
            SettlementExportColumn("回款方式", _record_value("payment_method")),
            SettlementExportColumn("银行备注", _record_value("bank_remark")),
        ),
    ),
    "case": SettlementExportTemplate(
        kind="case",
        sheet_name="案件清单",
        filename_prefix="案件清单",
        expand_details=True,
        columns=(
            SettlementExportColumn("回款编号", _record_serial),
            SettlementExportColumn("案号", _detail_value("case_no")),
            SettlementExportColumn("阶段", _detail_value("case_stage")),
            SettlementExportColumn("费用类型", _detail_value("fee_type")),
            SettlementExportColumn("本笔分配金额", _detail_value("current_amount"), True),
            SettlementExportColumn("本笔结算金额", _detail_value("settlement_amount"), True),
            SettlementExportColumn("本笔归档费", _detail_value("archive_fee"), True),
            SettlementExportColumn("客户", _detail_customer),
            SettlementExportColumn("经办律师", _detail_value("handling_lawyer")),
            SettlementExportColumn("律师助理", _detail_value("assistant")),
            SettlementExportColumn("合同号", _detail_value("contract_no")),
        ),
    ),
    "settlement": SettlementExportTemplate(
        kind="settlement",
        sheet_name="结算清单",
        filename_prefix="结算清单",
        columns=(
            SettlementExportColumn("回款编号", _record_serial),
            SettlementExportColumn("客户名称", _record_customer),
            SettlementExportColumn("客户管理人", _record_value("customer_manager")),
            SettlementExportColumn("回款单位", _record_value("payer_name")),
            SettlementExportColumn("回款日期", _record_value("received_date")),
            SettlementExportColumn("回款金额", _record_value("receipt_amount"), True),
            SettlementExportColumn("已分金额", _record_value("allocated_amount"), True),
            SettlementExportColumn("未分金额", _record_value("remaining_amount"), True),
            SettlementExportColumn("已分官费", _record_value("assigned_official_fee"), True),
            SettlementExportColumn("已分代理费", _record_value("assigned_agency_fee"), True),
            SettlementExportColumn("已分其他费用", _record_value("assigned_other_fee"), True),
            SettlementExportColumn("代理费结算金额", _record_value("agency_settlement_amount"), True),
            SettlementExportColumn("扣归档费", _record_value("archive_fee"), True),
            SettlementExportColumn("实际结算金额", _record_value("actual_settlement_amount"), True),
        ),
    ),
}


def _cell(value: Any, number: bool) -> str:
    text = f"{float(value or 0):.2f}" if number else str(value or "")
    value_type = "Number" if number else "String"
    return f'<Cell><Data ss:Type="{value_type}">{escape(text)}</Data></Cell>'


def render_general_settlement_export(
    kind: str,
    records: Iterable[dict[str, Any]],
    export_date: date,
) -> tuple[bytes, str, str]:
    """按已注册模板生成 Excel 兼容工作簿，返回内容、文件名和工作表名。"""

    template = GENERAL_SETTLEMENT_EXPORT_TEMPLATES.get(kind)
    if template is None:
        raise ValueError(f"不支持的结算导出模板: {kind}")
    header_row = "<Row>" + "".join(_cell(column.title, False) for column in template.columns) + "</Row>"
    data_rows = (
        "<Row>" + "".join(_cell(value, column.number) for value, column in zip(values, template.columns)) + "</Row>"
        for values in template.rows(records)
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<?mso-application progid="Excel.Sheet"?>'
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
        'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
        f'<Worksheet ss:Name="{escape(template.sheet_name)}"><Table>{header_row}{"".join(data_rows)}</Table></Worksheet>'
        "</Workbook>"
    )
    filename = f"{template.filename_prefix}-{export_date}.xls"
    return workbook.encode("utf-8"), filename, template.sheet_name
