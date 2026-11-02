"""网上立案材料准备（陶国南 11-01 21:49 定）：按“人民法院在线服务”网上立案的填写顺序，从 OA 取本案数据生成一份 Word，
只有两部分：立案信息表（管辖建议写成表里一行）和立案材料清单（逐项标 OA 已有 / 缺）。不生成起诉状、不登录平台、不代为提交。

先支持知识产权侵权民事案件的一审、二审。证件号、手机号由程序直接写进 Word，不经 AI 模型；有这个案件权限的人就能看
（陶国南 11-01 定，不另设授权）。预览只告诉“已有 / 缺”，不返回证件号和手机号原文。
栏目依据公开资料整理（各地法院公开的网上立案操作指引、《民事诉讼法》关于起诉状和上诉状内容的规定），以律师提交时页面为准。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
import re

from sqlalchemy import select

from app.models import BusinessRecord, FileAttachment, User

PENDING = "【待补充】"
SENSITIVE_LABELS = ("证件号码", "统一社会信用代码", "联系电话")
_ORG_SUFFIX = re.compile(r"(公司|店|厂|行|部|中心|事务所|合作社|商行|经营部|工作室|馆|社|院|所|集团|协会|学校|医院)$")


@dataclass
class Sheet:
    instance: str
    rows: list[tuple[str, str, str]] = field(default_factory=list)  # (栏目, 填写内容, 来源或说明)
    materials: list[tuple[str, str, str]] = field(default_factory=list)  # (材料, OA 已有/缺, 说明)

    def add(self, label: str, value, source: str = "") -> None:
        text = str(value or "").strip()
        self.rows.append((label, text or PENDING, source if text else (source or "OA 里没有，请律师补")))


def _names(value) -> list[str]:
    if isinstance(value, list):
        items = value
    else:
        items = re.split(r"[、,，;；\n]+", str(value or ""))
    return list(dict.fromkeys(str(item).strip() for item in items if str(item).strip()))


def _is_person(name: str, data: dict) -> bool:
    kind = str(data.get("organization_type") or data.get("customer_type") or "")
    if kind:
        return kind in {"个人", "自然人"}
    return not _ORG_SUFFIX.search(name) and 2 <= len(name) <= 4


async def _party_profile(name: str, db) -> tuple[dict, str]:
    """当事人资料：先当事人库，再客户档案；都没有就返回空。"""
    from app.data_models.parties import PartyRecord
    party = await db.scalar(select(PartyRecord).where(PartyRecord.name == name).order_by(PartyRecord.id.desc()))
    if party is not None and party.data:
        return dict(party.data), "当事人库"
    customer = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "customer", BusinessRecord.title == name).order_by(BusinessRecord.id.desc()))
    if customer is not None:
        return dict(customer.data or {}), "客户档案"
    return {}, ""


async def _add_party(sheet: Sheet, role: str, name: str, db) -> None:
    data, source = await _party_profile(name, db)
    where = source or "OA 未登记该当事人资料"
    if _is_person(name, data):
        sheet.add(f"{role}（自然人）姓名", name, "案件")
        sheet.add(f"{role}证件类型", "居民身份证" if data.get("identity_no") else "", where)
        sheet.add(f"{role}证件号码", data.get("identity_no"), where)
        sheet.add(f"{role}住所地/经常居住地", data.get("registered_address") or data.get("address"), where)
    else:
        sheet.add(f"{role}（单位）名称", name, "案件")
        sheet.add(f"{role}统一社会信用代码", data.get("credit_code") or data.get("organization_code"), where)
        sheet.add(f"{role}住所地", data.get("registered_address") or data.get("address"), where)
        sheet.add(f"{role}法定代表人/负责人", data.get("legal_representative"), where)
        sheet.add(f"{role}法定代表人职务", data.get("legal_agent_title"), where)
    sheet.add(f"{role}联系电话", data.get("phone") or data.get("invoice_phone"), where)


def _court_suggestion(data: dict, defendant_addresses: list[str]) -> str:
    court = str(data.get("first_court_name") or data.get("court") or "").strip()
    if court:
        return f"案件已登记法院：{court}"
    places = "、".join(address for address in defendant_addresses if address)
    hint = f"被告住所地（{places}）" if places else "被告住所地"
    return (f"建议：{hint}或侵权行为地的有管辖权法院；知识产权案件注意专门管辖（知识产权法院/法庭、指定管辖的基层法院）。"
            "最终由律师判断。")


async def _people(usernames: list[str], db) -> list[User]:
    if not usernames:
        return []
    return list((await db.scalars(select(User).where(User.username.in_(usernames)))).all())


def _attachment_hits(attachments: list[FileAttachment], *keywords: str) -> list[str]:
    return [item.original_name for item in attachments if any(word in (item.original_name or "") for word in keywords)]


async def build_sheet(case: BusinessRecord, instance: str, db) -> Sheet:
    data = dict(case.data or {})
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    sheet = Sheet(instance)
    second = instance == "二审"

    # 一、立案类型与法院
    sheet.add("立案类型", "审判立案 → 为他人或公司等组织申请（律师代理）", "固定")
    sheet.add("案件类型", "民事二审（上诉）" if second else "民事一审", "固定")
    cause = data.get("cause_or_charge") or data.get("cause") or legacy.get("CaseReasonName") or legacy.get("CaseReason")
    sheet.add("案由", cause, "案件")
    if second:
        court = str(data.get("first_court_name") or data.get("first_instance_court") or data.get("court") or "").strip()
        # 迁移数据里有的只存了法院代码（如“豫1728”），提醒律师核对全称。
        sheet.add("原审法院", court, "案件法院信息" + ("（这是法院代码，请核对法院全称）" if re.fullmatch(r"[\u4e00-\u9fff]\d{2,4}", court) else ""))
        sheet.add("原审案号", data.get("first_court_case_no") or data.get("first_instance_case_no") or data.get("court_case_no"), "案件法院信息")
        sheet.add("上诉法院（受理法院）", data.get("second_court_name") or data.get("second_instance_court"), "案件法院信息")
        sheet.add("原审裁判文书送达日期", data.get("first_judgment_served_date") or data.get("judgment_served_date"), "案件；上诉期从送达次日起算 15 日")

    # 二、当事人
    if second:
        plaintiffs = _names(data.get("appellant_names") or data.get("appellants") or data.get("plaintiffs") or data.get("plaintiff"))
        defendants = _names(data.get("appellee_names") or data.get("appellees") or data.get("defendants") or data.get("defendant"))
        roles = ("上诉人", "被上诉人")
    else:
        plaintiffs = _names(data.get("plaintiffs") or data.get("plaintiff"))
        defendants = _names(data.get("defendants") or data.get("defendant") or data.get("opponent"))
        roles = ("原告", "被告")
    if not plaintiffs:
        sheet.add(roles[0], "", "案件")
    for name in plaintiffs:
        await _add_party(sheet, roles[0], name, db)
    if not defendants:
        sheet.add(roles[1], "", "案件")
    defendant_addresses = []
    for name in defendants:
        await _add_party(sheet, roles[1], name, db)
        profile, _ = await _party_profile(name, db)
        defendant_addresses.append(str(profile.get("registered_address") or profile.get("address") or "").strip())

    # 三、代理人（本所律师）
    usernames = _names(data.get("handling_lawyer_usernames") or data.get("case_team_usernames"))
    lawyers = await _people(usernames, db) if usernames else []
    names = [user.display_name for user in lawyers] or _names(data.get("handling_lawyers") or data.get("case_lawyer_name"))
    if not names:
        sheet.add("代理人（律师）", "", "案件经办律师")
    for user_name in names:
        user = next((item for item in lawyers if item.display_name == user_name), None)
        profile = (user.profile or {}) if user else {}
        sheet.add("代理人（律师）姓名", user_name, "案件经办律师")
        sheet.add("律师执业证号", profile.get("license_no") or profile.get("practice_no"), "人员档案")
        sheet.add("律师联系电话", profile.get("mobile") or profile.get("office_phone"), "人员档案")
    sheet.add("律师事务所", "", "按授权委托书和所函上的律所填写")

    # 四、诉讼请求、事实与理由、标的额
    sheet.add("上诉请求" if second else "诉讼请求", "", "以律师起草的上诉状/起诉状为准，平台会自动识别后核对")
    sheet.add("上诉理由" if second else "事实与理由", "", "同上")
    sheet.add("标的金额（元）", data.get("claim_amount") or data.get("subject_amount") or data.get("litigation_amount"), "案件")

    # 五、管辖建议、送达地址
    sheet.add("管辖法院建议", "" if second else _court_suggestion(data, defendant_addresses),
              "二审向原审法院递交上诉状或直接向上一级法院提出" if second else "按被告住所地/侵权行为地")
    sheet.add("送达地址确认（收件人、地址、手机、接收方式）", "", "平台上点“生成”填写；一般写本所律师的收件信息")

    # 立案材料清单：逐项比对案件、客户、合同的附件。
    customer_id = data.get("customer_record_id")
    contract_id = data.get("contract_record_id") or data.get("contract_id")
    owners = [case.id] + [int(value) for value in (customer_id, contract_id) if str(value or "").isdigit()]
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id.in_(owners)))).all())

    def material(label: str, *keywords: str, note: str = "") -> None:
        hits = _attachment_hits(attachments, *keywords)
        sheet.materials.append((label, "OA 已有" if hits else "缺", "；".join(hits[:3]) + (f"（共 {len(hits)} 份）" if len(hits) > 3 else "") if hits else note))

    if second:
        material("上诉状（当事人签字盖章后扫描）", "上诉状", note="律师起草，客户签字盖章后扫描上传")
        material("一审判决书/裁定书", "判决书", "裁定书", note="从法院收文或一审卷宗取")
    else:
        material("起诉状（当事人签字盖章后扫描）", "起诉状", note="律师另外起草，客户签字盖章后扫描上传")
    material("原告/上诉人主体证明（营业执照或身份证）", "营业执照", "身份证复印件", "身份证正反面", "主体资格", note="向客户索取")
    material("法定代表人身份证明书", "法定代表人身份证明", "法人身份证明", "法人代表证明", note="客户盖章")
    material("被告/被上诉人主体信息（企业信用信息截图或身份信息）", "信用信息", "工商", "企查查", "天眼查", note="可从国家企业信用信息公示系统截图")
    material("授权委托书", "授权委托书", "委托书", note="客户盖章、律师签字")
    material("律师执业证", "执业证", note="律师执业证扫描件")
    material("律师事务所函（所函）", "所函", "律师事务所函", note="律所盖章")
    material("证据目录及证据（权属证明、公证书、侵权证据等）", "证据", "公证书", "权利证书", "注册证", note="合并成 PDF 上传")
    material("送达地址确认书", "送达地址确认", note="可在平台上直接“生成”")
    return sheet


def masked_rows(sheet: Sheet) -> list[dict]:
    """预览给智能体看的版本：证件号、信用代码、手机号只说“已有 / 待补充”，原文只写进 Word。"""
    rows = []
    for label, value, source in sheet.rows:
        if any(word in label for word in SENSITIVE_LABELS) and value != PENDING:
            value = "已有（保存后在 Word 里显示）"
        rows.append({"栏目": label, "填写内容": value, "来源或说明": source})
    return rows


def render_docx(case: BusinessRecord, sheet: Sheet) -> bytes:
    from docx import Document
    from docx.shared import Pt

    document = Document()
    style = document.styles["Normal"]
    style.font.size = Pt(10.5)
    document.add_heading(f"网上立案材料准备（{sheet.instance}）", level=1)
    document.add_paragraph(f"OA 案件：{case.serial_no} {case.title}")
    document.add_paragraph("用途：律师登录“人民法院在线服务”网上立案时，按下表逐项复制粘贴、上传材料，由律师本人提交。"
                           "栏目依据公开资料整理，各法院略有不同，以提交时页面为准。“【待补充】”的项请律师补齐后再填。")

    document.add_heading("一、立案信息表", level=2)
    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    header = table.rows[0].cells
    header[0].text, header[1].text, header[2].text = "平台栏目", "填写内容", "来源或说明"
    for label, value, source in sheet.rows:
        cells = table.add_row().cells
        cells[0].text, cells[1].text, cells[2].text = label, value, source

    document.add_heading("二、立案材料清单", level=2)
    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    header = table.rows[0].cells
    header[0].text, header[1].text, header[2].text = "材料", "OA 已有 / 缺", "OA 里的文件或怎么准备"
    for label, state, note in sheet.materials:
        cells = table.add_row().cells
        cells[0].text, cells[1].text, cells[2].text = label, state, note
    document.add_paragraph("材料格式：图片或 PDF，内容清晰；证据建议合并成 PDF。起诉状/上诉状须当事人本人签字盖章后扫描上传。")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
