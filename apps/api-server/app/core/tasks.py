"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.automatic_task_diagnostics import automatic_task_diagnostics_scope

from app.core.constants import (
    CASE_EVENT_COMPLETED_STATUS, logger,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, CaseEvent, ContractApprovalStep, Department,
    HTTPException, HearingSchedule, IprCaseWarning, Notification, SessionLocal,
    User, VipTask, VipTaskMessage, VipTaskNode, WorkflowEvent,
    asyncio, date, datetime, delete,
    func, or_, secrets, select,
    timedelta,
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


async def _automatic_case_conflict_blocked(case_record: BusinessRecord, db: AsyncSession) -> bool:
    """仅阻止已触发审查的案件，不中断尚未进入新流程的历史案件日常任务。"""
    from app.core.conflict_review import get_conflict_review_gate
    return (await get_conflict_review_gate(case_record, db, action="生成自动任务", existing_only=True))["blocking"]


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


def _task_schedule_state(record: BusinessRecord) -> tuple[date | None, int | None, str, bool, str]:
    data = record.data or {}
    try:
        # 历史任务使用 TaskEndTime/task_end_time，新任务使用 deadline，保持同一展示日期。
        raw_deadline = data.get("deadline") or data.get("task_end_time") or data.get("TaskEndTime") or ""
        deadline = date.fromisoformat(str(raw_deadline))
        is_terminal = record.status in {"已拒绝", "已完成", "已验收", "待确认"}
        terminal_at = data.get("rejected_at") if record.status == "已拒绝" else data.get("completion_submitted_at")
        end_date = (date.fromisoformat(str(terminal_at)[:10]) if terminal_at else None) if is_terminal else date.today()
        days_remaining = (deadline - end_date).days if end_date else None
    except ValueError:
        deadline = None
        days_remaining = None
    effective_status = "已完成" if record.status == "待确认" else record.status
    if record.status == "处理中" and str(data.get("source") or "").strip() == "案件任务":
        effective_status = "进行中"
    if days_remaining is not None and days_remaining < 0 and record.status in {"待接收", "待处理", "处理中", "进行中"}:
        effective_status = "已逾期"
    reminder_due = days_remaining in {1, 3} or (days_remaining is not None and days_remaining < 0 and abs(days_remaining) % 3 == 0)
    reminder_text = ""
    if days_remaining in {1, 3}:
        reminder_text = f"{days_remaining} 天后到期"
    elif days_remaining is not None and days_remaining < 0:
        reminder_text = f"已逾期 {abs(days_remaining)} 天" + ("，今日提醒" if reminder_due else "")
    elif days_remaining == 0:
        reminder_text = "今日到期"
    return deadline, days_remaining, effective_status, reminder_due, reminder_text


def _task_dict(record: BusinessRecord) -> dict:
    from app.core.case_automation import requires_phase_completion
    from app.core.system import (
        _explicit_vip_value, _record_dict,
    )
    data = record.data or {}
    raw_case_nos = data.get("case_nos") if isinstance(data.get("case_nos"), list) else []
    case_nos = [str(value).strip() for value in raw_case_nos if str(value).strip()]
    original_case_no = str(data.get("merged_from_case_no") or "").strip()
    if original_case_no and original_case_no not in case_nos:
        case_nos.append(original_case_no)
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
    deadline, days_remaining, effective_status, reminder_due, reminder_text = _task_schedule_state(record)
    workflow_status = record.status
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
        "phase_completion_required": requires_phase_completion(record),
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


def _is_task_notification_recipient(task: BusinessRecord, username: str) -> bool:
    data = task.data or {}
    return username in {
        task.owner,
        str(data.get("initiator") or ""),
        *(str(value) for value in (data.get("collaborators") or [])),
    }


def _notification_dict(
    item: Notification,
    users_by_username: dict[str, User] | None = None,
    records_by_id: dict[int, BusinessRecord] | None = None,
) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    users = users_by_username or {}
    source_record = (records_by_id or {}).get(item.source_id or 0)
    content = item.content
    source_key = str(item.source_key or "")
    if source_key.startswith("contract-approval-"):
        target_route = "contract-audit"
    elif source_key.startswith("finance-approval-"):
        target_route = "finance-audit"
    elif item.source_type == "case":
        target_route = "case-mine"
    elif item.source_type == "feedback":
        target_route = "feedback"
    elif item.source_type == "task":
        target_route = "task-my-accepted"
        if source_record and source_record.module == "task":
            from app.core.investigation import _is_investigation_task

            task_data = source_record.data or {}
            if _is_investigation_task(source_record):
                target_route = "investigation-task-sub-published" if task_data.get("initiator") == item.recipient else "investigation-task-sub-mine"
            elif source_record.owner != item.recipient:
                target_route = "task-my-created" if task_data.get("initiator") == item.recipient else "task-my-collaborating"
            if source_key.startswith("task-") and not source_key.startswith(("task-message-", "task-history-")) and "｜负责人：" in content:
                owner_name = _person_reference_display(source_record.owner, users)[0]
                content = content.rsplit("｜负责人：", 1)[0] + f"｜负责人：{owner_name}"
    elif item.source_type == "contract":
        target_route = "contract-mine"
    elif item.source_type in {"finance", "finance_package", "finance_settlement", "finance_archive_settlement"}:
        target_route = "finance-fee-query"
    elif item.source_type in {"clue", "notary", "evidence"}:
        target_route = item.source_type
    else:
        target_route = ""
    return {
        "id": item.id, "source_type": item.source_type, "source_id": item.source_id,
        "source_serial_no": source_record.serial_no if source_record else "",
        "sender": item.sender, "sender_display_name": _person_reference_display(item.sender, users)[0],
        "recipient": item.recipient, "recipient_display_name": _person_reference_display(item.recipient, users)[0],
        "notification_type": item.notification_type, "title": item.title, "content": content,
        "level": item.level, "is_read": item.is_read, "read_at": item.read_at,
        "dingtalk_status": item.dingtalk_status, "dingtalk_sent_at": item.dingtalk_sent_at, "created_at": item.created_at,
        "target_route": target_route,
    }


async def _dispatch_dingtalk_notifications() -> None:
    from app.core.notification_delivery import (
        dispatch_one, enqueue_dingtalk_notifications, mark_expired_claims_unknown,
    )

    await mark_expired_claims_unknown()
    async with SessionLocal() as db:
        await enqueue_dingtalk_notifications(db)
    for _ in range(50):
        if not await dispatch_one("dingtalk"):
            break


async def _dingtalk_notification_loop() -> None:
    while True:
        try:
            await _dispatch_dingtalk_notifications()
        except Exception:
            logger.exception("DingTalk notification loop failed")
        await asyncio.sleep(10)


async def _sync_notifications(identity: dict, db: AsyncSession) -> None:
    from app.core.query_batches import _scalars_in_batches
    from app.core.ipr import (
        _materialize_ipr_case_warnings,
    )
    from app.core.permissions import (
        _record_scope_conditions,
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
    tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task", BusinessRecord.owner == username,
        or_(BusinessRecord.status.is_(None), BusinessRecord.status.not_in(task_terminal_statuses)),
    ))).all())
    from app.core.notification_policy import case_fee_condition, visible_notification_condition

    stale = (await db.scalars(select(Notification).where(Notification.recipient == username, Notification.source_type.in_(["task", "finance", "contract", "case", "ipr_warning"]), visible_notification_condition()))).all()
    records_by_id = {
        record.id: record
        for record in await _scalars_in_batches(
            db, {notice.source_id for notice in stale if notice.source_id},
            lambda batch: select(BusinessRecord).where(BusinessRecord.id.in_(batch)),
        )
    } if stale else {}
    existing_record_ids = set(records_by_id)
    visible_task_ids = {
        task.id for task in records_by_id.values()
        if task.module == "task" and _is_task_notification_recipient(task, username)
    }
    terminal_task_ids = {
        task.id for task in records_by_id.values()
        if task.module == "task" and task.status in task_terminal_statuses
    }
    if identity.get("role") != "admin":
        scope_conditions = await _record_scope_conditions(identity, db)
        visible_ids = set(await _scalars_in_batches(
            db, existing_record_ids,
            lambda batch: select(BusinessRecord.id).where(
                BusinessRecord.id.in_(batch), *scope_conditions,
            ),
        ))
    else:
        visible_ids = existing_record_ids
    current_steps = (await db.execute(
        select(ContractApprovalStep, BusinessRecord)
        .join(BusinessRecord, BusinessRecord.id == ContractApprovalStep.contract_record_id)
        .where(ContractApprovalStep.status == "待审批", ContractApprovalStep.approver == username, BusinessRecord.status == "审批中")
    )).all()
    valid_contract_approval_keys = {
        key
        for step, contract in current_steps
        for key in (
            f"contract-approval-{contract.id}-{step.id}",
            f"contract-approval-{contract.id}-{step.id}-{username}",
        )
    }
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
        source_record = records_by_id.get(notice.source_id)
        if notice.source_type == "task" and source_record and notice.source_id not in visible_task_ids:
            await db.delete(notice)
            continue
        if notice.source_type == "task" and is_auto_reminder and source_record and source_record.owner != username:
            await db.delete(notice)
            continue
        if notice.source_type == "contract" and notice.source_key.startswith("contract-approval-") and notice.source_key not in valid_contract_approval_keys:
            await db.delete(notice)
            continue
        if notice.source_type == "finance" and source_record:
            source_data = source_record.data or {}
            responsible = {
                source_record.owner,
                str(source_data.get("approver") or "").strip(),
                str(source_data.get("current_approver") or "").strip(),
            }
            if username not in responsible:
                await db.delete(notice)
                continue
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
    fees = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance", BusinessRecord.status == "待审批", ~case_fee_condition(), *(await _record_scope_conditions(identity, db))))).all()
    fees = [fee for fee in fees if username in {
        fee.owner,
        str((fee.data or {}).get("approver") or "").strip(),
        str((fee.data or {}).get("current_approver") or "").strip(),
    }]
    for fee in fees:
        candidates.append({"source_key": f"finance-approval-{fee.id}-{username}", "source_type": "finance", "source_id": fee.id, "title": "费用待审批", "content": f"{fee.serial_no}｜{fee.title}｜{(fee.data or {}).get('amount', 0)} 元", "level": "warning"})
    for step, contract in current_steps:
        candidates.append({"source_key": f"contract-approval-{contract.id}-{step.id}-{username}", "source_type": "contract", "source_id": contract.id, "title": f"合同第 {step.step_order} 级待审批", "content": f"{contract.serial_no}｜{contract.title}｜审批人：{step.approver}", "level": "warning"})
    hearings = (await db.execute(select(HearingSchedule, BusinessRecord).join(BusinessRecord, BusinessRecord.id == HearingSchedule.case_record_id).where(HearingSchedule.hearing_date == today + timedelta(days=1), HearingSchedule.status == "已排期", *(await _record_scope_conditions(identity, db))))).all()
    for hearing, case_record in hearings:
        case_data = case_record.data or {}
        responsible = {
            case_record.owner,
            str(hearing.hearing_lawyer or "").strip(),
            str(case_data.get("assistant_username") or case_data.get("assistant") or "").strip(),
            str(case_data.get("investigator_username") or case_data.get("investigator") or "").strip(),
            *(str(value).strip() for value in (case_data.get("handling_lawyer_usernames") or []) if str(value).strip()),
        }
        if username not in responsible:
            continue
        candidates.append({"source_key": f"hearing-{hearing.id}-{hearing.hearing_date}-{username}", "source_type": "case", "source_id": case_record.id, "title": "明日开庭提醒", "content": f"{case_record.serial_no}｜{hearing.hearing_time}｜{hearing.court}｜{hearing.hearing_lawyer}", "level": "info"})
    existing_keys = set((await db.scalars(select(Notification.source_key).where(Notification.source_key.in_([x["source_key"] for x in candidates])))).all()) if candidates else set()
    for item in candidates:
        if item["source_key"] not in existing_keys: db.add(Notification(**item, recipient=username))
    await db.commit()


