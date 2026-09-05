"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    CONTRACT_APPROVAL_ACTION_CODE, CONTRACT_APPROVED_STATUS, CONTRACT_PERSON_NAME_PATTERN, RECORD_PERSON_FIELDS_BY_MODULE, UPLOAD_ROOT,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, ContractApprovalStep, ContractEvent, ContractObject,
    ContractObjectLog, ContractPaymentLine, FileAttachment, HTTPException, IncomingPayment,
    JSONResponse, Path, ReceivablePlan, User, WorkflowEvent,
    date, datetime, delete, func, or_,
    re, select, status, unicodedata,
)
from app.models_shared import (
    ContractEventInput, ContractWholeDeleteInput,
)


def _contract_allows_downstream_creation(contract: BusinessRecord | None) -> bool:
    """Only a persisted contract draft is barred from creating downstream work."""
    return bool(contract and contract.module == "contract" and contract.status != "草稿")


def _valid_contract_person_name(value: object, username: object = "") -> str:
    name = unicodedata.normalize("NFKC", str(value or "")).strip()
    compact_name = re.sub(r"\s+", "", name)
    if not compact_name:
        return ""
    return name


def _valid_contract_chinese_person_name(value: object) -> str:
    name = _valid_contract_person_name(value)
    return name if CONTRACT_PERSON_NAME_PATTERN.search(name) else ""


def _contract_person_values(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item or "").strip() for item in value if str(item or "").strip()]
    return [item.strip() for item in re.split(r"[、,，;；]", str(value or "")) if item.strip()]


def _contract_customer_manager_values(
    contract: BusinessRecord,
    customer: BusinessRecord | None,
) -> list[str]:
    """Use the linked customer's current manager roster for contract presentation.

    Contract records retain the manager snapshot captured when they were created,
    but list/detail responses must follow later customer-manager maintenance.  The
    snapshot remains the fallback only when the customer relation cannot be
    resolved, so this projection never rewrites historical contract data.
    """
    if customer:
        customer_data = customer.data or {}
        return list(dict.fromkeys(_contract_person_values(
            customer_data.get("customer_managers") or [customer.owner]
        )))
    contract_data = contract.data or {}
    return list(dict.fromkeys(_contract_person_values(
        contract_data.get("customer_managers") or contract_data.get("customer_manager")
    )))


def _contract_investigation_source_data(
    contract: BusinessRecord,
    customer: BusinessRecord | None,
) -> dict[str, object]:
    """Build immutable source identifiers for a contract-created investigation."""
    from app.core.system import (
        _positive_record_id,
    )
    contract_data = contract.data or {}
    return {
        "contract_id": contract.id,
        "contract_record_id": contract.id,
        "contract_no": contract.serial_no,
        "contract_name": contract.title,
        "customer_id": customer.id if customer else _positive_record_id(
            contract_data.get("customer_id") or contract_data.get("customer_record_id")
        ) or None,
        "customer_record_id": customer.id if customer else _positive_record_id(
            contract_data.get("customer_id") or contract_data.get("customer_record_id")
        ) or None,
        "customer_no": customer.serial_no if customer else str(contract_data.get("customer_no") or ""),
        "customer_name": customer.title if customer else contract.customer,
    }


