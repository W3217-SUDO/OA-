"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
import calendar
import math

from app.core.constants import (
    CASE_EVENT_COMPLETED_STATUS, logger,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, CaseEvent, ContractApprovalStep, Department, DingTalkError,
    HTTPException, HearingSchedule, IncomingPayment, IprCaseWarning, Notification, SessionLocal,
    LegacyInvestigationClue, LegacyInvestigationClueEvidence,
    SystemParameter, User, VipTask, VipTaskMessage, VipTaskNode, WorkflowEvent,
    asyncio, date, datetime, delete, dingtalk_client,
    func, httpx, or_, secrets, select,
    settings, timedelta,
)


def _task_creation_mode(data: dict) -> str:
    """Return the user-facing creation mode without conflating it with task origin."""
    explicit_mode = str(data.get("creation_mode") or "").strip()
    if explicit_mode in {"自动", "人工"}:
        return explicit_mode
    task_type = str(data.get("task_type") or "").strip()
    source = str(data.get("source") or "").strip()
    if task_type in {"固定任务", "自动任务"} or data.get("auto_task_type") or source in {"自动", "自动任务"}:
        return "自动"
    return "人工"


def _add_calendar_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


def _case_person_references(data: dict, *keys: str) -> list[str]:
    references: list[str] = []
    for key in keys:
        value = data.get(key)
        values = value if isinstance(value, list) else [value]
        for item in values:
            reference = str(item or "").strip()
            if reference and reference not in references:
                references.append(reference)
    return references


async def _active_case_task_user(data: dict, db: AsyncSession, *, username_keys: tuple[str, ...], display_keys: tuple[str, ...], field_name: str) -> User:
    references = _case_person_references(data, *username_keys, *display_keys)
    for reference in references:
        user = await db.scalar(select(User).where(User.username == reference, User.is_active.is_(True)))
        if user:
            return user
        matches = list((await db.scalars(select(User).where(
            User.display_name == reference, User.is_active.is_(True),
        ))).all())
        if len(matches) == 1:
            return matches[0]
    raise HTTPException(status_code=422, detail=f"案件未设置有效{field_name}，无法生成执行申请提醒任务")


async def _ensure_execution_application_reminder_task(
    case_record: BusinessRecord,
    db: AsyncSession,
    *,
    previous_status: str,
    operator: str,
    today: date | None = None,
) -> BusinessRecord | None:
    """Create the legacy execution reminder once when a case enters first-instance pending execution."""
    if case_record.status != "一审待执行" or previous_status == "一审待执行":
        return None
    existing = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "task",
        BusinessRecord.data["case_id"].as_integer() == case_record.id,
        BusinessRecord.data["auto_task_type"].as_string() == "execution_application_reminder",
    ))
    if existing:
        return existing
    data = case_record.data or {}
    lawyer = await _active_case_task_user(
        data, db,
        username_keys=("handling_lawyer_usernames",),
        display_keys=("handling_lawyers",),
        field_name="经办律师",
    )
    assistant = await _active_case_task_user(
        data, db,
        username_keys=("assistant_usernames", "assistant_username"),
        display_keys=("assistants", "assistant"),
        field_name="律师助理",
    )
    effective_today = today or date.today()
    description = f"本案{case_record.serial_no}判决书或调解书已生效,请尽快提交申请执行材料,并上传"
    task = BusinessRecord(
        module="task",
        serial_no=await _next_manual_task_serial(db),
        title="执行申请-提醒任务",
        customer=case_record.customer,
        status="待接收",
        owner=assistant.username,
        department=assistant.department,
        description=description,
        data={
            "deadline": str(_add_calendar_months(effective_today, 2)),
            "priority": "普通",
            "source": "案件任务",
            "creation_mode": "自动",
            "task_type": "自动任务",
            "auto_task_type": "execution_application_reminder",
            "initiator": lawyer.username,
            "collaborators": [],
            "case_no": case_record.serial_no,
            "case_nos": [case_record.serial_no],
            "case_id": case_record.id,
            "case_record_id": case_record.id,
            "case_ids": [case_record.id],
            "case_module": "case",
            "case_stage": case_record.status,
            "system_created_by": operator,
        },
    )
    db.add(task)
    await db.flush()
    message = (
        f"{lawyer.display_name}新建任务给负责人({assistant.display_name})，"
        f"协作人(无)，附言：{description}"
    )
    await _add_task_message_notifications(
        task,
        WorkflowEvent(
            record_id=task.id,
            action="系统生成执行申请提醒任务",
            to_status="待接收",
            operator=lawyer.username,
            comment=message,
        ),
        db,
        content=message,
    )
    case_record.data = {
        **data,
        "execution_application_reminder_task_id": task.id,
    }
    return task


async def _task_has_vip_customer(task: BusinessRecord, db: AsyncSession) -> bool:
    from app.core.crm import (
        _case_customer_has_vip_marker,
    )
    data = task.data or {}
    candidate_ids = [data.get("case_record_id"), data.get("case_id")]
    candidate_nos = [data.get("case_no")]
    candidate_ids.extend(data.get("case_ids") if isinstance(data.get("case_ids"), list) else [])
    candidate_nos.extend(data.get("case_nos") if isinstance(data.get("case_nos"), list) else [])
    seen_ids: set[int] = set()
    for raw_id in candidate_ids:
        try:
            case_id = int(raw_id or 0)
        except (TypeError, ValueError):
            case_id = 0
        if case_id <= 0 or case_id in seen_ids:
            continue
        seen_ids.add(case_id)
        case_record = await db.get(BusinessRecord, case_id)
        if case_record and case_record.module in {"case", "ipr_case"} and await _case_customer_has_vip_marker(case_record, db):
            return True
    for raw_no in candidate_nos:
        case_no = str(raw_no or "").strip()
        if not case_no:
            continue
        case_record = await db.scalar(select(BusinessRecord).where(
            BusinessRecord.module.in_({"case", "ipr_case"}), BusinessRecord.serial_no == case_no,
        ))
        if case_record and await _case_customer_has_vip_marker(case_record, db):
            return True
    return False


def _task_dict(record: BusinessRecord) -> dict:
    from app.core.system import (
        _explicit_vip_value, _record_dict,
    )
    data = record.data or {}
    raw_case_nos = data.get("case_nos") if isinstance(data.get("case_nos"), list) else []
    case_nos = [str(value).strip() for value in raw_case_nos if str(value).strip()]
    primary_case_no = str(data.get("case_no") or "").strip()
    if primary_case_no and primary_case_no not in case_nos:
        case_nos.insert(0, primary_case_no)
    raw_case_ids = data.get("case_ids") if isinstance(data.get("case_ids"), list) else []
    case_ids = []
    for value in raw_case_ids:
        try:
            normalized_id = int(value)
        except (TypeError, ValueError):
            continue
        if normalized_id > 0 and normalized_id not in case_ids:
            case_ids.append(normalized_id)
    try:
        # Imported legacy tasks used TaskEndTime/task_end_time; new writes use
        # deadline. Keep one response field while preserving both sources.
        raw_deadline = data.get("deadline") or data.get("task_end_time") or data.get("TaskEndTime") or ""
        deadline = date.fromisoformat(str(raw_deadline))
        days_remaining = (deadline - date.today()).days
    except ValueError:
        deadline = None
        days_remaining = None
    workflow_status = record.status
    # 兼容早期本地数据：旧“待确认”等同于原系统“进行中-已完成”。
    effective_status = "已完成" if record.status == "待确认" else record.status
    if record.status == "处理中" and str(data.get("source") or "").strip() == "案件任务":
        effective_status = "进行中"
    if days_remaining is not None and days_remaining < 0 and record.status in {"待接收", "待处理", "处理中"}:
        effective_status = "已逾期"
    reminder_due = days_remaining in {1, 3} or (days_remaining is not None and days_remaining < 0 and abs(days_remaining) % 3 == 0)
    reminder_text = ""
    if days_remaining in {1, 3}:
        reminder_text = f"{days_remaining} 天后到期"
    elif days_remaining is not None and days_remaining < 0:
        reminder_text = f"已逾期 {abs(days_remaining)} 天" + ("，今日提醒" if reminder_due else "")
    elif days_remaining == 0:
        reminder_text = "今日到期"
    return {
        **_record_dict(record), "status": effective_status, "workflow_status": workflow_status,
        "deadline": deadline, "days_remaining": days_remaining,
        "is_vip": _explicit_vip_value(data.get("is_vip")),
        "priority": data.get("priority", "普通"), "source": data.get("source", "日常任务"),
        "creation_mode": _task_creation_mode(data), "task_type": data.get("task_type", ""),
        "initiator": data.get("initiator", ""), "collaborators": data.get("collaborators", []),
        "case_no": primary_case_no, "case_nos": case_nos, "case_ids": case_ids,
        "case_record_id": data.get("case_record_id") or data.get("case_id"),
        "case_module": data.get("case_module", "case" if primary_case_no else ""),
        "start_at": data.get("start_at") or data.get("task_begin_time") or data.get("TaskBeginTime") or "",
        "end_at": data.get("end_at") or data.get("task_end_time") or data.get("TaskEndTime") or "",
        "rejected_reason": data.get("rejected_reason", ""),
        "plaintiff": data.get("plaintiff", ""), "defendant": data.get("defendant", ""),
        "case_stage": data.get("case_stage", ""),
        "accepted_at": data.get("accepted_at", ""),
        "verified_at": data.get("confirmed_at") or data.get("auto_confirmed_at", ""),
        "completion_auto_confirm_at": data.get("completion_auto_confirm_at", ""),
        "reminder_due": reminder_due, "reminder_text": reminder_text,
        "handoff_recipient": data.get("handoff_recipient", ""),
        "handoff_auto_complete_at": data.get("handoff_auto_complete_at", ""),
        "handoff_restarted": bool(data.get("handoff_restarted")),
        "auto_completed": bool(data.get("auto_completed")),
        "performance_impact": data.get("performance_impact", {}),
        "exception_request": data.get("exception_request", {}),
        "parent_task_id": data.get("parent_task_id"),
        "parent_task_no": data.get("parent_task_no", ""),
        "investigation_record_id": data.get("investigation_record_id"),
        "investigation_no": data.get("investigation_no", ""),
        "investigation_module": data.get("investigation_module", ""),
        "contract_no": data.get("contract_no", ""),
        "contract_name": data.get("contract_name", ""),
        "authorization_scope": data.get("authorization_scope", ""),
        "attachment_ids": data.get("attachment_ids", []),
    }


