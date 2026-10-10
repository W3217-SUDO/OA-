"""按独立业务职责组织的路由，注册顺序与端点行为保持稳定。"""
from app.core.constants import (
    UPLOAD_ROOT,
    case_agent_runtime,
    logger,
)
from app.core.dependencies import (
    AsyncSession,
    BusinessRecord,
    ContractObject,
    ContractPaymentLine,
    Depends,
    FileAttachment,
    HTTPException,
    HearingSchedule,
    IncomingPayment,
    Path,
    ReceivablePlan,
    StreamingResponse,
    User,
    WorkflowEvent,
    asyncio,
    base64,
    build_case_workflow_guide,
    current_identity,
    datetime,
    false,
    get_db,
    json,
    or_,
    read_attachment,
    select,
    settings,
    timezone,
)
from app.models_shared import (
    CaseAgentDecisionInput,
    CaseAgentMessageInput,
)
from fastapi import APIRouter

router = APIRouter()

@router.get(f"{settings.api_prefix}/case-spaces/{{case_id}}/context")
async def get_case_space_context(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Aggregate one authorized case into the stable context contract used by agents."""
    from app.core.finance import (
        _incoming_payment_dict, _receivable_dict,
    )
    from app.core.formatters import (
        _task_display_dict,
    )
    from app.core.permissions import (
        _case_detail_action_capabilities, _ensure_record_module, _filter_visible_attachments, _record_dict_for_identity, _record_scope_conditions,
        _record_dicts_for_identity, _require_record_owner_or_manager,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    case_data = case_record.data or {}
    allowed_fields = await _allowed_field_keys(identity, db)
    scope_conditions = await _record_scope_conditions(identity, db)

    contract_ids = {
        int(value)
        for value in (case_data.get("contract_id"), case_data.get("contract_record_id"))
        if str(value or "").isdigit() and int(value) > 0
    }
    contract_objects = list((await db.scalars(select(ContractObject).where(
        ContractObject.case_record_id == case_record.id,
    ).order_by(ContractObject.id))).all())
    contract_ids.update(item.contract_record_id for item in contract_objects)
    contract_no = str(case_data.get("contract_no") or "").strip()
    contract_match = BusinessRecord.id.in_(contract_ids)
    if contract_no:
        contract_match = or_(contract_match, BusinessRecord.serial_no == contract_no)
    contracts = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract", contract_match, *scope_conditions,
    ).order_by(BusinessRecord.id))).all()) if contract_ids or contract_no else []
    contract_ids = {item.id for item in contracts}

    payment_record_ids = set((await db.scalars(select(ContractPaymentLine.payment_record_id).where(
        ContractPaymentLine.case_record_id == case_record.id,
    ))).all())
    linked_records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(["finance", "invoice", "task", "contract_payment"]),
        or_(
            BusinessRecord.data["case_id"].as_integer() == case_record.id,
            BusinessRecord.data["case_record_id"].as_integer() == case_record.id,
            BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
            BusinessRecord.id.in_(payment_record_ids),
        ),
        *scope_conditions,
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    finance_records = [item for item in linked_records if item.module == "finance"]
    invoice_records = [item for item in linked_records if item.module == "invoice"]
    tasks = [item for item in linked_records if item.module == "task"]
    payment_records = [item for item in linked_records if item.module == "contract_payment"]

    reminders = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case_reminder",
        BusinessRecord.data["case_id"].as_integer() == case_record.id,
    ).order_by(BusinessRecord.data["deadline"].as_string(), BusinessRecord.id))).all())
    hearings = list((await db.scalars(select(HearingSchedule).where(
        HearingSchedule.case_record_id == case_record.id,
    ).order_by(HearingSchedule.hearing_date, HearingSchedule.hearing_time, HearingSchedule.id))).all())

    customer_id = int(case_data.get("customer_id") or case_data.get("customer_record_id") or 0)
    customer_conditions = [BusinessRecord.module == "customer", *scope_conditions]
    customer_conditions.append(BusinessRecord.id == customer_id if customer_id else BusinessRecord.title == case_record.customer)
    customer = await db.scalar(select(BusinessRecord).where(*customer_conditions).order_by(BusinessRecord.id))

    clue_ids = {
        int(value)
        for value in (
            case_data.get("clue_record_id"), case_data.get("investigation_clue_id"),
        )
        if str(value or "").isdigit() and int(value) > 0
    }
    clue_nos = {
        str(value or "").strip()
        for value in [
            case_data.get("clue_no"), case_data.get("investigation_clue"),
            case_data.get("source_clue_no"), *(case_data.get("investigation_clue_nos") or []),
        ]
        if str(value or "").strip()
    }
    clue_matches = [
        BusinessRecord.data["converted_case_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_record_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
    ]
    if clue_ids:
        clue_matches.append(BusinessRecord.id.in_(clue_ids))
    if clue_nos:
        clue_matches.append(BusinessRecord.serial_no.in_(clue_nos))
    clues = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "clue", or_(*clue_matches), *scope_conditions,
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())

    source_task_ids = {
        int((item.data or {}).get("source_task_id") or 0)
        for item in clues
        if str((item.data or {}).get("source_task_id") or "").isdigit()
        and int((item.data or {}).get("source_task_id") or 0) > 0
    }
    source_tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(source_task_ids),
        BusinessRecord.module.in_(["investigation", "task"]),
        *scope_conditions,
    ))).all()) if source_task_ids else []
    investigation_ids = {
        int(value)
        for value in [
            case_data.get("investigation_record_id"),
            *[(item.data or {}).get("investigation_record_id") for item in clues],
            *[item.id if item.module == "investigation" else (item.data or {}).get("investigation_record_id") for item in source_tasks],
        ]
        if str(value or "").isdigit() and int(value) > 0
    }
    investigation_nos = {
        str(value or "").strip()
        for value in [
            case_data.get("investigation_no"),
            *[(item.data or {}).get("investigation_no") for item in clues],
            *[item.serial_no if item.module == "investigation" else (item.data or {}).get("investigation_no") for item in source_tasks],
        ]
        if str(value or "").strip()
    }
    investigation_matches = [
        BusinessRecord.data["case_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_record_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
    ]
    if investigation_ids:
        investigation_matches.append(BusinessRecord.id.in_(investigation_ids))
    if investigation_nos:
        investigation_matches.append(BusinessRecord.serial_no.in_(investigation_nos))
    investigations = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "investigation", or_(*investigation_matches), *scope_conditions,
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())

    receivables = list((await db.scalars(select(ReceivablePlan).where(
        ReceivablePlan.contract_record_id.in_(contract_ids),
    ).order_by(ReceivablePlan.due_date, ReceivablePlan.id))).all()) if contract_ids else []
    incoming = list((await db.scalars(select(IncomingPayment).where(or_(
        IncomingPayment.case_no == case_record.serial_no,
        IncomingPayment.contract_record_id.in_(contract_ids) if contract_ids else false(),
    )).order_by(IncomingPayment.received_date.desc(), IncomingPayment.id.desc()))).all())

    source_records = [case_record, *contracts, *clues, *investigations, *finance_records, *invoice_records, *tasks, *payment_records]
    source_by_id = {item.id: item for item in source_records}
    source_ids = set(source_by_id)
    attachments = list((await db.scalars(select(FileAttachment).where(
        FileAttachment.record_id.in_(source_ids),
    ).order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc()))).all()) if source_ids else []
    attachments = await _filter_visible_attachments(attachments, identity, db)

    users = list((await db.scalars(select(User).where(User.is_active.is_(True)))).all())
    users_by_username = {item.username.casefold(): item for item in users}
    users_by_name = {str(item.display_name or "").strip().casefold(): item for item in users if str(item.display_name or "").strip()}

    def person(role: str, value: object) -> dict | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        user = users_by_username.get(raw.casefold()) or users_by_name.get(raw.casefold())
        return {"role": role, "username": user.username if user else "", "name": user.display_name if user else raw}

    people_values = [
        person("案件负责人", case_record.owner),
        *[person("经办律师", item) for item in list(case_data.get("handling_lawyers") or [])],
        person("律师助理", case_data.get("assistant") or case_data.get("assistant_username")),
        person("开庭律师", case_data.get("hearing_lawyer")),
        person("客户管理人", case_data.get("customer_manager")),
        person("案源人", case_data.get("business_owner") or case_data.get("source_person")),
        person("调查员", case_data.get("investigator")),
    ]
    people = []
    seen_people = set()
    for item in filter(None, people_values):
        key = (item["role"], item["username"] or item["name"])
        if key not in seen_people:
            seen_people.add(key)
            people.append(item)

    show_finance_amount = "finance.amount" in allowed_fields
    contract_payload = []
    for contract in contracts:
        objects = [item for item in contract_objects if item.contract_record_id == contract.id]
        plans = [item for item in receivables if item.contract_record_id == contract.id]
        contract_payload.append({
            **_record_dict(contract, allowed_fields),
            "objects": [{"id": item.id, "case_record_id": item.case_record_id, "fee_type": item.fee_type, "amount": item.amount if "contract.amount" in allowed_fields else None, "remark": item.remark} for item in objects],
            "receivables": [{**_receivable_dict(item, contract), **({} if show_finance_amount else {"amount": None, "received_amount": None, "remaining_amount": None})} for item in plans],
        })

    document_payload = []
    for item in attachments:
        source = source_by_id.get(item.record_id)
        document_payload.append({**_attachment_dict(item, source), "source_module": source.module if source else "", "source_status": source.status if source else ""})

    deadline_items = [
        {"type": "案件提醒", "id": item.id, "title": item.title, "reminder_date": (item.data or {}).get("reminder_date", ""), "deadline": (item.data or {}).get("deadline", ""), "status": item.status}
        for item in reminders
    ] + [
        {"type": "开庭排期", "id": item.id, "title": item.hearing_type, "deadline": str(item.hearing_date), "time": item.hearing_time, "court": item.court, "courtroom": item.courtroom, "status": item.status}
        for item in hearings
    ] + [
        {"type": "案件任务", "id": item.id, "title": item.title, "deadline": str((item.data or {}).get("deadline") or ""), "status": item.status, "owner": item.owner}
        for item in tasks if (item.data or {}).get("deadline")
    ]

    capabilities = await _case_detail_action_capabilities(case_record, identity, db)
    # 案件可见性已校验；工具入口不扩大原业务接口的操作权限。
    capabilities["can_use_mcp_tools"] = True
    capabilities["can_update_customer"] = False
    if customer:
        try:
            await _require_record_owner_or_manager(customer, identity, db)
            capabilities["can_update_customer"] = True
        except HTTPException:
            pass
    capabilities["can_update_contract"] = False
    for contract in contracts:
        try:
            await _require_record_owner_or_manager(contract, identity, db)
            if contract.status in {"草稿", "已拒绝"}:
                capabilities["can_update_contract"] = True
                break
        except HTTPException:
            continue

    from app.core.contracts import _contract_customer_record_dicts
    context = {
        "schema_version": "1.1",
        "space": {"id": f"case:{case_record.id}", "kind": "business_graph", "case_id": case_record.id, "case_no": case_record.serial_no, "generated_at": datetime.now(timezone.utc)},
        "case": await _record_dict_for_identity(case_record, identity, db),
        "customer": await _record_dict_for_identity(customer, identity, db) if customer else None,
        "people": people,
        "contracts": contract_payload,
        "finances": {
            "fees": await _contract_customer_record_dicts(finance_records, allowed_fields, db, identity=identity),
            "invoices": [_record_dict(item, allowed_fields) for item in invoice_records],
            "contract_payments": [_record_dict(item, allowed_fields) for item in payment_records],
            "incoming_payments": [_incoming_payment_dict(item, show_amount=show_finance_amount) for item in incoming],
        },
        "deadlines": deadline_items,
        "documents": document_payload,
        "tasks": [await _task_display_dict(item, db) for item in tasks],
        "relationships": {
            "clues": await _record_dicts_for_identity(clues, identity, db),
            "investigations": await _record_dicts_for_identity(investigations, identity, db),
            "edges": [
                *([{"from": f"case:{case_record.id}", "to": f"customer:{customer.id}", "type": "belongs_to_customer"}] if customer else []),
                *[{"from": f"case:{case_record.id}", "to": f"contract:{item.id}", "type": "covered_by_contract"} for item in contracts],
                *[{"from": f"clue:{item.id}", "to": f"case:{case_record.id}", "type": "converted_to_case"} for item in clues],
                *[{"from": f"investigation:{item.id}", "to": f"case:{case_record.id}", "type": "supports_case"} for item in investigations],
                *[{"from": f"finance:{item.id}", "to": f"case:{case_record.id}", "type": "financial_record"} for item in finance_records],
                *[{"from": f"invoice:{item.id}", "to": f"case:{case_record.id}", "type": "invoice_record"} for item in invoice_records],
            ],
        },
        "capabilities": capabilities,
        "agent": {
            **case_agent_runtime.status(),
            "shared_space_id": f"case:{case_record.id}",
            "private_thread_id": case_agent_runtime.thread_id(case_record.id, identity["username"]),
        },
    }
    context["standard_workflow"] = build_case_workflow_guide(context)
    return context


@router.get(f"{settings.api_prefix}/case-spaces/{{case_id}}/workflow-guide")
async def get_case_workflow_guide(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    context = await get_case_space_context(case_id, identity, db)
    return context["standard_workflow"]


@router.get(f"{settings.api_prefix}/case-spaces/{{case_id}}/agent/status")
async def case_agent_status(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _agent_skill_catalog_for_identity, _ensure_record_module,
    )
    await _ensure_record_module(case_id, "case", identity, db)
    runtime_status = case_agent_runtime.status()
    return {
        "case_id": case_id,
        "shared_space_id": f"case:{case_id}",
        "thread_id": case_agent_runtime.thread_id(case_id, identity["username"]),
        **runtime_status,
        "skills": await _agent_skill_catalog_for_identity(identity, db),
    }


@router.get(f"{settings.api_prefix}/case-spaces/{{case_id}}/agent/state")
async def case_agent_state(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    await _ensure_record_module(case_id, "case", identity, db)
    if not case_agent_runtime.status()["ready"]:
        raise HTTPException(status_code=503, detail="案件智能体尚未就绪")
    try:
        state = await case_agent_runtime.get_state(case_id, identity["username"])
        import hashlib
        actions = state.get("pending_actions") or []
        audit_serials = {
            action.get("id"): "AGENT-" + hashlib.sha256(f"{case_id}:{action.get('id')}".encode("utf-8")).hexdigest()[:40]
            for action in actions if action.get("id")
        }
        if audit_serials:
            audits = list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.module == "agent_action", BusinessRecord.serial_no.in_(list(audit_serials.values())),
            ))).all())
            status_by_serial = {item.serial_no: item.status for item in audits}
            for action in actions:
                if status_by_serial.get(audit_serials.get(action.get("id"), "")) == "已恢复":
                    action["status"] = "restored"
        return state
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="案件智能体状态读取失败") from exc


@router.post(f"{settings.api_prefix}/case-spaces/{{case_id}}/agent/messages")
async def send_case_agent_message(
    case_id: int,
    body: CaseAgentMessageInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _agent_skill_for_identity,
    )
    context = await get_case_space_context(case_id, identity, db)
    if not case_agent_runtime.status()["ready"]:
        raise HTTPException(status_code=503, detail="案件智能体尚未就绪")
    proposed_action = body.proposed_action.model_dump() if body.proposed_action else None
    selected_skill = await _agent_skill_for_identity(body.skill_id, identity, db)
    if proposed_action and not context["capabilities"].get("can_write"):
        raise HTTPException(status_code=403, detail="当前账号无权为该案件发起写操作")
    images: list[dict[str, object]] = []
    attachment_ids = list(dict.fromkeys(body.attachment_ids))
    if attachment_ids:
        attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(attachment_ids)))).all())
        if len(attachments) != len(attachment_ids) or any(item.record_id != case_id for item in attachments):
            raise HTTPException(status_code=404, detail="截图附件不存在或不属于当前案件")
        by_id = {item.id: item for item in attachments}
        total_size = 0
        mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
        for attachment_id in attachment_ids:
            item = by_id[attachment_id]
            suffix = Path(item.original_name or item.path).suffix.lower()
            mime_type = mime_types.get(suffix)
            if not mime_type:
                raise HTTPException(status_code=422, detail="截图证据仅支持 PNG、JPG、JPEG 或 WebP")
            path = Path(item.path)
            if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents:
                raise HTTPException(status_code=404, detail="截图附件文件不存在")
            content = path.read_bytes()
            total_size += len(content)
            if len(content) > 6 * 1024 * 1024 or total_size > 12 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="单张截图不能超过 6MB，单次分析总计不能超过 12MB")
            images.append({
                "id": item.id,
                "name": item.original_name,
                "mime_type": mime_type,
                "data_url": f"data:{mime_type};base64,{base64.b64encode(content).decode('ascii')}",
            })
    allowed_document_ids = [int(item.get("id") or 0) for item in context.get("documents", []) if int(item.get("id") or 0) > 0]
    document_ids = allowed_document_ids if body.document_ids is None else list(dict.fromkeys(body.document_ids))
    if any(item not in allowed_document_ids for item in document_ids):
        raise HTTPException(status_code=404, detail="所选材料不存在或不在当前账号可见的案件空间内")
    document_readings: list[dict[str, object]] = []
    if document_ids:
        visible_documents = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(document_ids)))).all())
        visible_by_id = {item.id: item for item in visible_documents}
        remaining_chars = 60_000
        visual_bytes = sum(len(str(item.get("data_url") or "")) for item in images)
        document_visual_groups: list[tuple[FileAttachment, tuple[dict[str, str], ...]]] = []
        seen_files: set[tuple[str, int]] = set()
        for attachment_id in document_ids:
            item = visible_by_id.get(attachment_id)
            if not item or len(document_readings) >= 12:
                continue
            dedupe_key = (str(item.original_name or "").strip().casefold(), int(item.size or 0))
            if dedupe_key in seen_files:
                continue
            seen_files.add(dedupe_key)
            path = Path(item.path)
            if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents or path.stat().st_size > 30 * 1024 * 1024:
                continue
            try:
                reading = await asyncio.to_thread(read_attachment, path, item.original_name)
            except Exception:
                logger.exception("agent attachment parse failed: attachment_id=%s", item.id)
                document_readings.append({"attachment_id": item.id, "file_name": item.original_name, "category": item.category, "status": "parse_failed"})
                continue
            text_content = reading.text[:remaining_chars]
            remaining_chars -= len(text_content)
            document_readings.append({
                "attachment_id": item.id,
                "file_name": item.original_name,
                "category": item.category,
                "status": reading.status,
                "page_count": reading.page_count,
                "content": text_content,
            })
            if reading.images:
                document_visual_groups.append((item, reading.images))
        document_visual_count = 0
        for page_index in range(4):
            for item, visual_pages in document_visual_groups:
                if page_index >= len(visual_pages) or document_visual_count >= 12:
                    continue
                visual = visual_pages[page_index]
                data_url = visual.get("data_url", "")
                if not data_url or visual_bytes + len(data_url) > 12 * 1024 * 1024:
                    continue
                visual_bytes += len(data_url)
                document_visual_count += 1
                images.append({
                    "id": f"document:{item.id}:page:{visual.get('page', '1')}",
                    "name": f"{item.original_name}（第 {visual.get('page', '1')} 页）",
                    "mime_type": visual.get("mime_type", "image/jpeg"),
                    "data_url": data_url,
                    "page": visual.get("page", "1"),
                })
    context["document_readings"] = document_readings
    invoke_arguments = {
        "case_id": case_id,
        "operator": identity["username"],
        "message": body.message,
        "case_snapshot": context,
        "proposed_action": proposed_action,
        "images": images,
        "skill_override": selected_skill,
    }
    if body.stream:
        async def stream_events():
            async for event in case_agent_runtime.invoke_stream(**invoke_arguments):
                yield json.dumps(event, ensure_ascii=False, default=str) + "\n"

        return StreamingResponse(
            stream_events(), media_type="application/x-ndjson",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )
    try:
        return await case_agent_runtime.invoke(
            **invoke_arguments,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="案件智能体调用失败") from exc


@router.post(f"{settings.api_prefix}/case-spaces/{{case_id}}/agent/actions/{{action_id}}/decision")
async def decide_case_agent_action(
    case_id: int,
    action_id: str,
    body: CaseAgentDecisionInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.encoders import jsonable_encoder
    from app.case_agent import _action_preview
    from app.core.documents import (
        _execute_case_agent_action,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_agent_action_access,
    )
    from app.agent_mcp.auth import require_human_decision

    require_human_decision(action_id)
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    case_customer = case_record.customer
    case_number = case_record.serial_no
    case_department = case_record.department
    try:
        state = await case_agent_runtime.get_state(case_id, identity["username"])
        action = next((item for item in state.get("pending_actions") or [] if item.get("id") == action_id), None)
        if not action:
            raise KeyError(action_id)
        if action.get("status") != "pending":
            raise ValueError("action_already_decided")
        if action.get("type") == "mcp.call":
            from app.agent_mcp.service import decide_tool_request

            request_id = (action.get("payload") or {}).get("request_id")
            if not isinstance(request_id, str) or not request_id:
                raise HTTPException(status_code=422, detail="待确认工具请求缺少有效编号")
            if action.get("requested_by") != identity["username"]:
                raise HTTPException(status_code=403, detail="只能确认本人发起的工具请求")
            _require_case_agent_action_access("mcp.call", {"can_use_mcp_tools": True})
            # 原业务路由自行提交，不能进入旧动作共用事务的执行器。
            execution = await decide_tool_request(
                request_id, body.decision, identity, db,
                comment=body.comment, expected_case_id=case_id,
            )
            expected_status = "succeeded" if body.decision == "approved" else "rejected"
            if execution.get("status") != expected_status:
                raise HTTPException(status_code=409, detail="工具请求未完成，请查看真实执行状态")
            return await case_agent_runtime.decide_action(
                case_id=case_id, action_id=action_id, decision=body.decision,
                operator=identity["username"], comment=body.comment,
                execution_result=execution,
            )
        context = await get_case_space_context(case_id, identity, db)
        capabilities = context.get("capabilities") or {}
        _require_case_agent_action_access(str(action.get("type") or ""), capabilities)
        action_type = str(action.get("type") or "")
        preview = action.get("preview") if isinstance(action.get("preview"), dict) else {}
        if body.decision == "approved":
            if action_type in {"case.update", "case.data.update", "customer.update", "contract.update"}:
                # 复用授权上下文的预览投影，旧操作缺少或不匹配的修改前值必须重新生成。
                current_preview = _action_preview(action, context)
                previous_changes = {
                    str(item.get("field") or ""): item for item in preview.get("changes") or []
                }
                changed_fields = [
                    item["field"] for item in current_preview["changes"]
                    if item["field"] not in previous_changes
                    or "before" not in previous_changes[item["field"]]
                    or item["before"] != previous_changes[item["field"]]["before"]
                ]
                if changed_fields:
                    raise HTTPException(status_code=409, detail="目标数据已变化，请重新生成并确认操作：" + "、".join(changed_fields))
            elif action_type in {"case.delete", "customer.delete", "contract.delete"}:
                if action_type == "customer.delete":
                    current_status = str((context.get("customer") or {}).get("status") or "")
                elif action_type == "contract.delete":
                    target_id = int((action.get("payload") or {}).get("target_id") or 0)
                    current_status = str(next((item.get("status") for item in context.get("contracts") or [] if int(item.get("id") or 0) == target_id), ""))
                else:
                    current_status = case_record.status
                if current_status != str(preview.get("before_status") or ""):
                    raise HTTPException(status_code=409, detail="目标状态已变化，请重新生成并确认删除操作")
        execution_result = None
        post_commit_conflict = None
        import hashlib
        audit_serial = "AGENT-" + hashlib.sha256(f"{case_id}:{action_id}".encode("utf-8")).hexdigest()[:40]
        audit = await db.scalar(select(BusinessRecord).where(
            BusinessRecord.module == "agent_action", BusinessRecord.serial_no == audit_serial,
        ).with_for_update())
        if audit and audit.status == "已执行":
            execution_result = (audit.data or {}).get("execution_result")
        elif audit and audit.status == "执行中":
            raise HTTPException(status_code=409, detail="该智能体操作正在执行，请勿重复批准")
        elif body.decision == "approved":
            try:
                # 业务写入与审批结果共用保存点；失败时只回滚本次操作，保留会话中已读取的对象。
                async with db.begin_nested():
                    if not audit:
                        audit = BusinessRecord(
                            module="agent_action", serial_no=audit_serial, title=str(action.get("summary") or "智能体操作"),
                            customer=case_customer, status="已执行", owner=identity["username"], department=case_department,
                            description=body.comment.strip(), data={
                                "case_id": case_id, "case_no": case_number, "action_id": action_id,
                                "action_type": str(action.get("type") or ""), "payload": jsonable_encoder(action.get("payload") or {}),
                                "approved_by": identity["username"], "approved_at": datetime.now(timezone.utc).isoformat(),
                                "executed_at": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                        db.add(audit)
                    else:
                        audit.status = "已执行"
                        audit.data = {
                            **(audit.data or {}),
                            "approved_by": identity["username"],
                            "approved_at": datetime.now(timezone.utc).isoformat(),
                            "executed_at": datetime.now(timezone.utc).isoformat(),
                        }
                    execution_result = await _execute_case_agent_action(case_record, action, identity, db, context)
                    post_commit_conflict = execution_result.pop("post_commit_conflict", None)
                    execution_result = jsonable_encoder(execution_result)
                    audit.status = "执行失败" if post_commit_conflict else "已执行"
                    audit.data = {
                        **(audit.data or {}), "execution_result": execution_result,
                        "executed_at": datetime.now(timezone.utc).isoformat(),
                    }
                    if post_commit_conflict:
                        audit.data = {
                            **audit.data, "failed_at": datetime.now(timezone.utc).isoformat(),
                            "error": str(post_commit_conflict.get("message") or "")[:500],
                        }
            except Exception as exc:
                failed_audit = await db.scalar(select(BusinessRecord).where(
                    BusinessRecord.module == "agent_action", BusinessRecord.serial_no == audit_serial,
                ).with_for_update())
                if failed_audit and failed_audit.status == "已执行":
                    # 并发批准时唯一编号只允许一方落库；另一方复用已提交的结果。
                    execution_result = (failed_audit.data or {}).get("execution_result")
                else:
                    if not failed_audit:
                        failed_audit = BusinessRecord(
                            module="agent_action", serial_no=audit_serial,
                            title=str(action.get("summary") or "智能体操作"), customer=case_customer,
                            status="执行失败", owner=identity["username"], department=case_department,
                            description=body.comment.strip(), data={
                                "case_id": case_id, "case_no": case_number, "action_id": action_id,
                                "action_type": str(action.get("type") or ""), "payload": jsonable_encoder(action.get("payload") or {}),
                            },
                        )
                        db.add(failed_audit)
                    failed_audit.status = "执行失败"
                    failed_audit.data = {**(failed_audit.data or {}), "failed_at": datetime.now(timezone.utc).isoformat(), "error": str(exc)[:500]}
                    await db.commit()
                    raise
            await db.commit()
            if post_commit_conflict:
                raise HTTPException(status_code=409, detail=jsonable_encoder(post_commit_conflict))
        elif not audit:
            db.add(BusinessRecord(
                module="agent_action", serial_no=audit_serial, title=str(action.get("summary") or "智能体操作"),
                customer=case_record.customer, status="已驳回", owner=identity["username"], department=case_record.department,
                description=body.comment.strip(), data={"case_id": case_id, "case_no": case_record.serial_no, "action_id": action_id, "action_type": str(action.get("type") or ""), "rejected_by": identity["username"]},
            ))
            await db.commit()
        return await case_agent_runtime.decide_action(
            case_id=case_id,
            action_id=action_id,
            decision=body.decision,
            operator=identity["username"],
            comment=body.comment,
            execution_result=execution_result,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="待审批操作不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="该操作已经完成审批") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="案件智能体尚未就绪") from exc


@router.post(f"{settings.api_prefix}/case-spaces/{{case_id}}/agent/actions/{{action_id}}/restore")
async def restore_case_agent_delete(
    case_id: int,
    action_id: str,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """恢复经智能体审批执行的逻辑删除，并保留完整审计链。"""
    from app.agent_mcp.auth import require_human_decision
    from app.core.permissions import _ensure_record_module, _require_case_agent_action_access

    require_human_decision(action_id)
    await _ensure_record_module(case_id, "case", identity, db)
    context = await get_case_space_context(case_id, identity, db)
    import hashlib
    audit_serial = "AGENT-" + hashlib.sha256(f"{case_id}:{action_id}".encode("utf-8")).hexdigest()[:40]
    audit = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "agent_action", BusinessRecord.serial_no == audit_serial,
    ).with_for_update())
    if not audit or audit.status != "已执行":
        raise HTTPException(status_code=409, detail="该智能体删除操作不可恢复或已经恢复")
    audit_data = dict(audit.data or {})
    action_type = str(audit_data.get("action_type") or "")
    if action_type not in {"case.delete", "customer.delete", "contract.delete"}:
        raise HTTPException(status_code=422, detail="该操作不是逻辑删除")
    _require_case_agent_action_access(action_type, context.get("capabilities") or {})
    result = audit_data.get("execution_result") if isinstance(audit_data.get("execution_result"), dict) else {}
    target_id = int(result.get("record_id") or 0)
    module = action_type.split(".", 1)[0]
    target = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.id == target_id, BusinessRecord.module == module,
    ).with_for_update())
    if not target or target.status != "已删除":
        raise HTTPException(status_code=409, detail="目标记录当前不是可恢复的逻辑删除状态")
    target_data = dict(target.data or {})
    restored_status = str(target_data.pop("status_before_delete", "") or "草稿")
    for key in ("deleted_at", "deleted_by", "delete_reason"):
        target_data.pop(key, None)
    target.status = restored_status
    target.data = target_data
    audit.status = "已恢复"
    audit.data = {**audit_data, "restored_by": identity["username"], "restored_at": datetime.now(timezone.utc).isoformat()}
    db.add(WorkflowEvent(
        record_id=target.id, action="恢复智能体逻辑删除", from_status="已删除", to_status=restored_status,
        operator=identity["username"], comment=f"恢复智能体操作 {action_id}",
    ))
    await db.commit()
    return {"record_id": target.id, "status": target.status, "restored": True}