async def _contract_customer_record_dict(
    record: BusinessRecord,
    allowed_fields: set[str] | None,
    db: AsyncSession,
    *,
    investigations_by_id: dict[int, BusinessRecord] | None = None,
    names_by_username: dict[str, str] | None = None,
    users_by_username: dict[str, User] | None = None,
    contract_context: dict | None = None,
    identity: dict | None = None,
) -> dict:
    from app.core.cases import (
        _case_phase_changed_days,
    )
    from app.core.crm import (
        _customer_reference_from_maps,
    )
    from app.core.formatters import (
        _apply_record_person_displays, _case_phase_changed_date, _contract_person_display_name, _user_display_map,
    )
    from app.core.permissions import (
        _can_act_on_contract_approval_step,
    )
    from app.core.projections import (
        _contract_customer_projection_context,
    )
    from app.core.system import (
        _record_dict, _record_person_usernames,
    )
    result = _record_dict(record, allowed_fields)
    if record.module not in {"case", "contract", "customer", "investigation", "task", "clue", "notary", "evidence"}:
        return result
    data = result["data"]
    if record.module == "case":
        phase_changed_date = _case_phase_changed_date(record)
        phase_changed_days = _case_phase_changed_days(record)
        data["phase_changed_at"] = phase_changed_date.isoformat()
        data["phase_changed_days"] = phase_changed_days
        data["phase_duration"] = f"{phase_changed_days}天"
    if record.module == "contract":
        context = contract_context or await _contract_customer_projection_context([record], db)
        customer, relation_status = _customer_reference_from_maps(
            record.customer,
            record.data or {},
            context["customers_by_id"],
            context["customers_by_no"],
            context["customers_by_name"],
        )
        current_step = context["current_steps"].get(record.id)
        current_approver = current_step.approver if current_step else ""
        if customer:
            customer_data = customer.data or {}
            data["customer_id"] = customer.id
            data["customer_record_id"] = customer.id
            data["customer_no"] = customer.serial_no
            data["customer_name"] = customer.title
            # A contract may contain an old creation-time manager snapshot.  The
            # current linked customer is authoritative for list/detail display.
            data["customer_managers"] = _contract_customer_manager_values(record, customer)
            data.pop("customer_manager_display_names", None)
            data.pop("customer_manager_display_name", None)
        data["customer_relation_status"] = relation_status
        data["signed_at"] = str(
            data.get("signed_at") or data.get("signed_date") or data.get("sign_date") or data.get("contract_date") or ""
        )
        data["current_approver"] = current_approver
        result.update({
            "customer_id": customer.id if customer else None,
            "customer_no": customer.serial_no if customer else str(data.get("customer_no") or ""),
            "customer_name": customer.title if customer else record.customer,
            "signed_at": data["signed_at"],
            "current_approver": current_approver,
        })
        can_approve_current = bool(
            identity
            and record.status == "审批中"
            and current_step
            and await _can_act_on_contract_approval_step(
                current_step,
                identity,
                CONTRACT_APPROVAL_ACTION_CODE,
                db,
            )
        )
        approval_capabilities = {
            "can_approve_current": can_approve_current,
            "current_approver": current_approver,
        }
        data["approval_capabilities"] = approval_capabilities
        result["approval_capabilities"] = approval_capabilities
    if record.module == "task" and data.get("investigation_record_id"):
        try:
            investigation_id = int(data.get("investigation_record_id") or 0)
        except (TypeError, ValueError):
            investigation_id = 0
        investigation = (
            investigations_by_id.get(investigation_id)
            if investigations_by_id is not None
            else await db.get(BusinessRecord, investigation_id) if investigation_id else None
        )
        if investigation and investigation.module == "investigation":
            investigation_data = investigation.data or {}
            for key in ("right_type", "region", "authorized_from", "authorized_to", "source_owner", "assigner", "assigned_by"):
                if not data.get(key) and investigation_data.get(key):
                    data[key] = investigation_data[key]
            data.setdefault("investigation_no", investigation.serial_no)
    usernames = [record.owner]
    for key in ("source_person", "customer_source", "submitted_by", "current_approver", "customer_manager", "reviewer", "customer_reviewer", "investigator", "investigation_assistant", "handler", "source_owner", "assigner", "assigned_by"):
        usernames.extend(_contract_person_values(data.get(key)))
    usernames.extend(_contract_person_values(data.get("customer_managers")))
    usernames.extend(_contract_person_values(data.get("contact_accounts") or data.get("contact")))
    usernames.extend(_record_person_usernames(record))
    if names_by_username is None:
        normalized_usernames = list(dict.fromkeys(value.lower() for value in usernames if value))
        users = list((await db.scalars(select(User).where(func.lower(User.username).in_(normalized_usernames)))).all()) if normalized_usernames else []
        names_by_username = {user.username.lower(): user.display_name for user in users}
    result["owner_display_name"] = _contract_person_display_name(record.owner, names_by_username)
    for key in ("source_person", "customer_source", "submitted_by", "current_approver", "investigator", "investigation_assistant", "handler", "source_owner", "assigner", "assigned_by"):
        if key in data:
            data[f"{key}_display_name"] = _contract_person_display_name(data.get(key), names_by_username)
    managers = _contract_person_values(data.get("customer_managers") or data.get("customer_manager"))
    if managers:
        manager_names = [_contract_person_display_name(value, names_by_username) for value in managers]
        data["customer_manager_display_names"] = manager_names
        data["customer_manager_display_name"] = "、".join(manager_names)
    contact_accounts = _contract_person_values(data.get("contact_accounts") or data.get("contact"))
    if contact_accounts:
        contact_names = [_contract_person_display_name(value, names_by_username) for value in contact_accounts]
        data["contact_account_display_names"] = contact_names
        data["contact_account_display_name"] = "、".join(contact_names)
    if record.module in {"investigation", "task", "clue", "notary", "evidence"}:
        people = _contract_person_values(data.get("customer_managers") or data.get("customer_manager"))
        manager_label = ""
        if people:
            # Usernames remain the authorization keys; UI receives display labels.
            manager_label = "、".join(str(names_by_username.get(value.lower()) or value) for value in people)
            data["customer_manager_display_name"] = manager_label
            data["customer_manager"] = manager_label
        for key in ("reviewer", "customer_reviewer"):
            value = str(data.get(key) or "").strip()
            if value:
                label = str(names_by_username.get(value.lower()) or value)
                data[f"{key}_display_name"] = label
                data[key] = label
        reviewer_label = str(data.get("customer_reviewer_display_name") or data.get("reviewer_display_name") or "")
        if record.module == "clue" and manager_label and reviewer_label:
            data["customer_manager"] = f"{manager_label}（审核人：{reviewer_label}）"
    if record.module in RECORD_PERSON_FIELDS_BY_MODULE:
        if users_by_username is None:
            users_by_username = await _user_display_map(_record_person_usernames(record), db)
        _apply_record_person_displays(result, record, users_by_username)
    return result