async def _add_task_message_notifications(
    task: BusinessRecord,
    event: WorkflowEvent,
    db: AsyncSession,
    *,
    content: str,
) -> None:
    """Persist one idempotent unread lifecycle/communication message per participant."""
    db.add(event)
    await db.flush()
    data = task.data or {}
    recipients = {
        task.owner,
        str(data.get("initiator") or ""),
        *(str(value) for value in data.get("collaborators", []) if value),
    } - {""}
    if event.operator != "system":
        recipients.discard(event.operator)
    active_recipients = set((await db.scalars(select(User.username).where(
        User.username.in_(recipients), User.is_active.is_(True),
    ))).all()) if recipients else set()
    existing_keys = set((await db.scalars(select(Notification.source_key).where(
        Notification.source_key.in_([
            f"task-message-{task.id}-{event.id}-{recipient}" for recipient in active_recipients
        ])
    ))).all()) if active_recipients else set()
    for recipient in active_recipients:
        source_key = f"task-message-{task.id}-{event.id}-{recipient}"
        if source_key in existing_keys:
            continue
        db.add(Notification(
            source_key=source_key, source_type="task", source_id=task.id,
            sender=event.operator or "system", recipient=recipient,
            notification_type="系统通知", title=f"任务新消息：{task.serial_no}",
            content=content.strip() or event.action, level="info", is_read=False,
        ))


async def _delete_task_notifications(task_id: int, db: AsyncSession) -> None:
    """Delete every notification owned by a task before deleting that task record."""
    await db.execute(delete(Notification).where(
        Notification.source_type == "task", Notification.source_id == task_id,
    ))


def _notification_dict(item: Notification, users_by_username: dict[str, User] | None = None) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    users = users_by_username or {}
    return {
        "id": item.id, "source_type": item.source_type, "source_id": item.source_id,
        "sender": item.sender, "sender_display_name": _person_reference_display(item.sender, users)[0],
        "recipient": item.recipient, "recipient_display_name": _person_reference_display(item.recipient, users)[0],
        "notification_type": item.notification_type, "title": item.title, "content": item.content,
        "level": item.level, "is_read": item.is_read, "read_at": item.read_at,
        "dingtalk_status": item.dingtalk_status, "dingtalk_sent_at": item.dingtalk_sent_at, "created_at": item.created_at,
    }


async def _dispatch_dingtalk_notifications() -> None:
    if not settings.dingtalk_notifications_enabled or not dingtalk_client.configured:
        return
    async with SessionLocal() as db:
        notices = (await db.scalars(
            select(Notification).where(
                Notification.is_read.is_(False),
                Notification.recipient_deleted.is_(False),
                Notification.dingtalk_status.in_(("pending", "failed")),
                Notification.dingtalk_attempts < 5,
            ).order_by(Notification.id).limit(50)
        )).all()
        if not notices:
            return
        usernames = {notice.recipient for notice in notices}
        users = (await db.scalars(select(User).where(User.username.in_(usernames), User.is_active.is_(True)))).all()
        users_by_username = {user.username: user for user in users}
        for notice in notices:
            user = users_by_username.get(notice.recipient)
            ding_user_id = str(((user.profile if user else {}) or {}).get("dingtalk_user_id") or "").strip()
            if not ding_user_id:
                continue
            try:
                await dingtalk_client.send_work_notification(ding_user_id, notice.title, notice.content)
                notice.dingtalk_status = "sent"
                notice.dingtalk_sent_at = datetime.now()
                notice.dingtalk_error = ""
            except (DingTalkError, httpx.HTTPError, ValueError) as exc:
                notice.dingtalk_status = "failed"
                notice.dingtalk_attempts = int(notice.dingtalk_attempts or 0) + 1
                notice.dingtalk_error = str(exc)[:500]
                logger.warning("DingTalk notification %s failed: %s", notice.id, exc)
        await db.commit()


async def _dingtalk_notification_loop() -> None:
    while True:
        try:
            await _dispatch_dingtalk_notifications()
        except Exception:
            logger.exception("DingTalk notification loop failed")
        await asyncio.sleep(10)


async def _sync_notifications(identity: dict, db: AsyncSession) -> None:
    from app.core.ipr import (
        _materialize_ipr_case_warnings,
    )
    from app.core.permissions import (
        _record_scope_conditions, _visible_record_ids,
    )
    username = identity["username"]; today = date.today(); candidates: list[dict] = []
    # Warning materialization belongs to the notification lifecycle so a case
    # owner receives an inbox item without first opening the IPR warning page.
    can_view_ipr = True
    try:
        await _materialize_ipr_case_warnings(identity, db)
    except HTTPException as exc:
        if exc.status_code != 403:
            raise
        can_view_ipr = False
    task_terminal_statuses = ["已完成", "待确认", "已验收", "已拒绝", "已撤回", "已停止", "已取消"]
    all_tasks = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all())
    tasks = [task for task in all_tasks if task.status not in task_terminal_statuses]
    terminal_task_ids = {task.id for task in all_tasks if task.status in task_terminal_statuses}
    current_user = await db.scalar(select(User).where(User.username == username))
    stale = (await db.scalars(select(Notification).where(Notification.recipient == username, Notification.source_type.in_(["task", "finance", "contract", "case", "ipr_warning"])))).all()
    existing_record_ids = set((await db.scalars(select(BusinessRecord.id))).all())
    if identity.get("role") != "admin":
        visible_tasks = [task for task in all_tasks if _is_task_participant(task, identity) or (identity.get("role") == "manager" and current_user and task.department == current_user.department)]
        tasks = [task for task in tasks if _is_task_participant(task, identity) or (identity.get("role") == "manager" and current_user and task.department == current_user.department)]
        visible_ids = await _visible_record_ids(identity, db)
        visible_task_ids = {task.id for task in visible_tasks}
    else:
        visible_ids = existing_record_ids
        visible_task_ids = {task.id for task in all_tasks}
    for notice in stale:
        if notice.source_type == "ipr_warning":
            if not can_view_ipr:
                await db.delete(notice)
                continue
            warning = await db.scalar(select(IprCaseWarning.id).where(IprCaseWarning.notification_id == notice.id, IprCaseWarning.recipient == username))
            if not warning:
                await db.delete(notice)
                continue
        is_auto_reminder = (
            (notice.source_type == "task" and notice.source_key.startswith("task-") and not notice.source_key.startswith(("task-history-", "task-message-")))
            or notice.source_key.startswith(("finance-approval-", "contract-approval-", "hearing-"))
        )
        # 旧版本的自动提醒键是全局唯一键，同一业务只能被第一个访问提醒页的
        # 用户取得。迁移为收件人维度，确保管理员与每个参与人都有独立提醒。
        if is_auto_reminder and not notice.source_key.endswith(f"-{username}"):
            recipient_key = f"{notice.source_key}-{username}"
            duplicate = await db.scalar(select(Notification).where(Notification.source_key == recipient_key))
            if duplicate:
                await db.delete(notice)
                continue
            notice.source_key = recipient_key
        allowed_ids = visible_task_ids if notice.source_type == "task" else visible_ids
        is_terminal_task_reminder = (
            notice.source_type == "task" and notice.source_id in terminal_task_ids
            and notice.source_key.startswith("task-")
            and not notice.source_key.startswith(("task-history-", "task-message-"))
        )
        if notice.source_id not in existing_record_ids or notice.source_id not in allowed_ids or is_terminal_task_reminder:
            await db.delete(notice)
    for task in tasks:
        info = _task_dict(task)
        if info["reminder_due"]:
            candidates.append({"source_key": f"task-{task.id}-{today}-{username}", "source_type": "task", "source_id": task.id, "title": info["reminder_text"], "content": f"{task.serial_no}｜{task.title}｜负责人：{task.owner}", "level": "error" if info["status"] == "已逾期" else "warning"})
    fees = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance", BusinessRecord.status == "待审批", *(await _record_scope_conditions(identity, db))))).all()
    for fee in fees:
        candidates.append({"source_key": f"finance-approval-{fee.id}-{username}", "source_type": "finance", "source_id": fee.id, "title": "费用待审批", "content": f"{fee.serial_no}｜{fee.title}｜{(fee.data or {}).get('amount', 0)} 元", "level": "warning"})
    current_steps = (await db.execute(select(ContractApprovalStep, BusinessRecord).join(BusinessRecord, BusinessRecord.id == ContractApprovalStep.contract_record_id).where(ContractApprovalStep.status == "待审批", BusinessRecord.status == "审批中"))).all()
    for step, contract in current_steps:
        if identity.get("role") == "admin" or step.approver == username:
            candidates.append({"source_key": f"contract-approval-{contract.id}-{step.id}-{username}", "source_type": "contract", "source_id": contract.id, "title": f"合同第 {step.step_order} 级待审批", "content": f"{contract.serial_no}｜{contract.title}｜审批人：{step.approver}", "level": "warning"})
    hearings = (await db.execute(select(HearingSchedule, BusinessRecord).join(BusinessRecord, BusinessRecord.id == HearingSchedule.case_record_id).where(HearingSchedule.hearing_date == today + timedelta(days=1), HearingSchedule.status == "已排期", *(await _record_scope_conditions(identity, db))))).all()
    for hearing, case_record in hearings:
        candidates.append({"source_key": f"hearing-{hearing.id}-{hearing.hearing_date}-{username}", "source_type": "case", "source_id": case_record.id, "title": "明日开庭提醒", "content": f"{case_record.serial_no}｜{hearing.hearing_time}｜{hearing.court}｜{hearing.hearing_lawyer}", "level": "info"})
    existing_keys = set((await db.scalars(select(Notification.source_key).where(Notification.source_key.in_([x["source_key"] for x in candidates])))).all()) if candidates else set()
    for item in candidates:
        if item["source_key"] not in existing_keys: db.add(Notification(**item, recipient=username))
    await db.commit()


