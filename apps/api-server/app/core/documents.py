"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    AGENT_CASE_DATA_FIELDS, AGENT_CASE_UPDATE_FIELDS, AI_SPACE_CATEGORY, ARCHIVE_REQUIRED_CATEGORIES, CASE_CUSTOM_DOCUMENT_FOLDERS_KEY,
    CASE_DOCUMENT_FOLDER_HEADERS, CASE_DOCUMENT_TYPES, CASE_FORMAL_DOCUMENT_FOLDERS, CASE_FORMAL_DOCUMENT_FOLDER_ORDER, CASE_INVESTIGATION_DOCUMENT_FOLDERS,
    CASE_LEGACY_LAW_FIRM_LETTER_TYPES, CUSTOMER_CREATE_DATA_FIELDS, SEAL_ACTION_CODES, SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY,
    SEAL_USE_TYPES, WORD_EDITOR_LOCK_SECONDS,
)
from app.core.dependencies import (
    AgentDocument, AsyncSession, BusinessRecord, CaseTypeFileTypeRelation, Document,
    DocumentTemplate, FileAttachment, HTTPException, Pt, SealAsset,
    SealAssetAudit, SystemConfig, SystemParameter, User, WD_ALIGN_PARAGRAPH,
    WorkflowEvent, datetime, func, hashlib, httpx,
    io, or_, qn, re, secrets,
    select, settings, timedelta, timezone, update,
    user_skill_config_key, uuid4,
)
from app.models_shared import (
    CaseLitigantAgentInput, CaseReminderInput, ContractDraftInput, CustomerPatchInput, SealApplicationInput,
    TaskInput, WordEditorTextBlockInput,
)


def _template_dict(item: DocumentTemplate) -> dict:
    return {"id": item.id, "name": item.name, "category": item.category, "version": item.version, "description": item.description, "fields": item.fields or [], "is_active": item.is_active, "created_at": item.created_at, "updated_at": item.updated_at}


async def _sync_case_document_readiness(case_record: BusinessRecord, db: AsyncSession) -> bool:
    categories = set((await db.scalars(select(FileAttachment.category).where(
        FileAttachment.record_id == case_record.id,
        FileAttachment.category != AI_SPACE_CATEGORY,
    ))).all())
    complete = ARCHIVE_REQUIRED_CATEGORIES.issubset(categories)
    case_record.data = {**(case_record.data or {}), "documents_complete": complete, "archive_material_categories": sorted(categories)}
    return complete


def _fill_template(template_content: str, data: dict) -> str:
    result = template_content
    for key, value in data.items():
        placeholder = "{{" + key + "}}"
        if placeholder in result:
            result = result.replace(placeholder, str(value) if value is not None else "")
    import re
    result = re.sub(r"\{\{[^}]+\}\}", "", result)
    return result


def _build_case_template_data(case_record: BusinessRecord) -> dict:
    from app.core.system import (
        _record_dict,
    )
    data = case_record.data or {}
    case_data = _record_dict(case_record, set())
    return {
        "case_no": case_data.get("serial_no", ""),
        "case_type": data.get("case_type", ""),
        "customer_name": data.get("customer", ""),
        "plaintiff_name": data.get("plaintiff", data.get("customer", "")),
        "defendant_name": data.get("defendant", ""),
        "opposite_name": data.get("defendant", ""),
        "handling_lawyer": ",".join(data.get("handling_lawyers") or []) if data.get("handling_lawyers") else "",
        "hearing_lawyer": data.get("hearing_lawyer", ""),
        "source_lawyer": data.get("source_lawyer", ""),
        "assistant": data.get("assistant", ""),
        "case_stage": data.get("case_stage", case_record.status),
        "litigation_amount": data.get("litigation_amount", ""),
        "contract_amount": data.get("contract_amount", ""),
        "received_amount": data.get("received_amount", ""),
        "outstanding_amount": data.get("outstanding_amount", ""),
        "refund_amount": data.get("refund_amount", ""),
        "commission_rate": data.get("commission_rate", ""),
        "commission_amount": data.get("commission_amount", ""),
        "court": data.get("court", ""),
        "law_firm_name": data.get("law_firm_name", "律师事务所"),
        "entrust_matter": data.get("entrust_matter", "代为进行诉讼活动，包括起诉、应诉、参加庭审、调解、和解等"),
        "entrust_authority": data.get("entrust_authority", "一般授权：代为调查取证、查阅案件材料、参加庭审、进行和解、调解；特别授权：代为承认、放弃、变更诉讼请求，进行和解，提起反诉或上诉，代收诉讼文书，代领标的款物"),
        "entrust_deadline": data.get("entrust_deadline", "本案一审终结"),
        "other_terms": data.get("other_terms", "无"),
        "sign_date": data.get("sign_date", ""),
        "recipient_unit": data.get("recipient_unit", data.get("court", "")),
        "subject_name": data.get("subject_name", data.get("customer", "")),
        "credit_code": data.get("credit_code", ""),
        "subject_address": data.get("subject_address", ""),
        "legal_representative": data.get("legal_representative", ""),
        "representative_title": data.get("representative_title", "法定代表人"),
        "review_comment": data.get("review_comment", ""),
    }


def _clean_case_litigant_agents(values: list[CaseLitigantAgentInput | str]) -> list[dict[str, str]]:
    """Normalize legacy name-only agents into the detailed case JSON format."""
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for value in values:
        if isinstance(value, str):
            agent = {"name": value.strip(), "law_firm": "", "position": "", "phone": "", "authority": ""}
        else:
            agent = {
                "name": value.name.strip(),
                "law_firm": value.law_firm.strip(),
                "position": value.position.strip(),
                "phone": value.phone.strip(),
                "authority": value.authority.strip(),
            }
        if not agent["name"]:
            raise HTTPException(status_code=422, detail="代理人姓名不能为空")
        key = tuple(agent[field] for field in ("name", "law_firm", "position", "phone", "authority"))
        if key not in seen:
            seen.add(key)
            result.append(agent)
    return result


async def _user_agent_skill_store(username: str, db: AsyncSession) -> tuple[SystemConfig | None, list[dict]]:
    key = user_skill_config_key(username)
    item = await db.scalar(select(SystemConfig).where(SystemConfig.key == key))
    value = item.value if item else {}
    if item and str(value.get("owner_username") or "").strip().casefold() != username.strip().casefold():
        raise HTTPException(status_code=403, detail="个人技能库归属校验失败")
    skills = value.get("skills") or []
    return item, [dict(skill) for skill in skills if isinstance(skill, dict)]


