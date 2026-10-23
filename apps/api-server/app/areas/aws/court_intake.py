"""一键收文：按法院送达链接下载文书 → 两级匹配案件 → 官方收文入库并回填案号、开庭 → 缴费通知生成待确认费用单。

全部复用原业务接口的处理函数和权限校验；费用只建草稿，律师确认后再提交缴纳并设提醒。
"""

from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers

from app.agent_skill_packages.court_doc_intake.scripts.normalize_case_no import parse as parse_case_no
from app.areas.aws.court_service import CourtServiceFetchInput, fetch_court_service_documents
from app.core.dependencies import current_identity, get_db, settings
from app.models import BusinessRecord, FileAttachment

router = APIRouter()

FEE_MARKER = "【法院收文】"
# 审级 → 官方费用类型（fee_type_id 为系统费用类型主数据，与收文技能规则一致）。
FEE_TYPES = {"一审": (19, "一审诉讼费"), "二审": (20, "二审诉讼费"), "执行": (27, "官费")}
# 审级 → 法院信息字段前缀；原接口要求同审级必须已有法院名称，缺失时用文书上的受理法院补齐。
HEARING_PREFIX = {"一审": "first_court", "二审": "second_court"}
_SUFFIX = re.compile(r"(有限责任公司|股份有限公司|有限公司|公司)$")
_REGION = re.compile(r"^[一-鿿]{2,3}?[省市]")


class CourtIntakeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    link: str = Field(min_length=20, max_length=2000, description="法院短信里的完整送达链接，可连同短信正文一起粘贴")
    case_id: int | None = Field(default=None, gt=0, description="命中多个候选时，用户选定的案件 ID；首次调用不要填")


class CourtFeeConfirmInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    remind: bool = Field(default=True, description="是否同时建缴费期限提醒任务")
    remind_owner: str = Field(default="", max_length=64, description="提醒任务负责人账号；留空为当前用户")


def _core_names(name: str) -> list[str]:
    core = _SUFFIX.sub("", name.strip())
    return list(dict.fromkeys(item for item in (core, _REGION.sub("", core)) if len(item) >= 2))


def _brief(record: BusinessRecord) -> dict:
    data = record.data or {}
    return {"case_id": record.id, "serial_no": record.serial_no, "title": record.title, "customer": record.customer,
            "status": record.status, "court": data.get("court") or "", "court_case_no": data.get("court_case_no") or "",
            "plaintiff": data.get("plaintiff") or "", "defendant": data.get("opponent") or data.get("defendant") or "",
            "hearing_lawyer": data.get("hearing_lawyer") or "", "case_lawyer": data.get("case_lawyer") or ""}


async def _search(conditions: dict, identity: dict, db: AsyncSession) -> list[BusinessRecord]:
    from app.api_schemas.cases import CounselCaseSearchInput
    from app.core.cases import _query_counsel_cases
    body = CounselCaseSearchInput(page=1, page_size=20, **conditions)
    return list(await _query_counsel_cases(body, identity, db, counsel_only=False, include_status_filter=False, search_projection=True))


async def _match_case(numbers: list[str], plaintiffs: list[str], defendants: list[str], identity: dict, db: AsyncSession) -> dict:
    """第一级官方案号直配；未命中再按当事人核心字号、法院代字反查。只在唯一命中时返回案件。"""
    tried = []
    for number in numbers:
        parsed = parse_case_no(number)
        for variant in parsed["检索变体"][:4]:
            found = await _search({"keyword": variant}, identity, db)
            tried.append(f"案号 {variant}：{len(found)} 件")
            if found:
                level = {"level": "第一级 官方案号直配", "basis": f"官方案号 {variant}"}
                return {**level, "records": found, "tried": tried}
    court_code = parse_case_no(numbers[0])["受理机关代字"] if numbers else ""
    for defendant in [item for name in defendants for item in _core_names(name)]:
        found = await _search({"defendant": defendant}, identity, db)
        tried.append(f"被告 {defendant}：{len(found)} 件")
        basis = [f"被告含“{defendant}”"]
        for key, values in (("plaintiff", plaintiffs), ("court", [court_code] if court_code else [])):
            if len(found) <= 1:
                break
            for value in [item for name in values for item in (_core_names(name) if key == "plaintiff" else [name])]:
                narrowed = await _search({"defendant": defendant, **({"plaintiff": value} if key == "plaintiff" else {}),
                                          **({"court": value} if key == "court" else {})}, identity, db)
                narrowed = [record for record in narrowed if record.id in {item.id for item in found}]
                tried.append(f"叠加{'原告' if key == 'plaintiff' else '法院代字'} {value}：{len(narrowed)} 件")
                if narrowed:
                    found = narrowed
                    basis.append(f"{'原告含' if key == 'plaintiff' else '法院代字'}“{value}”")
                    break
        if found:
            return {"level": "第二级 当事人+机关反查", "basis": "，".join(basis), "records": found, "tried": tried}
    return {"level": "", "basis": "", "records": [], "tried": tried}