async def _apply_task_auto_completion(db: AsyncSession) -> bool:
    """处理已完成任务的自动验收及既有仓库流转，不自动完成待接收任务。"""
    from app.core.query_batches import _scalars_in_batches

    # 这些终止状态既不交接、也不自动验收或流转仓库；空状态沿用历史处理路径。
    inactive_statuses = {"已拒绝", "已撤回", "已停止", "已取消"}
    tasks = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task",
        or_(BusinessRecord.status.is_(None), BusinessRecord.status.not_in(inactive_statuses)),
    ))).all()
    # 同一负责人通常拥有多条任务，批量读取避免每次刷新逐任务查询账号。
    owners = await _scalars_in_batches(
        db, {task.owner for task in tasks},
        lambda batch: select(User).where(User.username.in_(batch)),
    )
    owners_by_username = {user.username: user for user in owners}
    changed = False
    for task in tasks:
        data = task.data or {}
        owner_user = owners_by_username.get(task.owner)
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
                previous_data = evidence.data or {}
                next_data = {**previous_data, "evidence_status": target, "automatic_task_id": task.id}
                if next_data != previous_data:
                    evidence.data = next_data
                    changed = True
    if changed:
        await db.commit()
    return changed


async def _apply_task_overdue_performance(db: AsyncSession) -> bool:
    """Persist overdue facts so performance reports do not depend on a page being open."""
    terminal = {"已完成", "待确认", "已验收", "已拒绝", "已撤回", "已停止", "已取消"}
    tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task",
        or_(BusinessRecord.status.is_(None), BusinessRecord.status.not_in(terminal)),
    ))).all())
    changed = False
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