async def _contract_customer_record_dicts(
    records: list[BusinessRecord], allowed_fields: set[str] | None, db: AsyncSession,
    identity: dict | None = None,
) -> list[dict]:
    from app.core.crm import (
        _customer_reference_from_maps,
    )
    from app.core.projections import (
        _contract_customer_projection_context,
    )
    from app.core.system import (
        _record_person_usernames,
    )
    investigation_ids: set[int] = set()
    for record in records:
        if record.module != "task":
            continue
        try:
            investigation_id = int((record.data or {}).get("investigation_record_id") or 0)
        except (TypeError, ValueError):
            investigation_id = 0
        if investigation_id:
            investigation_ids.add(investigation_id)
    investigations = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "investigation", BusinessRecord.id.in_(investigation_ids),
    ))).all()) if investigation_ids else []
    investigations_by_id = {item.id: item for item in investigations}

    contract_context = await _contract_customer_projection_context(records, db)
    usernames: set[str] = set()
    person_keys = (
        "source_person", "customer_source", "submitted_by", "current_approver", "customer_manager",
        "reviewer", "customer_reviewer", "investigator", "investigation_assistant", "handler", "source_owner", "assigner", "assigned_by",
    )
    for record in records:
        usernames.add(str(record.owner or "").lower())
        data = record.data or {}
        investigation = investigations_by_id.get(int(data.get("investigation_record_id") or 0)) if record.module == "task" and str(data.get("investigation_record_id") or "").isdigit() else None
        inherited_data = investigation.data or {} if investigation else {}
        for key in person_keys:
            usernames.update(value.lower() for value in _contract_person_values(data.get(key) or inherited_data.get(key)))
        usernames.update(value.lower() for value in _contract_person_values(data.get("customer_managers")))
        usernames.update(value.lower() for value in _contract_person_values(data.get("contact_accounts") or data.get("contact")))
        usernames.update(value.lower() for value in _record_person_usernames(record))
        if record.module == "contract":
            customer, _ = _customer_reference_from_maps(
                record.customer,
                data,
                contract_context["customers_by_id"],
                contract_context["customers_by_no"],
                contract_context["customers_by_name"],
            )
            usernames.update(
                value.lower()
                for value in _contract_customer_manager_values(record, customer)
            )
    usernames.discard("")
    users = list((await db.scalars(select(User).where(func.lower(User.username).in_(usernames)))).all()) if usernames else []
    names_by_username = {user.username.lower(): user.display_name for user in users}
    users_by_username = {user.username.lower(): user for user in users}
    results = [
        await _contract_customer_record_dict(
            record, allowed_fields, db,
            investigations_by_id=investigations_by_id,
            names_by_username=names_by_username,
            users_by_username=users_by_username,
            contract_context=contract_context,
            identity=identity,
        )
        for record in records
    ]
    return results