async def _apply_task_auto_completion(db: AsyncSession) -> bool:
    """交接后未重新开始的任务，满 5 天自动完成。"""
    tasks = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all()
    changed = False
    for task in tasks:
        data = task.data or {}
        owner_user = await db.scalar(select(User).where(User.username == task.owner))
        if owner_user and not owner_user.is_active and task.status not in {"已完成", "待确认", "已验收", "已拒绝", "已撤回", "已停止", "已取消"}:
            department = await db.scalar(select(Department).where(
                Department.name == owner_user.department, Department.is_active.is_(True),
            ))
            manager = await db.scalar(select(User).where(
                User.username == department.manager, User.is_active.is_(True),
            )) if department and department.manager else None
            if manager:
                previous_owner = task.owner
                task.owner = manager.username
                task.department = manager.department
                task.data = {
                    **data, "deadline": str(date.today() + timedelta(days=7)),
                    "departing_owner": previous_owner, "departing_transfer_at": str(date.today()),
                }
                await _add_task_message_notifications(
                    task,
                    WorkflowEvent(record_id=task.id, action="员工离职任务自动交接部门负责人", from_status=task.status, to_status=task.status, operator="system", comment=f"{previous_owner} -> {manager.username}"),
                    db,
                    content="员工离职，任务自动交接部门负责人.",
                )
                data = task.data or {}
                changed = True
        confirm_at = data.get("completion_auto_confirm_at")
        if task.status in {"待确认", "已完成"} and confirm_at:
            try:
                should_confirm = date.fromisoformat(str(confirm_at)) <= date.today()
            except ValueError:
                should_confirm = False
            if should_confirm:
                previous = task.status
                task.status = "已验收"
                task.data = {**data, "auto_confirmed": True, "auto_confirmed_at": str(date.today())}
                await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="任务完成自动验收", from_status=previous, to_status="已验收", operator="system", comment="负责人提交完成后满 5 日，发起人未重启，系统自动验收"), db, content="任务已确认完成.")
                await _advance_case_from_fixed_task(task, db, operator="system")
                changed = True
                continue
        auto_task_type = str(data.get("auto_task_type") or "")
        if task.status in {"已完成", "待确认", "已验收"} and (auto_task_type.startswith("take_evidence") or auto_task_type.startswith("evidence_destroy")):
            raw_ids = data.get("warehouse_evidence_ids") or [data.get("warehouse_evidence_id")]
            for raw_id in raw_ids if isinstance(raw_ids, list) else [raw_ids]:
                try:
                    evidence = await db.get(BusinessRecord, int(raw_id or 0))
                except (TypeError, ValueError):
                    evidence = None
                if not evidence or evidence.module != "warehouse":
                    continue
                target = "已出库" if auto_task_type.startswith("take_evidence") else "已销毁"
                evidence.data = {**(evidence.data or {}), "evidence_status": target, "automatic_task_id": task.id}
                changed = True
        auto_at = data.get("handoff_auto_complete_at")
        if not auto_at or data.get("handoff_restarted") or task.status != "待接收":
            continue
        try:
            should_complete = date.fromisoformat(str(auto_at)) <= date.today()
        except ValueError:
            should_complete = False
        if should_complete:
            previous = task.status
            task.status = "已完成"
            task.data = {**data, "auto_completed": True, "auto_completed_at": str(date.today())}
            await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="交接任务自动完成", from_status=previous, to_status="已完成", operator="system", comment="交接满 5 天且未重新开始，系统自动完成"), db, content="任务已自动完成.")
            changed = True
    if changed:
        await db.commit()
    return changed


async def _apply_task_overdue_performance(db: AsyncSession) -> bool:
    """Persist overdue facts so performance reports do not depend on a page being open."""
    tasks = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all())
    changed = False
    terminal = {"已完成", "待确认", "已验收", "已拒绝", "已撤回", "已停止", "已取消"}
    for task in tasks:
        if task.status in terminal:
            continue
        data = task.data or {}
        try:
            overdue_days = (date.today() - date.fromisoformat(str(data.get("deadline") or ""))).days
        except ValueError:
            continue
        if overdue_days <= 0:
            continue
        previous = data.get("performance_impact") or {}
        impact = {
            "overdue": True, "overdue_days": overdue_days, "penalty_points": overdue_days,
            "recorded_for": str(date.today()), "responsible_user": task.owner,
        }
        if previous == impact:
            continue
        task.data = {**data, "performance_impact": impact}
        if not previous:
            db.add(WorkflowEvent(record_id=task.id, action="记录任务超期绩效", from_status=task.status, to_status=task.status, operator="system", comment=f"任务超期 {overdue_days} 天，记录绩效影响 {overdue_days} 分"))
        changed = True
    if changed:
        await db.commit()
    return changed


async def _apply_hearing_sms_reminders(db: AsyncSession) -> bool:
    """Create auditable 3-day/1-day hearing SMS records and send through a configured webhook."""
    today = date.today(); changed = False
    schedules = list((await db.scalars(select(HearingSchedule).where(HearingSchedule.status == "已排期", HearingSchedule.hearing_date.in_([today + timedelta(days=1), today + timedelta(days=3)])))).all())
    for hearing in schedules:
        days = (hearing.hearing_date - today).days
        duplicate = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.module == "sms", BusinessRecord.data["hearing_id"].as_integer() == hearing.id, BusinessRecord.data["remind_days"].as_integer() == days))
        if duplicate: continue
        case_record = await db.get(BusinessRecord, hearing.case_record_id)
        if not case_record: continue
        names = list(dict.fromkeys(value for value in [hearing.hearing_lawyer, *((case_record.data or {}).get("handling_lawyers") or []), (case_record.data or {}).get("assistant", "")] if value))
        users = list((await db.scalars(select(User).where(User.is_active.is_(True), or_(User.username.in_(names), User.display_name.in_(names))))).all()) if names else []
        phones = list(dict.fromkeys(str((user.profile or {}).get("phone") or "").strip() for user in users if str((user.profile or {}).get("phone") or "").strip()))
        content = f"开庭提醒：案件 {case_record.serial_no} 将于 {hearing.hearing_date} {hearing.hearing_time} 在 {hearing.court}{(' ' + hearing.courtroom) if hearing.courtroom else ''} 开庭。"
        sms_status = "待配置短信通道" if not settings.sms_webhook_url else "待发送"
        if not phones: sms_status = "待补充手机号"
        response_excerpt = ""
        if phones and settings.sms_webhook_url:
            try:
                headers = {"Authorization": f"Bearer {settings.sms_webhook_token}"} if settings.sms_webhook_token else {}
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(settings.sms_webhook_url, json={"phones": phones, "content": content, "case_no": case_record.serial_no, "hearing_id": hearing.id}, headers=headers)
                    response.raise_for_status(); response_excerpt = response.text[:500]
                sms_status = "已发送"
            except Exception as exc:
                sms_status = "发送失败"; response_excerpt = str(exc)[:500]
        sms = BusinessRecord(module="sms", serial_no=f"DX{datetime.now():%Y%m%d%H%M%S%f}", title=f"开庭短信提醒—{case_record.serial_no}", customer=case_record.customer, status=sms_status, owner="system", department=case_record.department, description=content, data={"hearing_id": hearing.id, "case_id": case_record.id, "case_no": case_record.serial_no, "remind_days": days, "phones": phones, "recipient_users": [user.username for user in users], "provider_response": response_excerpt})
        db.add(sms); await db.flush()
        db.add(WorkflowEvent(record_id=sms.id, action="生成开庭短信提醒", to_status=sms_status, operator="system", comment=f"开庭前 {days} 天；收件手机号 {len(phones)} 个"))
        for user in users:
            db.add(Notification(source_key=f"hearing-sms-{hearing.id}-{days}-{user.username}", source_type="case", source_id=case_record.id, sender="system", recipient=user.username, notification_type="系统通知", title=f"开庭短信：{sms_status}", content=content, level="info" if sms_status == "已发送" else "warning"))
        changed = True
    if changed: await db.commit()
    return changed


def _vip_task_member(task: VipTask, identity: dict) -> bool:
    return identity.get("role") == "admin" or identity["username"] in {
        task.created_by, task.owner, *(str(value) for value in (task.collaborators or [])),
    }


async def _vip_validate_task_transition(task: VipTask, target: str, identity: dict, db: AsyncSession) -> None:
    if target == task.status:
        return
    actor = identity["username"]
    is_admin = identity.get("role") == "admin"
    allowed = {
        "待处理": {"处理中", "已拒绝", "已暂停", "已取消"},
        "处理中": {"已完成", "已暂停", "已取消"},
        "已暂停": {"待处理", "处理中", "已取消"},
        "已完成": {"待处理", "已验收", "已拒绝"},
        "已拒绝": {"待处理"},
        "已验收": set(),
        "已取消": set(),
    }
    if target not in allowed.get(task.status, set()):
        raise HTTPException(status_code=409, detail=f"VIP任务不能从{task.status}变更为{target}")
    if target == "已完成":
        if not is_admin and actor != task.owner:
            raise HTTPException(status_code=403, detail="只有VIP任务负责人可以完成任务")
        node_statuses = list((await db.scalars(select(VipTaskNode.status).where(VipTaskNode.vip_task_id == task.id))).all())
        if any(value not in {"已完成", "已取消"} for value in node_statuses):
            raise HTTPException(status_code=409, detail="存在未办结的VIP任务节点，不能完成任务")
    elif target == "待处理" and task.status in {"已完成", "已拒绝", "已暂停"}:
        if not is_admin and actor != task.created_by:
            raise HTTPException(status_code=403, detail="只有VIP任务创建人可以重新打开任务")
    elif target in {"已验收", "已拒绝"} and task.status == "已完成":
        if not is_admin and actor != task.created_by:
            raise HTTPException(status_code=403, detail="只有VIP任务创建人可以验收或拒绝任务")
    elif not is_admin and actor not in {task.created_by, task.owner}:
        raise HTTPException(status_code=403, detail="只有VIP任务创建人或负责人可以变更状态")


