"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    UPLOAD_ROOT, VIP_TASK_PRIORITIES, VIP_TASK_STATUSES,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, File, FileAttachment,
    Form, HTTPException, Notification, Path, Query,
    Response, UploadFile, User, VipTask, VipTaskMessage,
    VipTaskNode, WorkflowEvent, current_identity, date, datetime,
    delete, func, get_db, or_, select,
    settings, status, timedelta, timezone, uuid4,
)
from app.models_shared import (
    TaskActionInput, TaskBatchLifecycleInput, TaskBatchReadInput, TaskBatchUpdateInput, TaskExceptionRequestInput,
    TaskExceptionReviewInput, TaskHandoffInput, TaskInput, VipTaskInput, VipTaskMessageInput,
    VipTaskMessageReadInput, VipTaskNodeInput, VipTaskNodeUpdateInput, VipTaskUpdateInput,
)
from fastapi import APIRouter

router = APIRouter()


@router.get(f"{settings.api_prefix}/tasks/print-export")
async def export_task_print_table(ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _scoped_export_records,
    )
    from app.core.system import (
        _csv_response,
    )
    records = await _scoped_export_records("task", ids, identity, db)
    rows = []
    for item in records:
        data = item.data or {}
        rows.append([item.serial_no, data.get("case_no", ""), item.title, item.description, item.customer, data.get("plaintiff", ""), data.get("defendant", ""), item.status, data.get("priority", ""), data.get("initiator", ""), item.owner, data.get("deadline", ""), data.get("source", "")])
    return _csv_response(f"案件任务打印表-{date.today()}.csv", ["任务编号", "案件编号", "任务标题", "任务内容", "客户", "原告", "被告", "状态", "优先级", "发起人", "负责人", "截止日期", "任务来源"], rows)


@router.get(f"{settings.api_prefix}/vip-tasks")
async def list_vip_tasks(
    keyword: str = "", customer: str = "", status_filter: str = "", priority: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.tasks import (
        _vip_task_member, _vip_task_response,
    )
    conditions = []
    if identity.get("role") != "admin":
        username = identity["username"]
        # JSON participant membership is normalized after fetch for SQLite/PostgreSQL parity.
        candidates = list((await db.scalars(select(VipTask).order_by(VipTask.updated_at.desc(), VipTask.id.desc()))).all())
        tasks = [task for task in candidates if _vip_task_member(task, identity)]
    else:
        tasks = list((await db.scalars(select(VipTask).order_by(VipTask.updated_at.desc(), VipTask.id.desc()))).all())
    needle = keyword.strip().casefold()
    customer_needle = customer.strip().casefold()
    tasks = [task for task in tasks if (
        (not needle or needle in f"{task.serial_no} {task.title} {task.customer} {task.description}".casefold())
        and (not customer_needle or customer_needle in task.customer.casefold())
        and (not status_filter or task.status == status_filter)
        and (not priority or task.priority == priority)
    )]
    total = len(tasks); start = (page - 1) * page_size
    return {"items": [await _vip_task_response(task, identity, db) for task in tasks[start:start + page_size]], "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size if total else 0}


@router.post(f"{settings.api_prefix}/vip-tasks", status_code=status.HTTP_201_CREATED)
async def create_vip_task(body: VipTaskInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _vip_active_usernames, _vip_validate_schedule,
    )
    from app.core.tasks import (
        _active_task_username, _vip_task_response,
    )
    if body.status not in VIP_TASK_STATUSES or body.priority not in VIP_TASK_PRIORITIES:
        raise HTTPException(status_code=422, detail="VIP任务状态或优先级无效")
    if body.status != "待处理":
        raise HTTPException(status_code=422, detail="新建VIP任务必须从待处理开始")
    _vip_validate_schedule(body.start_at, body.deadline, body.end_at)
    owner = await _active_task_username(body.owner, db, field_name="VIP任务负责人")
    collaborators = await _vip_active_usernames(body.collaborators, db, owner=owner)
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    task = VipTask(serial_no=f"VIP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}", title=body.title.strip(), customer=body.customer.strip(), status=body.status, priority=body.priority, owner=owner, department=user.department if user else "", description=body.description.strip(), collaborators=collaborators, created_by=identity["username"], start_at=body.start_at, deadline=body.deadline, end_at=body.end_at)
    db.add(task); await db.flush()
    recipients = {owner, *collaborators} - {identity["username"]}
    for recipient in recipients:
        db.add(VipTaskMessage(vip_task_id=task.id, sender=identity["username"], recipient=recipient, content=f"已向您分派VIP任务：{task.title}"))
    await db.commit(); await db.refresh(task)
    return await _vip_task_response(task, identity, db)


@router.get(f"{settings.api_prefix}/vip-tasks/{{task_id}}")
async def get_vip_task(task_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _vip_message_dict, _vip_node_dict, _vip_node_member,
    )
    from app.core.tasks import (
        _vip_task_or_404, _vip_task_response,
    )
    task = await _vip_task_or_404(task_id, identity, db)
    result = await _vip_task_response(task, identity, db)
    nodes = list((await db.scalars(select(VipTaskNode).where(VipTaskNode.vip_task_id == task.id).order_by(VipTaskNode.created_at, VipTaskNode.id))).all())
    messages = list((await db.scalars(select(VipTaskMessage).where(VipTaskMessage.vip_task_id == task.id, or_(VipTaskMessage.recipient == identity["username"], VipTaskMessage.sender == identity["username"])).order_by(VipTaskMessage.created_at.desc(), VipTaskMessage.id.desc()))).all())
    result.update({"nodes": [_vip_node_dict(node) for node in nodes if _vip_node_member(node, identity)], "messages": [_vip_message_dict(message) for message in messages]})
    return result


@router.put(f"{settings.api_prefix}/vip-tasks/{{task_id}}")
async def update_vip_task(task_id: int, body: VipTaskUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _vip_active_usernames, _vip_validate_schedule,
    )
    from app.core.tasks import (
        _active_task_username, _vip_task_or_404, _vip_task_response, _vip_validate_task_transition,
    )
    task = await _vip_task_or_404(task_id, identity, db, write=True)
    updates = body.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] not in VIP_TASK_STATUSES or "priority" in updates and updates["priority"] not in VIP_TASK_PRIORITIES:
        raise HTTPException(status_code=422, detail="VIP任务状态或优先级无效")
    if "status" in updates:
        await _vip_validate_task_transition(task, updates["status"], identity, db)
    owner = await _active_task_username(updates["owner"], db, field_name="VIP任务负责人") if "owner" in updates else task.owner
    collaborators = await _vip_active_usernames(updates["collaborators"], db, owner=owner) if "collaborators" in updates else task.collaborators
    _vip_validate_schedule(updates.get("start_at", task.start_at), updates.get("deadline", task.deadline), updates.get("end_at", task.end_at))
    for field in ("title", "customer", "status", "priority", "start_at", "deadline", "end_at", "description"):
        if field in updates: setattr(task, field, updates[field].strip() if isinstance(updates[field], str) else updates[field])
    task.owner = owner; task.collaborators = collaborators
    await db.commit(); await db.refresh(task)
    return await _vip_task_response(task, identity, db)


@router.delete(f"{settings.api_prefix}/vip-tasks/{{task_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vip_task(task_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _vip_task_or_404,
    )
    task = await _vip_task_or_404(task_id, identity, db, write=True)
    # SQLite does not enable foreign-key cascades on every local connection;
    # delete child rows explicitly so the command has identical semantics in
    # local verification and PostgreSQL deployments.
    await db.execute(delete(VipTaskMessage).where(VipTaskMessage.vip_task_id == task.id))
    await db.execute(delete(VipTaskNode).where(VipTaskNode.vip_task_id == task.id))
    await db.delete(task); await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/vip-tasks/{{task_id}}/nodes")
async def list_vip_task_nodes(task_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _vip_node_dict, _vip_node_member,
    )
    from app.core.tasks import (
        _vip_task_or_404,
    )
    task = await _vip_task_or_404(task_id, identity, db)
    nodes = list((await db.scalars(select(VipTaskNode).where(VipTaskNode.vip_task_id == task.id).order_by(VipTaskNode.created_at, VipTaskNode.id))).all())
    return {"items": [_vip_node_dict(node) for node in nodes if _vip_node_member(node, identity)]}


@router.post(f"{settings.api_prefix}/vip-tasks/{{task_id}}/nodes", status_code=status.HTTP_201_CREATED)
async def create_vip_task_node(task_id: int, body: VipTaskNodeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _vip_active_usernames, _vip_node_dict, _vip_validate_schedule,
    )
    from app.core.tasks import (
        _active_task_username, _vip_task_or_404,
    )
    task = await _vip_task_or_404(task_id, identity, db, write=True)
    if body.status not in VIP_TASK_STATUSES or body.priority not in VIP_TASK_PRIORITIES:
        raise HTTPException(status_code=422, detail="VIP节点状态或优先级无效")
    if body.status != "待处理":
        raise HTTPException(status_code=422, detail="新建VIP节点必须从待处理开始")
    _vip_validate_schedule(body.start_at, body.deadline, body.end_at)
    owner = await _active_task_username(body.owner, db, field_name="VIP节点负责人")
    node = VipTaskNode(vip_task_id=task.id, title=body.title.strip(), owner=owner, priority=body.priority, status=body.status, start_at=body.start_at, deadline=body.deadline, end_at=body.end_at, description=body.description.strip(), participants=await _vip_active_usernames(body.participants, db, owner=owner), created_by=identity["username"])
    db.add(node); await db.commit(); await db.refresh(node)
    return _vip_node_dict(node)


@router.put(f"{settings.api_prefix}/vip-tasks/{{task_id}}/nodes/{{node_id}}")
async def update_vip_task_node(task_id: int, node_id: int, body: VipTaskNodeUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _vip_active_usernames, _vip_node_dict, _vip_node_or_404, _vip_validate_node_transition, _vip_validate_schedule,
    )
    from app.core.tasks import (
        _active_task_username, _vip_task_or_404,
    )
    task = await _vip_task_or_404(task_id, identity, db)
    node = await _vip_node_or_404(task, node_id, identity, db, write=True); updates = body.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] not in VIP_TASK_STATUSES or "priority" in updates and updates["priority"] not in VIP_TASK_PRIORITIES:
        raise HTTPException(status_code=422, detail="VIP节点状态或优先级无效")
    if "status" in updates:
        _vip_validate_node_transition(node, updates["status"], identity)
    owner = await _active_task_username(updates["owner"], db, field_name="VIP节点负责人") if "owner" in updates else node.owner
    participants = await _vip_active_usernames(updates["participants"], db, owner=owner) if "participants" in updates else node.participants
    _vip_validate_schedule(updates.get("start_at", node.start_at), updates.get("deadline", node.deadline), updates.get("end_at", node.end_at))
    for field in ("title", "status", "priority", "start_at", "deadline", "end_at", "description"):
        if field in updates: setattr(node, field, updates[field].strip() if isinstance(updates[field], str) else updates[field])
    node.owner = owner; node.participants = participants
    await db.commit(); await db.refresh(node); return _vip_node_dict(node)