async def _resolve_contract_customer(customer_name: str, data: dict, identity: dict, db: AsyncSession) -> BusinessRecord:
    """Resolve the selected customer and keep contract linkage authoritative."""
    from app.core.permissions import (
        _record_scope_conditions,
    )
    name = customer_name.strip()
    customer_id = int(data.get("customer_id") or 0)
    conditions = [BusinessRecord.module == "customer", BusinessRecord.status != "已回收"]
    if customer_id:
        conditions.append(BusinessRecord.id == customer_id)
    else:
        conditions.append(BusinessRecord.title == name)
    customer = await db.scalar(
        select(BusinessRecord)
        .where(*conditions, *(await _record_scope_conditions(identity, db)))
        .order_by(BusinessRecord.id.desc())
    )
    if not customer or customer.title != name:
        raise HTTPException(status_code=422, detail="请选择当前账号可见的有效客户，不能手工录入未登记客户名称")
    return customer


def _contract_customer_source_person(customer: BusinessRecord) -> str:
    """Contracts inherit the customer's fixed source person, never their creator."""
    customer_data = customer.data or {}
    return str(
        customer_data.get("source_person")
        or customer_data.get("customer_source")
        or customer.owner
        or ""
    ).strip()


async def _user_has_contract_approval_action(user: User, db: AsyncSession) -> bool:
    """Resolve the explicit approval action without recursing through candidate payloads."""
    from app.core.permissions import (
        _apply_job_role_policy, _configured_user_job_role_name, _job_role_for_name, _permission_payload_for_roles, _system_user_role_ids,
    )
    if user.role == "admin":
        return True
    permission = await _permission_payload_for_roles(_system_user_role_ids(user), db)
    explicit_role_name = _configured_user_job_role_name(user)
    if explicit_role_name:
        if explicit_role_name in {"系统管理员", "管理员"}:
            return False
        job_role = await _job_role_for_name(explicit_role_name, db)
        if not job_role:
            return False
        permission = _apply_job_role_policy(permission, job_role)
    return CONTRACT_APPROVAL_ACTION_CODE in set(permission.get("action_keys") or [])


async def _is_contract_approver(user: User, db: AsyncSession) -> bool:
    """Resolve a selectable contract approver from one authoritative rule."""
    if not user.is_active:
        return False
    if not _valid_contract_person_name(user.display_name, user.username):
        return False
    if not bool((user.profile or {}).get("contract_approval_enabled")):
        return False
    employee_id = await db.scalar(
        select(BusinessRecord.id).where(
            BusinessRecord.module == "hr",
            or_(
                BusinessRecord.owner == user.username,
                BusinessRecord.data["username"].as_string() == user.username,
            ),
        ).limit(1)
    )
    return employee_id is not None