async def _vip_task_or_404(task_id: int, identity: dict, db: AsyncSession, *, write: bool = False) -> VipTask:
    task = await db.get(VipTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="VIP任务不存在")
    if not _vip_task_member(task, identity):
        raise HTTPException(status_code=403, detail="无权访问该VIP任务")
    if write and identity.get("role") != "admin" and identity["username"] not in {task.created_by, task.owner}:
        raise HTTPException(status_code=403, detail="只有发起人或负责人可以修改VIP任务")
    return task


def _vip_task_dict(task: VipTask, *, node_count: int = 0, unread_message_count: int = 0) -> dict:
    return {
        "id": task.id, "serial_no": task.serial_no, "title": task.title, "customer": task.customer,
        "status": task.status, "priority": task.priority, "owner": task.owner, "department": task.department,
        "description": task.description, "collaborators": task.collaborators or [], "created_by": task.created_by,
        "start_at": task.start_at, "deadline": task.deadline, "end_at": task.end_at,
        "created_at": task.created_at, "updated_at": task.updated_at,
        "node_count": node_count, "unread_message_count": unread_message_count,
    }


async def _vip_task_response(task: VipTask, identity: dict, db: AsyncSession) -> dict:
    node_count = int(await db.scalar(select(func.count()).select_from(VipTaskNode).where(VipTaskNode.vip_task_id == task.id)) or 0)
    unread_count = int(await db.scalar(select(func.count()).select_from(VipTaskMessage).where(
        VipTaskMessage.vip_task_id == task.id, VipTaskMessage.recipient == identity["username"], VipTaskMessage.is_read.is_(False),
    )) or 0)
    return _vip_task_dict(task, node_count=node_count, unread_message_count=unread_count)


async def _active_task_username(value: str, db: AsyncSession, *, field_name: str) -> str:
    requested = value.strip()
    if not requested:
        raise HTTPException(status_code=422, detail=f"{field_name}不能为空")
    user = await db.scalar(select(User).where(User.username == requested))
    if not user:
        matches = list((await db.scalars(select(User).where(User.display_name == requested))).all())
        if len(matches) > 1:
            raise HTTPException(status_code=422, detail=f"{field_name}姓名不唯一，请填写账号")
        user = matches[0] if matches else None
    if not user or not user.is_active:
        raise HTTPException(status_code=422, detail=f"{field_name}不存在或已停用")
    return user.username


def _validate_task_deadline(deadline: date) -> None:
    duration = (deadline - date.today()).days
    if duration < 0:
        raise HTTPException(status_code=422, detail="任务截止日期不能早于今天")
    if duration > 30:
        raise HTTPException(status_code=422, detail="任务截止日期不能超过 30 天")


async def _next_manual_task_serial(db: AsyncSession, *, now: datetime | None = None) -> str:
    """Return the legacy-compatible 11-digit visible task number.

    The legacy task list stores ``HHmmss`` followed by a five-digit collision
    suffix; whether a task is manual or automatic is represented separately.
    Historical identifiers remain untouched.
    """
    time_prefix = f"{now or datetime.now():%H%M%S}"
    for _ in range(100):
        candidate = f"{time_prefix}{secrets.randbelow(100000):05d}"
        if not await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == candidate)):
            return candidate
    raise HTTPException(status_code=503, detail="任务编号生成失败，请稍后重试")


def _one_calendar_month_after(value: date) -> date:
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


async def _resolve_case_task_username(values: object, db: AsyncSession) -> tuple[str, User | None]:
    raw_values = values if isinstance(values, list) else [values]
    for raw_value in raw_values:
        value = str(raw_value or "").strip()
        if not value:
            continue
        users = list((await db.scalars(select(User).where(
            User.is_active.is_(True),
            or_(User.username == value, User.display_name == value),
        ).order_by(User.id))).all())
        exact_username = next((user for user in users if user.username == value), None)
        if exact_username:
            return exact_username.username, exact_username
        if len(users) == 1:
            return users[0].username, users[0]
    return "", None


async def _ensure_document_preparation_task(
    case_record: BusinessRecord,
    db: AsyncSession,
    *,
    system_operator: str,
    transition_date: date | None = None,
) -> BusinessRecord | None:
    """Create the legacy document-preparation assignment once its two conditions hold."""
    if case_record.status != "文书准备" and transition_date is None:
        return None

    case_data = case_record.data or {}
    assistant_username, assistant_user = await _resolve_case_task_username(
        case_data.get("assistant_usernames")
        or case_data.get("assistant_username")
        or case_data.get("assistants")
        or case_data.get("assistant"),
        db,
    )
    initiator_username, initiator_user = await _resolve_case_task_username(
        case_data.get("handling_lawyer_usernames") or case_data.get("handling_lawyers"),
        db,
    )
    if not assistant_username or not initiator_username:
        return None

    linked_tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task",
        or_(
            BusinessRecord.data["case_id"].as_integer() == case_record.id,
            BusinessRecord.data["case_record_id"].as_integer() == case_record.id,
            BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
        ),
    ).order_by(BusinessRecord.id))).all())
    existing = next((task for task in linked_tasks if (
        str((task.data or {}).get("auto_task_type") or "") == "document_preparation_stage"
        or (
            task.title == "文书准备阶段"
            and _task_creation_mode(task.data or {}) == "自动"
        )
    )), None)
    if existing:
        case_record.data = {
            **case_data,
            "document_preparation_task_id": existing.id,
        }
        return existing

    started_on = transition_date or date.today()
    deadline = _one_calendar_month_after(started_on)
    description = f"{case_record.serial_no}已经分案,尽快完成文书."
    assistant_name = str(assistant_user.display_name or assistant_username).strip()
    initiator_name = str(initiator_user.display_name or initiator_username).strip()
    task = BusinessRecord(
        module="task",
        serial_no=await _next_manual_task_serial(db),
        title="文书准备阶段",
        customer=case_record.customer,
        status="待接收",
        owner=assistant_username,
        department=str(assistant_user.department or case_record.department).strip(),
        description=description,
        data={
            "deadline": str(deadline),
            "start_at": str(started_on),
            "end_at": str(deadline),
            "priority": "普通",
            "source": "案件任务",
            "creation_mode": "自动",
            "task_type": "自动任务",
            "auto_task_type": "document_preparation_stage",
            "initiator": initiator_username,
            "collaborators": [assistant_username],
            "case_no": case_record.serial_no,
            "case_nos": [case_record.serial_no],
            "case_id": case_record.id,
            "case_record_id": case_record.id,
            "case_ids": [case_record.id],
            "case_module": "case",
            "case_stage": "文书准备",
            "system_created_by": system_operator,
        },
    )
    db.add(task)
    await db.flush()
    comment = (
        f"{initiator_name}新建任务给负责人({assistant_name})，协作人({assistant_name})，附言：\n\n"
        f"{description}"
    )
    await _add_task_message_notifications(
        task,
        WorkflowEvent(
            record_id=task.id,
            action="系统生成文书准备阶段任务",
            to_status="待接收",
            operator=initiator_username,
            comment=comment,
        ),
        db,
        content=comment,
    )
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="生成文书准备阶段任务",
        from_status=case_record.status,
        to_status=case_record.status,
        operator="system",
        comment=f"任务 {task.serial_no}；负责人 {assistant_name}；发起人 {initiator_name}",
    ))
    case_record.data = {
        **case_data,
        "document_preparation_task_id": task.id,
    }
    return task


_TIMESTAMP_EVIDENCE_ORGANIZATIONS = {"时间戳", "权利卫士", "时间戳取证"}


def _case_clue_numbers(case_data: dict) -> list[str]:
    values = (
        case_data.get("investigation_clue_nos")
        or case_data.get("clue_nos")
        or case_data.get("clue_no")
        or case_data.get("investigation_clue")
        or case_data.get("source_clue_no")
        or []
    )
    raw_values = values if isinstance(values, list) else str(values).replace("，", ",").split(",")
    return list(dict.fromkeys(str(value or "").strip() for value in raw_values if str(value or "").strip()))


async def _case_originates_from_timestamp_evidence(
    case_record: BusinessRecord,
    db: AsyncSession,
) -> bool:
    case_data = case_record.data or {}
    if case_data.get("source_is_timestamp_evidence") is True:
        return True
    if str(case_data.get("source_evidence_method") or "").strip() == "timestamp":
        return True
    if str(case_data.get("source_notary_institution") or "").strip() in _TIMESTAMP_EVIDENCE_ORGANIZATIONS:
        return True

    raw_ids = (
        case_data.get("investigation_clue_ids")
        or [case_data.get("investigation_clue_id") or case_data.get("clue_record_id") or case_data.get("clue_id")]
    )
    clue_ids = []
    for raw_id in raw_ids if isinstance(raw_ids, list) else [raw_ids]:
        try:
            clue_id = int(raw_id or 0)
        except (TypeError, ValueError):
            continue
        if clue_id and clue_id not in clue_ids:
            clue_ids.append(clue_id)
    if clue_ids:
        clues = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "clue", BusinessRecord.id.in_(clue_ids),
        ))).all())
        for clue in clues:
            clue_data = clue.data or {}
            if (
                clue_data.get("is_timestamp_evidence") is True
                or str(clue_data.get("evidence_method") or "").strip() == "timestamp"
                or str(clue_data.get("notary_institution") or "").strip() in _TIMESTAMP_EVIDENCE_ORGANIZATIONS
            ):
                return True

    clue_numbers = _case_clue_numbers(case_data)
    if not clue_numbers:
        return False
    legacy_clues = list((await db.scalars(select(LegacyInvestigationClue).where(
        LegacyInvestigationClue.ClueNo.in_(clue_numbers),
    ))).all())
    clue_guids = [str(item.ClueGuid or "").strip() for item in legacy_clues if str(item.ClueGuid or "").strip()]
    if not clue_guids:
        return False
    legacy_evidence = list((await db.scalars(select(LegacyInvestigationClueEvidence).where(
        LegacyInvestigationClueEvidence.ClueGuid.in_(clue_guids),
        LegacyInvestigationClueEvidence.NotaryOrganization.in_(_TIMESTAMP_EVIDENCE_ORGANIZATIONS),
    ))).all())
    return any(str(item.IsActived or "").strip().upper() not in {"N", "F", "0"} for item in legacy_evidence)