@router.delete(f"{settings.api_prefix}/vip-tasks/{{task_id}}/nodes/{{node_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vip_task_node(task_id: int, node_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _vip_node_or_404,
    )
    from app.core.tasks import (
        _vip_task_or_404,
    )
    task = await _vip_task_or_404(task_id, identity, db); node = await _vip_node_or_404(task, node_id, identity, db, write=True)
    await db.execute(delete(VipTaskMessage).where(VipTaskMessage.vip_task_node_id == node.id))
    await db.delete(node); await db.commit(); return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/vip-tasks/{{task_id}}/messages")
async def list_vip_task_messages(task_id: int, unread_only: bool = False, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _vip_message_dict,
    )
    from app.core.tasks import (
        _vip_task_or_404,
    )
    task = await _vip_task_or_404(task_id, identity, db)
    conditions = [VipTaskMessage.vip_task_id == task.id, or_(VipTaskMessage.recipient == identity["username"], VipTaskMessage.sender == identity["username"])]
    if unread_only: conditions.extend([VipTaskMessage.recipient == identity["username"], VipTaskMessage.is_read.is_(False)])
    messages = list((await db.scalars(select(VipTaskMessage).where(*conditions).order_by(VipTaskMessage.created_at.desc(), VipTaskMessage.id.desc()))).all())
    unread = int(await db.scalar(select(func.count()).select_from(VipTaskMessage).where(VipTaskMessage.vip_task_id == task.id, VipTaskMessage.recipient == identity["username"], VipTaskMessage.is_read.is_(False))) or 0)
    return {"items": [_vip_message_dict(message) for message in messages], "unread_count": unread}


@router.post(f"{settings.api_prefix}/vip-tasks/{{task_id}}/messages", status_code=status.HTTP_201_CREATED)
async def create_vip_task_message(task_id: int, body: VipTaskMessageInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _vip_active_usernames, _vip_message_dict, _vip_node_or_404,
    )
    from app.core.tasks import (
        _vip_task_or_404,
    )
    task = await _vip_task_or_404(task_id, identity, db)
    node = await _vip_node_or_404(task, body.node_id, identity, db) if body.node_id else None
    task_recipients = {task.created_by, task.owner, *(str(value) for value in (task.collaborators or []))} - {""}
    if node: task_recipients.update({node.created_by, node.owner, *(str(value) for value in (node.participants or []))} - {""})
    recipients = set(body.recipients) if body.recipients else task_recipients - {identity["username"]}
    if not recipients.issubset(task_recipients): raise HTTPException(status_code=403, detail="消息收件人必须是VIP任务参与人")
    if recipients:
        active = set(await _vip_active_usernames(list(recipients), db))
        rows = [VipTaskMessage(vip_task_id=task.id, vip_task_node_id=node.id if node else None, sender=identity["username"], recipient=recipient, content=body.content.strip()) for recipient in active]
        db.add_all(rows); await db.commit()
        for row in rows: await db.refresh(row)
        return {"items": [_vip_message_dict(row) for row in rows]}
    await db.commit(); return {"items": []}


@router.post(f"{settings.api_prefix}/vip-tasks/{{task_id}}/messages/read")
async def read_vip_task_messages(task_id: int, body: VipTaskMessageReadInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _vip_task_or_404,
    )
    task = await _vip_task_or_404(task_id, identity, db)
    conditions = [VipTaskMessage.vip_task_id == task.id, VipTaskMessage.recipient == identity["username"], VipTaskMessage.is_read.is_(False)]
    if body.message_ids: conditions.append(VipTaskMessage.id.in_(set(body.message_ids)))
    messages = list((await db.scalars(select(VipTaskMessage).where(*conditions))).all())
    now = datetime.now(timezone.utc)
    for message in messages: message.is_read = True; message.read_at = now
    await db.commit(); return {"updated": len(messages)}