async def _has_explicit_contract_approval_action(identity: dict, action_key: str, db: AsyncSession) -> bool:
    """Allow delegated approval only when the caller explicitly invokes an assigned action node."""
    from app.core.permissions import (
        _permission_payload_for_identity,
    )
    if action_key != CONTRACT_APPROVAL_ACTION_CODE:
        return False
    permission = await _permission_payload_for_identity(identity, db)
    action_keys = set(permission.get("action_keys") or [])
    return "*" in action_keys or CONTRACT_APPROVAL_ACTION_CODE in action_keys


async def _next_contract_serial_no(db: AsyncSession) -> str:
    """Generate the compact legacy contract number: SHHT + YY + 5 digits."""
    prefix = f"SHHT{datetime.now():%y}"
    existing = (await db.scalars(select(BusinessRecord.serial_no).where(
        BusinessRecord.module == "contract",
        BusinessRecord.serial_no.like(f"{prefix}%"),
    ).order_by(BusinessRecord.serial_no.desc()))).all()
    sequence = max((int(match.group(1)) for value in existing if (match := re.fullmatch(rf"{re.escape(prefix)}(\d{{5}})", value))), default=0) + 1
    if sequence > 99999:
        raise HTTPException(status_code=409, detail=f"{datetime.now():%Y} 合同编号已用尽")
    return f"{prefix}{sequence:05d}"


async def _delete_contract_records(
    body: ContractWholeDeleteInput,
    identity: dict,
    db: AsyncSession,
    *,
    allow_company_contract: bool = False,
):
    """Legacy FCM ContractDelete parity: physically delete whole contract records.

    Recycle-bin removal accepts only recycled contracts. The separate company
    contract endpoint preserves the legacy company-ledger delete action while
    retaining every downstream-record guard before physical removal.
    """
    ids = list(dict.fromkeys([int(item_id) for item_id in [*body.contract_ids, *body.contractIds] if int(item_id) > 0]))
    if identity["role"] != "admin":
        return JSONResponse(status_code=status.HTTP_200_OK, content={"IsSuccess": False, "Message": "仅管理员可以删除合同", "deleted": 0})
    prepared: list[tuple[BusinessRecord, list[FileAttachment]]] = []
    try:
        if not ids:
            raise HTTPException(status_code=422, detail="请选择要删除的合同")
        contracts = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(ids), BusinessRecord.module == "contract"))).all())
        if len(contracts) != len(ids):
            raise HTTPException(status_code=404, detail="所选合同不存在或已删除")
        by_id = {item.id: item for item in contracts}
        ordered = [by_id[item_id] for item_id in ids]
        for contract in ordered:
            if not allow_company_contract and contract.status != "已回收":
                raise HTTPException(status_code=409, detail="只有回收站合同可以整体删除")
            if int(await db.scalar(select(func.count()).select_from(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == contract.id)) or 0):
                raise HTTPException(status_code=409, detail="合同已有审批记录，不能整体删除")
            if int(await db.scalar(select(func.count()).select_from(ReceivablePlan).where(ReceivablePlan.contract_record_id == contract.id)) or 0):
                raise HTTPException(status_code=409, detail="合同已有应收计划，不能整体删除")
            if int(await db.scalar(select(func.count()).select_from(IncomingPayment).where(IncomingPayment.contract_record_id == contract.id)) or 0):
                raise HTTPException(status_code=409, detail="合同已关联到账记录，不能整体删除")
            contract_object_ids = select(ContractObject.id).where(ContractObject.contract_record_id == contract.id)
            if int(await db.scalar(select(func.count()).select_from(ContractPaymentLine).where(ContractPaymentLine.contract_object_id.in_(contract_object_ids))) or 0):
                raise HTTPException(status_code=409, detail="合同已有付款申请明细，不能整体删除")
            related_record = await db.scalar(select(BusinessRecord.serial_no).where(
                BusinessRecord.id != contract.id,
                or_(
                    BusinessRecord.data["contract_record_id"].as_integer() == contract.id,
                    BusinessRecord.data["contract_id"].as_integer() == contract.id,
                ),
            ).limit(1))
            if related_record:
                raise HTTPException(status_code=409, detail="合同已被其他业务关联，不能整体删除")
            attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == contract.id))).all())
            prepared.append((contract, attachments))
        for contract, attachments in prepared:
            for attachment in attachments:
                await db.delete(attachment)
            await db.execute(delete(ContractObjectLog).where(ContractObjectLog.contract_object_id.in_(select(ContractObject.id).where(ContractObject.contract_record_id == contract.id))))
            await db.execute(delete(ContractObject).where(ContractObject.contract_record_id == contract.id))
            await db.execute(delete(ContractEvent).where(ContractEvent.contract_record_id == contract.id))
            await db.execute(delete(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == contract.id))
            await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == contract.id))
            await db.delete(contract)
        await db.commit()
    except HTTPException as exc:
        await db.rollback()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"IsSuccess": False, "Message": str(exc.detail), "deleted": 0})
    for _, attachments in prepared:
        for attachment in attachments:
            path = Path(attachment.path)
            if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
                path.unlink()
    return {"IsSuccess": True, "Message": "删除成功", "deleted": len(prepared)}


