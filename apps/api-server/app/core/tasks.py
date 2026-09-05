"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    CASE_EVENT_COMPLETED_STATUS, logger,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, CaseEvent, ContractApprovalStep, DingTalkError,
    HTTPException, HearingSchedule, IprCaseWarning, Notification, SessionLocal,
    User, VipTask, VipTaskMessage, VipTaskNode, WorkflowEvent,
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