async def _save_user_agent_skills(username: str, skills: list[dict], identity: dict, db: AsyncSession) -> None:
    from app.core.system import (
        _system_audit,
    )
    key = user_skill_config_key(username)
    item = await db.scalar(select(SystemConfig).where(SystemConfig.key == key))
    value = {"owner_username": username, "skills": skills}
    if item:
        item.value = value
        item.updated_by = username
    else:
        db.add(SystemConfig(
            key=key,
            label="个人智能体技能库",
            group="智能体",
            value=value,
            description="当前账号创建或上传的声明式智能体技能",
            updated_by=username,
        ))
    await _system_audit(db, identity, "更新个人智能体技能", f"个人技能库:{username}", {"skill_count": len(skills)})
    await db.commit()


def _case_agent_changes(payload: dict) -> dict:
    changes = payload.get("changes") if isinstance(payload.get("changes"), dict) else payload
    if not isinstance(changes, dict) or not changes:
        raise HTTPException(status_code=422, detail="智能体操作没有可执行的字段变更")
    return changes


async def _execute_case_agent_action(
    case_record: BusinessRecord,
    action: dict,
    identity: dict,
    db: AsyncSession,
    context: dict | None = None,
) -> dict:
    from app.areas.contract.router import (
        update_contract_draft,
    )
    from app.areas.crm.router import (
        patch_customer,
    )
    from app.areas.legal.router import (
        create_case_reminder,
    )
    from app.areas.tp.router import (
        create_task,
    )
    from app.core.formatters import (
        _case_agent_date, _case_agent_required_text,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    action_type = str(action.get("type") or "")
    payload = action.get("payload") or {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="智能体操作参数格式错误")

    if action_type == "customer.update":
        target_id = int(payload.get("target_id") or 0)
        linked_customer = (context or {}).get("customer") or {}
        if not target_id or int(linked_customer.get("id") or 0) != target_id:
            raise HTTPException(status_code=404, detail="目标客户不属于当前案件空间")
        changes = _case_agent_changes(payload)
        changes.pop("target_id", None)
        invalid = sorted(set(changes) - ({"description"} | CUSTOMER_CREATE_DATA_FIELDS))
        if invalid:
            raise HTTPException(status_code=422, detail=f"智能体无权修改客户字段：{', '.join(invalid)}")
        description = changes.pop("description", None)
        updated = await patch_customer(
            target_id,
            CustomerPatchInput(description=description, data=changes),
            identity,
            db,
        )
        return {"record_id": target_id, "operation": action_type, "updated_fields": {**changes, **({"description": description} if description is not None else {})}, "record": updated}

    if action_type == "contract.update":
        target_id = int(payload.get("target_id") or 0)
        linked_contract = next((item for item in (context or {}).get("contracts") or [] if int(item.get("id") or 0) == target_id), None)
        if not target_id or not linked_contract:
            raise HTTPException(status_code=404, detail="目标合同不属于当前案件空间")
        changes = _case_agent_changes(payload)
        changes.pop("target_id", None)
        invalid = sorted(set(changes) - {"title", "description", "data"})
        if invalid:
            raise HTTPException(status_code=422, detail=f"智能体无权修改合同字段：{', '.join(invalid)}")
        data_changes = changes.get("data") or {}
        if not isinstance(data_changes, dict):
            raise HTTPException(status_code=422, detail="合同资料变更必须为字段对象")
        protected = {"contract_guid", "customer_id", "customer_no", "customer_manager", "approval_steps", "current_approver", "investigation_ids"}
        if protected.intersection(data_changes):
            raise HTTPException(status_code=422, detail="智能体不能修改合同关系或审批控制字段")
        current = await _ensure_record_module(target_id, "contract", identity, db)
        updated = await update_contract_draft(
            target_id,
            ContractDraftInput(
                serial_no=current.serial_no,
                title=str(changes.get("title", current.title)),
                customer=current.customer,
                owner=current.owner,
                department=current.department,
                description=str(changes.get("description", current.description or "")),
                data={**(current.data or {}), **data_changes},
            ),
            identity,
            db,
        )
        return {"record_id": target_id, "operation": action_type, "updated_fields": changes, "record": updated}

    if action_type == "case.update":
        changes = _case_agent_changes(payload)
        invalid = sorted(set(changes) - AGENT_CASE_UPDATE_FIELDS)
        if invalid:
            raise HTTPException(status_code=422, detail=f"智能体无权修改字段：{', '.join(invalid)}")
        before_status = case_record.status
        applied = {}
        limits = {"title": 255, "customer": 255, "status": 32, "description": 5000}
        for field, value in changes.items():
            normalized = str(value or "").strip()
            if field in {"title", "status"} and not normalized:
                raise HTTPException(status_code=422, detail=f"{field}不能为空")
            if len(normalized) > limits[field]:
                raise HTTPException(status_code=422, detail=f"{field}内容过长")
            setattr(case_record, field, normalized)
            applied[field] = normalized
        db.add(WorkflowEvent(
            record_id=case_record.id,
            action="智能体审批后更新案件",
            from_status=before_status,
            to_status=case_record.status,
            operator=identity["username"],
            comment=f"操作：{action.get('summary', '')}；字段：{', '.join(applied)}",
        ))
        await db.commit()
        await db.refresh(case_record)
        return {"record_id": case_record.id, "operation": action_type, "updated_fields": applied}

    if action_type == "case.data.update":
        changes = _case_agent_changes(payload)
        invalid = sorted(set(changes) - AGENT_CASE_DATA_FIELDS)
        if invalid:
            raise HTTPException(status_code=422, detail=f"智能体无权修改案件扩展字段：{', '.join(invalid)}")
        normalized_changes = {}
        for field, value in changes.items():
            if isinstance(value, (dict, list)):
                raise HTTPException(status_code=422, detail=f"{field}不接受复合数据")
            normalized = value if isinstance(value, (bool, int, float)) else str(value or "").strip()
            if isinstance(normalized, str) and len(normalized) > 1000:
                raise HTTPException(status_code=422, detail=f"{field}内容过长")
            normalized_changes[field] = normalized
        case_record.data = {**(case_record.data or {}), **normalized_changes}
        db.add(WorkflowEvent(
            record_id=case_record.id,
            action="智能体审批后更新案件信息",
            from_status=case_record.status,
            to_status=case_record.status,
            operator=identity["username"],
            comment=f"操作：{action.get('summary', '')}；字段：{', '.join(normalized_changes)}",
        ))
        await db.commit()
        await db.refresh(case_record)
        return {"record_id": case_record.id, "operation": action_type, "updated_fields": normalized_changes}

    if action_type == "case.task.create":
        collaborators = payload.get("collaborators") or []
        if not isinstance(collaborators, list):
            raise HTTPException(status_code=422, detail="协作人必须为人员列表")
        task = await create_task(TaskInput(
            title=_case_agent_required_text(payload.get("title"), "任务名称", 255),
            owner=_case_agent_required_text(payload.get("owner"), "任务负责人", 128),
            deadline=_case_agent_date(payload.get("deadline"), "任务截止日期"),
            priority=str(payload.get("priority") or "普通").strip(),
            source="案件任务",
            collaborators=[str(item).strip() for item in collaborators if str(item).strip()],
            case_no=case_record.serial_no,
            description=str(payload.get("description") or "").strip(),
        ), identity, db)
        return {"record_id": task.get("id"), "operation": action_type, "serial_no": task.get("serial_no")}

    if action_type == "case.reminder.create":
        reminder = await create_case_reminder(case_record.id, CaseReminderInput(
            content=_case_agent_required_text(payload.get("content"), "提醒内容"),
            reminder_date=_case_agent_date(payload.get("reminder_date"), "提醒日期"),
            deadline=_case_agent_date(payload.get("deadline"), "截止日期"),
        ), identity, db)
        return {"record_id": reminder.get("id"), "operation": action_type, "serial_no": reminder.get("serial_no")}

    raise HTTPException(status_code=422, detail="该智能体操作类型不在系统白名单中")


async def _sync_seal_document_names(record: BusinessRecord, db: AsyncSession) -> None:
    """Keep the legacy file-name projection derived from real seal attachments."""
    files = (await db.scalars(
        select(FileAttachment.original_name)
        .where(FileAttachment.record_id == record.id, FileAttachment.category == "用印文件")
        .order_by(FileAttachment.created_at, FileAttachment.id)
    )).all()
    record.data = {**(record.data or {}), "document_names": "、".join(files)}


def _case_custom_document_folders(record: BusinessRecord) -> list[str]:
    values = (record.data or {}).get(CASE_CUSTOM_DOCUMENT_FOLDERS_KEY) or []
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(str(value or "").strip() for value in values if str(value or "").strip()))