async def _contract_archive_rows(
    identity: dict,
    db: AsyncSession,
    *,
    contract_no: str = "",
    customer: str = "",
    archive_status: str = "",
    archive_date_from: date | None = None,
    archive_date_to: date | None = None,
) -> list[dict]:
    """List only contracts which really have been archived or have active fee closure."""
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    await _require_record_module_menu("contract", identity, db, action="查看")
    visible_scope = await _record_scope_conditions(identity, db)
    contracts = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract", *visible_scope,
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    contract_ids = {record.id for record in contracts}
    active_closure_dates: dict[int, str] = {}
    if contract_ids:
        fees = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance",
            BusinessRecord.data["contract_id"].as_integer().in_(contract_ids),
        ))).all())
        for fee in fees:
            fee_data = fee.data or {}
            contract_id = int(fee_data.get("contract_id") or 0)
            if contract_id and fee_data.get("fee_archived"):
                archived_at = str(fee_data.get("fee_archived_at") or "").strip()
                active_closure_dates[contract_id] = max(active_closure_dates.get(contract_id, ""), archived_at)
    no_filter = contract_no.strip().casefold()
    customer_filter = customer.strip().casefold()
    requested_state = archive_status.strip()
    allowed_fields = await _allowed_field_keys(identity, db)
    rows: list[dict] = []
    for contract in contracts:
        data = contract.data or {}
        archived_at = str(data.get("archived_at") or "").strip()
        closure_at = active_closure_dates.get(contract.id, "")
        in_progress = contract.status in {"归档中", "归档审核中"} or bool(closure_at)
        state = "已归档" if contract.status == "已归档" or archived_at else "归档中" if in_progress else ""
        archive_date = archived_at or closure_at or str(data.get("archive_started_at") or "").strip()
        if not state or (requested_state and state != requested_state):
            continue
        if no_filter and no_filter not in contract.serial_no.casefold():
            continue
        if customer_filter and customer_filter not in str(contract.customer or "").casefold():
            continue
        archive_day = None
        if archive_date:
            try:
                archive_day = datetime.fromisoformat(archive_date.replace("Z", "+00:00")).date()
            except ValueError:
                try:
                    archive_day = date.fromisoformat(archive_date[:10])
                except ValueError:
                    archive_day = None
        if archive_date_from and (archive_day is None or archive_day < archive_date_from):
            continue
        if archive_date_to and (archive_day is None or archive_day > archive_date_to):
            continue
        item = (await _contract_customer_record_dicts([contract], allowed_fields, db, identity))[0]
        item["archive_status"] = state
        item["archive_date"] = archive_date
        rows.append(item)
    return rows