async def _ensure_timestamp_evidence_handoff_task(
    case_record: BusinessRecord,
    db: AsyncSession,
    *,
    system_operator: str,
) -> BusinessRecord | None:
    """Create the legacy timestamp-file handoff task once all conditions hold."""
    if case_record.status != "文书准备" or not await _case_originates_from_timestamp_evidence(case_record, db):
        return None

    case_data = case_record.data or {}
    assistant_username, assistant_user = await _resolve_case_task_username(
        case_data.get("assistant_usernames")
        or case_data.get("assistant_username")
        or case_data.get("assistants")
        or case_data.get("assistant"),
        db,
    )
    if not assistant_username or not assistant_user:
        return None

    linked_tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task",
        or_(
            BusinessRecord.data["case_id"].as_integer() == case_record.id,
            BusinessRecord.data["case_record_id"].as_integer() == case_record.id,
            BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
        ),
    ).order_by(BusinessRecord.id))).all())
    existing = next((task for task in linked_tasks if (
        str((task.data or {}).get("auto_task_type") or "") == "timestamp_evidence_handoff"
        or (task.title == "交接时间戳文件" and _task_creation_mode(task.data or {}) == "自动")
    )), None)
    if existing:
        case_record.data = {**case_data, "timestamp_evidence_handoff_task_id": existing.id}
        return existing

    owner_matches = list((await db.scalars(select(User).where(
        User.display_name == "范应根", User.is_active.is_(True),
    ).order_by(User.id))).all())
    if len(owner_matches) != 1:
        raise HTTPException(status_code=422, detail="自动任务负责人范应根不存在、已停用或姓名不唯一")
    owner_user = owner_matches[0]
    started_on = date.today()
    deadline = started_on + timedelta(days=7)
    description = f"{case_record.serial_no},交接时间戳文件."
    assistant_name = str(assistant_user.display_name or assistant_username).strip()
    owner_name = str(owner_user.display_name or owner_user.username).strip()
    task = BusinessRecord(
        module="task",
        serial_no=await _next_manual_task_serial(db),
        title="交接时间戳文件",
        customer=case_record.customer,
        status="待接收",
        owner=owner_user.username,
        department=str(owner_user.department or case_record.department).strip(),
        description=description,
        data={
            "deadline": str(deadline), "start_at": str(started_on), "end_at": str(deadline),
            "priority": "普通", "source": "案件任务", "creation_mode": "自动",
            "task_type": "自动任务", "auto_task_type": "timestamp_evidence_handoff",
            "initiator": assistant_username, "collaborators": [],
            "case_no": case_record.serial_no, "case_nos": [case_record.serial_no],
            "case_id": case_record.id, "case_record_id": case_record.id, "case_ids": [case_record.id],
            "case_module": "case", "case_stage": "文书准备",
            "source_evidence_method": "timestamp", "system_created_by": system_operator,
        },
    )
    db.add(task)
    await db.flush()
    comment = f"{assistant_name}新建任务给负责人({owner_name})，协作人(无)，附言：\n\n{description}"
    await _add_task_message_notifications(
        task,
        WorkflowEvent(
            record_id=task.id, action="系统生成交接时间戳文件任务",
            to_status="待接收", operator=assistant_username, comment=comment,
        ),
        db,
        content=comment,
    )
    db.add(WorkflowEvent(
        record_id=case_record.id, action="生成交接时间戳文件任务",
        from_status=case_record.status, to_status=case_record.status, operator="system",
        comment=f"任务 {task.serial_no}；负责人 {owner_name}；发起人 {assistant_name}",
    ))
    case_record.data = {**case_data, "timestamp_evidence_handoff_task_id": task.id}
    return task


def _task_rule_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


async def _materialize_legacy_case_task(
    case_record: BusinessRecord,
    db: AsyncSession,
    *,
    auto_task_type: str,
    legacy_task_type_id: int,
    title: str,
    initiator: User | None,
    owner: User,
    collaborators: list[User],
    description: str,
    started_on: date,
    deadline: date,
    trigger_at: date,
    trigger_source_id: str,
) -> BusinessRecord:
    existing = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "task",
        BusinessRecord.data["case_id"].as_integer() == case_record.id,
        BusinessRecord.data["auto_task_type"].as_string() == auto_task_type,
        BusinessRecord.data["trigger_source_id"].as_string() == trigger_source_id,
    ))
    if existing:
        return existing
    initiator_username = initiator.username if initiator else "system"
    initiator_name = str(initiator.display_name or initiator.username).strip() if initiator else "System"
    owner_name = str(owner.display_name or owner.username).strip()
    collaborator_users = list({user.username: user for user in collaborators}.values())
    collaborator_names = "、".join(str(user.display_name or user.username).strip() for user in collaborator_users) or "无"
    task = BusinessRecord(
        module="task", serial_no=await _next_manual_task_serial(db), title=title,
        customer=case_record.customer, status="待接收", owner=owner.username,
        department=str(owner.department or case_record.department).strip(), description=description,
        data={
            "deadline": str(deadline), "start_at": str(started_on), "end_at": str(deadline),
            "priority": "普通", "source": "案件任务", "creation_mode": "自动", "task_type": "自动任务",
            "auto_task_type": auto_task_type, "legacy_task_type_id": legacy_task_type_id,
            "initiator": initiator_username, "collaborators": [user.username for user in collaborator_users],
            "case_no": case_record.serial_no, "case_nos": [case_record.serial_no],
            "case_id": case_record.id, "case_record_id": case_record.id, "case_ids": [case_record.id],
            "case_module": case_record.module, "case_stage": case_record.status,
            "source_module": case_record.module, "source_record_id": case_record.id,
            "trigger_at": str(trigger_at), "trigger_source_id": trigger_source_id, "system_created_by": "system",
        },
    )
    db.add(task)
    await db.flush()
    message = (
        f"{initiator_name}新建任务给负责人({owner_name})，协作人({collaborator_names})，附言：\n\n"
        f"{description}"
    )
    await _add_task_message_notifications(
        task,
        WorkflowEvent(record_id=task.id, action=f"系统生成{title}", to_status="待接收", operator=initiator_username, comment=message),
        db,
        content=message,
    )
    db.add(WorkflowEvent(
        record_id=case_record.id, action=f"生成{title}", from_status=case_record.status,
        to_status=case_record.status, operator="system", comment=f"任务 {task.serial_no}；负责人 {owner_name}",
    ))
    return task


async def _case_rule_people(case_record: BusinessRecord, db: AsyncSession) -> tuple[User | None, User | None]:
    data = case_record.data or {}
    _, lawyer = await _resolve_case_task_username(
        data.get("handling_lawyer_usernames") or data.get("handling_lawyers"), db,
    )
    _, assistant = await _resolve_case_task_username(
        data.get("assistant_usernames") or data.get("assistant_username") or data.get("assistants") or data.get("assistant"), db,
    )
    return lawyer, assistant


async def _legacy_configured_task_user(db: AsyncSession, *codes: str) -> User | None:
    for code in codes:
        parameter = await db.scalar(select(SystemParameter).where(
            SystemParameter.category.in_({"task_service", "task_officer", "system"}),
            SystemParameter.code == code, SystemParameter.is_active.is_(True),
        ).order_by(SystemParameter.id))
        if not parameter:
            continue
        reference = str((parameter.extra or {}).get("username") or parameter.name or "").strip()
        username, user = await _resolve_case_task_username(reference, db)
        if username and user:
            return user
    return None


async def _linked_case_for_record(record: BusinessRecord, cases_by_id: dict[int, BusinessRecord], cases_by_no: dict[str, BusinessRecord]) -> BusinessRecord | None:
    data = record.data or {}
    try:
        case_id = int(data.get("case_id") or data.get("case_record_id") or 0)
    except (TypeError, ValueError):
        case_id = 0
    return cases_by_id.get(case_id) or cases_by_no.get(str(data.get("case_no") or "").strip())


async def _finish_legacy_auto_task(task: BusinessRecord, db: AsyncSession, *, reason: str) -> bool:
    if task.status in {"已完成", "待确认", "已验收", "已拒绝", "已撤回", "已停止", "已取消"}:
        return False
    previous = task.status
    task.status = "已完成"
    task.data = {**(task.data or {}), "auto_completed": True, "auto_completed_at": str(date.today())}
    await _add_task_message_notifications(
        task,
        WorkflowEvent(record_id=task.id, action="业务状态联动自动完成", from_status=previous, to_status="已完成", operator="system", comment=reason),
        db,
        content=reason,
    )
    return True