async def _case_related_document_record(record: BusinessRecord, module: str, db: AsyncSession) -> BusinessRecord | None:
    data = record.data or {}
    id_keys = ("customer_record_id", "customer_id") if module == "customer" else ("contract_record_id", "contract_id")
    for key in id_keys:
        related_id = int(data.get(key) or 0)
        if related_id:
            related = await db.get(BusinessRecord, related_id)
            if related and related.module == module:
                return related
    if module == "customer" and str(record.customer or "").strip():
        return await db.scalar(select(BusinessRecord).where(
            BusinessRecord.module == "customer", BusinessRecord.title == str(record.customer).strip(),
        ).order_by(BusinessRecord.id.desc()))
    contract_no = str(data.get("contract_no") or "").strip()
    if module == "contract" and contract_no:
        return await db.scalar(select(BusinessRecord).where(
            BusinessRecord.module == "contract", BusinessRecord.serial_no == contract_no,
        ).order_by(BusinessRecord.id.desc()))
    return None


async def _case_formal_document_folder_payload(record: BusinessRecord, db: AsyncSession) -> dict:
    from app.core.cases import (
        _case_type_parameter_for_value,
    )
    file_types = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "case_file_type",
        SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.id))).all())
    case_type = await _case_type_parameter_for_value(str((record.data or {}).get("case_type") or ""), db)
    if case_type:
        configured_count = int(await db.scalar(select(func.count()).select_from(CaseTypeFileTypeRelation).where(
            CaseTypeFileTypeRelation.case_type_id == case_type.id,
        )) or 0)
        if configured_count:
            allowed_ids = set((await db.scalars(select(CaseTypeFileTypeRelation.file_type_id).where(
                CaseTypeFileTypeRelation.case_type_id == case_type.id,
            ))).all())
            file_types = [item for item in file_types if item.id in allowed_ids]
    case_candidates = [
        *CASE_FORMAL_DOCUMENT_FOLDER_ORDER,
        *(str(item.name or "").strip() for item in file_types),
        *_case_custom_document_folders(record),
        "普通附件",
    ]
    case_folders = list(dict.fromkeys(
        name for name in case_candidates
        if name and name != AI_SPACE_CATEGORY and name not in CASE_DOCUMENT_FOLDER_HEADERS
        and name not in CASE_INVESTIGATION_DOCUMENT_FOLDERS
    ))
    customer_record = await _case_related_document_record(record, "customer", db)
    contract_record = await _case_related_document_record(record, "contract", db)
    # Upload choices are a catalog, not evidence that a case has those folders.
    # Query all persisted categories, independently of the attachment page size
    # and active type catalog, so historical document categories remain visible.
    attachment_categories = (await db.scalars(
        select(FileAttachment.category)
        .where(FileAttachment.record_id == record.id)
        .distinct().order_by(FileAttachment.category)
    )).all()
    visible_case_folders = list(dict.fromkeys(
        name for name in [
            *CASE_FORMAL_DOCUMENT_FOLDER_ORDER,
            *_case_custom_document_folders(record),
            *(str(category or "").strip() for category in attachment_categories),
        ]
        if name and name != AI_SPACE_CATEGORY and name not in CASE_DOCUMENT_FOLDER_HEADERS
        and name not in CASE_INVESTIGATION_DOCUMENT_FOLDERS
    ))
    tree = [
        {"label": "客户文档", "value": "客户文档", "disabled": customer_record is None},
        {"label": "合同文档", "value": "合同文档", "disabled": contract_record is None},
        {"label": "调查文档", "value": "调查文档全部", "options": [
            {"label": name, "value": name} for name in CASE_INVESTIGATION_DOCUMENT_FOLDERS
        ]},
        {"label": "案件文档", "value": "案件文档全部", "options": [
            {"label": name, "value": name} for name in visible_case_folders
        ]},
    ]
    folders = [
        *(["客户文档"] if customer_record else []),
        *(["合同文档"] if contract_record else []),
        *CASE_INVESTIGATION_DOCUMENT_FOLDERS,
        *case_folders,
    ]
    return {"folders": folders, "tree": tree}