def _contract_event_dict(event: ContractEvent) -> dict:
    return {
        "id": event.id,
        "contract_record_id": event.contract_record_id,
        "content": event.content,
        "operator": event.operator,
        "created_at": event.created_at,
    }


def _stored_contract_guid(contract: BusinessRecord) -> str:
    return str((contract.data or {}).get("contract_guid") or "").strip()


async def _contract_events_payload(
    contract: BusinessRecord,
    *,
    page: int | None,
    page_size: int | None,
    keyword: str,
    db: AsyncSession,
) -> dict:
    events = list((await db.scalars(
        select(ContractEvent)
        .where(ContractEvent.contract_record_id == contract.id)
        .order_by(ContractEvent.created_at.desc(), ContractEvent.id.desc())
    )).all())
    if keyword.strip():
        needle = keyword.strip().casefold()
        events = [item for item in events if needle in f"{item.content} {item.operator}".casefold()]
    total = len(events)
    result = {"items": [_contract_event_dict(event) for event in events], "total": total}
    if page is not None or page_size is not None or keyword.strip():
        current_page, current_size = page or 1, page_size or 15
        start = (current_page - 1) * current_size
        result.update({
            "items": [_contract_event_dict(event) for event in events[start:start + current_size]],
            "page": current_page, "page_size": current_size,
            "pages": (total + current_size - 1) // current_size if total else 0,
        })
    result["contract_guid"] = _stored_contract_guid(contract)
    return result


async def _create_contract_event_for_record(contract: BusinessRecord, body: ContractEventInput, identity: dict, db: AsyncSession) -> dict:
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    await _require_record_owner_or_manager(contract, identity, db)
    if contract.status == "已归档":
        raise HTTPException(status_code=409, detail="已归档合同不可新增事项记录")
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="事项内容不能为空")
    event = ContractEvent(contract_record_id=contract.id, content=content, operator=identity["username"])
    db.add(event)
    db.add(WorkflowEvent(
        record_id=contract.id,
        action="新增合同事项",
        from_status=contract.status,
        to_status=contract.status,
        operator=identity["username"],
        comment=content,
    ))
    await db.commit()
    await db.refresh(event)
    result = _contract_event_dict(event)
    result["contract_guid"] = _stored_contract_guid(contract)
    return result


async def _contract_object_payload(item: ContractObject, identity: dict, db: AsyncSession) -> dict:
    from app.core.permissions import (
        _ensure_record_visible,
    )
    case = await _ensure_record_visible(item.case_record_id, identity, db)
    if case.module != "case":
        raise HTTPException(status_code=409, detail="合同标的关联案件已失效")
    data = case.data or {}
    logs = (await db.scalars(select(ContractObjectLog).where(ContractObjectLog.contract_object_id == item.id).order_by(ContractObjectLog.created_at.desc(), ContractObjectLog.id.desc()))).all()
    return {"id": item.id, "contract_record_id": item.contract_record_id, "case_record_id": case.id, "case_no": case.serial_no, "case_title": case.title, "case_type": data.get("case_type", ""), "case_phase": case.status, "customer_manager": data.get("customer_manager", case.owner), "fee_type": item.fee_type, "amount": item.amount, "remark": item.remark, "created_by": item.created_by, "updated_by": item.updated_by, "created_at": item.created_at, "updated_at": item.updated_at, "logs": [{"id": log.id, "action": log.action, "before": log.before, "after": log.after, "operator": log.operator, "created_at": log.created_at} for log in logs]}


async def _contract_object_writable(contract: BusinessRecord, identity: dict, db: AsyncSession) -> None:
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    await _require_record_owner_or_manager(contract, identity, db)
    if contract.status == "已归档":
        raise HTTPException(status_code=409, detail="已归档合同的合同标的只读")
    if contract.status == "审批中":
        raise HTTPException(status_code=409, detail="合同审批中不能修改合同标的；请先撤回或等待审批结果")
    if contract.status not in {"草稿", "已拒绝", CONTRACT_APPROVED_STATUS, "已完成"}:
        raise HTTPException(status_code=409, detail="当前合同状态不能维护合同标的")


