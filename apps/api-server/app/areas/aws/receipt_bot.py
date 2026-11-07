"""钉钉收文助手（陶国南 11-07）：律师在收文群转发法院短信并 @收文助手，按发送人本人的账号收文，并在群里告知律师和律师助理。

这里只放与钉钉连接无关的部分：认人、调收文接口、记录、拼回复。下载、匹配、入库全部走现有“一键收文”接口，
用发送人本人的短期令牌调用，权限和留痕与网页一致，机器人没有自己的放宽路径。
群里只写案件要素，不写收款账号、法官电话和文书正文。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import asyncio
import hashlib
import logging
import re
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_skill_packages.court_doc_intake.scripts import fetch_court_docs as court_api
from app.areas.aws.court_intake import CourtIntakeInput
from app.config import settings
from app.core.dependencies import current_identity, get_db
from app.models import BusinessRecord, User, WorkflowEvent

logger = logging.getLogger(__name__)
router = APIRouter()

MODULE = "court_group_receipt"
WAITING, SAVING, PENDING, DONE, CLOSED, CANCELLED = "待确认", "入库中", "待处理", "已导入", "不入库", "已取消"
UNCERTAIN_STATUS = 504  # 请求发出去了但没等到结果，可能已经写入
CONFIRM_MINUTES = 30
MAX_RECORD_ID = 2_147_483_647  # 记录 ID 是 int4，更大的数字 PostgreSQL 会报错
SKILL_ID = "court-doc-intake"
INTAKE_PATH = "/documents/court-service/bot-receipts/intake"
RECEIPT_PAGE = "/?page=documents-official"
UNDO_HINT = "存错了：到官文收文删除这条（已处理的要先走撤销），上面列的回填内容到案件里改回，费用草稿到费用单删除。"
ASSISTANT_NAME_FIELDS = ("assistants", "assistant", "case_assistant")
ASSISTANT_ACCOUNT_FIELDS = ("assistant_usernames", "assistant_username")
_CASE_LOCKS: dict[int, asyncio.Lock] = {}
_MAX_LOCKS = 500
_LINK = re.compile(r"https?://[^\s，,。；;]+")
_COURT = re.compile(r"人民法院|法院|仲裁委员会|人民检察院")
_FIRST_LEVEL = "第一级"
_SECOND_LEVEL = "第二级"
COURT_NUMBER_FIELDS = ("court_case_no", "first_court_case_no", "first_instance_case_no", "second_court_case_no",
                       "retrial_court_case_no", "hearing_case_no", "court_no", "filing_no", "official_no")
COURT_NAME_FIELDS = ("court", "first_court_name", "second_court_name", "retrial_court_name", "execution_court_name")
# 只用来判断全所是否唯一，结果不显示给任何人，也不用它写入。
_UNIQUE_CHECK_IDENTITY = {"username": "receipt-bot-unique-check", "display_name": "收文助手唯一性检查", "role": "admin", "role_ids": ["admin"],
                          "_actual_role": "admin", "_actual_role_ids": ["admin"], "department": "", "action_keys": ["*"], "menu_keys": []}

Api = Callable[[str, str, dict], Awaitable[dict]]
AgentTurn = Callable[[str, str], Awaitable[None]]


@dataclass
class BotMessage:
    message_id: str
    conversation_type: str  # "1" 单聊，"2" 群聊
    conversation_id: str
    conversation_title: str
    text: str
    sender_id: str
    sender_nick: str = ""


@dataclass
class BotSettings:
    group_id: str
    use_cloud_agent: bool
    auto_save_unique: bool


@dataclass
class Reply:
    text: str
    at_user_ids: list[str]


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


def _serial(message_id: str) -> str:
    return "QSW" + hashlib.sha256(message_id.encode()).hexdigest()[:32]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _service_link(text: str) -> str:
    for link in _LINK.findall(text or ""):
        try:
            court_api.parse_service_link(link)
            return link
        except ValueError:
            continue
    return ""


def parse_command(text: str) -> tuple[str, int | None, int | None] | None:
    """律师的回复必须带编号才算数，明确指向哪一条：“确认 501842”“取消 501842”“确认 501842 2”（第 2 个候选）。

    不带编号的“确认”“取消”“2”也认出来，用来提示带编号重发，不会写入。不是这些内容时返回 None。
    """
    match = re.fullmatch(r"(确认|取消)(?:\s*([0-9]{1,12}))?(?:\s+([0-9]{1,2}))?", text)
    if match:
        return match.group(1), int(match.group(2)) if match.group(2) else None, int(match.group(3)) if match.group(3) else None
    if re.fullmatch(r"[0-9]{1,2}", text):
        return "确认", None, int(text)
    return None


def _people(value: Any) -> list[str]:
    values = value if isinstance(value, (list, tuple)) else re.split(r"[,，、;；\s]+", str(value or ""))
    return [text for text in (str(item).strip() for item in values) if text]


async def find_sender(sender_id: str, db: AsyncSession) -> User | None:
    from app.core.permissions import _profile_dingtalk_login_ids
    if not sender_id:
        return None
    users = (await db.scalars(select(User).where(User.is_active.is_(True)))).all()
    return next((user for user in users if sender_id in _profile_dingtalk_login_ids(user.profile)), None)


async def case_assistants(case: BusinessRecord | None, db: AsyncSession) -> tuple[list[str], list[str]]:
    """案件律师助理：返回 (可 @ 的钉钉 ID, 没绑定只能写姓名的人)。"""
    from app.core.permissions import _profile_dingtalk_login_ids
    data = (case.data or {}) if case is not None else {}
    accounts = [name for field in ASSISTANT_ACCOUNT_FIELDS for name in _people(data.get(field))]
    names = [name for field in ASSISTANT_NAME_FIELDS for name in _people(data.get(field))]
    users = (await db.scalars(select(User).where(User.is_active.is_(True)))).all()
    by_account = {user.username: user for user in users}
    by_name: dict[str, list[User]] = {}
    for user in users:
        by_name.setdefault(str(user.display_name or "").strip(), []).append(user)
    matched: dict[str, User] = {name: by_account[name] for name in accounts if name in by_account}
    unmatched = []
    for name in names:
        if name in by_account:
            matched[name] = by_account[name]
        elif len(by_name.get(name, [])) == 1:
            matched[by_name[name][0].username] = by_name[name][0]
        elif name not in {str(user.display_name or "").strip() for user in matched.values()}:
            unmatched.append(name)
    ids, plain = [], list(dict.fromkeys(unmatched))
    for user in matched.values():
        bound = _profile_dingtalk_login_ids(user.profile)
        if bound:
            ids.append(bound[0])
        else:
            plain.append(str(user.display_name or user.username))
    return list(dict.fromkeys(ids)), list(dict.fromkeys(plain))


def _documents_text(report: dict) -> str:
    kinds = [(item.get("fields") or {}).get("文书类型") or item.get("name") or "" for item in report.get("documents") or []]
    return "、".join(dict.fromkeys(kind for kind in kinds if kind)) or "未识别"


def _facts(report: dict) -> list[str]:
    """群里能看到的案件要素：只取这几项，不取收款账号、法官电话和正文（陶国南 11-07）。"""
    case = report.get("case") or {}
    numbers = report.get("case_numbers") or []
    parties = "，".join(part for part in (f"原告 {case.get('plaintiff')}" if case.get("plaintiff") else "",
                                         f"被告 {case.get('defendant')}" if case.get("defendant") else "") if part)
    lines = [f"系统案号：{case.get('serial_no') or '—'}", f"法院案号：{case.get('court_case_no') or (numbers[0] if numbers else '—')}"]
    if parties:
        lines.append(f"当事人：{parties}")
    lines.append(f"文书类型：{_documents_text(report)}")
    hearing = report.get("hearing") or {}
    plan = report.get("plan") or {}
    hearing_text = hearing.get("hearing") if isinstance(hearing, dict) else ""
    planned = plan.get("hearing") or []
    if hearing_text or planned:
        lines.append(f"开庭：{hearing_text or '；'.join(planned)}")
    fees = report.get("fees") or plan.get("fees") or []
    for fee in fees:
        amount = fee.get("amount")
        if amount:
            lines.append(f"缴费：{amount} 元" + (f"，期限 {fee['deadline']}" if fee.get("deadline") else ""))
    return lines


def _plan_lines(report: dict) -> list[str]:
    """预览时列出确认后会写的所有内容：文书、法院案号、开庭、承办法官和书记员、费用草稿。"""
    plan = report.get("plan") or {}
    receipts = [str(item) for item in plan.get("receipts") or []]
    skipped = sum(1 for item in receipts if item.startswith("已收过"))
    actions = []
    if len(receipts) - skipped:
        actions.append(f"存入文书 {len(receipts) - skipped} 份")
    if skipped:
        actions.append(f"{skipped} 份此前已收过，不重复存")
    court_no = str(plan.get("court_case_no") or "")
    if court_no and not court_no.startswith("已登记"):
        actions.append(f"回填法院案号 {court_no}")
    planned = [str(item) for item in plan.get("hearing") or []]
    existing = str(plan.get("hearing_existing") or "")
    if plan.get("hearing_note"):
        actions.append(f"开庭：{plan['hearing_note']}")
    elif planned and not existing:
        actions.append(f"回填开庭 {planned[0]}")
    elif planned and existing and not planned[0].startswith(existing):
        actions.append(f"系统已登记开庭 {existing}，文书为 {planned[0]}，不覆盖，请核对")
    staff = (plan.get("court_staff") or {}).get("display") or []
    if staff:
        actions.append("回填" + "、".join(str(item) for item in staff))
    for fee in plan.get("fees") or []:
        if fee.get("amount"):
            actions.append(f"生成费用草稿 {fee['amount']} 元" + (f"（期限 {fee['deadline']}）" if fee.get("deadline") else "") + "，提交仍需到系统确认")
    return ["确认后将：" + ("，".join(actions) or "不写入新内容")]


def _court_no_filled(report: dict, planned_court_no: str) -> str:
    """真的回填了才算：这次确实存入了文书，且入库后案件的法院案号就是预览计划要填的。文书全部已收过时不算。"""
    from app.agent_skill_packages.court_doc_intake.scripts.normalize_case_no import parse as parse_case_no
    saved = any(not item.get("skipped") for item in report.get("received") or [])
    current = str(report.get("court_case_no") or "").strip()
    if not (saved and planned_court_no and current):
        return ""
    return current if parse_case_no(current)["归一化"] == parse_case_no(planned_court_no)["归一化"] else ""


def _changes(report: dict, planned_court_no: str) -> dict:
    """这次写了什么，存进记录，撤回时照单改回。"""
    received = report.get("received") or []
    hearing = report.get("hearing") if isinstance(report.get("hearing"), dict) else {}
    staff = report.get("court_staff") if isinstance(report.get("court_staff"), dict) else {}
    fees = report.get("fees") or []
    return {"attachment_ids": [item.get("attachment_id") for item in received if not item.get("skipped")],
            "receipt_ids": [item.get("receipt_id") for item in received if item.get("receipt_id")],
            "hearing": {key: hearing.get(key) for key in ("status", "previous", "hearing") if hearing.get(key)},
            "also_filled": hearing.get("also_filled") or [], "court_no_filled": _court_no_filled(report, planned_court_no),
            "staff_filled": staff.get("filled") or [], "fee_ids": [item.get("fee_id") for item in fees if item.get("fee_id")]}


def _done_lines(report: dict, planned_court_no: str = "") -> list[str]:
    """写清改了什么：回填原值、法官书记员、费用单号都列出来；哪步失败也说清楚。"""
    received = report.get("received") or []
    saved = sum(1 for item in received if not item.get("skipped"))
    skipped = len(received) - saved
    actions = []
    if saved:
        actions.append(f"已存入案件文档和收文台 {saved} 份")
    if skipped:
        actions.append(f"{skipped} 份此前已收过，未重复存")
    court_no_filled = _court_no_filled(report, planned_court_no)
    if court_no_filled:
        actions.append(f"已回填法院案号 {court_no_filled}")
    hearing = report.get("hearing") if isinstance(report.get("hearing"), dict) else {}
    status = hearing.get("status")
    if status == "已回填":
        previous = str(hearing.get("previous") or "").replace("T", " ")
        actions.append("已回填开庭" + (f"（原为 {previous}）" if previous else ""))
    elif status == "已有开庭未覆盖":
        actions.append(f"系统已登记开庭 {str(hearing.get('previous') or '').replace('T', ' ')}，文书为 {hearing.get('hearing')}，未覆盖，请核对")
    elif status in {"冲突未回填", "审级不明未回填", "缺法院名称未回填"}:
        actions.append(f"开庭{status}，请核对")
    actions.extend(f"已回填{item}" for item in hearing.get("also_filled") or [])
    staff = report.get("court_staff") if isinstance(report.get("court_staff"), dict) else {}
    filled = staff.get("filled")
    if filled:
        actions.append("已回填" + "、".join(str(item) for item in filled))
    fees = report.get("fees") or []
    drafts = [str(item.get("serial_no") or "") for item in fees if item.get("status") == "待确认"]
    if drafts:
        actions.append(f"已生成费用草稿 {'、'.join(drafts)}，请到系统确认提交")
    failed = [item for item in [hearing, staff, *fees] if item.get("status") == "失败"]
    actions.extend(f"{item['step']}失败：{item.get('detail')}，请到系统处理" for item in failed)
    return ["已做：" + ("，".join(actions) or "无新增内容")]


def _link_line() -> str:
    base = (settings.dingtalk_app_url or "https://huzhilawfirm.com").rstrip("/")
    return f"系统查看：{base}{RECEIPT_PAGE}"


def _mention(ids: list[str]) -> str:
    return " ".join(f"@{item}" for item in ids)


async def _record(message: BotMessage, user: User, status: str, data: dict, db: AsyncSession) -> BusinessRecord | None:
    """每条收文短信留一条记录；同一条钉钉消息重复推送时只留一条（系统编号唯一）。"""
    record = BusinessRecord(module=MODULE, serial_no=_serial(message.message_id), title=(message.text or "收文短信")[:80],
                            customer="", status=status, owner=user.username, department=user.department or "",
                            description=message.sender_nick[:200],
                            data={"text": message.text[:4000], "sender_id": message.sender_id, "sender_nick": message.sender_nick,
                                  "sent_at": _now(), "source": "钉钉收文助手", **data})
    db.add(record)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return None
    db.add(WorkflowEvent(record_id=record.id, action="钉钉收文", from_status="", to_status=status, operator=user.username, comment=""))
    await db.commit()
    return record


async def _set_status(record: BusinessRecord, status: str, extra: dict, operator: str, db: AsyncSession) -> None:
    before = record.status
    record.status = status
    record.data = {**(record.data or {}), **extra}
    db.add(WorkflowEvent(record_id=record.id, action="钉钉收文", from_status=before, to_status=status, operator=operator,
                         comment=str(extra.get("reason") or extra.get("case_no") or "")[:500]))
    await db.commit()


def _case_lock(case_id: int) -> asyncio.Lock:
    """同一案件一次只入库一批：两位律师同时转发同一条短信时，后一批能查到前一批，不重复存。"""
    if case_id not in _CASE_LOCKS and len(_CASE_LOCKS) >= _MAX_LOCKS:
        for key in [key for key, lock in _CASE_LOCKS.items() if not lock.locked()]:
            del _CASE_LOCKS[key]
    return _CASE_LOCKS.setdefault(case_id, asyncio.Lock())


async def _move_from_waiting(record: BusinessRecord, status: str, extra: dict, operator: str, db: AsyncSession) -> bool:
    """只有还在“待确认”才改，和入库的 _claim 互斥：确认和取消同时发生时只有一个成功。"""
    data = {**(record.data or {}), **extra}
    changed = await db.execute(update(BusinessRecord).where(BusinessRecord.id == record.id, BusinessRecord.status == WAITING)
                               .values(status=status, data=data).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        await db.commit()
        return False
    db.add(WorkflowEvent(record_id=record.id, action="钉钉收文", from_status=WAITING, to_status=status, operator=operator,
                         comment=str(extra.get("reason") or "")[:500]))
    await db.commit()
    await db.refresh(record)
    return True


async def _claim(record: BusinessRecord, db: AsyncSession) -> bool:
    """入库前原子改状态，连发两次“确认”也只入库一次。"""
    changed = await db.execute(update(BusinessRecord).where(BusinessRecord.id == record.id, BusinessRecord.status == WAITING)
                               .values(status=SAVING, data={**(record.data or {}), "saving_at": _now()}).execution_options(synchronize_session=False))
    await db.commit()
    if changed.rowcount != 1:
        return False
    await db.refresh(record)
    return True


async def _save(record: BusinessRecord, case_id: int, user: User, message: BotMessage, api: Api, db: AsyncSession) -> Reply:
    me = _mention([message.sender_id])
    if not await _claim(record, db):
        return Reply(f"{me} 编号 {record.id} 这条收文已在处理或已处理。", [message.sender_id])
    link = (record.data or {}).get("link") or ""
    planned_court_no = str((record.data or {}).get("planned_court_no") or "")
    try:
        async with _case_lock(case_id):
            report = await api(user.username, INTAKE_PATH, {"link": link, "case_id": case_id, "confirm": True})
    except ApiError as exc:
        await _set_status(record, PENDING, {"reason": exc.detail}, user.username, db)
        if exc.status == UNCERTAIN_STATUS:
            return Reply(f"{me} {exc.detail}，已转到收文台待处理。请先到案件文档核对是否已存入，不要重发。\n{_link_line()}", [message.sender_id])
        return Reply(f"{me} 收文未完成：{exc.detail}。可能已存入部分文书，已转到收文台待处理，请核对。\n{_link_line()}", [message.sender_id])
    case = await db.get(BusinessRecord, case_id)
    await _set_status(record, DONE, {"case_id": case_id, "case_no": (report.get("case") or {}).get("serial_no") or "",
                                     "changes": _changes(report, planned_court_no)}, user.username, db)
    ids, plain = await case_assistants(case, db)
    at_ids = list(dict.fromkeys([message.sender_id, *ids]))
    if ids or plain:
        assistant_line = f"律师助理：{_mention(ids)}{' ' if ids and plain else ''}{'、'.join(plain)}"
    else:
        assistant_line = "本案未填律师助理"
    return Reply("\n".join([f"{me} 收文完成", *_facts(report), *_done_lines(report, planned_court_no), assistant_line, _link_line()]), at_ids)


async def expire_waiting(db: AsyncSession) -> int:
    """超时没回复的转待处理，收文台能看到，文书不会丢；入库中卡住（进程中断）的也转过去核对。"""
    now = datetime.now(timezone.utc)
    rows = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == MODULE, BusinessRecord.status.in_((WAITING, SAVING))))).all()
    changed = 0
    for record in rows:
        data = record.data or {}
        if record.status == WAITING and data.get("expires_at") and datetime.fromisoformat(data["expires_at"]) < now:
            changed += int(await _move_from_waiting(record, PENDING, {"reason": "超时未确认"}, record.owner, db))
        elif record.status == SAVING and data.get("saving_at") \
                and datetime.fromisoformat(data["saving_at"]) + timedelta(minutes=CONFIRM_MINUTES) < now:
            await _set_status(record, PENDING, {"reason": "入库结果不确定，请到案件文档核对"}, record.owner, db)
            changed += 1
    return changed


async def _waiting_records(user: User, db: AsyncSession) -> list[BusinessRecord]:
    return list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == MODULE, BusinessRecord.status == WAITING, BusinessRecord.owner == user.username,
    ).order_by(BusinessRecord.id.desc()).limit(10))).all())


async def _handle_command(command: tuple[str, int | None, int | None], user: User, message: BotMessage, api: Api, db: AsyncSession) -> Reply:
    verb, record_id, number = command
    me = _mention([message.sender_id])
    if record_id is None:
        # 没带编号不写入，列出来让律师带编号重发。
        waiting = await _waiting_records(user, db)
        if not waiting:
            return Reply(f"{me} 没有等你确认的收文。", [message.sender_id])
        lines = [f"{verb} {record.id}（{(record.data or {}).get('prompt_label') or '待确认收文'}）" for record in waiting]
        return Reply("\n".join([f"{me} 请带编号回复，明确是哪一条：", *lines]), [message.sender_id])
    record = await db.get(BusinessRecord, record_id) if record_id <= MAX_RECORD_ID else None
    if record is None or record.module != MODULE or record.owner != user.username:
        return Reply(f"{me} 没有等你确认的这条收文（编号 {record_id}），只有发短信的本人能确认。", [message.sender_id])
    if record.status != WAITING:
        return Reply(f"{me} 编号 {record_id} 这条状态为“{record.status}”，不用再确认。", [message.sender_id])
    data = record.data or {}
    expires = datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
    if expires is not None and expires < datetime.now(timezone.utc):
        if not await _move_from_waiting(record, PENDING, {"reason": "超时未确认"}, user.username, db):
            return Reply(f"{me} 编号 {record_id} 这条收文已在处理或已处理。", [message.sender_id])
        return Reply(f"{me} 这条收文已超过 {CONFIRM_MINUTES} 分钟未确认，已转到收文台待处理。\n{_link_line()}", [message.sender_id])
    if verb == "取消":
        if not await _move_from_waiting(record, CANCELLED, {"reason": "律师取消"}, user.username, db):
            return Reply(f"{me} 编号 {record_id} 这条收文已在处理或已处理，没能取消。", [message.sender_id])
        return Reply(f"{me} 已取消，编号 {record_id} 这条没有存入。", [message.sender_id])
    candidates = data.get("candidates") or []
    if candidates:
        if number is None or not 1 <= number <= len(candidates):
            return Reply(f"{me} 请回复“确认 {record_id} 序号”（序号 1～{len(candidates)}），或“取消 {record_id}”。", [message.sender_id])
        return await _save(record, int(candidates[number - 1]["case_id"]), user, message, api, db)
    if not data.get("case_id"):
        return Reply(f"{me} 这条收文缺少案件信息，请到收文台处理。", [message.sender_id])
    return await _save(record, int(data["case_id"]), user, message, api, db)


def _party_set(value: Any) -> set[str]:
    """案件和文书的当事人按分隔符拆开、统一括号和空格，整名比较，不用子串。"""
    values = value if isinstance(value, (list, tuple)) else re.split(r"[,，、;；/\n]+", str(value or ""))
    return {re.sub(r"\s+", "", str(item)).replace("(", "（").replace(")", "）") for item in values if str(item).strip()}


async def _cases_with_number(normalized: str, db: AsyncSession) -> set[int]:
    """全所登记了这个法院案号的案件，归一化后比较。只读，只用来判断是否唯一。"""
    from app.agent_skill_packages.court_doc_intake.scripts.normalize_case_no import parse as parse_case_no
    columns = [BusinessRecord.data[key].as_string() for key in COURT_NUMBER_FIELDS]
    rows = (await db.execute(select(BusinessRecord.id, *columns).where(BusinessRecord.module == "case", BusinessRecord.status != "已合并"))).all()
    return {row[0] for row in rows if any(value and str(value).strip() and parse_case_no(str(value))["归一化"] == normalized for value in row[1:])}


async def strict_unique(report: dict, db: AsyncSession) -> tuple[bool, str]:
    """能否不经律师确认直接存（陶国南 11-07 反查唯一也可直接存）。服务器判断，不看模型。全部满足才算唯一：

    1. 收文接口按发送人权限返回“待确认入库”，且只有一个案件；同一批文书不超过一个法院案号。
    2. 文书有案号时，该案同审级已登记的案号必须相同：登记了不同案号，可能是同一批当事人的另一个官司，不算唯一。
    3. 法院案号直配：文书案号归一化后，等于该案已登记的某个法院案号；检索命中别的字段不算。
    4. 当事人反查：文书的原告、被告都要有，每一个都要和该案原告、被告里的某一个整名相同；文书受理法院和该案登记的法院一致；
       文书上还要识别得出案号。识别不出案号的不直接存，请律师确认（调度 11-07，等陶国南答复前按此）。
    5. 不限发送人权限再查一遍全所，也只有这一个案件；发送人看不到的同名案件也算不唯一。
    返回 (是否唯一, 原因)。原因只存记录，不发群。不满足时不存，请律师回“确认”。
    """
    from app.agent_skill_packages.court_doc_intake.scripts.normalize_case_no import parse as parse_case_no
    from app.areas.aws.court_intake import _match_case
    case_id = int((report.get("case") or {}).get("case_id") or 0)
    case = await db.get(BusinessRecord, case_id) if case_id else None
    if case is None or case.module != "case":
        return False, "案件读取失败"
    data = case.data or {}
    level = str((report.get("match") or {}).get("level") or "")
    numbers = [str(item) for item in report.get("case_numbers") or []]
    if len(numbers) > 1:
        return False, "文书上有多个法院案号"
    fields = [item.get("fields") or {} for item in report.get("documents") or []]
    plaintiffs = list(dict.fromkeys(name for item in fields for name in item.get("原告") or []))
    defendants = list(dict.fromkeys(name for item in fields for name in item.get("被告") or []))
    registered = [parse_case_no(str(data[key])) for key in COURT_NUMBER_FIELDS if str(data.get(key) or "").strip()]
    document_number = parse_case_no(numbers[0]) if numbers else None
    if document_number is not None and document_number["归一化"] not in {item["归一化"] for item in registered}:
        same_level = [item for item in registered if not document_number["审级"] or not item["审级"] or item["审级"] == document_number["审级"]]
        if level.startswith(_FIRST_LEVEL) or same_level:
            return False, "法院案号与该案登记的不一致"
    if level.startswith(_FIRST_LEVEL) and document_number is None:
        return False, "文书上没有识别出法院案号"
    if level.startswith(_SECOND_LEVEL):
        if not (plaintiffs and defendants):
            return False, "文书上没有同时识别出原告和被告"
        if not (_party_set(plaintiffs) <= _party_set(data.get("plaintiff"))
                and _party_set(defendants) <= _party_set(data.get("opponent") or data.get("defendant"))):
            return False, "原告、被告没有全部对上"
        # 系统里法院多登记成代字（如 皖1226），文书上是全称：全称相同或案号里的代字相同都算。
        court = str(report.get("court") or next((item.get("受理机关") for item in fields if item.get("受理机关")), "") or "").strip()
        registered_courts = {str(data.get(key) or "").strip() for key in COURT_NAME_FIELDS} - {""}
        court_code = str(document_number["受理机关代字"] or "").strip() if document_number is not None else ""
        if not ((court and court in registered_courts) or (court_code and court_code in registered_courts)):
            return False, "受理法院与该案登记的不一致"
        if document_number is None:
            return False, "文书上没有识别出法院案号"
    elif not level.startswith(_FIRST_LEVEL):
        return False, "匹配方式不明确"
    # 案号搜索会漏案（已保存的 JSON 中文被转义、登记值带空格），这里直接比全所登记案号，不靠搜索。
    if document_number is not None:
        others = await _cases_with_number(document_number["归一化"], db)
        if others - {case_id}:
            return False, "全所不止这一个案件符合"
    everyone = await _match_case(numbers, plaintiffs, defendants, _UNIQUE_CHECK_IDENTITY, db)
    if [record.id for record in everyone["records"]] != [case_id]:
        return False, "全所不止这一个案件符合"
    return True, ""


async def _preview(message: BotMessage, link: str, user: User, config: BotSettings, api: Api, agent_turn: AgentTurn | None, db: AsyncSession) -> Reply | None:
    record = await _record(message, user, PENDING, {"kind": "zxfw", "link": link}, db)
    if record is None:
        return None
    return await _preview_record(record, message, link, user, config, api, agent_turn, db)


async def _preview_record(record: BusinessRecord, message: BotMessage, link: str, user: User, config: BotSettings, api: Api,
                          agent_turn: AgentTurn | None, db: AsyncSession) -> Reply:
    me = _mention([message.sender_id])
    if config.use_cloud_agent and agent_turn is not None:
        # 云端智能体按收文技能读短信并预览；它只能生成待确认请求，不能写入。结果以下面 OA 接口返回为准，云端失败不影响收文。
        try:
            await agent_turn(user.username, message.text[:2000])
        except Exception as exc:
            logger.warning("receipt bot cloud agent failed record=%s type=%s", record.id, type(exc).__name__)
    try:
        report = await api(user.username, INTAKE_PATH, {"link": link})
    except ApiError as exc:
        await _set_status(record, PENDING, {"reason": exc.detail}, user.username, db)
        return Reply(f"{me} 文书下载或识别失败：{exc.detail}。已转到收文台待处理。\n{_link_line()}", [message.sender_id])
    status = report.get("status")
    record_data = {"documents": [{"attachment_id": item.get("attachment_id"), "name": item.get("name") or "",
                                  "kind": (item.get("fields") or {}).get("文书类型") or ""} for item in report.get("documents") or []]}
    if status == "系统内未登记该案":
        await _set_status(record, PENDING, {**record_data, "reason": "未找到有权限的案件"}, user.username, db)
        return Reply(f"{me} 未找到你有权限的案件，文件没有存入案件，已转到收文台待处理。\n文书类型：{_documents_text(report)}\n{_link_line()}", [message.sender_id])
    expires = (datetime.now(timezone.utc) + timedelta(minutes=CONFIRM_MINUTES)).isoformat(timespec="seconds")
    if status == "需要选择案件":
        candidates = [{"case_id": item["case_id"], "serial_no": item.get("serial_no") or "", "title": item.get("title") or ""}
                      for item in (report.get("match") or {}).get("candidates") or []][:9]
        await _set_status(record, WAITING, {**record_data, "candidates": candidates, "expires_at": expires, "prompt_label": f"多个候选，{_documents_text(report)}"}, user.username, db)
        lines = [f"{index}. {item['serial_no']} {item['title']}" for index, item in enumerate(candidates, start=1)]
        return Reply("\n".join([f"{me} 匹配到多个案件，请回复“确认 {record.id} 序号”选择，或“取消 {record.id}”：", *lines, f"文书类型：{_documents_text(report)}"]), [message.sender_id])
    if status != "待确认入库":
        await _set_status(record, PENDING, {**record_data, "reason": str(status)}, user.username, db)
        return Reply(f"{me} 这条短信没有自动收文，已转到收文台待处理。\n{_link_line()}", [message.sender_id])
    case_id = int(report["case"]["case_id"])
    match = report.get("match") or {}
    basis = str(match.get("basis") or "")
    why_not = ""
    plan_court_no = str((report.get("plan") or {}).get("court_case_no") or "")
    record_data["planned_court_no"] = "" if plan_court_no.startswith("已登记") else plan_court_no
    if config.auto_save_unique:
        unique, why_not = await strict_unique(report, db)
        if unique:
            await _set_status(record, WAITING, {**record_data, "case_id": case_id, "auto_saved": True, "expires_at": expires,
                                                "match_level": str(match.get("level") or ""), "match_basis": basis}, user.username, db)
            reply = await _save(record, case_id, user, message, api, db)
            if record.status == DONE:
                reply.text += f"\n匹配依据：{basis}\n{UNDO_HINT}"
            return reply
    await _set_status(record, WAITING, {**record_data, "case_id": case_id, "expires_at": expires, "not_auto_reason": why_not,
                                                "prompt_label": f"{report['case'].get('serial_no') or ''} {_documents_text(report)}".strip()}, user.username, db)
    return Reply("\n".join([f"{me} 找到案件，请核对后回复“确认 {record.id}”存入，或“取消 {record.id}”：", *_facts(report), *_plan_lines(report),
                            *([f"匹配依据：{basis}"] if basis else [])]), [message.sender_id])


async def handle_message(message: BotMessage, config: BotSettings, *, api: Api, db: AsyncSession, agent_turn: AgentTurn | None = None) -> Reply | None:
    """处理一条 @收文助手 的消息，返回要回复的内容；None 表示不回复。"""
    from app.core.data_scope_gate import is_external_role
    me = _mention([message.sender_id]) if message.sender_id else ""
    if message.conversation_type != "2":
        return Reply("收文助手只在收文群使用，请在群里转发法院短信并 @收文助手。", [])
    if not config.group_id or message.conversation_id != config.group_id:
        logger.info("receipt bot ignored message from a group that is not the receipt group")
        return None
    user = await find_sender(message.sender_id, db)
    if user is None:
        return Reply(f"{me} 你的系统账号还没绑定钉钉，暂时不能用收文助手。请在钉钉里打开一次系统完成绑定后重发。", [message.sender_id])
    if is_external_role((user.profile or {}).get("permission_role")):
        return Reply(f"{me} 外部账号不能使用收文助手，请联系对接人。", [message.sender_id])
    if user.must_change_password:
        return Reply(f"{me} 请先登录系统修改初始密码，再重发。", [message.sender_id])
    text = (message.text or "").strip()
    command = parse_command(text)
    if command is not None:
        return await _handle_command(command, user, message, api, db)
    link = _service_link(text)
    if link:
        return await _preview(message, link, user, config, api, agent_turn, db)
    if not _COURT.search(text):
        return Reply(f"{me} 请转发法院送达短信（含送达链接）并 @收文助手。", [message.sender_id])
    record = await _record(message, user, PENDING, {"kind": "other_link" if _LINK.search(text) else "text_only",
                                                     "reason": "没有人民法院在线服务送达链接"}, db)
    if record is None:
        return None
    return Reply(f"{me} 短信里没有人民法院在线服务（zxfw.court.gov.cn）的送达链接，无法自动下载，已转到收文台待处理，请手工上传。\n{_link_line()}", [message.sender_id])


# ---------------------------------------------------------------------------
# 收文台“待处理”：没匹配上的短信，由有官文收文页面的人指定案件入库，或标记不入库。

class AssignInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_no: str = Field(min_length=2, max_length=64, description="指定入库的系统案号")


class CloseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(default="", max_length=500, description="不入库的原因，可不填")


def _require_internal(identity: dict) -> None:
    """外部账号不能用收文助手，收文台的待处理也一样（@ 机器人已拒绝，这里保持一致）。"""
    from app.core.data_scope_gate import is_external_role
    if is_external_role(identity.get("permission_role")):
        raise HTTPException(403, "外部账号不能使用钉钉收文")


@router.post(f"{settings.api_prefix}/documents/court-service/bot-receipts/intake", status_code=201)  # 与 INTAKE_PATH 相同；门禁脚本只认字面路径
async def bot_intake(body: CourtIntakeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """钉钉收文助手专用入口：权限和一键收文相同，不向智能体开放；已有开庭不覆盖，回填失败只写进结果。"""
    from app.areas.aws.court_intake import run_intake
    _require_internal(identity)
    return await run_intake(body, identity, db, direct_save=True)


def _row(record: BusinessRecord) -> dict:
    data = record.data or {}
    return {"id": record.id, "status": record.status, "sent_at": data.get("sent_at") or "", "sender": data.get("sender_nick") or "",
            "text": _LINK.sub("[送达链接]", data.get("text") or ""), "kind": data.get("kind") or "", "reason": data.get("reason") or "",
            "documents": [{"name": item.get("name") or "", "kind": item.get("kind") or ""} for item in data.get("documents") or []],
            "candidates": [item.get("serial_no") or "" for item in data.get("candidates") or []]}


async def _pending_record(record_id: int, db: AsyncSession) -> BusinessRecord:
    record = await db.get(BusinessRecord, record_id)
    if record is None or record.module != MODULE:
        raise HTTPException(404, "收文记录不存在")
    if record.status != PENDING:
        raise HTTPException(409, f"这条收文状态为“{record.status}”，不用再处理")
    return record


@router.get(f"{settings.api_prefix}/documents/court-service/bot-receipts")
async def list_bot_receipts(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.areas.aws.receipt_sources import _require_receipt_menu
    _require_internal(identity)
    await _require_receipt_menu("official", identity, db)
    rows = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == MODULE, BusinessRecord.status == PENDING)
                             .order_by(BusinessRecord.id.desc()).limit(300))).all()
    return {"items": [_row(row) for row in rows]}


@router.post(f"{settings.api_prefix}/documents/court-service/bot-receipts/{{record_id}}/assign")
async def assign_bot_receipt(record_id: int, body: AssignInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """指定案件入库：按处理人自己的案件权限，与一键收文确认入库相同。没有送达链接的短信不能在这里入库。"""
    from app.areas.aws.court_intake import intake_court_service
    from app.areas.aws.receipt_sources import _require_receipt_menu
    _require_internal(identity)
    await _require_receipt_menu("official", identity, db)
    record = await _pending_record(record_id, db)
    link = (record.data or {}).get("link")
    if not link:
        raise HTTPException(409, "这条短信没有送达链接，请手工上传后标记不入库")
    case = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == body.case_no.strip()))
    if case is None:
        raise HTTPException(422, f"未找到系统案号 {body.case_no.strip()}")
    # 人工在收文台指定案件，走网页收文的路径：已有开庭会按文书覆盖。写入清单照记。
    report = await intake_court_service(CourtIntakeInput(link=link, case_id=case.id, confirm=True), identity, db)
    record = await db.get(BusinessRecord, record_id)
    await _set_status(record, DONE, {"case_id": case.id, "case_no": case.serial_no, "handled_by": identity["username"],
                                     "changes": _changes(report, str((record.data or {}).get("planned_court_no") or ""))}, identity["username"], db)
    return _row(record)


@router.post(f"{settings.api_prefix}/documents/court-service/bot-receipts/{{record_id}}/close")
async def close_bot_receipt(record_id: int, body: CloseInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """不入库：标记已处理（例如不是本所案件、已手工上传），记录保留。"""
    from app.areas.aws.receipt_sources import _require_receipt_menu
    _require_internal(identity)
    await _require_receipt_menu("official", identity, db)
    record = await _pending_record(record_id, db)
    await _set_status(record, CLOSED, {"reason": body.reason.strip(), "handled_by": identity["username"]}, identity["username"], db)
    return _row(record)
