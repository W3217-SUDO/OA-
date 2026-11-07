"""钉钉收文助手（陶国南 11-07）：律师在沪知收文群转发法院短信并 @收文助手，按发送人本人的账号收文，并在群里告知律师和律师助理。

这里只放与钉钉连接无关的部分：认人、调收文接口、记录、拼回复。下载、匹配、入库全部走现有“一键收文”接口，
用发送人本人的短期令牌调用，权限和留痕与网页一致，机器人没有自己的放宽路径。
群里只写案件要素，不写收款账号、法官电话和文书正文。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import re
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_skill_packages.court_doc_intake.scripts import fetch_court_docs as court_api
from app.config import settings
from app.core.dependencies import current_identity, get_db
from app.models import BusinessRecord, User, WorkflowEvent

logger = logging.getLogger(__name__)
router = APIRouter()

MODULE = "court_group_receipt"
WAITING, PENDING, DONE, CLOSED, CANCELLED = "待确认", "待处理", "已导入", "不入库", "已取消"
CONFIRM_MINUTES = 30
SKILL_ID = "court-doc-intake"
RECEIPT_PAGE = "/?page=documents-official"
ASSISTANT_NAME_FIELDS = ("assistants", "assistant", "case_assistant")
ASSISTANT_ACCOUNT_FIELDS = ("assistant_usernames", "assistant_username")
_LINK = re.compile(r"https?://[^\s，,。；;]+")
_COURT = re.compile(r"人民法院|法院|仲裁委员会|人民检察院")
_FIRST_LEVEL = "第一级"

Api = Callable[[str, str, dict], Awaitable[dict]]
AgentTurn = Callable[[str, str], Awaitable[None]]


@dataclass
class BotMessage:
    message_id: str
    conversation_type: str  # "1" 单聊，"2" 群聊
    conversation_title: str
    text: str
    sender_id: str
    sender_nick: str = ""


@dataclass
class BotSettings:
    group_name: str
    use_cloud_agent: bool
    auto_save_court_no: bool


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


def _done_lines(report: dict) -> list[str]:
    received = report.get("received") or []
    saved = sum(1 for item in received if not item.get("skipped"))
    skipped = len(received) - saved
    actions = []
    if saved:
        actions.append(f"已存入案件文档和收文台 {saved} 份")
    if skipped:
        actions.append(f"{skipped} 份此前已收过，未重复存")
    hearing = report.get("hearing") or {}
    if isinstance(hearing, dict) and hearing.get("status") == "已回填":
        actions.append("已回填开庭")
    elif isinstance(hearing, dict) and hearing.get("status") in {"冲突未回填", "审级不明未回填", "缺法院名称未回填"}:
        actions.append(f"开庭{hearing['status']}，请核对")
    if any(item.get("status") == "待确认" for item in report.get("fees") or []):
        actions.append("已生成费用草稿，请到系统确认提交")
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


async def _waiting_record(user: User, db: AsyncSession) -> BusinessRecord | None:
    return await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == MODULE, BusinessRecord.status == WAITING, BusinessRecord.owner == user.username,
    ).order_by(BusinessRecord.id.desc()).limit(1))


async def _save(record: BusinessRecord, case_id: int, user: User, message: BotMessage, api: Api, db: AsyncSession) -> Reply:
    link = (record.data or {}).get("link") or ""
    try:
        report = await api(user.username, "/documents/court-service/intake", {"link": link, "case_id": case_id, "confirm": True})
    except ApiError as exc:
        await _set_status(record, PENDING, {"reason": exc.detail}, user.username, db)
        return Reply(f"{_mention([message.sender_id])} 收文未完成：{exc.detail}。已转到收文台待处理。\n{_link_line()}", [message.sender_id])
    case = await db.get(BusinessRecord, case_id)
    await _set_status(record, DONE, {"case_id": case_id, "case_no": (report.get("case") or {}).get("serial_no") or ""}, user.username, db)
    ids, plain = await case_assistants(case, db)
    at_ids = list(dict.fromkeys([message.sender_id, *ids]))
    if ids or plain:
        assistant_line = f"律师助理：{_mention(ids)}{' ' if ids and plain else ''}{'、'.join(plain)}"
    else:
        assistant_line = "本案未填律师助理"
    return Reply("\n".join([f"{_mention([message.sender_id])} 收文完成", *_facts(report), *_done_lines(report), assistant_line, _link_line()]), at_ids)


async def _handle_command(text: str, user: User, message: BotMessage, api: Api, db: AsyncSession) -> Reply | None:
    """律师回“确认”“取消”或候选序号。不是这些内容时返回 None。"""
    number = int(text) if text.isdigit() and len(text) <= 2 else None
    if text not in {"确认", "取消"} and number is None:
        return None
    me = _mention([message.sender_id])
    record = await _waiting_record(user, db)
    if record is None:
        return Reply(f"{me} 没有等你确认的收文。", [message.sender_id])
    data = record.data or {}
    expires = datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
    if expires is not None and expires < datetime.now(timezone.utc):
        await _set_status(record, PENDING, {"reason": "超时未确认"}, user.username, db)
        return Reply(f"{me} 这条收文已超过 {CONFIRM_MINUTES} 分钟未确认，已转到收文台待处理。\n{_link_line()}", [message.sender_id])
    if text == "取消":
        await _set_status(record, CANCELLED, {"reason": "律师取消"}, user.username, db)
        return Reply(f"{me} 已取消，这条收文没有存入。", [message.sender_id])
    candidates = data.get("candidates") or []
    if candidates:
        if number is None or not 1 <= number <= len(candidates):
            return Reply(f"{me} 请回复候选序号（1～{len(candidates)}），或回复“取消”。", [message.sender_id])
        return await _save(record, int(candidates[number - 1]["case_id"]), user, message, api, db)
    if text != "确认" or not data.get("case_id"):
        return Reply(f"{me} 请回复“确认”或“取消”。", [message.sender_id])
    return await _save(record, int(data["case_id"]), user, message, api, db)


async def _preview(message: BotMessage, link: str, user: User, config: BotSettings, api: Api, agent_turn: AgentTurn | None, db: AsyncSession) -> Reply | None:
    me = _mention([message.sender_id])
    record = await _record(message, user, PENDING, {"kind": "zxfw", "link": link}, db)
    if record is None:
        return None
    if config.use_cloud_agent and agent_turn is not None:
        # 云端智能体按收文技能读短信并预览；它只能生成待确认请求，不能写入。结果以下面 OA 接口返回为准，云端失败不影响收文。
        try:
            await agent_turn(user.username, message.text[:2000])
        except Exception as exc:
            logger.warning("receipt bot cloud agent failed record=%s type=%s", record.id, type(exc).__name__)
    try:
        report = await api(user.username, "/documents/court-service/intake", {"link": link})
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
        await _set_status(record, WAITING, {**record_data, "candidates": candidates, "expires_at": expires}, user.username, db)
        lines = [f"{index}. {item['serial_no']} {item['title']}" for index, item in enumerate(candidates, start=1)]
        return Reply("\n".join([f"{me} 匹配到多个案件，请回复序号选择，或回复“取消”：", *lines, f"文书类型：{_documents_text(report)}"]), [message.sender_id])
    if status != "待确认入库":
        await _set_status(record, PENDING, {**record_data, "reason": str(status)}, user.username, db)
        return Reply(f"{me} 这条短信没有自动收文，已转到收文台待处理。\n{_link_line()}", [message.sender_id])
    case_id = int(report["case"]["case_id"])
    level = str((report.get("match") or {}).get("level") or "")
    if config.auto_save_court_no and level.startswith(_FIRST_LEVEL):
        await _set_status(record, WAITING, {**record_data, "case_id": case_id}, user.username, db)
        return await _save(record, case_id, user, message, api, db)
    await _set_status(record, WAITING, {**record_data, "case_id": case_id, "expires_at": expires}, user.username, db)
    basis = (report.get("match") or {}).get("basis") or ""
    return Reply("\n".join([f"{me} 找到案件，请核对后回复“确认”存入，或回复“取消”：", *_facts(report),
                            *([f"匹配依据：{basis}"] if basis else [])]), [message.sender_id])


async def handle_message(message: BotMessage, config: BotSettings, *, api: Api, db: AsyncSession, agent_turn: AgentTurn | None = None) -> Reply | None:
    """处理一条 @收文助手 的消息，返回要回复的内容；None 表示不回复。"""
    from app.core.data_scope_gate import is_external_role
    me = _mention([message.sender_id]) if message.sender_id else ""
    if message.conversation_type != "2":
        return Reply("收文助手只在收文群使用，请在群里转发法院短信并 @收文助手。", [])
    if message.conversation_title != config.group_name:
        logger.info("receipt bot ignored group message from another group")
        return None
    user = await find_sender(message.sender_id, db)
    if user is None:
        return Reply(f"{me} 你的系统账号还没绑定钉钉，暂时不能用收文助手。请在钉钉里打开一次系统完成绑定后重发。", [message.sender_id])
    if is_external_role((user.profile or {}).get("permission_role")):
        return Reply(f"{me} 外部账号不能使用收文助手，请联系对接人。", [message.sender_id])
    if user.must_change_password:
        return Reply(f"{me} 请先登录系统修改初始密码，再重发。", [message.sender_id])
    text = (message.text or "").strip()
    command = await _handle_command(text, user, message, api, db)
    if command is not None:
        return command
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


def _row(record: BusinessRecord) -> dict:
    data = record.data or {}
    return {"id": record.id, "status": record.status, "sent_at": data.get("sent_at") or "", "sender": data.get("sender_nick") or "",
            "text": data.get("text") or "", "kind": data.get("kind") or "", "reason": data.get("reason") or "",
            "documents": [{"name": item.get("name") or "", "kind": item.get("kind") or ""} for item in data.get("documents") or []],
            "candidates": [item.get("serial_no") or "" for item in data.get("candidates") or []]}


async def _pending_record(record_id: int, db: AsyncSession) -> BusinessRecord:
    record = await db.get(BusinessRecord, record_id)
    if record is None or record.module != MODULE:
        raise HTTPException(404, "收文记录不存在")
    if record.status != PENDING:
        raise HTTPException(409, f"这条收文已{record.status}，不用再处理")
    return record


@router.get(f"{settings.api_prefix}/documents/court-service/bot-receipts")
async def list_bot_receipts(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.areas.aws.receipt_sources import _require_receipt_menu
    await _require_receipt_menu("official", identity, db)
    rows = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == MODULE, BusinessRecord.status == PENDING)
                             .order_by(BusinessRecord.id.desc()).limit(300))).all()
    return {"items": [_row(row) for row in rows]}


@router.post(f"{settings.api_prefix}/documents/court-service/bot-receipts/{{record_id}}/assign")
async def assign_bot_receipt(record_id: int, body: AssignInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """指定案件入库：按处理人自己的案件权限，与一键收文确认入库相同。没有送达链接的短信不能在这里入库。"""
    from app.areas.aws.court_intake import CourtIntakeInput, intake_court_service
    from app.areas.aws.receipt_sources import _require_receipt_menu
    await _require_receipt_menu("official", identity, db)
    record = await _pending_record(record_id, db)
    link = (record.data or {}).get("link")
    if not link:
        raise HTTPException(409, "这条短信没有送达链接，请手工上传后标记不入库")
    case = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == body.case_no.strip()))
    if case is None:
        raise HTTPException(422, f"未找到系统案号 {body.case_no.strip()}")
    await intake_court_service(CourtIntakeInput(link=link, case_id=case.id, confirm=True), identity, db)
    record = await db.get(BusinessRecord, record_id)
    await _set_status(record, DONE, {"case_id": case.id, "case_no": case.serial_no, "handled_by": identity["username"]}, identity["username"], db)
    return _row(record)


@router.post(f"{settings.api_prefix}/documents/court-service/bot-receipts/{{record_id}}/close")
async def close_bot_receipt(record_id: int, body: CloseInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """不入库：标记已处理（例如不是本所案件、已手工上传），记录保留。"""
    from app.areas.aws.receipt_sources import _require_receipt_menu
    await _require_receipt_menu("official", identity, db)
    record = await _pending_record(record_id, db)
    await _set_status(record, CLOSED, {"reason": body.reason.strip(), "handled_by": identity["username"]}, identity["username"], db)
    return _row(record)