async def _resolve_clue_source_contract(clue: BusinessRecord, identity: dict, db: AsyncSession) -> tuple[BusinessRecord | None, str]:
    """Resolve a clue's contract from its source task chain, never from a UI pick."""
    from app.core.permissions import (
        _record_scope_conditions,
    )
    candidate_ids: set[int] = set()
    candidate_nos: set[str] = set()
    candidate_titles: set[str] = set()
    task_id = 0
    source_data = clue.data or {}
    visited: set[int] = set()
    for key in ("contract_record_id", "contract_id"):
        try:
            if source_data.get(key): candidate_ids.add(int(source_data[key]))
        except (TypeError, ValueError):
            pass
    for key in ("contract_no", "source_contract_no"):
        if str(source_data.get(key) or "").strip(): candidate_nos.add(str(source_data[key]).strip())
    for key in ("contract_name", "contract_title"):
        if str(source_data.get(key) or "").strip(): candidate_titles.add(str(source_data[key]).strip())
    try:
        task_id = int(source_data.get("source_task_id") or 0)
    except (TypeError, ValueError):
        task_id = 0
    while task_id and task_id not in visited and len(visited) < 12:
        visited.add(task_id)
        task = await db.get(BusinessRecord, task_id)
        if not task or task.module not in {"task", "investigation"}: break
        task_data = task.data or {}
        for key in ("contract_record_id", "contract_id"):
            try:
                if task_data.get(key): candidate_ids.add(int(task_data[key]))
            except (TypeError, ValueError):
                pass
        for key in ("contract_no", "source_contract_no"):
            if str(task_data.get(key) or "").strip(): candidate_nos.add(str(task_data[key]).strip())
        for key in ("contract_name", "contract_title"):
            if str(task_data.get(key) or "").strip(): candidate_titles.add(str(task_data[key]).strip())
        try:
            task_id = int(task_data.get("parent_task_id") or 0)
        except (TypeError, ValueError):
            task_id = 0
    conditions = [BusinessRecord.module == "contract", *(await _record_scope_conditions(identity, db))]
    candidates = list((await db.scalars(select(BusinessRecord).where(*conditions))).all())
    matches = [item for item in candidates if item.id in candidate_ids or item.serial_no in candidate_nos or item.title in candidate_titles]
    matches = [item for item in matches if item.customer.strip() == clue.customer.strip()]
    unique = {item.id: item for item in matches}
    if len(unique) == 1: return next(iter(unique.values())), ""
    if not unique: return None, "线索来源调查任务未解析到同客户合同"
    return None, "线索来源任务匹配到多个合同，无法自动绑定"


async def _single_linked_case_for_contract(
    contract: BusinessRecord,
    identity: dict,
    db: AsyncSession,
) -> BusinessRecord | None:
    from app.core.permissions import (
        _record_scope_conditions,
    )
    scope = await _record_scope_conditions(identity, db)
    linked_case_ids = select(ContractObject.case_record_id).where(
        ContractObject.contract_record_id == contract.id,
    )
    rows = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
        BusinessRecord.id.in_(linked_case_ids),
        *scope,
    ).order_by(BusinessRecord.id).limit(2))).all())
    if len(rows) == 1:
        return rows[0]
    if rows:
        return None
    rows = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
        or_(
            BusinessRecord.data["contract_record_id"].as_integer() == contract.id,
            BusinessRecord.data["contract_id"].as_integer() == contract.id,
            BusinessRecord.data["contract_no"].as_string() == contract.serial_no,
        ),
        *scope,
    ).order_by(BusinessRecord.id).limit(2))).all())
    return rows[0] if len(rows) == 1 else None