from app.core.hearing_reminders import _apply_hearing_sms_reminders as _apply_hearing_sms_reminders


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


async def _record_task_manual_intervention(
    task: BusinessRecord, identity: dict, db: AsyncSession, *, action: str,
    completion_override: bool = False,
) -> None:
    """仅在专用入口校验通过后，保存自动任务的人工操作阶段快照。"""
    if _task_creation_mode(task.data or {}) != "自动":
        return
    data = task.data or {}
    case_id = data.get("case_record_id") or data.get("case_id")
    if not case_id:
        return
    case_record = await db.get(BusinessRecord, int(case_id))
    if not case_record or case_record.module not in {"case", "ipr_case"}:
        raise HTTPException(status_code=409, detail="自动任务关联案件不存在，不能记录人工干预")
    phase_changed_at = str((case_record.data or {}).get("phase_changed_at") or "")
    previous = data.get("manual_intervention") or {}
    # 普通接收和维护只记审计，不停用自动完成；同阶段保留已明确的退回重启意图。
    retain_override = (
        previous.get("completion_override") is True
        and previous.get("case_id") == case_record.id
        and previous.get("case_stage") == case_record.status
        and previous.get("phase_changed_at") == phase_changed_at
    )
    task.data = {
        **data,
        "manual_intervention": {
            "action": action,
            "operator": identity["username"],
            "at": datetime.now().isoformat(timespec="seconds"),
            "case_id": case_record.id,
            "case_stage": case_record.status,
            "phase_changed_at": phase_changed_at,
            "completion_override": completion_override or retain_override,
        },
    }


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
    from app.core.automatic_task_lookup import find_automatic_task, remember_automatic_task

    existing = await find_automatic_task(db, case_record.id, auto_task_type, trigger_source_id)
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
    remember_automatic_task(db, case_record.id, auto_task_type, trigger_source_id, task.id)
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