def _stem(name: str) -> str:
    stem = Path(name).stem
    return re.sub(r"(?i)\.(pdf|ofd|docx?)$", "", stem)


async def _receive(case: BusinessRecord, document: dict, court_no: str, received: str, identity: dict, db: AsyncSession) -> dict:
    """官方收文入库；同一案件已收过同名同大小的文书则跳过。"""
    from app.areas.aws.router import upload_official_document
    from app.core.storage import _attachment_storage_path
    source = await db.get(FileAttachment, document["attachment_id"])
    suffix = Path(source.original_name).suffix.lower() or ".pdf"
    expected = "_".join(part for part in (case.serial_no, court_no, _stem(source.original_name)) if part)[:200] + suffix
    existing = await db.scalar(select(FileAttachment).where(
        FileAttachment.record_id == case.id, FileAttachment.category == "官方收文",
        FileAttachment.original_name == expected, FileAttachment.size == source.size))
    if existing is not None:
        return {"name": expected, "attachment_id": existing.id, "skipped": True}
    path = _attachment_storage_path(source)
    if path is None:
        raise HTTPException(409, f"法院文书附件暂不可读取：{source.original_name}")
    upload = UploadFile(BytesIO(path.read_bytes()), filename=_stem(source.original_name) + suffix,
                        headers=Headers({"content-type": source.content_type or "application/pdf"}))
    result = await upload_official_document(
        file=upload, document_date=date.fromisoformat(received), category="收文附件",
        remark=document["fields"].get("文书类型") or "法院文书", case_ids="", case_id=case.id,
        court_case_no=court_no, identity=identity, db=db)
    return {"name": result["attachment"]["original_name"], "attachment_id": result["attachment"]["id"],
            "receipt_id": result["record"]["id"], "skipped": False}


async def _backfill_hearing(case: BusinessRecord, documents: list[dict], level: str, court_name: str, court_no: str,
                            identity: dict, db: AsyncSession) -> dict:
    """传票与出庭通知书一致时回填开庭时间和法庭；不一致或审级不明时只报告。"""
    from app.api_schemas.cases import CaseCourtInfoInput
    from app.areas.legal.router import update_case_court_info
    hearings = {(item["fields"].get("开庭日期"), item["fields"].get("开庭时刻")): item["fields"].get("开庭法庭") or ""
                for item in documents if item["fields"].get("开庭日期") and item["fields"].get("开庭时刻")}
    if not hearings:
        return {"status": "无开庭信息"}
    if len(hearings) > 1:
        return {"status": "冲突未回填", "values": [f"{day} {clock}" for day, clock in hearings]}
    (day, clock), room = next(iter(hearings.items()))
    rooms = [item["fields"].get("开庭法庭") for item in documents if item["fields"].get("开庭法庭")]
    room = max(rooms, key=len) if rooms else room
    if level not in HEARING_PREFIX:
        return {"status": "审级不明未回填", "hearing": f"{day} {clock} {room}"}
    prefix = HEARING_PREFIX[level]
    date_field, room_field = prefix + "_hearing_date", prefix + "_courtroom"
    data = case.data or {}
    value = f"{day}T{clock}:00"
    previous = str(data.get(date_field) or "")
    if previous.replace(" ", "T")[:16] == value[:16] and (data.get(room_field) or "") == room:
        return {"status": "已是最新", "hearing": f"{day} {clock} {room}"}
    payload = {date_field: datetime.fromisoformat(value), "comment": "法院收文：按传票/出庭通知书回填开庭"}
    if room:
        payload[room_field] = room
    filled = []
    if not str(data.get(prefix + "_name") or "").strip():
        if not court_name:
            return {"status": "缺法院名称未回填", "hearing": f"{day} {clock} {room}"}
        payload[prefix + "_name"] = court_name
        filled.append(f"{level}法院 {court_name}")
    if court_no and not str(data.get(prefix + "_case_no") or "").strip():
        payload[prefix + "_case_no"] = court_no
        filled.append(f"{level}案号 {court_no}")
    await update_case_court_info(case.id, CaseCourtInfoInput(**payload), identity=identity, db=db)
    return {"status": "已回填", "hearing": f"{day} {clock} {room}", "previous": previous, "also_filled": filled}


def _deadline(fields: dict, documents: list[dict]) -> str:
    """“收到次日起 N 日内”：以送达当日（文书落款日，缺失时取同批文书落款日，再缺则今天）加 N 日。"""
    days = fields.get("预交天数")
    if not days:
        return ""
    dates = [fields.get("落款日期")] + [item["fields"].get("落款日期") for item in documents]
    served = next((value for value in dates if value), date.today().isoformat())
    return (date.fromisoformat(served) + timedelta(days=int(days))).isoformat()