def _word_editor_now() -> datetime:
    """Use naive UTC because SQLite drops timezone data while PostgreSQL accepts it."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _word_editor_paragraph_editable(paragraph) -> bool:
    """Only permit plain w:p/w:r text; preserve every other Word construct."""
    allowed_paragraph_children = {"pPr", "r"}
    allowed_run_children = {"rPr", "t", "tab", "br", "cr"}
    if any(child.tag.rsplit("}", 1)[-1] not in allowed_paragraph_children for child in paragraph._p):
        return False
    return all(
        child.tag.rsplit("}", 1)[-1] in allowed_run_children
        for run in paragraph.runs for child in run._r
    )


def _word_editor_blocks(document: Document) -> list[dict]:
    """Return stable editable text locations without flattening a DOCX file."""
    blocks: list[dict[str, str]] = []

    def block_value(block_id: str, paragraph) -> dict:
        editable = _word_editor_paragraph_editable(paragraph)
        return {
            "id": block_id, "text": paragraph.text, "editable": editable,
            "read_only_reason": "该段落包含非纯文本 Word 结构，在线编辑会保护其原有内容" if not editable else "",
        }

    def add_paragraphs(paragraphs, prefix: str) -> None:
        for index, paragraph in enumerate(paragraphs):
            blocks.append(block_value(f"{prefix}/p:{index}", paragraph))

    seen_cells: set[object] = set()

    def add_tables(tables, prefix: str) -> None:
        for table_index, table in enumerate(tables):
            table_prefix = f"{prefix}/t:{table_index}"
            for row_index, row in enumerate(table.rows):
                for cell_index, cell in enumerate(row.cells):
                    cell_key = cell._tc
                    if cell_key in seen_cells:
                        continue
                    seen_cells.add(cell_key)
                    cell_prefix = f"{table_prefix}/r:{row_index}/c:{cell_index}"
                    add_paragraphs(cell.paragraphs, cell_prefix)
                    add_tables(cell.tables, cell_prefix)

    add_paragraphs(document.paragraphs, "body")
    add_tables(document.tables, "body")
    return blocks


def _word_editor_version(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _replace_word_editor_blocks(document: Document, requested_blocks: list[WordEditorTextBlockInput]) -> None:
    """Update only identified paragraphs, retaining all unedited DOCX XML."""
    requested = {item.id: item.text for item in requested_blocks}
    if len(requested) != len(requested_blocks):
        raise HTTPException(status_code=422, detail="Word 编辑内容包含重复文本块")

    paragraphs: dict[str, object] = {}

    def add_paragraphs(values, prefix: str) -> None:
        for index, paragraph in enumerate(values):
            paragraphs[f"{prefix}/p:{index}"] = paragraph

    seen_cells: set[object] = set()

    def add_tables(tables, prefix: str) -> None:
        for table_index, table in enumerate(tables):
            table_prefix = f"{prefix}/t:{table_index}"
            for row_index, row in enumerate(table.rows):
                for cell_index, cell in enumerate(row.cells):
                    cell_key = cell._tc
                    if cell_key in seen_cells:
                        continue
                    seen_cells.add(cell_key)
                    cell_prefix = f"{table_prefix}/r:{row_index}/c:{cell_index}"
                    add_paragraphs(cell.paragraphs, cell_prefix)
                    add_tables(cell.tables, cell_prefix)

    add_paragraphs(document.paragraphs, "body")
    add_tables(document.tables, "body")
    if set(requested) != set(paragraphs):
        raise HTTPException(status_code=409, detail="Word 文档结构已变化，请重新打开后再保存")
    for block_id, paragraph in paragraphs.items():
        replacement = requested[block_id]
        if paragraph.text == replacement:
            continue
        if not _word_editor_paragraph_editable(paragraph):
            raise HTTPException(status_code=422, detail="含非纯文本 Word 结构的段落暂不支持修改；未修改的内容会原样保留")
        runs = paragraph.runs
        if runs:
            # Preserve paragraph properties and the original first-run formatting.
            runs[0].text = replacement
            for run in runs[1:]:
                run.text = ""
        else:
            paragraph.add_run(replacement)


def _word_editor_lock_payload(item: FileAttachment, *, include_token: bool = False) -> dict:
    payload = {
        "lock_holder": item.word_editor_locked_by or "",
        "lock_expires_at": item.word_editor_lock_expires_at.isoformat() if item.word_editor_lock_expires_at else "",
    }
    if include_token:
        payload["lock_token"] = item.word_editor_lock_token
    return payload


async def _acquire_case_word_editor_lock(item: FileAttachment, identity: dict, db: AsyncSession) -> FileAttachment:
    """Acquire one DB-backed lease using a conditional UPDATE for multi-process safety."""
    now = _word_editor_now()
    expires_at = now + timedelta(seconds=WORD_EDITOR_LOCK_SECONDS)
    token = secrets.token_urlsafe(48)
    attachment_id = item.id
    result = await db.execute(update(FileAttachment).where(
        FileAttachment.id == item.id,
        or_(
            FileAttachment.word_editor_lock_token == "",
            FileAttachment.word_editor_lock_expires_at.is_(None),
            FileAttachment.word_editor_lock_expires_at <= now,
        ),
    ).values(
        word_editor_lock_token=token,
        word_editor_locked_by=identity["username"],
        word_editor_lock_expires_at=expires_at,
    ).execution_options(synchronize_session=False))
    if not result.rowcount:
        await db.rollback()
        current = await db.get(FileAttachment, attachment_id)
        detail = "该 Word 文件正在由其他会话编辑"
        if current and current.word_editor_locked_by == identity["username"]:
            detail = "该 Word 文件已在另一个页面编辑，请在原页面继续"
        raise HTTPException(status_code=409, detail={"message": detail, **_word_editor_lock_payload(current or item)})
    await db.commit()
    await db.refresh(item)
    return item


async def _validate_case_formal_document_category(
    case_record: BusinessRecord, category: str, db: AsyncSession,
) -> str:
    from app.core.cases import (
        _case_type_parameter_for_value,
    )
    target = str(category or "").strip()
    if not target or target == AI_SPACE_CATEGORY or (
        target in CASE_DOCUMENT_FOLDER_HEADERS and target not in {"客户文档", "合同文档", "调查文档"}
    ):
        raise HTTPException(status_code=422, detail="请选择具体的正式案件文档目录")
    if target in {"客户文档", "合同文档"}:
        module = "customer" if target == "客户文档" else "contract"
        if not await _case_related_document_record(case_record, module, db):
            raise HTTPException(status_code=422, detail=f"当前案件未关联可用的{target}")
        return target
    if target in CASE_INVESTIGATION_DOCUMENT_FOLDERS:
        return target
    if target == "普通附件" or target in CASE_FORMAL_DOCUMENT_FOLDERS or target in _case_custom_document_folders(case_record):
        return target
    file_types = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "case_file_type",
        SystemParameter.name == target,
        SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.id))).all())
    if not file_types:
        raise HTTPException(status_code=422, detail="正式案件文档目录不存在或已停用")
    case_type = await _case_type_parameter_for_value(str((case_record.data or {}).get("case_type") or ""), db)
    if not case_type:
        return target
    configured_count = int(await db.scalar(select(func.count()).select_from(CaseTypeFileTypeRelation).where(
        CaseTypeFileTypeRelation.case_type_id == case_type.id,
    )) or 0)
    if not configured_count:
        return target
    allowed_ids = set((await db.scalars(select(CaseTypeFileTypeRelation.file_type_id).where(
        CaseTypeFileTypeRelation.case_type_id == case_type.id,
    ))).all())
    if not any(item.id in allowed_ids for item in file_types):
        raise HTTPException(status_code=422, detail="该案件类型不允许使用所选正式文档目录")
    return target


def _seal_asset_dict(item: SealAsset) -> dict:
    return {"id": item.id, "code": item.code, "name": item.name, "seal_type": item.seal_type, "custodian": item.custodian, "location": item.location, "status": item.status, "usage_count": item.usage_count, "last_used_at": item.last_used_at, "remark": item.remark, "created_at": item.created_at, "updated_at": item.updated_at}


def _seal_asset_audit_dict(item: SealAssetAudit) -> dict:
    return {"id": item.id, "asset_id": item.asset_id, "asset_code": item.asset_code, "asset_name": item.asset_name, "action": item.action, "operator": item.operator, "comment": item.comment, "created_at": item.created_at}


def _seal_legacy_file_names(record: BusinessRecord) -> list[str]:
    """Read legacy file-name projections so historical seal rows keep their counts."""
    data = record.data or {}
    values: list[object] = []

    def append(value: object) -> None:
        if not value:
            return
        if isinstance(value, list):
            for item in value:
                append(item)
            return
        if isinstance(value, dict):
            append(value.get("original_name") or value.get("file_name") or value.get("FileName") or value.get("name"))
            return
        values.append(value)

    for key in ("file_names", "fileNames", "attachments", "files"):
        append(data.get(key))
    if record.status not in {"已用印", "已归档"}:
        for key in ("document_names", "documentNames"):
            append(data.get(key))

    names: list[str] = []
    for value in values:
        for item in re.split(r"[\n\r,;，、]+", str(value)):
            item = item.strip()
            if item and item not in names:
                names.append(item)
    return names


async def _seal_record_dict(
    record: BusinessRecord,
    db: AsyncSession,
    users_by_username: dict[str, User] | None = None,
    identity: dict | None = None,
    attachments_by_record: dict[int, list[FileAttachment]] | None = None,
    assets_by_id: dict[int, SealAsset] | None = None,
    authorization_context: dict | None = None,
) -> dict:
    from app.core.formatters import (
        _apply_record_person_displays, _user_display_map,
    )
    from app.core.permissions import (
        _seal_application_capabilities,
    )
    from app.core.system import (
        _record_dict, _record_person_usernames,
    )
    if users_by_username is None:
        users_by_username = await _user_display_map(_record_person_usernames(record), db)
    result = _apply_record_person_displays(_record_dict(record), record, users_by_username)
    visible_files = attachments_by_record.get(record.id, []) if attachments_by_record is not None else list((await db.scalars(
        select(FileAttachment)
        .where(
            FileAttachment.record_id == record.id,
            FileAttachment.category.in_({SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY}),
        )
        .order_by(FileAttachment.created_at, FileAttachment.id)
    )).all())
    application_files = [item for item in visible_files if item.category == SEAL_APPLICATION_FILE_CATEGORY]
    stamped_files = [item for item in visible_files if item.category == SEAL_STAMPED_FILE_CATEGORY]
    application_names = list(dict.fromkeys(item.original_name for item in application_files if item.original_name))
    stamped_names = list(dict.fromkeys(item.original_name for item in stamped_files if item.original_name))
    result["file_count"] = len(visible_files)
    result["application_file_count"] = len(application_files)
    result["stamped_file_count"] = len(stamped_files)
    result["application_file_names"] = application_names
    result["stamped_file_names"] = stamped_names
    result["file_category"] = "用印附件"
    result["data"] = {
        **(result.get("data") or {}),
        "file_names": [*application_names, *(name for name in stamped_names if name not in application_names)],
        "application_file_names": application_names,
        "stamped_file_names": stamped_names,
        "file_category": "用印附件",
    }
    asset_id = int((record.data or {}).get("seal_asset_id") or 0)
    asset = assets_by_id.get(asset_id) if assets_by_id is not None else (await db.get(SealAsset, asset_id) if asset_id else None)
    result["seal_asset"] = _seal_asset_dict(asset) if asset else None
    if identity is not None:
        capabilities = await _seal_application_capabilities(record, identity, db, authorization_context)
        result["capabilities"] = capabilities
        result["action_keys"] = [key for key in ("approve", "reject", "stamp", "archive") if capabilities.get(key)]
    return result


async def _seal_authorization_context(identity: dict, db: AsyncSession) -> dict:
    """Use the common role action-key payload for every seal workflow decision."""
    from app.core.permissions import (
        _permission_payload_for_identity,
    )
    permission = await _permission_payload_for_identity(identity, db)
    action_keys = set(permission.get("action_keys") or [])
    granted = {name: ("*" in action_keys or code in action_keys) for name, code in SEAL_ACTION_CODES.items()}
    return {"identity": identity, "action_keys": action_keys, **granted}


async def _user_has_seal_action(user: User, action: str, db: AsyncSession) -> bool:
    from app.core.permissions import (
        _user_permission_payload,
    )
    if not user.is_active:
        return False
    permission = await _user_permission_payload(user, db)
    keys = set(permission.get("action_keys") or [])
    return "*" in keys or SEAL_ACTION_CODES[action] in keys


async def _get_seal_application_for_action(record_id: int, action: str, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.permissions import (
        _seal_application_capabilities,
    )
    item = await db.get(BusinessRecord, record_id)
    if not item or item.module != "seal":
        raise HTTPException(status_code=404, detail="用印申请不存在或无权访问")
    capabilities = await _seal_application_capabilities(item, identity, db)
    if not capabilities.get(action):
        raise HTTPException(status_code=403, detail="当前账号没有执行该用印操作的权限")
    return item


async def _validated_seal_relations(body: SealApplicationInput, identity: dict, db: AsyncSession) -> tuple[str, str, str, str, int | None, int | None, int | None]:
    """Return canonical, visible seal references and prevent dangling business links."""
    from app.core.contracts import (
            _single_linked_case_for_contract,
        )
    from app.core.permissions import (
            _ensure_record_module, _record_scope_conditions,
        )
    from app.core.system import (
            _positive_record_id,
        )
    case_no, contract_no, customer = body.case_no.strip(), body.contract_no.strip(), body.customer.strip()
    use_type = body.use_type.strip() or ("案件用印" if case_no else "合同用印" if contract_no else "行政用印")
    if use_type not in SEAL_USE_TYPES:
        raise HTTPException(status_code=422, detail="用印类型无效")
    scope = await _record_scope_conditions(identity, db)

    async def visible(module: str, serial_no: str, label: str) -> BusinessRecord:
        row = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == module, BusinessRecord.serial_no == serial_no, *scope))
        if not row:
            raise HTTPException(status_code=422, detail=f"关联{label}不存在或当前账号无权使用")
        return row

    if use_type == "案件用印" and not case_no:
        raise HTTPException(status_code=422, detail="案件用印必须选择关联案件")
    if use_type == "合同用印" and not contract_no:
        raise HTTPException(status_code=422, detail="合同用印必须选择关联合同")
    case = await visible("case", case_no, "案件") if case_no else None
    contract = await visible("contract", contract_no, "合同") if contract_no else None
    if case:
        case_data = case.data or {}
        linked_contract_id = _positive_record_id(case_data.get("contract_record_id") or case_data.get("contract_id"))
        linked_contract_no = str(case_data.get("contract_no") or "").strip()
        linked_contract = None
        if linked_contract_id:
            linked_contract = await _ensure_record_module(linked_contract_id, "contract", identity, db)
        elif linked_contract_no:
            linked_contract = await visible("contract", linked_contract_no, "合同")
        if contract and (not linked_contract or contract.id != linked_contract.id):
            raise HTTPException(status_code=422, detail="关联案件与合同不匹配")
        if linked_contract:
            contract = linked_contract
            contract_no = linked_contract.serial_no
    elif contract:
        linked_case = await _single_linked_case_for_contract(contract, identity, db)
        if linked_case:
            case = linked_case
            case_no = linked_case.serial_no
    customer_row = None
    if customer:
        customer_row = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "customer", or_(BusinessRecord.title == customer, BusinessRecord.customer == customer, BusinessRecord.serial_no == customer), *scope))
        if not customer_row:
            raise HTTPException(status_code=422, detail="关联客户不存在或当前账号无权使用")
        customer = customer_row.title or customer_row.customer
    elif case:
        customer = case.customer
    elif contract:
        customer = contract.customer
    if not customer_row:
        linked_customer_id = _positive_record_id(
            ((case.data or {}).get("customer_record_id") or (case.data or {}).get("customer_id")) if case else None
        ) or _positive_record_id(
            ((contract.data or {}).get("customer_record_id") or (contract.data or {}).get("customer_id")) if contract else None
        )
        if linked_customer_id:
            customer_row = await _ensure_record_module(linked_customer_id, "customer", identity, db)
        elif customer:
            customer_row = await db.scalar(select(BusinessRecord).where(
                BusinessRecord.module == "customer",
                or_(BusinessRecord.title == customer, BusinessRecord.customer == customer),
                *scope,
            ))
    return (
        case_no, contract_no, customer, use_type,
        case.id if case else None,
        contract.id if contract else None,
        customer_row.id if customer_row else None,
    )


async def _next_seal_application_serial(
    db: AsyncSession,
    applied_at: datetime | None = None,
) -> str:
    prefix = f"P{applied_at or datetime.now():%y%m%d}-"
    for _ in range(20):
        suffix = int(uuid4().hex, 16) % 100_000_000
        candidate = f"{prefix}{suffix:08d}"
        exists = await db.scalar(
            select(BusinessRecord.id).where(BusinessRecord.serial_no == candidate)
        )
        if not exists:
            return candidate
    raise HTTPException(status_code=503, detail="用印编号生成失败，请重试")


async def _get_seal_application(record_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.permissions import (
        _ensure_record_module,
    )
    try:
        return await _ensure_record_module(record_id, "seal", identity, db)
    except HTTPException as exc:
        if exc.status_code == 404: raise HTTPException(status_code=404, detail="用印申请不存在或无权访问") from exc
        raise


def _case_document_value(data: dict, *keys: str) -> str:
    for key in keys:
        item = data.get(key)
        if isinstance(item, list):
            item = "、".join(str(part).strip() for part in item if str(part).strip())
        if item is not None and str(item).strip():
            return str(item).strip()
    return ""


def _case_document_required_fields(record: BusinessRecord, document_type: str, context: dict) -> list[str]:
    data = record.data or {}
    common = [
        ("客户名称", record.customer),
        ("经办律师", context.get("case_lawyer")),
        ("被告", _case_document_value(data, "opponent", "defendant", "appellee", "respondent")),
        ("案由", _case_document_value(data, "cause_or_charge", "cause", "charge")),
    ]
    if document_type == "authorization-letter":
        return [label for label, value in common if not str(value or "").strip()]
    if document_type not in CASE_LEGACY_LAW_FIRM_LETTER_TYPES:
        return []
    if document_type.startswith("first-instance"):
        court = _case_document_value(data, "first_court_name", "first_instance_court", "court")
        court_label = "一审法院"
    elif document_type.startswith("second-instance"):
        court = _case_document_value(data, "second_court_name", "second_instance_court")
        court_label = "二审法院"
    else:
        court = _case_document_value(data, "execution_court_name", "execution_court")
        court_label = "执行法院"
    required = [
        (court_label, court),
        ("客户名称", record.customer),
        ("开庭律师", context.get("court_lawyer")),
        ("经办律师", context.get("case_lawyer")),
        ("律师助理", context.get("assistant")),
        ("原告", _case_document_value(data, "plaintiff", "appellant", "applicant")),
        ("被告", _case_document_value(data, "opponent", "defendant", "appellee", "respondent")),
        ("案由", _case_document_value(data, "cause_or_charge", "cause", "charge")),
    ]
    return [label for label, value in required if not str(value or "").strip()]


async def _case_document_context(record: BusinessRecord, db: AsyncSession) -> dict:
    data = record.data or {}
    company_config = await db.scalar(select(SystemConfig).where(SystemConfig.key == "company_profile"))
    company = dict(company_config.value or {}) if company_config else {}
    customer_record = None
    customer_id = data.get("customer_id")
    if customer_id:
        customer_record = await db.get(BusinessRecord, int(customer_id))
        if customer_record and customer_record.module != "customer":
            customer_record = None
    if not customer_record:
        customer_no = _case_document_value(data, "customer_no")
        customer_conditions = [BusinessRecord.module == "customer"]
        if customer_no:
            customer_conditions.append(or_(BusinessRecord.serial_no == customer_no, BusinessRecord.data["customer_no"].as_string() == customer_no))
        elif record.customer:
            customer_conditions.append(or_(BusinessRecord.title == record.customer, BusinessRecord.customer == record.customer))
        if len(customer_conditions) > 1:
            customer_record = await db.scalar(select(BusinessRecord).where(*customer_conditions).limit(1))
    customer_data = dict(customer_record.data or {}) if customer_record else {}
    handling_usernames = data.get("handling_lawyer_usernames") or []
    if isinstance(handling_usernames, str):
        handling_usernames = [handling_usernames]
    case_lawyer = _case_document_value(data, "handling_lawyers", "handling_lawyer")
    assistant = _case_document_value(data, "assistant", "case_assistant")
    court_lawyer = _case_document_value(data, "hearing_lawyer", "court_lawyer", "court_lawyer_name")
    username_keys = {str(value).strip() for value in [*(handling_usernames or []), data.get("assistant_username"), data.get("hearing_lawyer_username")] if str(value or "").strip()}
    users = list((await db.scalars(select(User).where(User.username.in_(username_keys)))).all()) if username_keys else []
    users_by_name = {user.username: user for user in users}
    primary_user = users_by_name.get(str(handling_usernames[0])) if handling_usernames else None
    assistant_user = users_by_name.get(str(data.get("assistant_username") or ""))
    if not case_lawyer and primary_user:
        case_lawyer = primary_user.display_name
    if not assistant and assistant_user:
        assistant = assistant_user.display_name
    case_lawyer_phone = _case_document_value(data, "handling_lawyer_mobile", "case_lawyer_mobile")
    assistant_phone = _case_document_value(data, "assistant_mobile")
    if not case_lawyer_phone and primary_user:
        case_lawyer_phone = str((primary_user.profile or {}).get("mobile") or "")
    if not assistant_phone and assistant_user:
        assistant_phone = str((assistant_user.profile or {}).get("mobile") or "")
    return {
        "company": {
            "name": str(company.get("name") or "上海申浩律师事务所"),
            "address": str(company.get("address") or ""),
            "phone": str(company.get("phone") or ""),
        },
        "customer": customer_data,
        "case_lawyer": case_lawyer,
        "court_lawyer": court_lawyer,
        "assistant": assistant,
        "case_lawyer_phone": case_lawyer_phone,
        "assistant_phone": assistant_phone,
    }


def _case_document_paragraph(document: Document, text: str = "", *, center: bool = False, bold: bool = False, size: int = 14):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.name = "SimSun"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(size)
    return paragraph


def _case_document_bytes(record: BusinessRecord, document_type: str, context: dict) -> tuple[str, bytes]:
    """Generate the formal legacy-equivalent case document, not a generic case summary."""
    from app.core.formatters import (
        _format_case_document,
    )
    title = CASE_DOCUMENT_TYPES[document_type]
    data = record.data or {}
    company = context["company"]
    case_lawyer = context.get("case_lawyer") or "（未填写）"
    assistant = context.get("assistant") or "（未填写）"
    plaintiff = _case_document_value(data, "plaintiff", "appellant", "applicant") or "（未填写）"
    defendant = _case_document_value(data, "opponent", "defendant", "appellee", "respondent") or "（未填写）"
    cause = _case_document_value(data, "cause_or_charge", "cause", "charge") or "（未填写）"
    today_cn = f"{datetime.now():%Y年%m月%d日}"
    document = Document()
    _format_case_document(document)
    document.core_properties.title = title
    document.core_properties.subject = f"案件 {record.serial_no} 系统生成文书"

    if document_type == "authorization-letter":
        _case_document_paragraph(document, "授权委托书", center=True, bold=True, size=22)
        _case_document_paragraph(document, f"委托人：{record.customer}")
        _case_document_paragraph(document, f"受委托人：{case_lawyer}")
        _case_document_paragraph(document, f"地址：{company.get('address') or '（公司设置未填写）'}")
        phones = "、".join(dict.fromkeys(value for value in [context.get("case_lawyer_phone"), context.get("assistant_phone")] if value)) or "（员工档案未填写）"
        _case_document_paragraph(document, f"联系电话：{phones}")
        third_party = _case_document_value(data, "third_party", "third_person", "the_third_names")
        opponents = "、".join(value for value in [defendant, third_party] if value)
        _case_document_paragraph(document, f"委托人兹委托{case_lawyer}为本委托人与{opponents}{cause}一案诉讼代理人。")
        _case_document_paragraph(document, "代理权限为特别授权，包括但不限于：", bold=True)
        for item in [
            "代为进行协商、谈判和签署有关和解协议；", "代为起草、签署、递交起诉状、财产保全申请书；", "代为申请撤诉；",
            "代为提起反诉；", "代为起草、签署、递交答辩状，提出答辩；", "代为起草、签署、递交上诉状，提出上诉；",
            "代为收集、提供有关证据材料，代为申请法院调查令；", "代为申请回避；", "出庭陈述事实，进行法庭辩论；",
            "提出、接受调解或和解；", "代为接受、放弃或变更诉讼请求；", "代为申请执行并收取执行款项；",
            "代为收取诉讼费退费、保全费退费、调解款、判赔款、执行款等；", "签收与本案有关的法律文件。",
        ]:
            _case_document_paragraph(document, item, size=12)
        _case_document_paragraph(document, "上述代理权限自本委托书签署之日起至本案纠纷全部处理结束之日止。代理人在上述授权范围内的一切行为、所签署的文件，委托人均予以承认并对委托人具有约束力。受托人有转委托权。", size=12)
        _case_document_paragraph(document, "")
        _case_document_paragraph(document, f"委托人：{record.customer}")
        _case_document_paragraph(document, f"日期：{today_cn}")
    elif document_type == "archive-cover":
        _case_document_paragraph(document, "案件卷宗", center=True, bold=True, size=28)
        _case_document_paragraph(document, f"案号：{record.serial_no}", center=True, size=18)
        _case_document_paragraph(document, f"案件名称：{record.title}", center=True, size=18)
        _case_document_paragraph(document, f"客户：{record.customer}", center=True, size=16)
        _case_document_paragraph(document, f"案件类型：{_case_document_value(data, 'case_type') or '（未填写）'}", center=True, size=16)
        _case_document_paragraph(document, f"经办律师：{case_lawyer}", center=True, size=16)
        _case_document_paragraph(document, f"归档日期：{_case_document_value(data, 'archive_date', 'archived_at') or today_cn}", center=True, size=16)
    elif document_type == "compensation-payment-application":
        _case_document_paragraph(document, "代收代付赔偿款申请单", center=True, bold=True, size=22)
        _case_document_paragraph(document, f"案件编号：{record.serial_no}")
        _case_document_paragraph(document, f"案件名称：{record.title}")
        _case_document_paragraph(document, f"客户名称：{record.customer}")
        _case_document_paragraph(document, f"收款/付款对象：{_case_document_value(data, 'compensation_counterparty', 'opponent', 'defendant') or '（未填写）'}")
        _case_document_paragraph(document, f"赔偿款金额：{_case_document_value(data, 'compensation_amount', 'settlement_amount') or '（未填写）'}")
        _case_document_paragraph(document, f"收款账户：{_case_document_value(data, 'compensation_account', 'payment_account') or '（未填写）'}")
        _case_document_paragraph(document, f"经办律师：{case_lawyer}")
        _case_document_paragraph(document, f"申请日期：{today_cn}")
        _case_document_paragraph(document, "申请说明：本申请依据案件已保存的赔偿、和解或执行回款信息生成，请财务审核后办理代收代付。")
    elif document_type in CASE_LEGACY_LAW_FIRM_LETTER_TYPES:
        if document_type.startswith("first-instance"):
            court = _case_document_value(data, "first_court_name", "first_instance_court", "court")
        elif document_type.startswith("second-instance"):
            court = _case_document_value(data, "second_court_name", "second_instance_court")
        else:
            court = _case_document_value(data, "execution_court_name", "execution_court")
        if document_type == "first-instance-appellant-lawyer-letter":
            parties = f"原告{plaintiff}与被告{defendant}"
            client_role = "原告"
        elif document_type == "first-instance-appellee-lawyer-letter":
            parties = f"原告{plaintiff}诉被告{defendant}"
            client_role = "被告"
        elif document_type == "second-instance-appellant-lawyer-letter":
            parties = f"上诉人{plaintiff}与被上诉人{defendant}"
            client_role = "上诉人"
        elif document_type == "second-instance-appellee-lawyer-letter":
            parties = f"上诉人{plaintiff}与被上诉人{defendant}"
            client_role = "被上诉人"
        else:
            parties = f"申请执行人{plaintiff}与被执行人{defendant}"
            client_role = "当事人"
        _case_document_paragraph(document, f"{company['name']} 函", center=True, bold=True, size=22)
        _case_document_paragraph(document, f"案号：{record.serial_no}")
        _case_document_paragraph(document, f"{court}：")
        _case_document_paragraph(document, f"{parties}{cause}一案贵院已受理，现{client_role}{record.customer}已委托本所{case_lawyer}律师为其代理人。")
        _case_document_paragraph(document, "特此函告！")
        _case_document_paragraph(document, "")
        _case_document_paragraph(document, company["name"])
        _case_document_paragraph(document, today_cn)
        phone_parts = [value for value in [context.get("case_lawyer_phone"), context.get("assistant_phone")] if value]
        phone_text = "、".join(dict.fromkeys(phone_parts)) or "（员工档案未填写）"
        _case_document_paragraph(document, f"附：经办律师{case_lawyer}，开庭律师{context.get('court_lawyer') or case_lawyer}，律师助理{assistant}；联系电话：{phone_text}", size=12)
    elif document_type == "identification_letter":
        # Basic editable letter until a dedicated approved template is supplied.
        _case_document_paragraph(document, title, center=True, bold=True, size=22)
        _case_document_paragraph(document, f"案件编号：{record.serial_no}")
        _case_document_paragraph(document, f"案件名称：{record.title}")
        _case_document_paragraph(document, "致：________________（鉴定机构）")
        _case_document_paragraph(document, f"本所接受{record.customer or '（未填写）'}委托，由{case_lawyer}律师办理上述案件，现就本案司法鉴定相关事宜函告贵机构。")
        _case_document_paragraph(document, "鉴定事项及要求：________________")
        _case_document_paragraph(document, "送鉴材料：________________")
        _case_document_paragraph(document, "请就上述事项依法办理鉴定。")
        _case_document_paragraph(document, company["name"])
        _case_document_paragraph(document, today_cn)
        _case_document_paragraph(document, f"经办律师：{case_lawyer}；联系电话：{context.get('case_lawyer_phone') or '（未填写）'}", size=12)
    elif document_type == "identity-certificate":
        customer = context.get("customer") or {}
        legal_name = _case_document_value(customer, "legal_representative", "legal_agent_name") or "（客户档案未填写）"
        legal_id = _case_document_value(customer, "legal_agent_id_no", "legal_representative_id_no") or "（客户档案未填写）"
        legal_title = _case_document_value(customer, "legal_agent_title", "legal_representative_title") or "（客户档案未填写）"
        _case_document_paragraph(document, "法定代表人身份证明", center=True, bold=True, size=22)
        _case_document_paragraph(document, "")
        _case_document_paragraph(document, f"兹证明{legal_name}（身份证号码：{legal_id}）在我单位担任{legal_title}职务，系我单位法定代表人。")
        _case_document_paragraph(document, "特此证明！")
        _case_document_paragraph(document, "")
        _case_document_paragraph(document, record.customer)
        _case_document_paragraph(document, f"日期：{today_cn}")
    else:
        document.add_heading(title, level=0)
        document.add_paragraph(f"案件编号：{record.serial_no}")
        document.add_paragraph(f"案件名称：{record.title}")
        document.add_paragraph(f"客户：{record.customer or '（未填写）'}")
        document.add_paragraph(f"案件阶段：{record.status}")
        if document_type == "settlement-list":
            document.add_paragraph(f"诉讼标的金额：{_case_document_value(data, 'litigation_amount') or '（未填写）'}")
            document.add_paragraph(f"判决/和解金额：{_case_document_value(data, 'settlement_amount') or '（未填写）'}")
    output = io.BytesIO()
    document.save(output)
    return title, output.getvalue()


def _agent_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _agent_document_dict(item: AgentDocument, template: DocumentTemplate | None = None, record: BusinessRecord | None = None, capabilities: dict | None = None, users_by_username: dict[str, User] | None = None) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    users = users_by_username or {}
    return {"id": item.id, "job_no": item.job_no, "template_id": item.template_id, "template_name": template.name if template else "", "record_id": item.record_id, "record_no": record.serial_no if record else "", "record_title": record.title if record else "", "title": item.title, "instruction": item.instruction, "content": item.content, "status": item.status, "content_version": item.content_version, "confirmed_by": item.confirmed_by, "confirmed_by_display_name": _person_reference_display(item.confirmed_by, users)[0], "confirmed_at": item.confirmed_at, "conversation_id": item.conversation_id, "dify_message_id": item.dify_message_id, "error": item.error, "creator": item.creator, "creator_display_name": _person_reference_display(item.creator, users)[0], "created_at": item.created_at, "updated_at": item.updated_at, "capabilities": capabilities or {}}


def _agent_document_operation_result(item: AgentDocument, template: DocumentTemplate | None = None, record: BusinessRecord | None = None) -> dict:
    """Expose whether this operation made an editable outline or a provider result.

    The status alone is intentionally retained for workflow compatibility, while these
    fields let clients avoid describing a local outline as an AI-generated document.
    """
    provider_configured = bool(settings.dify_base_url and settings.dify_api_key)
    result = _agent_document_dict(item, template, record)
    result.update({
        "provider_configured": provider_configured,
        "generation_mode": "dify" if provider_configured else "outline",
        "operation_result": "outline_created" if item.status == "待配置" else "document_generated" if item.status == "已生成" else "generation_failed" if item.status == "生成失败" else "generation_pending",
    })
    return result


async def _run_document_agent(item: AgentDocument) -> None:
    if not settings.dify_base_url or not settings.dify_api_key:
        item.status = "待配置"; item.error = "Dify 尚未配置；可先编辑系统生成的字段提纲，配置后点击重试。"; return
    item.status = "生成中"; item.error = ""
    payload = {"inputs": {"document_job_no": item.job_no}, "query": item.prompt, "response_mode": "blocking", "conversation_id": item.conversation_id, "user": item.creator}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{settings.dify_base_url.rstrip('/')}/v1/chat-messages", headers={"Authorization": f"Bearer {settings.dify_api_key}"}, json=payload)
            response.raise_for_status(); result = response.json()
        item.content = result.get("answer", "").strip(); item.conversation_id = result.get("conversation_id", ""); item.dify_message_id = result.get("message_id", "")
        if not item.content: raise ValueError("Dify 未返回文档内容")
        item.status = "已生成"
    except Exception as exc:
        item.status = "生成失败"; item.error = str(exc)[:1000]