async def _finish_legacy_auto_task(task: BusinessRecord, db: AsyncSession, *, reason: str) -> bool:
    if task.status in {"已完成", "待确认", "已验收", "已拒绝", "已撤回", "已停止", "已取消"}:
        return False
    previous = task.status
    task.status = "已完成"
    task.data = {
        **(task.data or {}), "auto_completed": True,
        "auto_completed_at": str(date.today()),
        "completion_auto_confirm_at": str(date.today() + timedelta(days=5)),
    }
    await _add_task_message_notifications(
        task,
        WorkflowEvent(record_id=task.id, action="业务状态联动自动完成", from_status=previous, to_status="已完成", operator="system", comment=reason),
        db,
        content=reason,
    )
    return True


async def _apply_case_automatic_task_rules(db: AsyncSession, *, today: date | None = None) -> int:
    from app.core.case_automation import scan_confirmed_case_rules

    async with automatic_task_diagnostics_scope():
        return await scan_confirmed_case_rules(db, today=today)


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
    from app.core.case_automation import case_progress_rank
    if case_progress_rank(target) <= case_progress_rank(case_record.status):
        return
    from app.core.conflict_review import require_conflict_clear
    await require_conflict_clear(case_record, db, action="通过固定任务推进案件阶段", existing_only=True)
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