async def _prepare_fee(case: BusinessRecord, document: dict, court_no: str, level: str, documents: list[dict],
                       identity: dict, db: AsyncSession) -> dict:
    """缴费通知只建费用草稿，等律师确认后再提交缴纳；同一文号同金额已有费用则复用。"""
    from app.api_schemas.finance import FinanceFeeInput
    from app.areas.finance.router import create_finance_fee
    fields = document["fields"]
    amount = float(fields.get("缴费金额") or 0)
    if amount <= 0:
        return {"status": "金额未识别，需人工建单", "document": document["name"]}
    if level not in FEE_TYPES:
        return {"status": "审级不明，需律师确认费用类型", "amount": amount}
    fee_type_id, subtype = FEE_TYPES[level]
    existing = [record for record in (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance"))).all()
                if str((record.data or {}).get("case_id") or (record.data or {}).get("case_record_id") or "") == str(case.id)
                and (record.data or {}).get("document_no") == court_no and int((record.data or {}).get("fee_type_id") or 0) == fee_type_id
                and abs(float((record.data or {}).get("amount") or 0) - amount) < 0.01]
    account = fields.get("收款账户") or {}
    deadline = _deadline(fields, documents)
    if existing:
        record = existing[0]
        return {"status": "已有费用单", "fee_id": record.id, "serial_no": record.serial_no, "fee_status": record.status,
                "amount": amount, "fee_type": subtype, "deadline": (record.data or {}).get("deadline") or deadline}
    description = (f"{FEE_MARKER}{fields.get('文书类型') or '缴费通知'}：{fields.get('受理机关') or ''} {court_no}，金额 {amount:g} 元，"
                   f"收到次日起{fields.get('预交天数') or '?'}日内预交；收款户名 {account.get('户名', '')}，"
                   f"开户行 {account.get('开户行', '')}，账号 {account.get('账号', '')}")
    created = await create_finance_fee(FinanceFeeInput(
        title=subtype, customer=case.customer, amount=amount, fee_type_id=fee_type_id, fee_type="官方费用",
        expense_scope="律所", expense_subtype=subtype, case_no=case.serial_no, case_record_id=case.id,
        handler=identity["username"], court=fields.get("受理机关") or "", document_no=court_no,
        payee=account.get("户名", ""), deadline=date.fromisoformat(deadline) if deadline else None, description=description,
    ), identity=identity, db=db)
    return {"status": "待确认", "fee_id": created["id"], "serial_no": created.get("serial_no"), "amount": amount,
            "fee_type": subtype, "deadline": deadline, "payee": account.get("户名", ""), "account": account.get("账号", ""),
            "bank": account.get("开户行", "")}


@router.post(f"{settings.api_prefix}/documents/court-service/intake", status_code=201)
async def intake_court_service(body: CourtIntakeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """一键法院收文：下载送达文书、匹配案件、官方收文入库、回填法院案号和开庭；缴费通知生成待确认的官方费用单。

    命中多个案件时返回候选，让用户选定后带 case_id 再调用；匹配不到则停止，不新建案件。
    """
    fetched = await fetch_court_service_documents(CourtServiceFetchInput(link=body.link), identity, db)
    documents = fetched["documents"]
    numbers = fetched["case_numbers"]
    plaintiffs = list(dict.fromkeys(name for item in documents for name in item["fields"].get("原告") or []))
    defendants = list(dict.fromkeys(name for item in documents for name in item["fields"].get("被告") or []))
    report = {"court": fetched["court"], "case_numbers": numbers,
              "documents": [{"attachment_id": item["attachment_id"], "name": item["name"], "fields": item["fields"]} for item in documents]}
    if body.case_id is not None:
        from app.core.permissions import _ensure_record_module
        case = await _ensure_record_module(body.case_id, "case", identity, db)
        match = {"level": "用户选定", "basis": f"用户从候选中选定 {case.serial_no}", "records": [case], "tried": []}
    else:
        match = await _match_case(numbers, plaintiffs, defendants, identity, db)
    records = match["records"]
    report["match"] = {"level": match["level"], "basis": match["basis"], "tried": match["tried"],
                       "candidates": [_brief(record) for record in records[:20]]}
    if len(records) != 1:
        report["status"] = "需要选择案件" if records else "系统内未登记该案"
        report["next_step"] = ("请用户从候选中选定案件后，带 case_id 重新调用本工具。" if records else
                               "已停止：系统内未找到对应案件，请先建案；文书已保存为附件，可稍后再收文。")
        return report
    from app.core.permissions import _ensure_record_module
    # 检索返回的是投影对象，写入前按原权限重新读取完整案件记录。
    case = await _ensure_record_module(records[0].id, "case", identity, db)
    court_no = numbers[0] if numbers else ""
    level = parse_case_no(court_no)["审级"] if court_no else ""
    received = [await _receive(case, item, court_no, item["fields"].get("落款日期") or date.today().isoformat(), identity, db)
                for item in documents]
    await db.refresh(case)
    court_name = fetched["court"] or next((item["fields"].get("受理机关") for item in documents if item["fields"].get("受理机关")), "")
    hearing = await _backfill_hearing(case, documents, level, court_name, court_no, identity, db)
    fees = [await _prepare_fee(case, item, court_no, level, documents, identity, db)
            for item in documents if item["fields"].get("文书类型") == "交纳诉讼费用通知书"]
    await db.refresh(case)
    report.update({
        "status": "已收文", "case": _brief(case), "instance_level": level, "received": received,
        "court_case_no": (case.data or {}).get("court_case_no") or "", "hearing": hearing, "fees": fees,
        "next_step": ("有待确认的官方费用：请向律师确认是否提交缴纳并设缴费期限提醒，确认后对每个 fee_id 调用“确认收文费用”。"
                      if any(item.get("status") == "待确认" for item in fees) else "收文完成。"),
    })
    return report


@router.post(f"{settings.api_prefix}/documents/court-service/fees/{{fee_id}}/confirm")
async def confirm_court_intake_fee(fee_id: int, body: CourtFeeConfirmInput, identity: dict = Depends(current_identity),
                                   db: AsyncSession = Depends(get_db)):
    """确认收文费用：把收文生成的官方费用草稿提交缴纳（自动匹配收款单位），并按最后缴费期限建提醒任务。"""
    from app.api_schemas.finance import FinanceActionInput
    from app.api_schemas.tasks import TaskInput
    from app.areas.finance.fee_workflows import list_finance_fee_payment_types, submit_finance_fee
    from app.areas.tp.router import create_task
    from app.core.permissions import _ensure_record_module
    fee = await _ensure_record_module(fee_id, "finance", identity, db)
    data = dict(fee.data or {})
    if not str(fee.description or data.get("description") or "").startswith(FEE_MARKER):
        raise HTTPException(409, "只能确认法院收文生成的费用单")
    result = {"fee_id": fee.id, "serial_no": fee.serial_no}
    if fee.status in {"草稿", "已退回"}:
        account = re.search(r"账号 ([0-9]{6,40})", str(fee.description or ""))
        options = (await list_finance_fee_payment_types(fee_id, "", identity=identity, db=db))["items"]
        matched = [item for item in options if account and account.group(1) in re.sub(r"\D", "", str(item.get("account") or ""))]
        if not matched and data.get("payee"):
            matched = [item for item in options if data["payee"] in f"{item.get('name', '')}{item.get('payee', '')}" and item.get("nature") == "官费"]
        payment_type = matched[0] if len(matched) == 1 else None
        submitted = await submit_finance_fee(fee_id, FinanceActionInput(
            amount=abs(float(data.get("amount") or 0)), payment_type_id=payment_type["id"] if payment_type else None,
            payment_remark=str(fee.description or "").removeprefix(FEE_MARKER)[:1000],
            comment=f"法院收文：申请缴纳{data.get('expense_subtype') or '官方费用'}（{data.get('document_no') or ''}）"), identity=identity, db=db)
        result.update({"submitted": True, "fee_status": submitted.get("status") if isinstance(submitted, dict) else "",
                       "payment_type": (payment_type or {}).get("name") or "未匹配到系统收款单位，按费用单收款信息办理"})
    else:
        result.update({"submitted": False, "fee_status": fee.status, "note": "费用单已不在草稿状态，未重复提交"})
    deadline = data.get("deadline")
    if body.remind and deadline:
        title = f"缴纳{data.get('expense_subtype') or '官方费用'}{abs(float(data.get('amount') or 0)):g}元（最后期限{deadline}）"
        case_id = data.get("case_id") or data.get("case_record_id")
        exists = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "task", BusinessRecord.title == title))
        if exists is not None:
            result["task"] = {"task_id": exists.id, "skipped": True}
        else:
            task = await create_task(TaskInput(
                title=title, owner=body.remind_owner or identity["username"], deadline=date.fromisoformat(str(deadline)[:10]),
                priority="重要", **({"case_record_id": int(case_id)} if case_id else {"case_no": data.get("case_no") or ""}),
                description=f"{data.get('document_no') or ''} 缴费通知：最后缴费期限 {deadline}，逾期未交按撤诉处理。费用单 {fee.serial_no}"),
                identity=identity, db=db)
            result["task"] = {"task_id": task.get("id"), "serial_no": task.get("serial_no"), "deadline": deadline, "skipped": False}
    return result