async def _ensure_phase_automatic_tasks(
    case_record: BusinessRecord,
    db: AsyncSession,
    *,
    previous_status: str,
    today: date | None = None,
) -> list[BusinessRecord]:
    if case_record.status == previous_status:
        return []
    effective_today = today or date.today()
    lawyer, assistant = await _case_rule_people(case_record, db)
    created: list[BusinessRecord] = []
    if case_record.status in {"二审待执行", "再审待执行"} and lawyer and assistant:
        created.append(await _materialize_legacy_case_task(
            case_record, db, auto_task_type="execution_application_reminder", legacy_task_type_id={"二审待执行": 102017, "再审待执行": 103015}[case_record.status],
            title="执行申请-提醒任务", initiator=lawyer, owner=assistant, collaborators=[],
            description=f"本案{case_record.serial_no}判决书或调解书已生效,请尽快提交申请执行材料,并上传",
            started_on=effective_today, deadline=_add_calendar_months(effective_today, 2),
            trigger_at=effective_today, trigger_source_id=f"phase:{case_record.status}",
        ))
    if case_record.status in {"执行受理", "执行立案受理"} and lawyer and assistant:
        created.append(await _materialize_legacy_case_task(
            case_record, db, auto_task_type="execution_follow_up", legacy_task_type_id=104012,
            title="跟进执行", initiator=lawyer, owner=assistant, collaborators=[],
            description=f"{case_record.serial_no} 执行情况跟踪.", started_on=effective_today,
            deadline=_add_calendar_months(effective_today, 3), trigger_at=effective_today,
            trigger_source_id="phase:104012",
        ))
    if case_record.status == "执行终本" and assistant:
        created.append(await _materialize_legacy_case_task(
            case_record, db, auto_task_type="execution_end_follow_up", legacy_task_type_id=104015,
            title="案件研究", initiator=assistant, owner=lawyer or assistant, collaborators=[],
            description=f"{case_record.serial_no}研究终本案件后续处理.", started_on=effective_today,
            deadline=_add_calendar_months(effective_today, 2), trigger_at=effective_today,
            trigger_source_id="phase:104015",
        ))
    if case_record.status == "一审和解结案":
        fixed = list((await db.scalars(select(User).where(User.display_name == "梁晨宇", User.is_active.is_(True)))).all())
        if len(fixed) != 1:
            raise HTTPException(status_code=422, detail="自动任务固定负责人“梁晨宇”未配置或存在重名账号")
        created.append(await _materialize_legacy_case_task(
            case_record, db, auto_task_type="first_mediation_closed_archive", legacy_task_type_id=101024,
            title="结算归档一审和解结案", initiator=None, owner=fixed[0], collaborators=[],
            description="结算归档", started_on=effective_today, deadline=effective_today + timedelta(days=50),
            trigger_at=effective_today, trigger_source_id="phase:101024:immediate",
        ))
    elif case_record.status in {"一审和解中", "二审和解中", "再审和解中"} and lawyer:
        legacy_type = {"一审和解中": 101023, "二审和解中": 102023, "再审和解中": 103023}[case_record.status]
        created.append(await _materialize_legacy_case_task(
            case_record, db, auto_task_type=f"mediation_follow_up_{legacy_type}", legacy_task_type_id=legacy_type,
            title="跟进和解—提醒任务", initiator=lawyer, owner=lawyer, collaborators=[],
            description=f"本案{case_record.serial_no}和解中，请尽快协商确定.", started_on=effective_today,
            deadline=_add_calendar_months(effective_today, 1), trigger_at=effective_today,
            trigger_source_id=f"phase:{legacy_type}",
        ))
    closing_types = {
        "一审和解结案": 101024,
        "一审判决结案": 101025, "二审和解结案": 102024, "二审判决结案": 102025,
        "再审和解结案": 103024, "再审判决结案": 103025, "执行结案": 104014,
    }
    if case_record.status in closing_types and lawyer and assistant:
        created.append(await _materialize_legacy_case_task(
            case_record, db, auto_task_type=f"settlement_archive_{closing_types[case_record.status]}",
            legacy_task_type_id=closing_types[case_record.status], title="归档结算—提醒任务",
            initiator=lawyer, owner=assistant, collaborators=[assistant],
            description=f"本案{case_record.serial_no}已结案,请尽快提交结算并归档.",
            started_on=effective_today, deadline=_add_calendar_months(effective_today, 2),
            trigger_at=effective_today, trigger_source_id=f"phase:{closing_types[case_record.status]}",
        ))
        created.append(await _materialize_legacy_case_task(
            case_record, db, auto_task_type=f"close_case_{closing_types[case_record.status]}",
            legacy_task_type_id=closing_types[case_record.status], title=f"结算归档{case_record.status}",
            initiator=lawyer, owner=assistant, collaborators=[], description="结算归档",
            started_on=effective_today, deadline=effective_today + timedelta(days=20),
            trigger_at=effective_today, trigger_source_id=f"close-case:{closing_types[case_record.status]}",
        ))
    return created


_LEGACY_AGENCY_FEE_TYPE_IDS = {"11020010", "11020020", "11020030", "11020040"}