@router.get(f"{settings.api_prefix}/tasks")
async def list_tasks(
    keyword: str = "", status_filter: str = "", reminder_only: bool = False, scope: str = "default",
    relation: str = Query("", pattern="^(|initiated|owned|collaborating)$"), statuses: str = "",
    page_id: str | None = Query(None, description="legacy TaskController PageId"),
    priority: str = "", serial_no: str = "", title: str = "", description: str = "",
    initiator: str = "", case_no: str = "", source: str = "", owner: str = "",
    plaintiff: str = "", defendant: str = "",
    created_from: date | None = None, created_to: date | None = None,
    deadline_from: date | None = None, deadline_to: date | None = None,
    sort_by: str = Query("deadline", pattern="^(created_at|deadline|days_remaining|updated_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.formatters import (
            _task_display_dicts,
        )
    from app.core.investigation import (
            _is_investigation_task,
        )
    from app.core.permissions import (
            _require_company_task_read_scope,
        )
    from app.core.tasks import (
            _apply_task_auto_completion, _apply_task_overdue_performance,
        )
    await _apply_task_auto_completion(db)
    await _apply_task_overdue_performance(db)
    legacy_page_map = {
        "9001001010": ("default", "initiated"), "9001002010": ("department", "initiated"),
        "9001003010": ("company", "initiated"), "9001001020": ("default", "owned"),
        "9001002020": ("department", "owned"), "9001001030": ("default", "collaborating"),
        "9001002030": ("department", "collaborating"),
    }
    if page_id is not None:
        mapped = legacy_page_map.get(str(page_id).strip())
        if not mapped:
            raise HTTPException(status_code=422, detail="无效的任务页面")
        scope, relation = mapped
    if scope not in {"default", "mine", "department", "company"}: raise HTTPException(status_code=422, detail="无效的任务范围")
    if scope == "company":
        await _require_company_task_read_scope(identity, db, relation)
    if created_from and created_to and created_from > created_to: raise HTTPException(status_code=422, detail="发起开始日期不能晚于结束日期")
    if deadline_from and deadline_to and deadline_from > deadline_to: raise HTTPException(status_code=422, detail="截止开始日期不能晚于结束日期")
    # Apply participant visibility in SQL before any Python filtering/pagination.
    # This is the stable equivalent of TaskController's PageId relation matrix:
    # initiated -> data.initiator, accepted/owned -> owner, collaborating ->
    # the serialized collaborators array.  The later relation branch preserves
    # explicit legacy query semantics while this candidate query prevents an
    # unrelated task from entering the in-memory page window.
    task_conditions = [BusinessRecord.module == "task"]
    if scope in {"mine", "default"}:
        username_token = f'"{identity["username"]}"'
        task_conditions.append(or_(
            BusinessRecord.owner == identity["username"],
            BusinessRecord.data["initiator"].as_string() == identity["username"],
            BusinessRecord.data["collaborators"].as_string().contains(username_token),
        ))
    elif scope == "department":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if not user:
            raise HTTPException(status_code=401, detail="current user does not exist")
        department_usernames = set((await db.scalars(select(User.username).where(User.department == user.department))).all())
        department_tokens = [BusinessRecord.data["collaborators"].as_string().contains(f'"{name}"') for name in department_usernames]
        task_conditions.append(or_(
            BusinessRecord.department == user.department,
            BusinessRecord.owner.in_(department_usernames),
            BusinessRecord.data["initiator"].as_string().in_(department_usernames),
            *department_tokens,
        ))
    tasks = list((await db.scalars(select(BusinessRecord).where(*task_conditions).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    if scope in {"mine", "default"}:
        username = identity["username"]
        tasks = [task for task in tasks if task.owner == username or (task.data or {}).get("initiator") == username or username in (task.data or {}).get("collaborators", [])]
    elif scope == "department":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if not user:
            raise HTTPException(status_code=401, detail="current user does not exist")
        department_usernames = set((await db.scalars(select(User.username).where(
            User.department == user.department,
        ))).all())
        if relation == "owned":
            tasks = [task for task in tasks if task.owner in department_usernames]
        elif relation == "collaborating":
            tasks = [task for task in tasks if department_usernames.intersection((task.data or {}).get("collaborators", []))]
        else:
            tasks = [task for task in tasks if (task.data or {}).get("initiator") in department_usernames]
    username = identity["username"]
    if scope == "company":
        # Company initiated/accepted views include every company task.  The
        # collaboration view is the company-wide subset with collaborators,
        # independent of which employee is currently signed in.
        if relation == "collaborating":
            tasks = [task for task in tasks if (task.data or {}).get("collaborators", [])]
    elif scope != "department":
        # Personal entries are always about the signed-in user, including for
        # administrators.  Company-wide visibility requires scope=company.
        if relation == "initiated":
            tasks = [task for task in tasks if (task.data or {}).get("initiator") == username]
        elif relation == "owned":
            tasks = [task for task in tasks if task.owner == username]
        elif relation == "collaborating":
            tasks = [task for task in tasks if username in (task.data or {}).get("collaborators", [])]
    tasks = [task for task in tasks if not _is_investigation_task(task)]
    items = await _task_display_dicts(tasks, db)
    if relation == "initiated":
        for item in items:
            if item.get("workflow_status") in {"待接收", "待处理"} and item.get("source") == "案件任务":
                item["status"] = "进行中"
    all_task_items = list(items)

    def contains(value: object, needle: str) -> bool:
        return not needle.strip() or needle.strip().casefold() in str(value or "").casefold()

    if keyword:
        key = keyword.lower()
        items = [item for item in items if key in (
            f"{item['serial_no']} {item['title']} {item['customer']} "
            f"{item['owner']} {item.get('owner_display_name', '')} "
            f"{item.get('initiator', '')} {item.get('initiator_display_name', '')}"
        ).lower()]
    items = [item for item in items if
        contains(item.get("priority"), priority)
        and contains(item.get("serial_no"), serial_no)
        and contains(item.get("title"), title)
        and contains(item.get("description"), description)
        and contains(f"{item.get('initiator', '')} {item.get('initiator_display_name', '')}", initiator)
        and contains(" ".join(item.get("case_nos") or [item.get("case_no", "")]), case_no)
        and contains(item.get("creation_mode") if source in {"自动", "人工"} else item.get("source"), source)
        and contains(f"{item.get('owner', '')} {item.get('owner_display_name', '')}", owner)
        and contains(item.get("plaintiff"), plaintiff)
        and contains(item.get("defendant"), defendant)
    ]
    if created_from:
        items = [item for item in items if item.get("created_at") and item["created_at"].date() >= created_from]
    if created_to:
        items = [item for item in items if item.get("created_at") and item["created_at"].date() <= created_to]
    if deadline_from:
        items = [item for item in items if item.get("deadline") and item["deadline"] >= deadline_from]
    if deadline_to:
        items = [item for item in items if item.get("deadline") and item["deadline"] <= deadline_to]
    reverse_sort = sort_order == "desc"
    # 先按 ID 做稳定次排序，再按所选字段排序；空值始终位于末尾。
    items.sort(key=lambda item: item["id"], reverse=reverse_sort)
    populated = [item for item in items if item.get(sort_by) is not None and item.get(sort_by) != ""]
    missing = [item for item in items if item.get(sort_by) is None or item.get(sort_by) == ""]
    populated.sort(key=lambda item: item[sort_by], reverse=reverse_sort)
    items = populated + missing
    if reminder_only:
        items = [item for item in items if item["reminder_due"]]
    status_counts: dict[str, int] = {}
    for item in items:
        status_name = str(item.get("status") or "")
        status_counts[status_name] = status_counts.get(status_name, 0) + 1
    selected_statuses = {value.strip() for value in statuses.split(",") if value.strip()}
    if selected_statuses.intersection({"处理中", "进行中"}):
        selected_statuses.update({"处理中", "进行中"})
    if selected_statuses:
        items = [item for item in items if item["status"] in selected_statuses]
    if status_filter:
        items = [item for item in items if item["status"] == status_filter]
    all_items = all_task_items
    if reminder_only:
        all_items = [item for item in all_items if item["reminder_due"]]
    total = len(items)
    effective_page_size = page_size
    pages = (total + effective_page_size - 1) // effective_page_size if total else 0
    start = (page - 1) * effective_page_size
    items = items[start:start + effective_page_size]
    return {
        "items": items, "total": total, "page": page, "page_size": effective_page_size,
        "pages": pages,
        "status_counts": status_counts,
        "summary": {
            "total": len(all_items),
            "pending": sum(1 for item in all_items if item["status"] in {"待接收", "待处理"}),
            "processing": sum(1 for item in all_items if item["status"] in {"处理中", "进行中"}),
            "awaiting_confirmation": sum(1 for item in all_items if item["status"] == "已完成"),
            "due_soon": sum(1 for item in all_items if item["days_remaining"] in {0, 1} and item["status"] not in {"已完成", "已撤回"}),
            "overdue": sum(1 for item in all_items if item["status"] == "已逾期"),
            "reminders": sum(1 for item in all_items if item["reminder_due"]),
        },
    }


@router.get(f"{settings.api_prefix}/tasks/unread-messages")
async def list_unread_task_messages(
    priority: str = "", serial_no: str = "", title: str = "", description: str = "",
    initiator: str = "", case_no: str = "", source: str = "", owner: str = "",
    plaintiff: str = "", defendant: str = "",
    created_from: date | None = None, created_to: date | None = None,
    deadline_from: date | None = None, deadline_to: date | None = None,
    sort_by: str = Query("", pattern="^(|created_at|deadline|days_remaining|updated_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Aggregate the current recipient's unread task communication messages.

    Administrator visibility is intentionally not expanded here: unread state is
    personal, so even an administrator only sees notifications addressed to that
    administrator.  The task record itself still uses the normal participant
    guard for non-administrators.
    """
    from app.core.formatters import (
        _person_reference_display, _task_display_dicts, _user_display_map,
    )
    from app.core.tasks import (
        _is_task_participant,
    )
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="发起开始日期不能晚于结束日期")
    if deadline_from and deadline_to and deadline_from > deadline_to:
        raise HTTPException(status_code=422, detail="截止开始日期不能晚于结束日期")

    notices = list((await db.scalars(
        select(Notification).where(
            Notification.recipient == identity["username"],
            Notification.recipient_deleted.is_(False),
            Notification.is_read.is_(False),
            Notification.source_type == "task",
            Notification.source_id.is_not(None),
            or_(
                Notification.source_key.like("task-message-%"),
                Notification.source_key.like("task-history-%"),
            ),
        ).order_by(Notification.created_at.desc(), Notification.id.desc())
    )).all())
    grouped: dict[int, list[Notification]] = {}
    for notice in notices:
        if notice.source_id is not None:
            grouped.setdefault(int(notice.source_id), []).append(notice)
    if not grouped:
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "unread_messages": 0}

    tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task", BusinessRecord.id.in_(list(grouped)),
    ))).all())
    if identity.get("role") != "admin":
        tasks = [task for task in tasks if _is_task_participant(task, identity)]

    def contains(value: object, needle: str) -> bool:
        return not needle.strip() or needle.strip().casefold() in str(value or "").casefold()

    sender_users = await _user_display_map({notice.sender for notice in notices}, db)
    task_rows = {row["id"]: row for row in await _task_display_dicts(tasks, db)}
    items: list[dict] = []
    visible_notice_count = 0
    for task in tasks:
        row = task_rows[task.id]
        if not (
            contains(row.get("priority"), priority)
            and contains(row.get("serial_no"), serial_no)
            and contains(row.get("title"), title)
            and contains(row.get("description"), description)
            and contains(row.get("initiator"), initiator)
            and contains(" ".join(row.get("case_nos") or [row.get("case_no", "")]), case_no)
            and contains(row.get("creation_mode") if source in {"自动", "人工"} else row.get("source"), source)
            and contains(row.get("owner"), owner)
            and contains(row.get("plaintiff"), plaintiff)
            and contains(row.get("defendant"), defendant)
        ):
            continue
        if created_from and (not row.get("created_at") or row["created_at"].date() < created_from):
            continue
        if created_to and (not row.get("created_at") or row["created_at"].date() > created_to):
            continue
        if deadline_from and (not row.get("deadline") or row["deadline"] < deadline_from):
            continue
        if deadline_to and (not row.get("deadline") or row["deadline"] > deadline_to):
            continue
        task_notices = grouped[task.id]
        latest = task_notices[0]
        latest_content = latest.content or latest.title
        if latest.source_key.startswith("task-history-") and "｜" in latest_content:
            latest_content = latest_content.split("｜", 1)[1]
        visible_notice_count += len(task_notices)
        sender_display_name = _person_reference_display(latest.sender, sender_users)[0]
        items.append({
            **row,
            "latest_unread_message": latest_content,
            "latest_unread_sender": sender_display_name,
            "latest_unread_sender_display_name": sender_display_name,
            "latest_unread_at": latest.created_at,
            "latest_unread_notification_id": latest.id,
            "unread_count": len(task_notices),
        })
    if sort_by:
        reverse_sort = sort_order == "desc"
        items.sort(key=lambda item: item["id"], reverse=reverse_sort)
        populated = [item for item in items if item.get(sort_by) is not None and item.get(sort_by) != ""]
        missing = [item for item in items if item.get(sort_by) is None or item.get(sort_by) == ""]
        populated.sort(key=lambda item: item[sort_by], reverse=reverse_sort)
        items = populated + missing
    else:
        items.sort(key=lambda item: (item["latest_unread_at"], item["latest_unread_notification_id"]), reverse=True)
    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": items[start:start + page_size], "total": total, "page": page, "page_size": page_size,
        "unread_messages": visible_notice_count,
    }


@router.post(f"{settings.api_prefix}/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _case_customer_has_vip_marker,
    )
    from app.core.permissions import (
        _case_detail_action_capabilities, _ensure_active_ipr_case_write, _ensure_record_module,
    )
    from app.core.tasks import (
        _active_task_username, _add_task_message_notifications, _next_manual_task_serial, _task_dict, _validate_task_deadline,
    )
    _validate_task_deadline(body.deadline)
    if body.start_at and body.end_at and body.start_at >= body.end_at:
        raise HTTPException(status_code=422, detail="任务结束时间必须晚于开始时间")
    if body.end_at and body.end_at.date() != body.deadline:
        raise HTTPException(status_code=422, detail="截止日期必须与任务结束时间的日期一致")
    requested_case_nos = [body.case_no.strip(), *(str(value).strip() for value in body.case_nos)]
    case_nos = list(dict.fromkeys(value for value in requested_case_nos if value))
    case_no = case_nos[0] if case_nos else ""
    source = body.source.strip() or "日常任务"
    if source == "客户任务":
        raise HTTPException(status_code=403, detail="客户任务只能由客户通过客户端发布")
    if body.case_record_id and case_nos:
        raise HTTPException(status_code=422, detail="案件 ID 与案号列表不能同时提交")
    if source == "案件任务" and not case_nos and not body.case_record_id:
        raise HTTPException(status_code=422, detail="案件任务必须关联有效案件")
    case_records: list[BusinessRecord] = []
    if body.case_record_id:
        case_record = await _ensure_record_module(body.case_record_id, body.case_module, identity, db)
        if body.case_module == "case":
            capabilities = await _case_detail_action_capabilities(case_record, identity, db)
            if not capabilities["can_create_case_task"]:
                raise HTTPException(status_code=403, detail=f"当前账号没有创建案件 {case_record.serial_no} 任务的权限")
        else:
            await _ensure_active_ipr_case_write(case_record.id, identity, db)
        case_records.append(case_record)
    for linked_case_no in case_nos:
        case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == linked_case_no))
        if not case_record:
            raise HTTPException(status_code=404, detail=f"关联案件不存在：{linked_case_no}")
        case_record = await _ensure_record_module(case_record.id, "case", identity, db)
        capabilities = await _case_detail_action_capabilities(case_record, identity, db)
        if not capabilities["can_create_case_task"]:
            raise HTTPException(status_code=403, detail=f"当前账号没有创建案件 {linked_case_no} 任务的权限")
        case_records.append(case_record)
    case_record = case_records[0] if case_records else None
    case_no = case_record.serial_no if case_record else case_no
    serial = await _next_manual_task_serial(db)
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    owner = await _active_task_username(body.owner, db, field_name="负责人")
    collaborators = []
    for value in body.collaborators:
        collaborator = await _active_task_username(value, db, field_name="协作人")
        if collaborator != owner and collaborator not in collaborators:
            collaborators.append(collaborator)
    initial_status = "待处理" if source == "案件任务" else "待接收"
    inherited_vip = False
    for linked_case in case_records:
        if await _case_customer_has_vip_marker(linked_case, db):
            inherited_vip = True
            break
    task = BusinessRecord(module="task", serial_no=serial, title=body.title, customer=case_record.customer if case_record else body.customer, status=initial_status, owner=owner, department=user.department if user else "上海分所", description=body.description, data={"deadline": str(body.deadline), "start_at": body.start_at.isoformat() if body.start_at else "", "end_at": body.end_at.isoformat() if body.end_at else "", "priority": body.priority, "source": source, "creation_mode": "人工", "task_type": "手动任务", "initiator": identity["username"], "collaborators": collaborators, "case_no": case_no, "case_nos": [item.serial_no for item in case_records], "case_id": case_record.id if case_record else None, "case_record_id": case_record.id if case_record else None, "case_ids": [item.id for item in case_records], "case_module": body.case_module if case_record else "", "is_vip": bool(body.is_vip or inherited_vip)})
    db.add(task)
    await db.flush()
    await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="发起任务", to_status=initial_status, operator=identity["username"], comment=f"负责人：{owner}；截止日期：{body.deadline}"), db, content="任务已分派.")
    await db.commit()
    await db.refresh(task)
    return _task_dict(task)


@router.post(f"{settings.api_prefix}/tasks/batch-update")
async def batch_update_tasks(body: TaskBatchUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_task_owner_or_initiator,
    )
    from app.core.system import (
        _explicit_vip_value,
    )
    from app.core.tasks import (
        _active_task_username, _add_task_message_notifications, _task_dict, _task_has_vip_customer,
    )
    if body.owner is None and body.deadline is None and body.priority is None and body.is_vip is None:
        raise HTTPException(status_code=422, detail="请至少选择一个需要修改的字段")
    if body.deadline is not None:
        duration = (body.deadline - date.today()).days
        if duration < 0: raise HTTPException(status_code=422, detail="任务截止日期不能早于今天")
        if duration > 30: raise HTTPException(status_code=422, detail="任务截止日期不能超过 30 天")
    if body.priority is not None and body.priority not in {"普通", "重要", "紧急"}:
        raise HTTPException(status_code=422, detail="任务优先级无效")
    tasks = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task", BusinessRecord.id.in_(set(body.task_ids))))).all()
    if len(tasks) != len(set(body.task_ids)):
        raise HTTPException(status_code=404, detail="部分任务不存在")
    normalized_owner = None
    if body.owner is not None:
        normalized_owner = await _active_task_username(body.owner, db, field_name="负责人")
    for task in tasks:
        _require_task_owner_or_initiator(task, identity, action="批量修改任务")
        if task.status not in {"待接收", "待处理", "处理中"}:
            raise HTTPException(status_code=409, detail=f"任务 {task.serial_no} 已进入不可批量修改的状态")
        changes: list[str] = []
        if normalized_owner is not None:
            changes.append(f"负责人：{task.owner} → {normalized_owner}")
            task.owner = normalized_owner
        data = dict(task.data or {})
        if body.deadline is not None:
            changes.append(f"截止日期：{data.get('deadline', '')} → {body.deadline}")
            data["deadline"] = str(body.deadline)
        if body.priority is not None:
            changes.append(f"优先级：{data.get('priority', '')} → {body.priority}")
            data["priority"] = body.priority
        if body.is_vip is not None:
            previous_vip = _explicit_vip_value(data.get("is_vip"))
            next_vip = bool(body.is_vip or await _task_has_vip_customer(task, db))
            changes.append(f"VIP：{'是' if previous_vip else '否'} ⇒ {'是' if next_vip else '否'}")
            data["is_vip"] = next_vip
        task.data = data
        await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="批量修改任务", from_status=task.status, to_status=task.status, operator=identity["username"], comment="；".join(changes + ([body.comment] if body.comment else []))), db, content="任务已修改.")
    await db.commit()
    for task in tasks:
        await db.refresh(task)
    return {"updated": len(tasks), "items": [_task_dict(task) for task in tasks]}


@router.post(f"{settings.api_prefix}/tasks/batch-lifecycle")
async def batch_lifecycle_tasks(body: TaskBatchLifecycleInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Apply one dedicated task lifecycle action atomically to selected tasks.

    This deliberately does not reuse ``batch-update`` or the generic record
    transition endpoint: task state transitions have different participants,
    automatic deadlines and audit semantics.
    """
    from app.core.tasks import (
            _active_task_username, _add_task_message_notifications, _task_dict,
        )
    task_ids = list(dict.fromkeys(body.task_ids))
    tasks = (await db.scalars(
        select(BusinessRecord).where(BusinessRecord.module == "task", BusinessRecord.id.in_(task_ids))
    )).all()
    if len(tasks) != len(task_ids):
        raise HTTPException(status_code=404, detail="部分任务不存在")
    tasks_by_id = {task.id: task for task in tasks}
    ordered_tasks = [tasks_by_id[task_id] for task_id in task_ids]
    comment = body.comment.strip()
    recipient = ""
    if body.action == "handoff":
        recipient = await _active_task_username(body.recipient, db, field_name="接收人")
    if body.action == "withdraw" and not comment:
        raise HTTPException(status_code=422, detail="批量撤回任务必须填写撤回原因")

    # Validate the full selection before changing any record, so a mixed
    # selection never creates a partial lifecycle result.
    for task in ordered_tasks:
        data = task.data or {}
        if body.action == "accept":
            if identity.get("role") != "admin" and task.owner != identity["username"]:
                raise HTTPException(status_code=403, detail=f"任务 {task.serial_no} 仅负责人可接收")
            if task.status not in {"待接收", "待处理"}:
                raise HTTPException(status_code=409, detail=f"任务 {task.serial_no} 当前状态不能接收")
        elif body.action == "complete":
            if identity.get("role") != "admin" and task.owner != identity["username"]:
                raise HTTPException(status_code=403, detail=f"任务 {task.serial_no} 仅负责人可提交完成")
            if task.status not in {"待接收", "待处理", "处理中", "进行中", "已逾期"}:
                raise HTTPException(status_code=409, detail=f"任务 {task.serial_no} 当前状态不能提交完成")
        elif body.action == "confirm":
            if identity.get("role") != "admin" and data.get("initiator") != identity["username"]:
                raise HTTPException(status_code=403, detail=f"任务 {task.serial_no} 仅任务发起人可以批量确认完成")
            if task.status not in {"待确认", "已完成", "已拒绝"}:
                raise HTTPException(status_code=409, detail=f"任务 {task.serial_no} 当前状态不能批量确认")
        elif body.action == "handoff":
            if identity.get("role") != "admin" and task.owner != identity["username"]:
                raise HTTPException(status_code=403, detail=f"任务 {task.serial_no} 仅当前负责人可交接")
            if task.status in {"已完成", "已验收", "已撤回", "已停止", "已取消", "待确认", "已拒绝"}:
                raise HTTPException(status_code=409, detail=f"任务 {task.serial_no} 已结束，不能交接")
            if recipient == task.owner:
                raise HTTPException(status_code=422, detail=f"任务 {task.serial_no} 不能交接给当前负责人")
        else:  # withdraw
            if data.get("initiator") != identity["username"]:
                raise HTTPException(status_code=403, detail=f"任务 {task.serial_no} 仅发起人可撤回")
            if task.status not in {"待接收", "待处理", "处理中"}:
                raise HTTPException(status_code=409, detail=f"任务 {task.serial_no} 当前状态不能撤回")

    auto_at = date.today() + timedelta(days=5)
    action_labels = {
        "accept": "批量接收任务",
        "complete": "批量提交任务完成",
        "confirm": "批量验收任务",
        "handoff": "批量任务交接",
        "withdraw": "批量撤回任务",
    }
    content_labels = {
        "accept": "任务已批量接收.",
        "complete": "任务已批量提交完成，等待确认.",
        "handoff": "任务已批量交接.",
        "withdraw": "任务已批量撤回.",
    }
    for task in ordered_tasks:
        previous = task.status
        data = dict(task.data or {})
        if body.action == "accept":
            task.status = "处理中"
            task.data = {
                **data,
                "accepted_at": datetime.now().isoformat(timespec="seconds"),
                "handoff_restarted": True,
                "rejected_reason": "",
            }
        elif body.action == "complete":
            task.status = "已完成"
            task.data = {
                **data,
                "completion_submitted_at": datetime.now().isoformat(timespec="seconds"),
                "completion_auto_confirm_at": str(auto_at),
                "completion_comment": comment,
            }
        elif body.action == "confirm":
            task.status = "已验收"
            task.data = {
                **data,
                "verified_at": datetime.now().isoformat(timespec="seconds"),
                "verify_comment": comment,
                "completion_auto_confirm_at": "",
            }
        elif body.action == "handoff":
            previous_owner = task.owner
            task.owner = recipient
            task.status = "待接收"
            task.data = {
                **data,
                "handoff_from": previous_owner,
                "handoff_recipient": recipient,
                "handed_off_at": str(date.today()),
                "handoff_auto_complete_at": str(auto_at),
                "handoff_restarted": False,
            }
        else:
            task.status = "已撤回"
            task.data = {
                **data,
                "withdrawn_by": identity["username"],
                "withdrawn_at": datetime.now().isoformat(timespec="seconds"),
                "withdraw_comment": comment,
                "handoff_auto_complete_at": "",
                "completion_auto_confirm_at": "",
                "exception_request": {},
            }
        event_comment = comment
        if body.action == "handoff":
            event_comment = f"{previous_owner} 交接给 {recipient}；未重新开始将于 {auto_at} 自动完成。{comment}"
        elif body.action == "complete":
            event_comment = f"发起人应在 {auto_at} 前验收或退回重启。{comment}"
        await _add_task_message_notifications(
            task,
            WorkflowEvent(
                record_id=task.id,
                action=action_labels[body.action],
                from_status=previous,
                to_status=task.status,
                operator=identity["username"],
                comment=event_comment,
            ),
            db,
            content=content_labels.get(body.action, "任务已批量验收"),
        )
    await db.commit()
    for task in ordered_tasks:
        await db.refresh(task)
    return {"updated": len(ordered_tasks), "action": body.action, "items": [_task_dict(task) for task in ordered_tasks]}


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/accept")
async def accept_task(task_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _add_task_message_notifications, _task_dict, _task_or_404,
    )
    task = await _task_or_404(task_id, db)
    if identity.get("role") != "admin" and task.owner != identity["username"]:
        raise HTTPException(status_code=403, detail="只有任务负责人可以接收任务")
    if task.status not in {"待接收", "待处理"}:
        raise HTTPException(status_code=409, detail="当前状态不能接收任务")
    previous = task.status; task.status = "处理中"
    task.data = {**(task.data or {}), "accepted_at": datetime.now().isoformat(timespec="seconds"), "handoff_restarted": True, "rejected_reason": ""}
    await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="接收任务", from_status=previous, to_status="处理中", operator=identity["username"], comment=body.comment), db, content="任务已接受.")
    await db.commit(); await db.refresh(task); return _task_dict(task)


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/reject")
async def reject_task(task_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _add_task_message_notifications, _task_dict, _task_or_404,
    )
    task = await _task_or_404(task_id, db)
    if identity.get("role") != "admin" and task.owner != identity["username"]:
        raise HTTPException(status_code=403, detail="只有任务负责人可以拒绝任务")
    if task.status not in {"待接收", "待处理"}:
        raise HTTPException(status_code=409, detail="当前状态不能拒绝任务")
    if not body.comment.strip(): raise HTTPException(status_code=422, detail="拒绝任务必须填写理由")
    previous = task.status; task.status = "已拒绝"
    task.data = {**(task.data or {}), "rejected_reason": body.comment.strip(), "rejected_at": datetime.now().isoformat(timespec="seconds"), "handoff_auto_complete_at": ""}
    await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="拒绝任务", from_status=previous, to_status="已拒绝", operator=identity["username"], comment=body.comment), db, content="任务已拒绝.")
    await db.commit(); await db.refresh(task); return _task_dict(task)


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/withdraw")
async def withdraw_task(task_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Withdraw a live task through its dedicated lifecycle, never generic transition."""
    from app.core.tasks import (
            _add_task_message_notifications, _task_dict, _task_or_404,
        )
    task = await _task_or_404(task_id, db)
    data = task.data or {}
    if data.get("initiator") != identity["username"]:
        raise HTTPException(status_code=403, detail="只有任务发起人可以撤回任务")
    # ``待处理`` is retained for historical imported tasks and has the same pre-accept semantics.
    if task.status not in {"待接收", "待处理", "处理中"}:
        raise HTTPException(status_code=409, detail="只有待接收或处理中的任务可以撤回")
    comment = body.comment.strip()
    if not comment:
        raise HTTPException(status_code=422, detail="撤回任务必须填写撤回原因")
    previous = task.status
    task.status = "已撤回"
    task.data = {
        **data,
        "withdrawn_by": identity["username"],
        "withdrawn_at": datetime.now().isoformat(timespec="seconds"),
        "withdraw_comment": comment,
        "handoff_auto_complete_at": "",
        "completion_auto_confirm_at": "",
        "exception_request": {},
    }
    await _add_task_message_notifications(
        task,
        WorkflowEvent(
            record_id=task.id,
            action="撤回任务",
            from_status=previous,
            to_status="已撤回",
            operator=identity["username"],
            comment=comment,
        ),
        db,
        content="任务已撤回。",
    )
    await db.commit(); await db.refresh(task); return _task_dict(task)


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/resend")
async def resend_task(task_id: int, body: TaskHandoffInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _active_task_username, _add_task_message_notifications, _task_dict, _task_or_404,
    )
    task = await _task_or_404(task_id, db); data = task.data or {}
    if identity.get("role") != "admin" and data.get("initiator") != identity["username"]:
        raise HTTPException(status_code=403, detail="只有任务发起人可以重新派发")
    if task.status != "已拒绝": raise HTTPException(status_code=409, detail="只有已拒绝任务可以重新派发")
    previous_owner = task.owner
    recipient = await _active_task_username(body.recipient, db, field_name="新负责人")
    auto_at = date.today() + timedelta(days=5)
    task.owner = recipient; task.status = "待接收"
    task.data = {**data, "rejected_reason": "", "resent_at": datetime.now().isoformat(timespec="seconds"), "handoff_from": previous_owner, "handoff_recipient": recipient, "handed_off_at": str(date.today()), "handoff_auto_complete_at": str(auto_at), "handoff_restarted": False}
    await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="重新派发任务", from_status="已拒绝", to_status="待接收", operator=identity["username"], comment=f"{previous_owner} → {recipient}。{body.comment}"), db, content="任务已重新派发.")
    await db.commit(); await db.refresh(task); return _task_dict(task)


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/comments", status_code=status.HTTP_201_CREATED)
async def add_task_comment(task_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _add_task_message_notifications, _is_task_participant, _task_or_404,
    )
    task = await _task_or_404(task_id, db)
    if not _is_task_participant(task, identity): raise HTTPException(status_code=403, detail="只有任务参与人可以沟通")
    if not body.comment.strip(): raise HTTPException(status_code=422, detail="沟通内容不能为空")
    event = WorkflowEvent(record_id=task.id, action="任务沟通", from_status=task.status, to_status=task.status, operator=identity["username"], comment=body.comment.strip())
    await _add_task_message_notifications(task, event, db, content=body.comment.strip())
    await db.commit(); await db.refresh(event)
    return {"id": event.id, "operator": event.operator, "comment": event.comment, "created_at": event.created_at}


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/feedback", status_code=status.HTTP_201_CREATED)
async def create_task_feedback(
    task_id: int,
    comment: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Create one task feedback message and all selected attachments atomically."""
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.tasks import (
        _add_task_message_notifications, _is_task_participant, _task_or_404,
    )
    task = await _task_or_404(task_id, db)
    if not _is_task_participant(task, identity):
        raise HTTPException(status_code=403, detail="只有任务参与人可以提交反馈")
    normalized_comment = comment.strip()
    if not normalized_comment:
        raise HTTPException(status_code=422, detail="反馈内容不能为空")
    if len(normalized_comment) > 1000:
        raise HTTPException(status_code=422, detail="反馈内容不能超过 1000 个字符")
    if len(files) > 20:
        raise HTTPException(status_code=422, detail="一次最多上传 20 个反馈附件")

    allowed = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
    prepared_files: list[tuple[str, str, bytes]] = []
    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in allowed:
            raise HTTPException(status_code=422, detail="不支持的文件格式")
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="单个文件不能超过 20MB")
        prepared_files.append((Path(file.filename or f"task-feedback{suffix}").name, file.content_type or "application/octet-stream", content))

    written_paths: list[Path] = []
    attachments: list[FileAttachment] = []
    try:
        await _add_task_message_notifications(
            task,
            WorkflowEvent(
                record_id=task.id, action="任务沟通", from_status=task.status,
                to_status=task.status, operator=identity["username"], comment=normalized_comment,
            ),
            db,
            content=normalized_comment,
        )
        for original_name, content_type, content in prepared_files:
            suffix = Path(original_name).suffix.lower()
            target = UPLOAD_ROOT / f"{uuid4().hex}{suffix}"
            target.write_bytes(content)
            written_paths.append(target)
            attachment = FileAttachment(
                record_id=task.id, category="任务反馈附件", original_name=original_name,
                stored_name=target.name, content_type=content_type, size=len(content),
                path=str(target), uploader=identity["username"], remark=normalized_comment,
            )
            db.add(attachment)
            attachments.append(attachment)
            await _add_task_message_notifications(
                task,
                WorkflowEvent(
                    record_id=task.id, action="上传任务反馈附件", from_status=task.status,
                    to_status=task.status, operator=identity["username"],
                    comment=f"任务反馈附件：{original_name}",
                ),
                db,
                content=f"已上传任务反馈附件：{original_name}",
            )
        await db.commit()
        for attachment in attachments:
            await db.refresh(attachment)
    except Exception:
        await db.rollback()
        for path in written_paths:
            path.unlink(missing_ok=True)
        raise
    return {
        "comment": normalized_comment,
        "attachments": [_attachment_dict(attachment, task) for attachment in attachments],
    }


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/materials", status_code=status.HTTP_201_CREATED)
async def upload_task_materials(
    task_id: int,
    files: list[UploadFile] = File(...),
    remark: str = Form(""),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Upload task materials independently from feedback messages.

    Task materials are business files supplied at creation or during handling.  They
    must not be represented as feedback attachments because that would fabricate a
    communication entry and erase their distinct audit meaning.
    """
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.tasks import (
        _add_task_message_notifications, _is_task_participant, _task_or_404,
    )
    task = await _task_or_404(task_id, db)
    if not _is_task_participant(task, identity):
        raise HTTPException(status_code=403, detail="只有任务参与人可以上传任务资料附件")
    if not files:
        raise HTTPException(status_code=422, detail="请至少选择一个任务资料附件")
    if len(files) > 20:
        raise HTTPException(status_code=422, detail="一次最多上传 20 个任务资料附件")

    allowed = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
    prepared_files: list[tuple[str, str, bytes]] = []
    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in allowed:
            raise HTTPException(status_code=422, detail="不支持的文件格式")
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="单个文件不能超过 20MB")
        prepared_files.append((Path(file.filename or f"task-material{suffix}").name, file.content_type or "application/octet-stream", content))

    written_paths: list[Path] = []
    attachments: list[FileAttachment] = []
    try:
        for original_name, content_type, content in prepared_files:
            suffix = Path(original_name).suffix.lower()
            target = UPLOAD_ROOT / f"{uuid4().hex}{suffix}"
            target.write_bytes(content)
            written_paths.append(target)
            attachment = FileAttachment(
                record_id=task.id, category="任务资料附件", original_name=original_name,
                stored_name=target.name, content_type=content_type, size=len(content),
                path=str(target), uploader=identity["username"], remark=remark.strip(),
            )
            db.add(attachment)
            attachments.append(attachment)
            await _add_task_message_notifications(
                task,
                WorkflowEvent(
                    record_id=task.id, action="上传任务资料附件", from_status=task.status,
                    to_status=task.status, operator=identity["username"],
                    comment=f"任务资料附件：{original_name}",
                ),
                db,
                content=f"已上传任务资料附件：{original_name}",
            )
        await db.commit()
        for attachment in attachments:
            await db.refresh(attachment)
    except Exception:
        await db.rollback()
        for path in written_paths:
            path.unlink(missing_ok=True)
        raise
    return {"attachments": [_attachment_dict(attachment, task) for attachment in attachments]}


@router.get(f"{settings.api_prefix}/tasks/{{task_id}}/history")
async def task_history(task_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _person_reference_display, _user_display_map,
    )
    from app.core.tasks import (
        _is_task_participant, _task_or_404,
    )
    task = await _task_or_404(task_id, db)
    if not _is_task_participant(task, identity): raise HTTPException(status_code=403, detail="只有任务参与人可以查看沟通记录")
    events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == task.id).order_by(WorkflowEvent.created_at.desc(), WorkflowEvent.id.desc()))).all()
    users_by_username = await _user_display_map({item.operator for item in events}, db)
    unread_keys = set((await db.scalars(select(Notification.source_key).where(
        Notification.recipient == identity["username"], Notification.recipient_deleted.is_(False),
        Notification.is_read.is_(False), Notification.source_type == "task", Notification.source_id == task.id,
        Notification.source_key.like(f"task-history-{task.id}-%-{identity['username']}"),
    ))).all())
    return {"items": [{
        "id": item.id, "action": item.action, "operator": item.operator, "comment": item.comment,
        "operator_display_name": _person_reference_display(item.operator, users_by_username)[0],
        "from_status": item.from_status, "to_status": item.to_status, "created_at": item.created_at,
        "unread": f"task-history-{task.id}-{item.id}-{identity['username']}" in unread_keys,
    } for item in events]}


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/history/{{event_id}}/mark-unread")
async def mark_task_history_unread(task_id: int, event_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _is_task_participant, _notification_dict, _task_or_404,
    )
    task = await _task_or_404(task_id, db)
    if not _is_task_participant(task, identity):
        raise HTTPException(status_code=403, detail="只有任务参与人可以标记沟通记录")
    event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.id == event_id, WorkflowEvent.record_id == task.id))
    if not event:
        raise HTTPException(status_code=404, detail="任务历史事件不存在")
    source_key = f"task-history-{task.id}-{event.id}-{identity['username']}"
    item = await db.scalar(select(Notification).where(Notification.source_key == source_key))
    if item:
        item.is_read = False
        item.read_at = None
        item.recipient_deleted = False
        if item.sender == identity["username"]:
            item.sender_deleted = False
    else:
        item = Notification(
            source_key=source_key, source_type="task", source_id=task.id,
            sender=event.operator or "system", recipient=identity["username"], notification_type="系统通知",
            title=f"任务历史待处理：{task.serial_no}",
            content=f"{event.action}｜{event.comment or '无备注'}", level="info", is_read=False,
        )
        db.add(item)
    await db.commit()
    await db.refresh(item)
    return _notification_dict(item)


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/messages/read")
async def read_task_messages(task_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _is_task_participant, _task_or_404,
    )
    task = await _task_or_404(task_id, db)
    if not _is_task_participant(task, identity):
        raise HTTPException(status_code=403, detail="只有任务参与人可以读取任务消息")
    items = list((await db.scalars(select(Notification).where(
        Notification.recipient == identity["username"], Notification.recipient_deleted.is_(False),
        Notification.is_read.is_(False), Notification.source_type == "task", Notification.source_id == task.id,
        or_(
            Notification.source_key.like("task-message-%"),
            Notification.source_key.like("task-history-%"),
        ),
    ))).all())
    now = datetime.now()
    for item in items:
        item.is_read = True
        item.read_at = now
    await db.commit()
    return {"task_id": task.id, "updated": len(items), "is_read": True}


@router.post(f"{settings.api_prefix}/tasks/messages/batch-read")
async def batch_read_task_messages(body: TaskBatchReadInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Mark unread task messages read for the current recipient only.

    The original unread-task page has a selected-row "标记已读" action.  This
    command deliberately does not grant administrators access to somebody
    else's personal inbox: every notification is still filtered by recipient.
    All selected tasks are checked before any notification changes, so a mixed
    selection cannot partially succeed.
    """
    from app.core.tasks import (
        _is_task_participant,
    )
    task_ids = list(dict.fromkeys(body.task_ids))
    tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task", BusinessRecord.id.in_(task_ids),
    ))).all())
    if len(tasks) != len(task_ids):
        raise HTTPException(status_code=404, detail="部分任务不存在")
    for task in tasks:
        if not _is_task_participant(task, identity):
            raise HTTPException(status_code=403, detail="只有任务参与人可以读取任务消息")
    items = list((await db.scalars(select(Notification).where(
        Notification.recipient == identity["username"], Notification.recipient_deleted.is_(False),
        Notification.is_read.is_(False), Notification.source_type == "task", Notification.source_id.in_(task_ids),
        or_(
            Notification.source_key.like("task-message-%"),
            Notification.source_key.like("task-history-%"),
        ),
    ))).all())
    now = datetime.now()
    for item in items:
        item.is_read = True
        item.read_at = now
    await db.commit()
    return {"task_ids": task_ids, "updated": len(items), "is_read": True}


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/handoff")
async def handoff_task(task_id: int, body: TaskHandoffInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _active_task_username, _add_task_message_notifications, _task_dict, _task_or_404,
    )
    task = await _task_or_404(task_id, db)
    if identity.get("role") != "admin" and task.owner != identity["username"]:
        raise HTTPException(status_code=403, detail="只有当前负责人可以转交任务")
    if task.status in {"已完成", "已验收", "已撤回", "已停止", "已取消", "待确认", "已拒绝"}:
        raise HTTPException(status_code=409, detail="已结束任务不能交接")
    previous_owner, previous_status = task.owner, task.status
    recipient = await _active_task_username(body.recipient, db, field_name="接收人")
    if recipient == previous_owner:
        raise HTTPException(status_code=422, detail="任务不能转交给当前负责人")
    auto_at = date.today() + timedelta(days=5)
    task.owner = recipient
    task.status = "待接收"
    task.data = {**(task.data or {}), "handoff_from": previous_owner, "handoff_recipient": recipient, "handed_off_at": str(date.today()), "handoff_auto_complete_at": str(auto_at), "handoff_restarted": False}
    await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="任务交接", from_status=previous_status, to_status="待接收", operator=identity["username"], comment=f"{previous_owner} 交接给 {recipient}；未重新开始将于 {auto_at} 自动完成。{body.comment}"), db, content="任务已交接.")
    await db.commit()
    await db.refresh(task)
    return _task_dict(task)


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/restart")
async def restart_task(task_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _add_task_message_notifications, _task_dict, _task_or_404,
    )
    task = await _task_or_404(task_id, db); data = task.data or {}
    if task.status == "已完成" and (task.data or {}).get("auto_completed"):
        raise HTTPException(status_code=409, detail="任务已自动完成，请新建后续任务")
    if task.status in {"待确认", "已完成", "已拒绝"}:
        if identity.get("role") != "admin" and data.get("initiator") != identity["username"]: raise HTTPException(status_code=403, detail="只有发起人可以退回重启")
    elif identity.get("role") != "admin" and task.owner != identity["username"]:
        raise HTTPException(status_code=403, detail="只有任务负责人可以开始任务")
    if task.status == "已停止" and ((data.get("exception_request") or {}).get("action") != "挂起" or (data.get("exception_request") or {}).get("status") != "已通过"):
        raise HTTPException(status_code=409, detail="只有审批通过的挂起任务可以恢复")
    if task.status not in {"待接收", "待处理", "待确认", "已完成", "已拒绝", "已停止"}: raise HTTPException(status_code=409, detail="当前状态不能重新开始")
    previous = task.status
    restart_status = "待处理" if task.status == "已拒绝" else "处理中"
    task.status = restart_status
    task.data = {**data, "handoff_restarted": True, "restarted_at": str(date.today()), "completion_auto_confirm_at": "", "completion_comment": "", "rejected_reason": "", "exception_request": {**(data.get("exception_request") or {}), "resumed_at": datetime.now().isoformat(timespec="seconds"), "resumed_by": identity["username"]}}
    await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="重新开始任务", from_status=previous, to_status=restart_status, operator=identity["username"], comment=body.comment), db, content="任务已重新开始.")
    await db.commit()
    await db.refresh(task)
    return _task_dict(task)


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/exception-request")
async def request_task_exception(task_id: int, body: TaskExceptionRequestInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _add_task_message_notifications, _task_dict, _task_or_404,
    )
    task = await _task_or_404(task_id, db)
    if identity.get("role") != "admin" and task.owner != identity["username"]:
        raise HTTPException(status_code=403, detail="只有任务负责人可以申请挂起或取消")
    if task.status not in {"待接收", "待处理", "处理中"}:
        raise HTTPException(status_code=409, detail="当前任务状态不能申请挂起或取消")
    data = task.data or {}; pending = data.get("exception_request") or {}
    if pending.get("status") == "待审批":
        raise HTTPException(status_code=409, detail="已有任务特殊处理申请正在审批")
    request_data = {"action": body.action, "reason": body.reason.strip(), "status": "待审批", "requested_by": identity["username"], "requested_at": datetime.now().isoformat(timespec="seconds"), "status_before_request": task.status}
    task.data = {**data, "exception_request": request_data}
    await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action=f"申请任务{body.action}", from_status=task.status, to_status=task.status, operator=identity["username"], comment=body.reason.strip()), db, content=f"任务{body.action}申请待审批.")
    await db.commit(); await db.refresh(task)
    return _task_dict(task)


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/exception-review")
async def review_task_exception(task_id: int, body: TaskExceptionReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _add_task_message_notifications, _task_dict, _task_or_404,
    )
    task = await _task_or_404(task_id, db); data = task.data or {}; pending = data.get("exception_request") or {}
    if pending.get("status") != "待审批":
        raise HTTPException(status_code=409, detail="该任务没有待审批的特殊处理申请")
    if identity.get("role") != "admin" and pending.get("requested_by") == identity["username"]:
        raise HTTPException(status_code=403, detail="申请人不能审批自己的任务挂起或取消申请")
    reviewer = await db.scalar(select(User).where(User.username == identity["username"]))
    is_same_department_manager = bool(
        identity.get("role") == "manager" and reviewer and reviewer.department == task.department
    )
    if identity.get("role") != "admin" and data.get("initiator") != identity["username"] and not is_same_department_manager:
        raise HTTPException(status_code=403, detail="只有任务发起人、部门负责人或管理员可以审批")
    if not body.approved and not body.comment.strip():
        raise HTTPException(status_code=422, detail="驳回时必须填写原因")
    previous = task.status; action_name = str(pending.get("action") or "")
    if body.approved:
        task.status = "已停止" if action_name == "挂起" else "已取消"
    reviewed = {**pending, "status": "已通过" if body.approved else "已驳回", "reviewed_by": identity["username"], "reviewed_at": datetime.now().isoformat(timespec="seconds"), "review_comment": body.comment.strip()}
    task.data = {**data, "exception_request": reviewed}
    await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action=f"任务{action_name}审批{'通过' if body.approved else '驳回'}", from_status=previous, to_status=task.status, operator=identity["username"], comment=body.comment), db, content=f"任务{action_name}申请已{'通过' if body.approved else '驳回'}.")
    await db.commit(); await db.refresh(task)
    return _task_dict(task)


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/complete")
async def complete_task(task_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _add_task_message_notifications, _task_dict, _task_or_404,
    )
    task = await _task_or_404(task_id, db)
    if identity.get("role") != "admin" and task.owner != identity["username"]: raise HTTPException(status_code=403, detail="只有任务负责人可以提交完成")
    if task.status not in {"待接收", "待处理", "处理中", "进行中", "已逾期"}: raise HTTPException(status_code=409, detail="当前状态不能提交完成")
    previous = task.status
    task.status = "已完成"
    auto_at = date.today() + timedelta(days=5)
    task.data = {**(task.data or {}), "completion_submitted_at": datetime.now().isoformat(timespec="seconds"), "completion_auto_confirm_at": str(auto_at), "completion_comment": body.comment}
    await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="提交任务完成", from_status=previous, to_status="已完成", operator=identity["username"], comment=f"发起人应在 {auto_at} 前验收或退回重启。{body.comment}"), db, content="任务已完成，等待确认.")
    await db.commit()
    await db.refresh(task)
    return _task_dict(task)


@router.post(f"{settings.api_prefix}/tasks/{{task_id}}/confirm")
async def confirm_task(task_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.tasks import (
        _add_task_message_notifications, _advance_case_from_fixed_task, _task_dict, _task_or_404,
    )
    task = await _task_or_404(task_id, db); data = task.data or {}
    if identity.get("role") != "admin" and data.get("initiator") != identity["username"]: raise HTTPException(status_code=403, detail="只有任务发起人可以确认完成")
    if task.status not in {"待确认", "已完成", "已拒绝"}: raise HTTPException(status_code=409, detail="当前状态不能确认完成")
    previous = task.status
    task.status = "已验收"; task.data = {**data, "confirmed_at": datetime.now().isoformat(timespec="seconds"), "completion_auto_confirm_at": ""}
    await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="验收任务", from_status=previous, to_status="已验收", operator=identity["username"], comment=body.comment), db, content="任务已确认完成.")
    await _advance_case_from_fixed_task(task, db, operator=identity["username"])
    await db.commit(); await db.refresh(task); return _task_dict(task)
