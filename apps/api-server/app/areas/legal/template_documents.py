"""以清理过的沪知原件填充文书，保留表格、页眉、页脚和样式。"""

from copy import deepcopy
from datetime import datetime
from io import BytesIO
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED

from docx import Document
from lxml import etree

from app.areas.legal.case_export_projection import case_value


TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "export_templates" / "huzhi"
TEMPLATE_TYPES = frozenset({
    "authorization-letter", "archive-cover", "identity-certificate",
    "compensation-payment-application", "first-instance-appellant-lawyer-letter",
    "first-instance-appellee-lawyer-letter", "second-instance-appellant-lawyer-letter",
    "second-instance-appellee-lawyer-letter", "execution-lawyer-letter",
})
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
SLOT = re.compile(r"\{\{([a-z_]+)\}\}")


def _replace_slots(paragraph, values: dict) -> None:
    nodes = paragraph.xpath(".//w:t", namespaces=WORD_NS)
    text = "".join(node.text or "" for node in nodes)
    for match in reversed(list(SLOT.finditer(text))):
        value = str(values[match.group(1)])
        start, stop = match.span()
        offset = 0
        inserted = False
        for node in nodes:
            original = node.text or ""
            end = offset + len(original)
            if end > start and offset < stop:
                node.text = original[:max(0, start - offset)] + (value if not inserted else "") + original[max(0, stop - offset):]
                node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                inserted = True
            offset = end
    for node in nodes:
        parts = (node.text or "").split("\n")
        if len(parts) < 2:
            continue
        node.text = parts[0]
        parent = node.getparent()
        position = parent.index(node) + 1
        for part in parts[1:]:
            parent.insert(position, etree.Element("{" + WORD_NS["w"] + "}br"))
            text_node = etree.Element("{" + WORD_NS["w"] + "}t")
            text_node.text = part
            text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            parent.insert(position + 1, text_node)
            position += 2


def fill_template(document_type: str, values: dict) -> bytes:
    output = BytesIO()
    with ZipFile(TEMPLATE_ROOT / f"{document_type}.docx") as source, ZipFile(output, "w", ZIP_DEFLATED) as target:
        for item in source.infolist():
            payload = source.read(item.filename)
            if item.filename.startswith("word/") and item.filename.endswith(".xml") and b"{{" in payload:
                root = etree.fromstring(payload)
                for paragraph in root.xpath("//w:p", namespaces=WORD_NS):
                    _replace_slots(paragraph, values)
                payload = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            target.writestr(item, payload)
    return output.getvalue()


def case_template_values(record, document_type: str, context: dict) -> dict:
    data = record.data or {}
    customer = context.get("customer") or {}
    plaintiff = case_value(data, "plaintiff", "plaintiffs", "appellant", "applicant", legacy="AppellantNames")
    defendant = case_value(data, "opponent", "defendant", "defendants", "appellee", "respondent", legacy="AppelleeNames")
    # 根据生成菜单的当事人角色确定对方，二审与执行不误用一审原告。
    opponent = plaintiff if document_type == "first-instance-appellee-lawyer-letter" else defendant
    if record.customer and defendant == record.customer:
        opponent = plaintiff
    if document_type == "authorization-letter":
        third_party = case_value(data, "third_party", "third_parties", "third_person", "the_third_names", legacy="TheThirdNames")
        opponent = "、".join(value for value in [opponent, third_party] if value)
    if document_type.startswith("first-instance"):
        court = case_value(data, "first_court_name", "first_instance_court", "court", legacy="FirstIntanceCourtName")
    elif document_type.startswith("second-instance"):
        court = case_value(data, "second_court_name", "second_instance_court", legacy="SecondIntanceCourtName")
    elif document_type == "execution-lawyer-letter":
        court = case_value(data, "execution_court_name", "execution_court", "execution_instance_court", legacy="ExecutionIntanceCourtName")
    else:
        court = case_value(data, "court", "second_court_name", "first_court_name", legacy="FirstIntanceCourtName")
    trial_level = case_value(data, "trial_level", "court_level")
    if document_type == "archive-cover":
        if "二审" in record.status:
            trial_level = "二审"
            court = case_value(data, "second_court_name", "second_instance_court", legacy="SecondIntanceCourtName")
        elif "再审" in record.status:
            trial_level = "再审"
            court = case_value(data, "retrial_court_name", "last_instance_court", legacy="LastIntanceCourtName")
        elif "一审" in record.status:
            trial_level = "一审"
            court = case_value(data, "first_court_name", "first_instance_court", "court", legacy="FirstIntanceCourtName")
    return {
        "case_no": record.serial_no, "client": record.customer,
        "plaintiff": plaintiff, "defendant": defendant, "opponent": opponent,
        "cause": case_value(data, "cause_or_charge", "cause", "charge", legacy="CauseName"),
        "lawyer": context.get("case_lawyer") or "", "assistant": context.get("assistant") or "",
        "court_lawyer": context.get("court_lawyer") or "", "court": court,
        "phones": "、".join(dict.fromkeys(value for value in [context.get("case_lawyer_phone"), context.get("assistant_phone")] if value)),
        "today": f"{datetime.now():%Y年%m月%d日}",
        "case_type": case_value(data, "case_type", legacy="CaseTypeName"),
        "received_date": case_value(data, "case_register_date", "source_date", legacy="CaseRegisterDate")[:10],
        "archive_date": f"{datetime.now():%Y年%m月%d日}",
        "file_maker": case_value(data, "archive_submitter_display_name", "file_maker") or context.get("file_maker") or "",
        "trial_level": trial_level,
        "closed_date": case_value(data, "closed_date", "case_closed_date")[:10],
        "trial_result": case_value(data, "trial_result", "judgment_result"),
        "page_count": case_value(data, "paper_page_count", "archive_page_count"),
        "archive_remark": case_value(data, "archive_remark"),
        "fonds_no": case_value(data, "fonds_no"), "catalogue_no": case_value(data, "catalogue_no"),
        "volume_no": case_value(data, "volume_no"), "archive_no": case_value(data, "archive_no", legacy="FileNo"),
        "legal_name": case_value(customer, "legal_representative", legacy="LegalAgentName"),
        "legal_id": case_value(customer, "legal_agent_id_no", legacy="LegalAgentIdNo"),
        "legal_title": case_value(customer, "legal_agent_title", legacy="LegalAgentTitle"),
    }


def render_case_document(record, document_type: str, context: dict) -> bytes:
    return fill_template(document_type, case_template_values(record, document_type, context))


def render_case_print_tables(records, projections: list[dict]) -> bytes:
    document = None
    for record, data in zip(records, projections, strict=True):
        item = Document(BytesIO(fill_template("print-table", {
            "case_no": record.serial_no, "plaintiff": data["plaintiff"], "defendant": data["defendant"],
            "notary_no": data["notary_no"].replace("（", "(").replace("）", ")").replace("，", ",").replace(",", "\n"),
            "lawyer": data["lawyer"], "assistant": data["assistant"],
            "court_lawyer": data["court_lawyer"], "brand_managers": data["brand_managers"],
        })))
        if document is None:
            document = item
        else:
            for element in item.element.body:
                if element.tag != "{" + WORD_NS["w"] + "}sectPr":
                    document.element.body.insert(-1, deepcopy(element))
    output = BytesIO()
    document.save(output)
    return output.getvalue()