def _numeric_task_rule_value(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _legacy_case_fee_matches_case(fee: BusinessRecord, case_record: BusinessRecord) -> bool:
    """Match a fee only through an explicit current or retained legacy case key."""
    data = fee.data or {}
    current_case_ids = [data.get("case_id"), data.get("case_record_id")]
    explicit_current_ids = {str(value) for value in current_case_ids if value not in (None, "")}
    if explicit_current_ids:
        return explicit_current_ids == {str(case_record.id)}

    current_case_nos = {case_record.serial_no}
    current_case_nos.update(str((case_record.data or {}).get(key) or "").strip() for key in (
        "legacy_system_case_no", "legacy_case_no", "case_no",
    ))
    current_case_nos.discard("")
    fee_case_nos = {str(data.get(key) or "").strip() for key in ("case_no", "legacy_case_no")}
    if fee_case_nos.intersection(current_case_nos):
        return True

    legacy_case_ids = set()
    legacy_case_id = (case_record.data or {}).get("legacy_case_id")
    if legacy_case_id not in (None, ""):
        legacy_case_ids.add(str(legacy_case_id))
    legacy = data.get("legacy_record")
    if isinstance(legacy, dict):
        fee_legacy_case_id = legacy.get("CaseId")
        return fee_legacy_case_id not in (None, "") and str(fee_legacy_case_id) in legacy_case_ids
    return False


def _legacy_agency_fee_amounts(fee: BusinessRecord) -> tuple[bool, tuple[float, float] | None]:
    """Return whether this is a target fee and, when provable, its two totals."""
    data = fee.data or {}
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    fee_type_id = next((str(value).strip() for value in (
        data.get("case_fee_type_id"), data.get("legacy_case_fee_type_id"), data.get("fee_type_code"),
        legacy.get("CaseFeeTypeId"),
    ) if value not in (None, "")), "")
    if fee_type_id not in _LEGACY_AGENCY_FEE_TYPE_IDS:
        return False, None
    active_value = data.get("legacy_is_actived", legacy.get("IsActived", data.get("is_active")))
    if active_value is False or str(active_value or "").strip().upper() in {"F", "N", "0", "FALSE"}:
        return False, None
    raw_amount = data.get("amount") if data.get("amount") is not None else legacy.get("Amount")
    raw_cashed = data.get("cashed_amount")
    if raw_cashed is None:
        raw_cashed = data.get("received_amount")
    if raw_cashed is None:
        # SQL Server's ISNULL(CashedAmount, 0) makes a legacy NULL an unpaid
        # balance. A missing current receipt amount carries the same meaning.
        raw_cashed = legacy.get("CashedAmount")
    amount = _numeric_task_rule_value(raw_amount)
    cashed = 0.0 if raw_cashed is None else _numeric_task_rule_value(raw_cashed)
    if amount is None or cashed is None:
        return True, None
    return True, (amount, cashed)


def _case_fee_received_amounts(fees: list[BusinessRecord], payments: list[IncomingPayment]) -> dict[int, float]:
    """Index explicit receipt-to-fee links once for the complete rule scan."""
    from app.core.finance import (
        _case_fee_link_maps, _resolve_case_fee_link_id,
    )

    fee_ids, legacy_fee_ids = _case_fee_link_maps(fees)
    received_by_fee = {fee_id: 0.0 for fee_id in fee_ids}
    for payment in payments:
        for allocation in payment.allocations or []:
            if not isinstance(allocation, dict):
                continue
            nested_linked = False
            for settlement_item in allocation.get("settlement_items") or []:
                if not isinstance(settlement_item, dict):
                    continue
                fee_id = _resolve_case_fee_link_id(settlement_item, fee_ids, legacy_fee_ids)
                if fee_id in received_by_fee:
                    amount = _numeric_task_rule_value(settlement_item.get("amount") or settlement_item.get("settlement_amount"))
                    if amount is not None:
                        received_by_fee[fee_id] += amount
                    nested_linked = True
            if nested_linked:
                continue
            fee_id = _resolve_case_fee_link_id(allocation, fee_ids, legacy_fee_ids)
            if not fee_id:
                try:
                    fee_id = int(allocation.get("finance_record_id") or 0)
                except (TypeError, ValueError):
                    fee_id = 0
            if fee_id in received_by_fee:
                amount = _numeric_task_rule_value(allocation.get("amount"))
                if amount is not None:
                    received_by_fee[fee_id] += amount
    return received_by_fee


def _case_has_outstanding_legacy_agency_fee(
    case_record: BusinessRecord,
    fees: list[BusinessRecord],
    received_by_fee: dict[int, float],
) -> bool | None:
    """Return whether verified old-type agency fees remain unpaid; None means no proof."""
    verified_fees: dict[int, tuple[BusinessRecord, float, float]] = {}
    for fee in fees:
        if not _legacy_case_fee_matches_case(fee, case_record):
            continue
        is_target_fee, amounts = _legacy_agency_fee_amounts(fee)
        if not is_target_fee:
            continue
        if amounts is None:
            return None
        if amounts is not None:
            verified_fees[fee.id] = (fee, *amounts)
    if not verified_fees:
        return None

    for fee_id, (_, amount, recorded_cashed) in verified_fees.items():
        # Imported FAM_Case_Fee.CashedAmount and current receipt allocations
        # describe the same balance. Use the greater proved total, never a
        # customer/case-name estimate and never both totals added together.
        cashed = max(recorded_cashed, received_by_fee.get(fee_id, 0.0))
        if amount - cashed > 0.001:
            return True
    return False


async def _apply_case_automatic_task_rules(db: AsyncSession, *, today: date | None = None) -> int:
    effective_today = today or date.today()
    task_count_before = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
        BusinessRecord.module == "task",
    )) or 0)
    cases = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "case"))).all())
    cases_by_id = {item.id: item for item in cases}
    cases_by_no = {item.serial_no: item for item in cases}
    related_records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_({"contract", "finance", "invoice", "refund", "warehouse", "notary", "case_fee"}),
    ))).all())
    all_payments = list((await db.scalars(select(IncomingPayment))).all())
    receipts = [item for item in all_payments if item.received_date <= effective_today - timedelta(days=30)]
    receipts_by_case_id: dict[int, list[IncomingPayment]] = {}
    receipts_by_case_no: dict[str, list[IncomingPayment]] = {}
    for receipt in receipts:
        if receipt.case_no:
            receipts_by_case_no.setdefault(receipt.case_no, []).append(receipt)
        for allocation in receipt.allocations or []:
            if not isinstance(allocation, dict):
                continue
            try:
                allocation_case_id = int(allocation.get("case_id") or 0)
            except (TypeError, ValueError):
                allocation_case_id = 0
            allocation_case_no = str(allocation.get("case_no") or "").strip()
            if allocation_case_id:
                receipts_by_case_id.setdefault(allocation_case_id, []).append(receipt)
            if allocation_case_no:
                receipts_by_case_no.setdefault(allocation_case_no, []).append(receipt)
    for case_record in cases:
        data = case_record.data or {}
        phase_date = _task_rule_date(data.get("phase_changed_at") or case_record.updated_at or case_record.created_at)
        if not phase_date:
            continue
        lawyer, assistant = await _case_rule_people(case_record, db)
        # Compensation scan shares the same idempotency keys as the synchronous
        # transition path, covering imports, batch changes and earlier failures.
        await _ensure_document_preparation_task(case_record, db, system_operator="system")
        await _ensure_timestamp_evidence_handoff_task(case_record, db, system_operator="system")
        if case_record.status == "一审待执行":
            await _ensure_execution_application_reminder_task(
                case_record, db, previous_status="", operator="system", today=effective_today,
            )
        await _ensure_phase_automatic_tasks(case_record, db, previous_status="", today=effective_today)
        if case_record.status == "一审和解结案" and lawyer and assistant and effective_today >= phase_date + timedelta(days=50):
            await _materialize_legacy_case_task(
                case_record, db, auto_task_type="first_mediation_closed_reminder", legacy_task_type_id=101024,
                title="归档结算—提醒任务", initiator=lawyer, owner=assistant, collaborators=[assistant],
                description=f"本案{case_record.serial_no}已结案,请尽快提交结算并归档.", started_on=effective_today,
                deadline=_add_calendar_months(effective_today, 2), trigger_at=phase_date + timedelta(days=50),
                trigger_source_id=f"phase:101024:{phase_date}:50d",
            )
        if case_record.status == "提交立案" and lawyer and assistant and effective_today >= phase_date + timedelta(days=20):
            await _materialize_legacy_case_task(
                case_record, db, auto_task_type="filing_follow_up", legacy_task_type_id=1010131,
                title="跟进立案", initiator=lawyer, owner=assistant, collaborators=[],
                description=(f"案件{case_record.serial_no}提交立案后,跟踪法院立案情况,完成情况,填入案号,"
                             "诉调案号,或申请交诉讼费后,并转到立案受理阶段."),
                started_on=effective_today, deadline=effective_today + timedelta(days=220),
                trigger_at=phase_date + timedelta(days=20), trigger_source_id=f"phase:1010131:{phase_date}:20d",
            )
        case_receipts = list({receipt.id: receipt for receipt in (
            receipts_by_case_id.get(case_record.id, []) + receipts_by_case_no.get(case_record.serial_no, [])
        )}.values())
        if case_receipts:
            if not lawyer or not assistant:
                logger.warning(
                    "case automatic task skipped: case_id=%s rule=payment_received_30d_archive missing=%s",
                    case_record.id,
                    "handling_lawyer" if not lawyer else "assistant",
                )
            else:
                existing_payment_task = await db.scalar(select(BusinessRecord).where(
                    BusinessRecord.module == "task",
                    BusinessRecord.data["case_id"].as_integer() == case_record.id,
                    BusinessRecord.data["auto_task_type"].as_string() == "payment_received_30d_archive",
                ))
                if not existing_payment_task:
                    first_receipt = min(case_receipts, key=lambda item: (item.received_date, item.id))
                    collection_task = await _materialize_legacy_case_task(
                        case_record, db, auto_task_type="payment_received_30d_archive", legacy_task_type_id=1001003,
                        title="结算归档任务", initiator=lawyer, owner=assistant, collaborators=[assistant],
                        description=f"本案{case_record.serial_no}已到账超过30日,请尽快提交结算并归档.",
                        started_on=effective_today, deadline=_add_calendar_months(effective_today, 2),
                        trigger_at=first_receipt.received_date + timedelta(days=30),
                        trigger_source_id=f"case:{case_record.id}:payment_received_30d",
                    )

    # Complete tasks whose source business state has already reached the old
    # service's terminal condition. This also repairs missed historical events.
    tasks = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all())
    case_fees = [item for item in related_records if item.module in {"finance", "case_fee"}]
    received_by_fee = _case_fee_received_amounts(case_fees, all_payments)
    for task in tasks:
        data = task.data or {}
        case_record = cases_by_id.get(int(data.get("case_id") or 0)) if str(data.get("case_id") or "").isdigit() else None
        task_kind = str(data.get("auto_task_type") or "")
        if case_record and task_kind == "document_preparation_stage" and case_record.status not in {"新案待分配", "文书准备"}:
            await _finish_legacy_auto_task(task, db, reason="案件已提交立案，文书准备任务自动完成")
        if case_record and task_kind == "payment_received_30d_archive" and case_record.status in {"已归档", "亏损归档"}:
            await _finish_legacy_auto_task(task, db, reason="案件已归档，结算归档任务自动完成")
        if case_record and task_kind.startswith("notary_audit:") and case_record.status not in {"等待审核公证书", "审核公证书"}:
            await _finish_legacy_auto_task(task, db, reason="案件已离开公证审核阶段，审核公证书任务自动完成")
        if case_record and task_kind.startswith("agency_fee_collection:"):
            outstanding = _case_has_outstanding_legacy_agency_fee(case_record, case_fees, received_by_fee)
            if outstanding is False:
                await _finish_legacy_auto_task(task, db, reason="指定代理费类型已全部到账，催收代理费任务自动完成")

    for source in related_records:
        data = source.data or {}
        case_record = await _linked_case_for_record(source, cases_by_id, cases_by_no)
        lawyer, assistant = await _case_rule_people(case_record, db) if case_record else (None, None)

        if source.module == "refund" and case_record and assistant:
            requested = float(data.get("refund_requested_amount") or data.get("refund_amount") or data.get("amount") or 0)
            refunded = float(data.get("refunded_amount") or 0)
            if requested > 0:
                refund_task = await _materialize_legacy_case_task(
                    case_record, db, auto_task_type=f"refund_application:{source.id}", legacy_task_type_id=1001004,
                    title="办理退费", initiator=lawyer, owner=assistant, collaborators=[],
                    description=f"本案{case_record.serial_no}存在退费，请补充退费材料日期、法院联系人和联系方式.",
                    started_on=effective_today, deadline=_add_calendar_months(effective_today, 2),
                    trigger_at=_task_rule_date(source.created_at) or effective_today, trigger_source_id=f"refund:{source.id}",
                )
                if source.status in {"已退款", "已完成"} or refunded >= requested:
                    await _finish_legacy_auto_task(refund_task, db, reason="退费已全部到账，办理退费任务自动完成")

        if source.module == "invoice" and case_record:
            invoice_date = _task_rule_date(data.get("invoice_date") or source.created_at)
            fee_type = str(data.get("fee_type") or data.get("invoice_type") or "")
            cashed = bool(data.get("cashed_at") or data.get("received_at") or data.get("receipt_date"))
            if invoice_date and "代理" in fee_type and not cashed and effective_today >= invoice_date + timedelta(days=90):
                owner_name = str(data.get("invoice_applicant") or data.get("applicant") or source.owner or "").strip()
                _, owner = await _resolve_case_task_username(owner_name, db)
                finance_user = await _legacy_configured_task_user(db, "FinanceTaskOfficer", "TASK_FINANCE")
                if owner:
                    collection_task = await _materialize_legacy_case_task(
                        case_record, db, auto_task_type=f"agency_fee_collection:{source.id}", legacy_task_type_id=1001005,
                        title="催收代理费", initiator=finance_user, owner=owner,
                        collaborators=[lawyer] if lawyer else [], description=f"本案{case_record.serial_no}代理费发票开具已超过90日，请跟进到账.",
                        started_on=effective_today, deadline=effective_today + timedelta(days=30),
                        trigger_at=invoice_date + timedelta(days=90), trigger_source_id=f"invoice:{source.id}:90d",
                    )
                    outstanding = _case_has_outstanding_legacy_agency_fee(case_record, case_fees, received_by_fee)
                    if outstanding is False:
                        await _finish_legacy_auto_task(collection_task, db, reason="指定代理费类型已全部到账，催收代理费任务自动完成")

        if source.module == "contract":
            end_date = _task_rule_date(data.get("end_date") or data.get("contract_end_date"))
            contract_type = str(data.get("contract_type") or data.get("contract_category") or source.title)
            if end_date and any(word in contract_type for word in ("顾问", "框架")) and effective_today >= _add_calendar_months(end_date, -2) and end_date >= effective_today:
                _, owner = await _resolve_case_task_username(
                    data.get("brand_manager_username") or data.get("customer_manager_username") or source.owner, db,
                )
                if owner:
                    await _materialize_legacy_case_task(
                        source, db, auto_task_type=f"consulting_contract_expiry:{source.id}", legacy_task_type_id=1001006,
                        title="顾问合同到期", initiator=owner, owner=owner, collaborators=[],
                        description=f"合同{source.serial_no}将在{end_date}到期，请及时联系续签.",
                        started_on=effective_today, deadline=end_date, trigger_at=_add_calendar_months(end_date, -2),
                        trigger_source_id=f"contract:{source.id}:expiry",
                    )

        if source.module == "notary" and case_record and source.status in {"待审核", "等待审核", "审核中"}:
            evidence_status = str(data.get("evidence_status") or data.get("storage_state") or "未入库")
            owner = assistant or lawyer
            if owner:
                await _materialize_legacy_case_task(
                    case_record, db, auto_task_type=f"notary_audit:{source.id}", legacy_task_type_id=101002,
                    title="审核公证书", initiator=lawyer, owner=owner, collaborators=[],
                    description=f"本案{case_record.serial_no}公证书待审核，请完成审核.",
                    started_on=effective_today, deadline=effective_today + timedelta(days=30),
                    trigger_at=_task_rule_date(source.updated_at) or effective_today, trigger_source_id=f"notary:{source.id}:audit",
                )
                if evidence_status not in {"已入库", "已重新入库"}:
                    await _materialize_legacy_case_task(
                        case_record, db, auto_task_type=f"notary_evidence_storage:{source.id}", legacy_task_type_id=101003,
                        title="证物入库", initiator=lawyer, owner=owner, collaborators=[],
                        description=f"本案{case_record.serial_no}公证证物尚未入库，请办理入库.",
                        started_on=effective_today, deadline=effective_today + timedelta(days=30),
                        trigger_at=_task_rule_date(source.updated_at) or effective_today, trigger_source_id=f"notary:{source.id}:storage",
                    )

    task_officer = await _legacy_configured_task_user(db, "TaskOfficer", "TASK_OFFICER")
    hearings = list((await db.scalars(select(HearingSchedule).where(HearingSchedule.status == "已排期"))).all())
    for hearing in hearings:
        case_record = cases_by_id.get(hearing.case_record_id)
        if not case_record:
            continue
        lawyer, assistant = await _case_rule_people(case_record, db)
        handling = set(_case_person_references(case_record.data or {}, "handling_lawyer_usernames", "handling_lawyers"))
        _, hearing_user = await _resolve_case_task_username(hearing.hearing_lawyer, db)
        if hearing_user and hearing.hearing_lawyer not in handling and hearing_user.username not in handling:
            await _materialize_legacy_case_task(
                case_record, db, auto_task_type=f"court_lawyer_mismatch:{hearing.id}", legacy_task_type_id=1001007,
                title="开庭律师与经办律师不一致", initiator=lawyer, owner=hearing_user, collaborators=[],
                description=f"本案{case_record.serial_no}开庭律师不在经办律师中，请修改授权文件并变更经办律师.",
                started_on=effective_today, deadline=_add_calendar_months(effective_today, 1),
                trigger_at=_task_rule_date(hearing.created_at) or effective_today, trigger_source_id=f"hearing:{hearing.id}:lawyer",
            )
        needs_evidence = bool((case_record.data or {}).get("needs_hearing_evidence") or (case_record.data or {}).get("evidence_required"))
        if task_officer and needs_evidence and hearing.hearing_date >= effective_today:
            investigator_name = str((case_record.data or {}).get("investigator_username") or (case_record.data or {}).get("investigator") or "")
            _, investigator = await _resolve_case_task_username(investigator_name, db)
            take_task = await _materialize_legacy_case_task(
                case_record, db, auto_task_type=f"take_evidence:{hearing.id}", legacy_task_type_id=1001008,
                title="系统自动任务-拿证物", initiator=lawyer, owner=task_officer,
                collaborators=[investigator] if investigator else [], description=f"本案{case_record.serial_no}开庭需要证物，请办理出库.",
                started_on=effective_today, deadline=hearing.hearing_date - timedelta(days=3),
                trigger_at=effective_today, trigger_source_id=f"hearing:{hearing.id}:evidence",
            )
            evidence_rows = list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.module == "warehouse",
                or_(
                    BusinessRecord.data["case_id"].as_integer() == case_record.id,
                    BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
                ),
            ))).all())
            take_task.data = {**(take_task.data or {}), "warehouse_evidence_ids": [item.id for item in evidence_rows]}

    for case_record in cases:
        data = case_record.data or {}
        lawyer, assistant = await _case_rule_people(case_record, db)
        if data.get("notary_certificate_ready") is True or data.get("notary_prepared_at"):
            owner = await _legacy_configured_task_user(db, "TaskOfficer_Gzs", "TASK_OFFICER_GZS")
            if owner:
                prepared_on = _task_rule_date(data.get("notary_prepared_at")) or effective_today
                await _materialize_legacy_case_task(
                    case_record, db, auto_task_type="notary_certificate_handover", legacy_task_type_id=101004,
                    title="交接公证书", initiator=assistant or lawyer, owner=owner, collaborators=[],
                    description=f"{case_record.serial_no},交接公证书.", started_on=effective_today,
                    deadline=effective_today + timedelta(days=7), trigger_at=prepared_on,
                    trigger_source_id=f"case:{case_record.id}:notary-handover",
                )
        if data.get("preservation_fee_paid_at") or data.get("preservation_fee_paid") is True:
            owner = lawyer or assistant
            if owner:
                paid_on = _task_rule_date(data.get("preservation_fee_paid_at")) or effective_today
                await _materialize_legacy_case_task(
                    case_record, db, auto_task_type="preservation_deadline", legacy_task_type_id=1001009,
                    title="设定保全期限任务", initiator=lawyer, owner=owner, collaborators=[],
                    description=f"本案{case_record.serial_no}保全费已支付，请设定保全期限.",
                    started_on=effective_today, deadline=effective_today + timedelta(days=7),
                    trigger_at=paid_on, trigger_source_id=f"case:{case_record.id}:preservation",
                )
    task_count_after = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
        BusinessRecord.module == "task",
    )) or 0)
    changed = max(task_count_after - task_count_before, 0)
    # This scheduler routine owns its scan transaction. Completion helpers can
    # flush during notification lookups, so Session.dirty is not a reliable
    # commit gate. Commit every successful scan; failures propagate to the
    # scheduler, whose exception path rolls the whole transaction back.
    await db.commit()
    return changed


async def _next_rw_task_serial_no(db: AsyncSession, *, now: datetime | None = None) -> str:
    """Generate RW-prefixed task serial number: RW + yyMMdd + 4-digit sequence."""
    today = now or datetime.now()
    date_prefix = f"RW{today:%y%m%d}"
    last = await db.scalar(
        select(BusinessRecord.serial_no)
        .where(BusinessRecord.serial_no.like(f"{date_prefix}%"))
        .order_by(BusinessRecord.serial_no.desc())
        .limit(1)
    )
    seq = 1
    if last and len(last) == len(date_prefix) + 4:
        try:
            seq = int(last[-4:]) + 1
        except ValueError:
            seq = 1
    for _ in range(9999):
        if seq > 9999:
            raise HTTPException(status_code=503, detail="今日任务编号已达上限")
        candidate = f"{date_prefix}{seq:04d}"
        if not await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == candidate)):
            return candidate
        seq += 1
    raise HTTPException(status_code=503, detail="任务编号生成失败，请稍后重试")


async def _task_or_404(task_id: int, db: AsyncSession) -> BusinessRecord:
    task = await db.get(BusinessRecord, task_id)
    if not task or task.module != "task":
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


def _is_task_participant(task: BusinessRecord, identity: dict) -> bool:
    data = task.data or {}
    username = identity["username"]
    return identity.get("role") == "admin" or username == task.owner or username == data.get("initiator") or username in data.get("collaborators", [])


async def _advance_case_from_fixed_task(task: BusinessRecord, db: AsyncSession, *, operator: str) -> None:
    data = task.data or {}
    if data.get("task_type") != "固定任务" or task.status != "已验收":
        return
    case_record = await db.get(BusinessRecord, int(data.get("case_id") or 0))
    if not case_record or case_record.module != "case" or case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        return
    targets = {"filing-registration": "一审立案受理", "service-tracking": "一审准备开庭"}
    target = targets.get(str(data.get("fixed_task_key") or ""))
    if not target:
        return
    ranks = {"新案待分配": 0, "文书准备": 1, "一审立案受理": 2, "一审准备开庭": 3, "待上诉": 4, "二审": 5, "执行": 6}
    if ranks.get(target, -1) <= ranks.get(case_record.status, -1):
        return
    previous = case_record.status; case_record.status = target
    case_record.data = {**(case_record.data or {}), "stage_advanced_by_task_id": task.id, "stage_advanced_at": datetime.now().isoformat(timespec="seconds"), "business_stage": "审理" if target == "一审准备开庭" else "立案"}
    db.add(WorkflowEvent(record_id=case_record.id, action="固定任务验收自动推进阶段", from_status=previous, to_status=target, operator=operator, comment=f"任务 {task.serial_no}：{task.title}"))


def _validate_case_event_reminder(*, deadline: date | None, reminder_enabled: bool, remind_at: datetime | None) -> datetime | None:
    from app.core.formatters import (
        _case_event_display_time,
    )
    if not reminder_enabled:
        return None
    if remind_at is None:
        raise HTTPException(status_code=422, detail="启用提醒时必须填写提醒日期")
    if deadline and _case_event_display_time(remind_at).date() > deadline:
        raise HTTPException(status_code=422, detail="提醒日期不能晚于截止日期")
    return remind_at


async def _sync_case_event_reminder(item: CaseEvent, case_record: BusinessRecord, identity: dict, db: AsyncSession) -> None:
    """Project enabled event reminders into the existing ordinary-case reminder module."""
    from app.core.formatters import (
        _case_event_display_time,
    )
    linked = await db.get(BusinessRecord, item.reminder_record_id) if item.reminder_record_id else None
    if linked and (linked.module != "case_reminder" or int((linked.data or {}).get("case_id") or 0) != case_record.id):
        linked = None
        item.reminder_record_id = None
    if not item.reminder_enabled or item.status == CASE_EVENT_COMPLETED_STATUS:
        if linked:
            await db.delete(linked)
        item.reminder_record_id = None
        return
    if item.remind_at is None:
        raise HTTPException(status_code=422, detail="启用提醒时必须填写提醒日期")
    reminder_content = f"[{item.event_type}] {item.content}"
    reminder_data = {
        "case_id": case_record.id,
        "case_no": case_record.serial_no,
        "reminder_date": str(_case_event_display_time(item.remind_at).date()),
        "deadline": str(item.deadline or _case_event_display_time(item.remind_at).date()),
        "case_event_id": item.id,
    }
    if linked:
        linked.title = reminder_content[:255]
        linked.description = reminder_content
        linked.status = "有效"
        linked.data = reminder_data
        return
    linked = BusinessRecord(
        module="case_reminder", serial_no=f"TX{datetime.now():%Y%m%d%H%M%S%f}",
        title=reminder_content[:255], customer=case_record.customer, status="有效",
        owner=identity["username"], department=case_record.department,
        description=reminder_content, data=reminder_data,
    )
    db.add(linked)
    await db.flush()
    item.reminder_record_id = linked.id
