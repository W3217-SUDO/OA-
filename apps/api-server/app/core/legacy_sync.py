"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    LEGACY_CONTRACT_STATUS_BY_NEW, LEGACY_INVESTIGATION_CLUE_STATUS, LEGACY_INVESTIGATION_STATUS, LEGACY_INVESTIGATION_TASK_STATUS, LEGACY_OFFICIAL_DOCUMENT_STATUS,
    SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, FileAttachment, HTTPException, LegacyCase,
    LegacyCaseFile, LegacyCaseLog, LegacyCaseParticipant, LegacyCaseTaskHistory, LegacyContract,
    LegacyContractAudit, LegacyContractFile, LegacyCustomer, LegacyCustomerContact, LegacyFinanceRecord,
    LegacyHistoricalAttachment, LegacyInvestigation, LegacyInvestigationClue, LegacyInvestigationClueEvidence, LegacyInvestigationClueEvidenceFile,
    LegacyInvestigationClueFile, LegacyInvestigationTask, LegacyOfficialDocument, LegacyOfficialDocumentAudit, LegacyOfficialDocumentFile,
    NAMESPACE_URL, User, WorkflowEvent, date, datetime,
    delete, false, func, inspect, or_,
    select, status, uuid4, uuid5,
)


def _legacy_failure_response(message: str, data: object | None = None) -> dict:
    return {"IsSuccess": False, "Data": data, "Message": message}


def _legacy_customer_business_failure_response(exc: HTTPException) -> dict:
    if exc.status_code in {status.HTTP_409_CONFLICT, status.HTTP_422_UNPROCESSABLE_ENTITY}:
        return _legacy_failure_response(str(exc.detail or "操作失败"))
    raise exc


def _legacy_contract_business_failure_response(exc: HTTPException) -> dict:
    if exc.status_code in {status.HTTP_409_CONFLICT, status.HTTP_422_UNPROCESSABLE_ENTITY}:
        return _legacy_failure_response(str(exc.detail or "操作失败"))
    raise exc


def _legacy_finance_business_failure_response(exc: HTTPException) -> dict:
    if exc.status_code in {status.HTTP_409_CONFLICT, status.HTTP_422_UNPROCESSABLE_ENTITY}:
        return _legacy_failure_response(str(exc.detail or "操作失败"))
    raise exc


async def _legacy_customer_history_users(ids: set[int], db: AsyncSession) -> dict[int, dict]:
    if not ids:
        return {}
    rows = list((await db.scalars(select(User).where(User.id.in_(ids)))).all())
    return {item.id: {"id": item.id, "username": item.username, "display_name": item.display_name or item.username} for item in rows}


def _legacy_customer_history_item(item, *, user: dict | None = None, kind: str) -> dict:
    payload = {
        "id": item.id,
        "kind": kind,
        "source_system": item.source_system,
        "source_table": item.source_table,
        "source_primary_key": item.source_primary_key,
        "customer_record_id": item.customer_record_id,
        "legacy_customer_guid": getattr(item, "legacy_customer_guid", ""),
        "parent_mapping_status": item.parent_mapping_status,
        "orphan_reason": item.orphan_reason,
        "mapped_user": user,
        "user_mapping_status": getattr(item, "user_mapping_status", ""),
        "source_payload": item.source_payload or {},
        "read_only": True,
    }
    if kind == "coordinator":
        payload.update({
            "legacy_customer_id": item.legacy_customer_id,
            "legacy_customer_no": item.legacy_customer_no,
            "source_username": item.source_username,
            "relation_type_id": item.relation_type_id,
        })
    elif kind == "contact":
        payload.update({
            "legacy_contact_guid": item.legacy_contact_guid,
            "legacy_customer_no": item.legacy_customer_no,
            "contact_name": item.contact_name,
            "title": item.title,
            "mobile_phone": item.mobile_phone,
            "email": item.email,
            "is_active": item.is_active,
            "photo_recovery_status": item.photo_recovery_status,
            "source_username": item.source_username,
        })
    elif kind == "event":
        payload.update({
            "operator_username": item.operator_username,
            "operated_at": item.operated_at,
            "content": item.content,
            "is_active": item.is_active,
        })
    elif kind == "file":
        payload.update({
            "legacy_file_guid": item.legacy_file_guid,
            "original_name": item.original_name,
            "source_path": item.source_path,
            "declared_size_bytes": item.declared_size_bytes,
            "is_license": item.is_license,
            "is_active": item.is_active,
            "uploader_username": item.uploader_username,
            "uploaded_at": item.uploaded_at,
            "physical_recovery_status": item.physical_recovery_status,
            "can_download": False,
            "can_preview": False,
        })
    return payload


async def _sync_legacy_contract_audit(
    contract: BusinessRecord,
    identity: dict,
    db: AsyncSession,
    _legacy_status: int,
    _comment: str,
) -> None:
    """Keep the approval call site stable while using the complete projection."""
    await _sync_legacy_projection(contract, identity, db)


def _legacy_case_task_history_dict(item: LegacyCaseTaskHistory) -> dict:
    return {
        "id": item.id,
        "legacy_task_id": item.legacy_task_id,
        "legacy_task_guid": item.legacy_task_guid,
        "legacy_task_no": item.legacy_task_no,
        "legacy_case_id": item.legacy_case_id,
        "legacy_case_no": item.legacy_case_no,
        "case_record_id": item.case_record_id,
        "case_mapping_state": item.case_mapping_state,
        "task_title": item.task_title,
        "task_sub_title": item.task_sub_title,
        "task_priority": item.task_priority,
        "task_type_id": item.task_type_id,
        "task_status": item.task_status,
        "is_active": item.is_active,
        "task_begin_time": item.task_begin_time,
        "task_finished_time": item.task_finished_time,
        "task_end_time": item.task_end_time,
        "initiator": item.initiator,
        "officer": item.officer,
        "first_officer": item.first_officer,
        "current_node_guid": item.current_node_guid,
        "first_node_guid": item.first_node_guid,
        "task_content": item.task_content,
        "imported_at": item.imported_at,
        "updated_at": item.updated_at,
    }


def _legacy_case_task_history_item_dict(item: object, entity: str) -> dict:
    if entity == "nodes":
        return {
            "id": item.id, "legacy_node_id": item.legacy_node_id, "legacy_node_guid": item.legacy_node_guid,
            "legacy_task_guid": item.legacy_task_guid, "task_history_id": item.task_history_id,
            "task_relationship_state": item.task_relationship_state, "node_begin_time": item.node_begin_time,
            "node_finished_time": item.node_finished_time, "node_end_time": item.node_end_time,
            "node_type_id": item.node_type_id, "node_type_name": item.node_type_name, "node_status": item.node_status,
            "is_active": item.is_active, "initiator": item.initiator, "officer": item.officer,
            "associates": item.associates, "associate_names": item.associate_names, "node_content": item.node_content,
        }
    if entity == "participants":
        return {
            "id": item.id, "legacy_seq_id": item.legacy_seq_id, "legacy_task_guid": item.legacy_task_guid,
            "legacy_node_guid": item.legacy_node_guid, "task_history_id": item.task_history_id,
            "node_history_id": item.node_history_id, "task_relationship_state": item.task_relationship_state,
            "node_relationship_state": item.node_relationship_state, "participant": item.participant,
            "sorting_index": item.sorting_index,
        }
    if entity == "messages":
        return {
            "id": item.id, "legacy_message_id": item.legacy_message_id, "legacy_message_guid": item.legacy_message_guid,
            "legacy_task_guid": item.legacy_task_guid, "legacy_node_guid": item.legacy_node_guid,
            "task_history_id": item.task_history_id, "node_history_id": item.node_history_id,
            "task_relationship_state": item.task_relationship_state, "node_relationship_state": item.node_relationship_state,
            "message_type_id": item.message_type_id, "message_type_name": item.message_type_name,
            "content": item.content, "sender": item.sender, "send_time": item.send_time,
        }
    if entity == "notifications":
        return {
            "id": item.id, "legacy_seq_id": item.legacy_seq_id, "legacy_task_guid": item.legacy_task_guid,
            "legacy_message_guid": item.legacy_message_guid, "task_history_id": item.task_history_id,
            "message_history_id": item.message_history_id, "task_relationship_state": item.task_relationship_state,
            "message_relationship_state": item.message_relationship_state, "notification_type_id": item.notification_type_id,
            "notification_type_name": item.notification_type_name, "notification_object": item.notification_object,
            "have_read": item.have_read,
        }
    if entity == "read-receipts":
        return {
            "id": item.id, "legacy_seq_id": item.legacy_seq_id, "legacy_task_id": item.legacy_task_id,
            "legacy_message_id": item.legacy_message_id, "task_history_id": item.task_history_id,
            "message_history_id": item.message_history_id, "task_relationship_state": item.task_relationship_state,
            "message_relationship_state": item.message_relationship_state, "reader": item.reader, "have_read": item.have_read,
        }
    return {
        "id": item.id, "legacy_file_id": item.legacy_file_id, "legacy_file_guid": item.legacy_file_guid,
        "legacy_task_guid": item.legacy_task_guid, "legacy_message_guid": item.legacy_message_guid,
        "task_history_id": item.task_history_id, "message_history_id": item.message_history_id,
        "task_relationship_state": item.task_relationship_state, "message_relationship_state": item.message_relationship_state,
        "file_name": item.file_name, "source_path": item.source_path, "file_size": item.file_size,
        "upload_user": item.upload_user, "upload_time": item.upload_time, "is_active": item.is_active,
        "physical_content_materialized": False,
    }


async def _legacy_finance_scope_conditions(identity: dict, db: AsyncSession) -> list:
    """Restrict historical finance to the same records visible to the caller."""
    from app.core.permissions import (
        _record_scope_conditions,
    )
    if identity.get("role") in {"admin", "auditor"}:
        return []
    visible_ids = list((await db.scalars(select(BusinessRecord.id).where(
        await _record_scope_conditions(identity, db)
    ))).all())
    if not visible_ids:
        return [false()]
    return [or_(
        LegacyFinanceRecord.contract_record_id.in_(visible_ids),
        LegacyFinanceRecord.case_record_id.in_(visible_ids),
        LegacyFinanceRecord.customer_record_id.in_(visible_ids),
    )]


async def _legacy_finance_audit_table_exists(db: AsyncSession) -> bool:
    return await db.run_sync(lambda session: inspect(session.bind).has_table("legacy_finance_audits"))


def _legacy_finance_record_dict(
    item: LegacyFinanceRecord,
    *,
    allocation_count: int,
    file_count: int,
    audit_count: int,
    show_amount: bool,
    include_payload: bool = False,
) -> dict:
    payload = {
        "id": item.id,
        "source_table": item.source_table,
        "legacy_id": item.legacy_id,
        "record_kind": item.record_kind,
        "status_code": item.status_code,
        "status_label": item.status_label,
        "is_active": item.is_active,
        "currency": item.currency,
        "legacy_contract_no": item.legacy_contract_no,
        "legacy_case_no": item.legacy_case_no,
        "legacy_customer_no": item.legacy_customer_no,
        "contract_record_id": item.contract_record_id,
        "case_record_id": item.case_record_id,
        "customer_record_id": item.customer_record_id,
        "mapping_status": item.mapping_status,
        "allocation_count": allocation_count,
        "file_count": file_count,
        "audit_count": audit_count,
        "primary_amount": round(float(item.primary_amount or 0), 2) if show_amount else None,
        "imported_at": item.imported_at.isoformat() if item.imported_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }
    if include_payload:
        payload["source_payload"] = item.source_payload or {}
    return payload


def _legacy_historical_attachment_dict(item: LegacyHistoricalAttachment, *, include_payload: bool = False) -> dict:
    result = {
        "id": item.id,
        "source_system": item.source_system,
        "legacy_entity_type": item.legacy_entity_type,
        "legacy_file_id": item.legacy_file_id,
        "legacy_file_guid": item.legacy_file_guid,
        "legacy_parent_id": item.legacy_parent_id,
        "legacy_parent_guid": item.legacy_parent_guid,
        "legacy_parent_no": item.legacy_parent_no,
        "legacy_parent_tuple": item.legacy_parent_tuple or {},
        "file_name": item.file_name,
        "legacy_declared_size_bytes": item.legacy_declared_size_bytes,
        "legacy_file_path": item.legacy_file_path,
        "legacy_is_active": bool(item.legacy_is_active),
        "physical_exists": bool(item.source_physical_exists),
        "physical_size_bytes": item.source_physical_size_bytes,
        "recovery_status": item.source_recovery_status,
        "quarantine_reasons": item.source_quarantine_reasons or [],
        "observed_at": item.source_observed_at.isoformat() if item.source_observed_at else None,
        "read_only": True,
        "download_available": False,
        "preview_available": False,
        "download_reason": "仅保留历史元数据；旧系统源文件不可恢复，禁止下载和预览",
        "imported_at": item.imported_at.isoformat() if item.imported_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }
    if include_payload:
        result["source_payload"] = item.source_payload or {}
    return result


def _legacy_case_fee_projection(data: dict) -> dict:
    result = dict(data or {})
    legacy = result.get("legacy_record")
    if not isinstance(legacy, dict) or not result.get("legacy_case_fee_id"):
        return result

    # Early imports collapsed requested/refunded amounts and omitted the cash
    # date. Only repair fields that still have that old shape so later OA
    # transactions remain authoritative.
    if "refund_requested_amount" not in result and "refunded_amount" not in result:
        requested = legacy.get("RefundAmount")
        refunded = legacy.get("RefundedAmount")
        result["refund_amount"] = requested if requested is not None else 0
        result["refund_requested_amount"] = requested if requested is not None else 0
        result["refunded_amount"] = refunded if refunded is not None else 0
    cashed_date = legacy.get("CashedDate")
    if cashed_date and not (result.get("received_at") or result.get("cashed_date")):
        result["received_at"] = cashed_date
        result["cashed_date"] = cashed_date
    if "received_amount" not in result and legacy.get("CashedAmount") is not None:
        result["received_amount"] = legacy.get("CashedAmount")
    if "cashed_amount" not in result and legacy.get("CashedAmount") is not None:
        result["cashed_amount"] = legacy.get("CashedAmount")
    if "payment_requested_amount" not in result:
        paid_amount = legacy.get("PaidAmount")
        result["payment_requested_amount"] = paid_amount if paid_amount is not None else legacy.get("PrePaidAmount") or 0
    if not result.get("submitted_at"):
        result["submitted_at"] = legacy.get("InformDate") or legacy.get("CreateTime") or ""
    if not result.get("submitted_by"):
        result["submitted_by"] = str(legacy.get("RequestUser") or legacy.get("CreateUser") or "").strip()
    if not result.get("invoice_date"):
        result["invoice_date"] = legacy.get("InvoiceDate") or ""
    if not result.get("invoice_no"):
        result["invoice_no"] = str(legacy.get("InvoiceNo") or "").strip()
    return result


def _legacy_case_number_values(record: BusinessRecord) -> set[str]:
    data = record.data or {}
    values = {record.serial_no, str(data.get("legacy_system_case_no") or ""), str(data.get("legacy_case_no") or ""), str(data.get("case_no") or "")}
    return {value.lstrip("0") or "0" for value in values if value and value.isdigit()}


async def _legacy_projection_pk(record: BusinessRecord, column: str, db: AsyncSession) -> dict[str, int]:
    """SQLite cannot auto-generate BIGINT primary keys; preserve imported IDs."""
    connection = await db.connection()
    return {column: -record.id} if connection.dialect.name == "sqlite" else {}


def _legacy_snapshot_value(data: dict, *keys: str) -> object | None:
    """Read an exact legacy value retained by an imported business record."""
    snapshot = data.get("legacy_record")
    if not isinstance(snapshot, dict):
        return None
    for key in keys:
        value = snapshot.get(key)
        if value not in (None, ""):
            return value
    return None


async def _sync_legacy_customer(record: BusinessRecord, identity: dict, db: AsyncSession) -> LegacyCustomer:
    """Keep CRM_Customer and CRM_Customer_Contacts synchronized with customer APIs."""
    from app.core.crm import (
        _customer_guid,
    )
    data = record.data or {}
    legacy = await db.scalar(select(LegacyCustomer).where(LegacyCustomer.CustomerNo == record.serial_no[:20]))
    if not legacy:
        legacy = LegacyCustomer(
            **await _legacy_projection_pk(record, "CustomerId", db),
            CustomerNo=record.serial_no[:20],
            CustomerGuid=_customer_guid(record),
            CustomerName=record.title[:400],
            CreateUser=identity["username"][:20],
            CreateTime=_legacy_contract_datetime(record.created_at) or datetime.now(),
        )
        db.add(legacy)
    legacy.CustomerNo = record.serial_no[:20]
    legacy.CustomerGuid = _customer_guid(record)
    legacy.CustomerName = record.title[:400]
    legacy.ContactAddress = str(data.get("registered_address") or "")[:500] or None
    legacy.ContactPhone = str(data.get("phone") or "")[:50] or None
    legacy.Fax = str(data.get("fax") or "")[:50] or None
    legacy.Zip = str(data.get("postal_code") or "")[:50] or None
    legacy.Province = str(data.get("province") or "")[:20] or None
    legacy.City = str(data.get("registration_region") or "")[:20] or None
    legacy.Industry = str(data.get("industry") or "")[:100] or None
    legacy.ProductionValue = str(data.get("output_value") or "")[:100] or None
    legacy.CustomerTypeName = str(data.get("customer_type") or "")[:100] or None
    legacy.CooperatioSituation = str(data.get("cooperation_status") or "")[:100] or None
    legacy.CustomerSourceType = str(data.get("customer_source") or "")[:100] or None
    legacy.WebSite = str(data.get("website") or "")[:200] or None
    legacy.BusinessOwner = record.owner[:20]
    legacy.IsAssisted = "Y" if data.get("is_assisted") == "是" else "N"
    legacy.CompanyTypeName = str(data.get("organization_nature") or "")[:100] or None
    legacy.GBTypeName = str(data.get("gb_classification") or "")[:100] or None
    legacy.RegisteredCapital = str(data.get("registered_capital") or "")[:100] or None
    legacy.RegistrationDate = _legacy_contract_datetime(data.get("registration_year"))
    legacy.RegistrationCity = str(data.get("registration_region") or "")[:100] or None
    legacy.RegistrationZip = str(data.get("registration_postal_code") or "")[:100] or None
    legacy.RegistrationAddress = str(data.get("registered_address") or "")[:500] or None
    legacy.OrganizationCode = str(data.get("organization_code") or "")[:100] or None
    legacy.LicenseNo = str(data.get("credit_code") or "")[:100] or None
    legacy.AccountBankName = str(data.get("bank_name") or "")[:100] or None
    legacy.BankAccount = str(data.get("bank_account") or "")[:100] or None
    legacy.InputDate = _legacy_contract_datetime(data.get("file_date")) or _legacy_contract_datetime(record.created_at) or datetime.now()
    legacy.Holder = record.owner[:20]
    legacy.CustomerOwner = record.owner[:20]
    legacy.IsShared = "Y" if data.get("is_shared") == "是" else "N"
    legacy.IsActived = "N" if record.status == "已回收" else "Y"
    legacy.CustomerStatus = record.status[:100]
    legacy.LastContactTime = _legacy_contract_datetime(data.get("last_contact_at"))
    legacy.LastUpdateTime = datetime.now()
    legacy.IsFeeReducing = "Y" if data.get("fee_reduction") == "是" else "N"
    legacy.CustomerLevelName = str(data.get("level") or "")[:100] or None
    legacy.LegalAgentName = str(data.get("legal_representative") or "")[:200] or None
    legacy.LegalAgentIdNo = str(data.get("legal_agent_id_no") or "")[:200] or None
    legacy.LegalAgentTitle = str(data.get("legal_agent_title") or "")[:200] or None
    legacy.CustomerShortName = str(data.get("short_name") or "")[:100] or None
    legacy.ChangeUser = identity["username"][:20]
    legacy.ChangeTime = datetime.now()
    await db.flush()
    await _sync_legacy_customer_contacts(record, legacy, identity, db)
    return legacy


async def _sync_legacy_customer_contacts(record: BusinessRecord, legacy: LegacyCustomer, identity: dict, db: AsyncSession) -> None:
    from app.core.crm import (
        _customer_contact_dict,
    )
    contacts = [_customer_contact_dict(item) for item in list((record.data or {}).get("contacts") or [])]
    active_guids: set[str] = set()
    for contact in contacts:
        contact_id = str(contact.get("id") or uuid4().hex)
        contact_guid = str(uuid5(NAMESPACE_URL, f"customer-contact:{record.id}:{contact_id}"))
        active_guids.add(contact_guid)
        row = await db.scalar(select(LegacyCustomerContact).where(LegacyCustomerContact.ContactsGuid == contact_guid))
        if not row:
            row = LegacyCustomerContact(**({"ContactsId": -(record.id * 10000 + len(active_guids))} if (await db.connection()).dialect.name == "sqlite" else {}), ContactsGuid=contact_guid, CreateUser=identity["username"][:20], CreateTime=datetime.now())
            db.add(row)
        row.CustomerId = legacy.CustomerId
        row.CustomerNo = record.serial_no[:20]
        row.ContactsTitle = str(contact.get("position") or "")[:200] or None
        row.Contacts = str(contact.get("name") or "")[:200] or None
        row.ProjectRole = str(contact.get("project_role") or "")[:100] or None
        row.Email = str(contact.get("email") or "")[:200] or None
        row.OfficePhone = str(contact.get("office_phone") or "")[:50] or None
        row.Mobilephone = str(contact.get("phone") or "")[:50] or None
        row.IM = str(contact.get("im_account") or "")[:100] or None
        row.IsContacted = "Y" if contact.get("is_contacted", True) else "N"
        row.IsPeopleBASE = "Y" if contact.get("is_people_base", True) else "N"
        row.IsReceivedEmail = "Y" if contact.get("is_received_email", True) else "N"
        row.IsDefault = "Y" if contact.get("is_primary", False) else "N"
        row.IsActived = "Y" if contact.get("is_valid", True) else "N"
        row.ChangeUser = identity["username"][:20]
        row.ChangeTime = datetime.now()
    existing = (await db.scalars(select(LegacyCustomerContact).where(LegacyCustomerContact.CustomerNo == record.serial_no[:20]))).all()
    for row in existing:
        if row.ContactsGuid not in active_guids:
            row.IsActived = "N"
            row.ChangeUser = identity["username"][:20]
            row.ChangeTime = datetime.now()


def _legacy_contract_datetime(value: object) -> datetime | None:
    """Convert new-system timestamps to legacy SQL Server DATETIME semantics."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        return None


def _legacy_contract_int(value: object) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _legacy_contract_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


async def _sync_legacy_contract(record: BusinessRecord, identity: dict, db: AsyncSession) -> LegacyContract:
    """Persist FCM_Contract fields and legacy text links from a new contract record."""
    data = record.data or {}
    legacy = await db.scalar(select(LegacyContract).where(LegacyContract.ContractNo == record.serial_no[:20]))
    if not legacy:
        legacy_values = {
            **await _legacy_projection_pk(record, "ContractId", db),
            "ContractNo": record.serial_no[:20],
            "ContractGuid": str(data.get("contract_guid") or uuid4()),
            "CreateUser": identity["username"][:20],
            "CreateTime": _legacy_contract_datetime(record.created_at) or datetime.now(),
            "IsActived": "Y",
        }
        # The imported SQLite schema uses BIGINT for this legacy primary key.
        # SQLite only auto-generates keys for an exact INTEGER PRIMARY KEY,
        # whereas production databases retain their native identity column.
        connection = await db.connection()
        if connection.dialect.name == "sqlite":
            legacy_values["ContractId"] = int(
                await db.scalar(select(func.coalesce(func.max(LegacyContract.ContractId), 0))) or 0
            ) + 1
        legacy = LegacyContract(**legacy_values)
        db.add(legacy)
    legacy.ContractNo = record.serial_no[:20]
    legacy.ContractGuid = str(data.get("contract_guid") or legacy.ContractGuid or uuid4())[:36]
    legacy.RefContractNo = str(data.get("ref_contract_no") or data.get("external_contract_no") or "")[:50] or None
    legacy.ContractName = record.title[:200]
    customer_no = _legacy_case_text(
        data.get("customer_no") or _legacy_snapshot_value(data, "CustomerNo", "customer_no"),
        20,
    )
    customer_projection = await db.scalar(
        select(LegacyCustomer).where(LegacyCustomer.CustomerNo == customer_no)
    ) if customer_no else None
    legacy.CustomerId = (
        customer_projection.CustomerId
        if customer_projection
        else _legacy_contract_int(
            data.get("legacy_customer_id")
            or _legacy_snapshot_value(data, "CustomerId", "legacy_customer_id")
            or data.get("customer_id")
        )
    )
    legacy.CustomerNo = customer_no
    legacy.BusinessOwner = record.owner[:20]
    legacy.ContractType = _legacy_contract_int(data.get("contract_type_id") or data.get("contract_type"))
    legacy.ChargingType = _legacy_contract_int(data.get("charging_type_id") or data.get("charging_type"))
    legacy.ContractMoney = _legacy_contract_float(data.get("amount") or data.get("contract_money"))
    legacy.TaxRate = _legacy_contract_float(data.get("tax_rate"))
    legacy.ContractStatus = LEGACY_CONTRACT_STATUS_BY_NEW.get(record.status, 0)
    legacy.ContractBeginDate = _legacy_contract_datetime(data.get("contract_begin_date") or data.get("signed_at") or data.get("start_date"))
    legacy.ContractEndDate = _legacy_contract_datetime(data.get("contract_end_date") or data.get("end_date"))
    legacy.AuditRoundId = _legacy_contract_int(data.get("approval_count"))
    legacy.AuditDate = _legacy_contract_datetime(data.get("approved_at") or data.get("submitted_at"))
    legacy.Remark = str(data.get("remark") or record.description or "")[:1000]
    legacy.IsChanged = "Y" if data.get("is_changed") else "N"
    legacy.IsActived = "N" if record.status in {"已删除", "已回收"} else "Y"
    legacy.ChangeUser = identity["username"][:20]
    legacy.ChangeTime = datetime.now()
    await db.flush()
    await _sync_legacy_contract_files(record, legacy, identity, db)
    return legacy


async def _sync_legacy_contract_files(record: BusinessRecord, legacy: LegacyContract, identity: dict, db: AsyncSession) -> None:
    attachments = (await db.scalars(select(FileAttachment).where(
        FileAttachment.record_id == record.id,
        FileAttachment.category == "合同附件",
    ))).all()
    connection = await db.connection()
    next_sqlite_file_id = None
    if connection.dialect.name == "sqlite":
        next_sqlite_file_id = int(
            await db.scalar(select(func.coalesce(func.max(LegacyContractFile.FileId), 0))) or 0
        ) + 1
    for attachment in attachments:
        file_guid = str(uuid5(NAMESPACE_URL, f"contract-attachment:{attachment.id}"))
        legacy_file = await db.scalar(select(LegacyContractFile).where(LegacyContractFile.FileGuid == file_guid))
        if not legacy_file:
            legacy_values = dict(
                FileGuid=file_guid,
                ContractGuid=legacy.ContractGuid,
                CreateUser=identity["username"][:20],
                CreateTime=datetime.now(),
                IsActived="Y",
            )
            if next_sqlite_file_id is not None:
                legacy_values["FileId"] = next_sqlite_file_id
                next_sqlite_file_id += 1
            legacy_file = LegacyContractFile(**legacy_values)
            db.add(legacy_file)
        legacy_file.ContractGuid = legacy.ContractGuid
        legacy_file.FileName = attachment.original_name[:400]
        legacy_file.FilePath = attachment.path[:500]
        legacy_file.FileSize = attachment.size
        legacy_file.UploadUser = attachment.uploader[:20]
        legacy_file.UploadTime = _legacy_contract_datetime(attachment.created_at) or datetime.now()
        legacy_file.ChangeUser = identity["username"][:20]
        legacy_file.ChangeTime = datetime.now()


async def _sync_legacy_contract_audit(record: BusinessRecord, identity: dict, db: AsyncSession, status_code: int, comment: str = "") -> None:
    legacy = await _sync_legacy_contract(record, identity, db)
    round_id = int((record.data or {}).get("legacy_contract_audit_round") or 0) + 1
    record.data = {**(record.data or {}), "legacy_contract_audit_round": round_id}
    audit_values = dict(
        ContractId=legacy.ContractId,
        ContractNo=record.serial_no[:20],
        AuditRoundId=round_id,
        Auditor=identity["username"][:20],
        AuditDate=datetime.now(),
        AuditStatus=status_code,
        AuditContent=comment[:200],
        CreateUser=identity["username"][:20],
        CreateTime=datetime.now(),
    )
    connection = await db.connection()
    if connection.dialect.name == "sqlite":
        audit_values["AuditId"] = int(
            await db.scalar(select(func.coalesce(func.max(LegacyContractAudit.AuditId), 0))) or 0
        ) + 1
    db.add(LegacyContractAudit(**audit_values))


def _legacy_case_text(value: object, limit: int) -> str | None:
    value = str(value or "").strip()
    return value[:limit] or None


def _legacy_case_datetime(value: object) -> datetime | None:
    return _legacy_contract_datetime(value)


def _legacy_case_amount(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _legacy_case_list(value: object, limit: int = 2000) -> str | None:
    if isinstance(value, list):
        entries: list[str] = []
        for item in value:
            name = item.get("name") if isinstance(item, dict) else item
            text = str(name or "").strip()
            if text:
                entries.append(text)
        return _legacy_case_text("、".join(entries), limit)
    return _legacy_case_text(value, limit)


async def _sync_legacy_case(record: BusinessRecord, identity: dict, db: AsyncSession) -> LegacyCase:
    """Project a current case into the legacy Legal_Case shape and soft links."""
    data = record.data or {}
    legacy = await db.scalar(select(LegacyCase).where(LegacyCase.CaseNo == record.serial_no[:20]))
    now = datetime.now()
    if not legacy:
        legacy = LegacyCase(**await _legacy_projection_pk(record, "CaseId", db), CaseNo=record.serial_no[:20], CreateUser=identity["username"][:20], CreateTime=_legacy_contract_datetime(record.created_at) or now)
        db.add(legacy)
    stage_aliases = {
        "FirstIntance": ("first_instance", "first_intance"),
        "SecondIntance": ("second_instance", "second_intance"),
        "LastIntance": ("last_instance", "last_intance"),
        "ExecutionIntance": ("execution_instance", "execution_intance"),
    }
    for stage, aliases in stage_aliases.items():
        prefix = aliases[0]
        setattr(legacy, f"{stage}Court", _legacy_case_text(data.get(f"{prefix}_court") or (data.get("court") if stage == "FirstIntance" else ""), 20))
        setattr(legacy, f"{stage}Judge", _legacy_case_text(data.get(f"{prefix}_judge") or (data.get("judge") if stage == "FirstIntance" else ""), 200))
        setattr(legacy, f"{stage}Clerk", _legacy_case_text(data.get(f"{prefix}_clerk") or (data.get("clerk") if stage == "FirstIntance" else ""), 200))
        setattr(legacy, f"{stage}CaseNo", _legacy_case_text(data.get(f"{prefix}_case_no") or (data.get("court_case_no") if stage == "FirstIntance" else ""), 50))
        setattr(legacy, f"{stage}RegisterDate", _legacy_case_datetime(data.get(f"{prefix}_register_date") or (data.get("filing_date") if stage == "FirstIntance" else "")))
        setattr(legacy, f"{stage}LawfulDay", _legacy_case_datetime(data.get(f"{prefix}_lawful_day")))
        setattr(legacy, f"{stage}JudgmentDate", _legacy_case_datetime(data.get(f"{prefix}_judgment_date") or (data.get("judgment_date") if stage == "FirstIntance" else "")))
        setattr(legacy, f"{stage}CourtRoom", _legacy_case_text(data.get(f"{prefix}_courtroom") or (data.get("courtroom") if stage == "FirstIntance" else ""), 200))
    legacy.CaseNo = record.serial_no[:20]
    legacy.CaseName = record.title[:500]
    legacy.CustomerNo = _legacy_case_text(
        data.get("customer_no") or _legacy_snapshot_value(data, "CustomerNo", "customer_no"),
        20,
    )
    legacy.CaseTypeId = _legacy_contract_int(data.get("case_type_id"))
    legacy.CaseRightTypeId = _legacy_contract_int(data.get("right_type_id"))
    legacy.CauseName = _legacy_case_text(data.get("cause_or_charge"), 400)
    legacy.CasePhaseId = _legacy_contract_int(data.get("case_phase_id"))
    legacy.CaseOriginPeople = _legacy_case_text(data.get("source_person") or data.get("business_owner"), 200)
    legacy.CaseRegisterDate = _legacy_case_datetime(data.get("case_register_date") or record.created_at)
    legacy.CaseLawyer = _legacy_case_list(data.get("handling_lawyer_usernames") or data.get("handling_lawyers"), 200)
    legacy.CaseLawyerName = _legacy_case_list(data.get("handling_lawyers"), 400)
    legacy.CaseAssistant = _legacy_case_text(data.get("assistant_username") or data.get("assistant"), 200)
    legacy.CaseAssistantName = _legacy_case_text(data.get("assistant"), 400)
    for column, key in (("AppellantNames", "plaintiffs"), ("AppellantAgent", "plaintiff_agents"), ("AppelleeNames", "defendants"), ("AppelleeAgent", "defendant_agents"), ("TheThirdNames", "third_parties"), ("TheThirdAgent", "third_party_agents")):
        setattr(legacy, column, _legacy_case_list(data.get(key)))
    legacy.BusinessOwner = _legacy_case_text(data.get("business_owner") or data.get("source_person") or record.owner, 50)
    legacy.ContractNo = _legacy_case_text(
        data.get("contract_no") or _legacy_snapshot_value(data, "ContractNo", "contract_no"),
        30,
    )
    legacy.InvestigationClueNos = _legacy_case_list(data.get("investigation_clue_nos") or data.get("investigation_clue"))
    legacy.Deadline = _legacy_case_datetime(data.get("deadline"))
    legacy.SettlementAmount = _legacy_case_amount(data.get("settlement_amount"))
    legacy.LitigationAmount = _legacy_case_amount(data.get("litigation_amount"))
    legacy.Investigator = _legacy_case_text(data.get("investigator_username") or data.get("investigator"), 200)
    legacy.InvestigatorName = _legacy_case_text(data.get("investigator"), 200)
    legacy.NotarialNos = _legacy_case_list(data.get("notary_nos"), 800)
    legacy.DepositAddress = _legacy_case_text(data.get("deposit_address"), 1000)
    legacy.ConsultantBeginDate = _legacy_case_datetime(data.get("counsel_start"))
    legacy.ConsultantEndDate = _legacy_case_datetime(data.get("counsel_end"))
    legacy.ArchiveStatus = (
        20 if record.status in {"已归档", "亏损归档"}
        else 10 if record.status in {"待归档审核", "亏损审核"}
        else 7 if record.status == "亏损内审"
        else 0
    )
    legacy.ArchiveTypeId = 2 if data.get("archive_type") == "deficit" else 1 if data.get("archive_type") == "normal" else None
    legacy.FileNo = _legacy_case_text(data.get("archive_no"), 20)
    legacy.ArchivedFileNo = _legacy_case_text(data.get("archive_no"), 100)
    legacy.ClosingTime = _legacy_case_datetime(data.get("case_closed_at"))
    legacy.ToAuditTime = _legacy_case_datetime(data.get("archive_submitted_at"))
    legacy.ToAuditApplicant = _legacy_case_text(data.get("archive_submitter"), 20)
    legacy.ToAuditRemark = _legacy_case_text(data.get("archive_submit_comment"), 2000)
    legacy.InternalAuditor = _legacy_case_text(data.get("archive_internal_reviewer"), 20)
    legacy.InternalAuditedTime = _legacy_case_datetime(data.get("archive_internal_reviewed_at"))
    legacy.InternalAuditedRemark = _legacy_case_text(data.get("archive_internal_review_comment"), 200)
    legacy.Auditor = _legacy_case_text(data.get("archive_reviewer"), 20)
    legacy.AuditedTime = _legacy_case_datetime(data.get("archived_at") or data.get("archive_reviewed_at"))
    legacy.AuditedRemark = _legacy_case_text(data.get("archive_review_comment") or data.get("archive_reject_reason"), 2000)
    legacy.ExecutionStatus = _legacy_contract_int(data.get("execution_status_code"))
    legacy.ExecutionAcceptanceTime = _legacy_case_datetime(data.get("execution_acceptance_time"))
    legacy.OriginalCaseNo = _legacy_case_text(data.get("original_case_no"), 20)
    legacy.IsActived = "N" if record.status in {"已删除", "已合并"} else "Y"
    legacy.ChangeUser = identity["username"][:20]
    legacy.ChangeTime = now
    await _sync_legacy_case_relations(record, identity, db, legacy)
    return legacy


async def _sync_legacy_case_relations(record: BusinessRecord, identity: dict, db: AsyncSession, legacy: LegacyCase | None = None) -> None:
    """Project files, responsible staff and workflow history into old case tables."""
    legacy = legacy or await _sync_legacy_case(record, identity, db)
    now = datetime.now()
    case_id = legacy.CaseId or -record.id
    case_no = record.serial_no[:20]
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == record.id))).all())
    for attachment in attachments:
        item = await db.scalar(select(LegacyCaseFile).where(LegacyCaseFile.FileId == -attachment.id))
        if not item:
            item = LegacyCaseFile(FileId=-attachment.id, CaseId=case_id, CaseNo=case_no, CreateUser=identity["username"][:20], CreateTime=_legacy_contract_datetime(attachment.created_at) or now)
            db.add(item)
        item.CaseId = case_id
        item.CaseNo = case_no
        item.FileName = _legacy_case_text(attachment.original_name, 200)
        item.FileTypeId = _legacy_contract_int(attachment.file_type_code)
        item.CaseFileTypeId = _legacy_contract_int(attachment.file_type_code)
        item.FullPath = _legacy_case_text(attachment.path, 500)
        item.FileSize = attachment.size
        item.UploadingUser = _legacy_case_text(attachment.uploader, 20)
        item.UploadingTime = _legacy_contract_datetime(attachment.created_at) or now
        item.Actived = "Y"
        item.IsTransmitted = "Y" if attachment.is_transmitted else "N"
        item.SortingIndex = attachment.id
        item.FileGuid = str(uuid5(NAMESPACE_URL, f"case-file:{attachment.id}"))
        item.ChangeUser = identity["username"][:20]
        item.ChangeTime = now

    data = record.data or {}
    people: list[str] = [record.owner]
    # Legacy StaffName stores the account reference. Prefer the explicit
    # username fields and use display names only when no account is supplied.
    lawyer_refs = data.get("handling_lawyer_usernames") or data.get("handling_lawyers") or []
    people.extend(lawyer_refs if isinstance(lawyer_refs, list) else [lawyer_refs])
    people.append(data.get("assistant_username") or data.get("assistant"))
    people.append(data.get("investigator_username") or data.get("investigator"))
    # Historical imports preserve the old participant relation in the current
    # case record. Include it when refreshing the compatibility projection so
    # a normal case edit cannot silently erase migrated participants.
    for participant in data.get("legacy_participants") or []:
        if isinstance(participant, dict):
            people.append(participant.get("staff_name"))
    wanted = {str(value or "").strip() for value in people if str(value or "").strip()}
    existing = list((await db.scalars(select(LegacyCaseParticipant).where(LegacyCaseParticipant.CaseNo == case_no))).all())
    for participant in existing:
        if participant.StaffName not in wanted:
            await db.delete(participant)
    for index, staff_name in enumerate(sorted(wanted), start=1):
        participant = await db.get(LegacyCaseParticipant, {"CaseNo": case_no, "StaffName": staff_name[:20]})
        if not participant:
            participant = LegacyCaseParticipant(CaseNo=case_no, StaffName=staff_name[:20], CreateUser=identity["username"][:20], CreateTime=now)
            db.add(participant)
        participant.SortingIndex = index
        participant.ChangeUser = identity["username"][:20]
        participant.ChangeTime = now

    events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == record.id).order_by(WorkflowEvent.id))).all())
    for event in events:
        log_id = -event.id
        log = await db.get(LegacyCaseLog, log_id)
        if not log:
            log = LegacyCaseLog(LogId=log_id, CaseId=case_id, CaseNo=case_no, CreateUser=event.operator[:20], CreateTime=_legacy_contract_datetime(event.created_at) or now)
            db.add(log)
        log.CaseId = case_id
        log.CaseNo = case_no
        log.Content = _legacy_case_text(f"{event.action}：{event.comment}".rstrip("："), 8000)
        log.LogType = 10
        log.IsActived = "Y"
        log.ChangeUser = identity["username"][:20]
        log.ChangeTime = now


def _legacy_yes_no(value: object) -> str:
    return "Y" if bool(value) else "N"


def _legacy_region(data: dict, key: str) -> str | None:
    value = data.get(key)
    if isinstance(value, list):
        value = "、".join(str(item).strip() for item in value if str(item).strip())
    return _legacy_case_text(value, 2000)


async def _sync_legacy_investigation(record: BusinessRecord, identity: dict, db: AsyncSession) -> LegacyInvestigation:
    data = record.data or {}
    legacy = await db.scalar(select(LegacyInvestigation).where(LegacyInvestigation.InvestigationNo == record.serial_no[:20]))
    now = datetime.now()
    if not legacy:
        legacy = LegacyInvestigation(**await _legacy_projection_pk(record, "InvestigationId", db), InvestigationNo=record.serial_no[:20], InvestigationGuid=str(uuid5(NAMESPACE_URL, f"investigation:{record.id}")), CreateUser=identity["username"][:20], CreateTime=_legacy_contract_datetime(record.created_at) or now)
        db.add(legacy)
    legacy.InvestigationTitle = record.title[:200]
    legacy.Remark = _legacy_case_text(record.description, 8000)
    legacy.Indicter = _legacy_case_text(data.get("source_owner") or data.get("publisher"), 200)
    legacy.IndicterName = _legacy_case_text(data.get("source_owner") or data.get("publisher"), 2000)
    legacy.CaseTypeId = _legacy_contract_int(data.get("case_type_id"))
    legacy.AuthorizationBeginTime = _legacy_case_datetime(data.get("authorized_from"))
    legacy.AuthorizationEndTime = _legacy_case_datetime(data.get("authorized_to"))
    scope = str(data.get("authorization_scope") or "").strip()
    legacy.InvestigationScope = "1" if scope in {"全国", "全国范围"} else "0"
    legacy.Province = _legacy_region(data, "province") or _legacy_region(data, "region")
    legacy.City = _legacy_region(data, "city")
    legacy.BusinessOwner = record.owner[:20]
    legacy.Auditor = _legacy_case_text(data.get("auditor"), 20)
    legacy.Status = LEGACY_INVESTIGATION_STATUS.get(record.status, 0)
    legacy.IsActived = "N" if record.status in {"已删除", "已取消"} else "Y"
    legacy.NeedToAuditOnCustomer = _legacy_yes_no(data.get("customer_review"))
    legacy.ContractNo = _legacy_case_text(
        data.get("contract_no") or _legacy_snapshot_value(data, "ContractNo", "contract_no"),
        20,
    )
    legacy.ChangeUser = identity["username"][:20]
    legacy.ChangeTime = now
    return legacy


async def _sync_legacy_investigation_task(record: BusinessRecord, identity: dict, db: AsyncSession) -> LegacyInvestigationTask:
    data = record.data or {}
    legacy = await db.scalar(select(LegacyInvestigationTask).where(LegacyInvestigationTask.TaskNo == record.serial_no[:20]))
    now = datetime.now()
    if not legacy:
        legacy = LegacyInvestigationTask(**await _legacy_projection_pk(record, "TaskId", db), TaskNo=record.serial_no[:20], TaskGuid=str(uuid5(NAMESPACE_URL, f"investigation-task:{record.id}")), CreateUser=identity["username"][:20], CreateTime=_legacy_contract_datetime(record.created_at) or now)
        db.add(legacy)
    legacy.TaskName = record.title[:200]
    legacy.TaskType = "子任务" if data.get("parent_task_id") else "主任务"
    legacy.InvestigationNo = _legacy_case_text(
        data.get("investigation_no")
        or _legacy_snapshot_value(data, "InvestigationNo", "investigation_no"),
        20,
    )
    legacy.Investigator = record.owner[:200]
    legacy.Assistant = _legacy_case_text(data.get("assistant"), 200)
    legacy.BeginTime = _legacy_case_datetime(data.get("start_date") or data.get("authorized_from"))
    legacy.EndTime = _legacy_case_datetime(data.get("end_date") or data.get("deadline") or data.get("authorized_to"))
    legacy.InvestigationScope = "全国" if str(data.get("authorization_scope") or "") in {"全国", "全国范围"} else "区域"
    legacy.Province = _legacy_region(data, "province") or _legacy_region(data, "region")
    legacy.City = _legacy_region(data, "city")
    legacy.District = _legacy_case_text(data.get("district"), 200)
    legacy.TaskStatus = LEGACY_INVESTIGATION_TASK_STATUS.get(record.status, 0)
    legacy.IsActived = "N" if record.status in {"已删除", "已取消"} else "Y"
    legacy.Remark = _legacy_case_text(record.description, 2000)
    legacy.ChangeUser = identity["username"][:20]
    legacy.ChangeTime = now
    return legacy


async def _sync_legacy_investigation_clue(record: BusinessRecord, identity: dict, db: AsyncSession) -> LegacyInvestigationClue:
    data = record.data or {}
    legacy = await db.scalar(select(LegacyInvestigationClue).where(LegacyInvestigationClue.ClueNo == record.serial_no[:20]))
    now = datetime.now()
    if not legacy:
        legacy = LegacyInvestigationClue(**await _legacy_projection_pk(record, "ClueId", db), ClueNo=record.serial_no[:20], ClueGuid=str(uuid5(NAMESPACE_URL, f"investigation-clue:{record.id}")), CreateUser=identity["username"][:20], CreateTime=_legacy_contract_datetime(record.created_at) or now)
        db.add(legacy)
    task_no = (
        data.get("investigation_task_no")
        or _legacy_snapshot_value(data, "InvestigationTaskNo", "investigation_task_no")
    )
    if not task_no:
        source_task_id = _legacy_contract_int(data.get("source_task_id"))
        source_task = await db.get(BusinessRecord, source_task_id) if source_task_id else None
        if source_task and source_task.module == "task":
            task_no = source_task.serial_no
    legacy.InvestigationTaskNo = _legacy_case_text(task_no, 20)
    legacy.InvestigationNo = _legacy_case_text(
        data.get("investigation_no")
        or _legacy_snapshot_value(data, "InvestigationNo", "investigation_no"),
        20,
    )
    legacy.BusinessType = _legacy_case_text(data.get("business_type"), 10)
    legacy.ChannelType = _legacy_case_text(data.get("channel_type"), 10)
    legacy.PlatformName = _legacy_case_text(data.get("platform"), 200)
    legacy.StoreName = _legacy_case_text(data.get("store_name") or record.title, 200)
    legacy.StoreUrl = _legacy_case_text(data.get("store_url") or data.get("source_url"), 2000)
    legacy.LocationAddress = _legacy_case_text(data.get("location_address") or data.get("address"), 1000)
    legacy.Address = _legacy_case_text(data.get("address") or data.get("location_address"), 1000)
    for key, column in (("province", "Province"), ("city", "City"), ("district", "District")):
        value = _legacy_case_text(data.get(key), 20)
        setattr(legacy, column, value)
        setattr(legacy, f"{column}Zh", _legacy_case_text(data.get(f"{key}_zh") or data.get(key), 100))
    legacy.HasProduct = _legacy_yes_no(data.get("product"))
    legacy.InvestigationDate = _legacy_case_datetime(data.get("investigation_date") or data.get("collected_at"))
    legacy.HasTort = _legacy_yes_no(data.get("has_tort") or data.get("tort"))
    legacy.Indictee = _legacy_case_text(data.get("opponent") or data.get("indictee"), 1000)
    legacy.Status = LEGACY_INVESTIGATION_CLUE_STATUS.get(record.status, 0)
    legacy.IsActived = "N" if record.status == "已删除" else "Y"
    legacy.Remark = _legacy_case_text(record.description, 2000)
    legacy.ToAuditTime = _legacy_case_datetime(data.get("submitted_at") or data.get("resubmitted_at"))
    legacy.Auditor = _legacy_case_text(data.get("reviewer"), 20)
    legacy.AuditTime = _legacy_case_datetime(data.get("reviewed_at"))
    legacy.AuditRemark = _legacy_case_text(data.get("review_comment") or data.get("rejection_reason"), 2000)
    legacy.AuditNeedMergeCase = _legacy_yes_no(data.get("audit_need_merge_case") or data.get("merge_into_case_no"))
    legacy.AuditNeedMergeCaseNo = _legacy_case_text(data.get("merge_into_case_no"), 20)
    legacy.Investigators = _legacy_case_text(record.owner, 200)
    legacy.InvestigatorNames = _legacy_case_text(record.owner, 200)
    legacy.CaseNo = _legacy_case_text(data.get("converted_case_no") or data.get("case_no"), 20)
    legacy.CustomerAuditor = _legacy_case_text(data.get("customer_reviewer"), 20)
    legacy.CustomerAuditTime = _legacy_case_datetime(data.get("customer_reviewed_at"))
    legacy.CustomerAuditRemark = _legacy_case_text(data.get("customer_review_comment"), 2000)
    legacy.StoreId = _legacy_case_text(data.get("store_id"), 100)
    legacy.ChangeUser = identity["username"][:20]
    legacy.ChangeTime = now
    return legacy


def _legacy_evidence_status(value: object) -> int:
    return {
        "未入库": 10,
        "已入库": 20,
        "已重新入库": 20,
        "已出库": 30,
        "已销毁": 40,
    }.get(str(value or "").strip(), 0)


async def _sync_legacy_investigation_clue_evidence(
    clue: BusinessRecord,
    identity: dict,
    db: AsyncSession,
    attachment_ids: list[int] | None = None,
) -> LegacyInvestigationClueEvidence:
    """Project one registered collection into the old clue/evidence GUID chain."""
    clue_projection = await _sync_legacy_investigation_clue(clue, identity, db)
    data = clue.data or {}
    evidence_guid = str(uuid5(NAMESPACE_URL, f"investigation-clue-evidence:{clue.id}"))
    legacy = await db.scalar(
        select(LegacyInvestigationClueEvidence).where(
            LegacyInvestigationClueEvidence.EvidenceGuid == evidence_guid,
        ),
    )
    now = datetime.now()
    if not legacy:
        legacy = LegacyInvestigationClueEvidence(
            # Imported legacy rows retain their positive SQL Server IDs. New
            # compatibility rows use a stable separate range without changing
            # the GUID-based old-system relationship.
            EvidenceId=-clue.id,
            EvidenceGuid=evidence_guid,
            EvidenceNo=_legacy_case_text(f"EV-{clue.serial_no}", 200),
            ClueGuid=clue_projection.ClueGuid,
            CreateUser=identity["username"][:20],
            CreateTime=now,
        )
        db.add(legacy)
    legacy.EvidenceType = "NT"
    legacy.ClueGuid = clue_projection.ClueGuid
    legacy.EvidenceDate = _legacy_case_datetime(data.get("collected_at"))
    legacy.EvidenceAddress = _legacy_case_text(data.get("address") or data.get("location_address"), 1000)
    legacy.NotaryOrganization = _legacy_case_text(data.get("notary_institution"), 200)
    legacy.NotarialNo = _legacy_case_text(data.get("notarization_no") or data.get("certificate_no"), 200)
    legacy.NotarialObtainDate = _legacy_case_datetime(data.get("collected_at"))
    legacy.Remark = _legacy_case_text(clue.description, 2000)
    legacy.IsActived = "Y"
    legacy.ChangeUser = identity["username"][:20]
    legacy.ChangeTime = now
    legacy.DepositAddress = _legacy_case_text(data.get("storage_location"), 1000)
    legacy.InvoiceNo = _legacy_case_text(data.get("invoice_no"), 100)
    legacy.EvidenceStatus = _legacy_evidence_status(data.get("evidence_status"))
    legacy.StorageLocationName = _legacy_case_text(data.get("storage_location"), 20)
    legacy.StorageLocationNo = _legacy_case_text(data.get("storage_location_no"), 20)
    legacy.WarehouseNo = _legacy_case_text(data.get("warehouse_no"), 20)

    selected_ids = set(attachment_ids if attachment_ids is not None else data.get("collection_file_ids", []))
    attachments = list(
        (await db.scalars(select(FileAttachment).where(FileAttachment.record_id == clue.id))).all(),
    )
    for attachment in attachments:
        target_model = LegacyInvestigationClueEvidenceFile if attachment.id in selected_ids else LegacyInvestigationClueFile
        filters = [target_model.FileId == attachment.id]
        target = await db.scalar(select(target_model).where(*filters))
        other_model = LegacyInvestigationClueFile if target_model is LegacyInvestigationClueEvidenceFile else LegacyInvestigationClueEvidenceFile
        # A file belongs to exactly one side of the legacy collection chain.
        # Re-registering a clue with a different selection must move it rather
        # than leave stale duplicate rows in both old attachment tables.
        await db.execute(delete(other_model).where(other_model.FileId == attachment.id))
        if not target:
            target = target_model(FileId=attachment.id, CreateUser=identity["username"][:20], CreateTime=_legacy_contract_datetime(attachment.created_at) or now)
            db.add(target)
        target.ClueGuid = clue_projection.ClueGuid
        if target_model is LegacyInvestigationClueEvidenceFile:
            target.EvidenceGuid = evidence_guid
        target.FileName = _legacy_case_text(attachment.original_name, 200)
        target.MediaType = _legacy_case_text(attachment.content_type, 20)
        target.FileTypeId = _legacy_contract_int(attachment.file_type_code)
        target.FullPath = _legacy_case_text(attachment.path, 500)
        target.FileSize = attachment.size
        target.UploadingUser = _legacy_case_text(attachment.uploader, 20)
        target.UploadingTime = _legacy_contract_datetime(attachment.created_at) or now
        target.IsActived = "Y"
        target.ChangeUser = identity["username"][:20]
        target.ChangeTime = now
    return legacy


async def _legacy_official_document_customer_no(record: BusinessRecord, data: dict, db: AsyncSession) -> str | None:
    customer_no = _legacy_case_text(
        data.get("customer_no") or _legacy_snapshot_value(data, "CustomerNo", "customer_no"),
        50,
    )
    if customer_no:
        return customer_no
    for module, serial_no in (("case", data.get("case_no")), ("contract", data.get("contract_no"))):
        if not serial_no:
            continue
        related = await db.scalar(select(BusinessRecord).where(
            BusinessRecord.module == module,
            BusinessRecord.serial_no == str(serial_no),
        ))
        related_data = related.data if related else {}
        customer_no = _legacy_case_text(
            related_data.get("customer_no") or _legacy_snapshot_value(related_data, "CustomerNo", "customer_no"),
            50,
        )
        if customer_no:
            return customer_no
    customer = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "customer",
        BusinessRecord.title == record.customer,
    ))
    customer_data = customer.data if customer else {}
    return _legacy_case_text(
        customer_data.get("customer_no") or _legacy_snapshot_value(customer_data, "CustomerNo", "customer_no"),
        50,
    )


async def _sync_legacy_official_document_files(
    record: BusinessRecord,
    legacy: LegacyOfficialDocument,
    identity: dict,
    db: AsyncSession,
) -> None:
    attachments = list((await db.scalars(select(FileAttachment).where(
        FileAttachment.record_id == record.id,
        FileAttachment.category.in_({SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY}),
    ))).all())
    now = datetime.now()
    active_guids = set()
    for attachment in attachments:
        file_guid = str(uuid5(NAMESPACE_URL, f"official-document-attachment:{attachment.id}"))
        active_guids.add(file_guid)
        legacy_file = await db.scalar(select(LegacyOfficialDocumentFile).where(
            LegacyOfficialDocumentFile.FileGuid == file_guid,
        ))
        if not legacy_file:
            values = {
                "FileGuid": file_guid,
                "OfficialDocumentGuid": legacy.OfficialDocumentGuid,
                "CreateUser": identity["username"][:20],
                "CreateTime": now,
            }
            connection = await db.connection()
            if connection.dialect.name == "sqlite":
                values["FileId"] = -attachment.id
            legacy_file = LegacyOfficialDocumentFile(**values)
            db.add(legacy_file)
        legacy_file.OfficialDocumentGuid = legacy.OfficialDocumentGuid
        legacy_file.FileName = attachment.original_name[:400]
        legacy_file.FilePath = attachment.path[:500]
        legacy_file.FileSize = attachment.size
        legacy_file.Uploader = attachment.uploader[:20]
        legacy_file.UploadTime = _legacy_contract_datetime(attachment.created_at) or now
        legacy_file.IsActived = "Y"
        legacy_file.ChangeUser = identity["username"][:20]
        legacy_file.ChangeTime = now

    projected_files = list((await db.scalars(select(LegacyOfficialDocumentFile).where(
        LegacyOfficialDocumentFile.OfficialDocumentGuid == legacy.OfficialDocumentGuid,
    ))).all())
    for legacy_file in projected_files:
        if legacy_file.FileGuid not in active_guids:
            legacy_file.IsActived = "N"
            legacy_file.ChangeUser = identity["username"][:20]
            legacy_file.ChangeTime = now


async def _sync_legacy_official_document(
    record: BusinessRecord,
    identity: dict,
    db: AsyncSession,
) -> LegacyOfficialDocument:
    """Project a seal application into the legacy AWS official-document tables."""
    data = record.data or {}
    legacy = await db.scalar(select(LegacyOfficialDocument).where(
        LegacyOfficialDocument.OfficialDocumentNo == record.serial_no[:20],
    ))
    now = datetime.now()
    if not legacy:
        values = {
            **await _legacy_projection_pk(record, "OfficialDocumentId", db),
            "OfficialDocumentNo": record.serial_no[:20],
            "OfficialDocumentGuid": str(data.get("official_document_guid") or uuid5(NAMESPACE_URL, f"official-document:{record.id}")),
            "CreateUser": identity["username"][:20],
            "CreateTime": _legacy_contract_datetime(record.created_at) or now,
            "IsActived": "Y",
        }
        legacy = LegacyOfficialDocument(**values)
        db.add(legacy)
    legacy.OfficialDocumentNo = record.serial_no[:20]
    legacy.OfficialDocumentGuid = str(data.get("official_document_guid") or legacy.OfficialDocumentGuid or uuid5(NAMESPACE_URL, f"official-document:{record.id}"))[:36]
    legacy.CaseNo = _legacy_case_text(data.get("case_no") or _legacy_snapshot_value(data, "CaseNo", "case_no"), 50)
    legacy.ContractNo = _legacy_case_text(data.get("contract_no") or _legacy_snapshot_value(data, "ContractNo", "contract_no"), 50)
    legacy.CustomerNo = await _legacy_official_document_customer_no(record, data, db)
    legacy.OfficialDocumentName = record.title[:200]
    legacy.CompanyId = _legacy_contract_int(data.get("company_id") or _legacy_snapshot_value(data, "CompanyId", "company_id"))
    legacy.DepartmentId = _legacy_contract_int(data.get("department_id") or _legacy_snapshot_value(data, "DepartmentId", "department_id"))
    legacy.BusinessOwner = record.owner[:20]
    legacy.OfficialDocumentType = _legacy_contract_int(data.get("official_document_type_id") or data.get("official_document_type") or _legacy_snapshot_value(data, "OfficialDocumentType", "official_document_type_id"))
    legacy.IsElectronicSeal = _legacy_yes_no(data.get("is_electronic_seal"))
    legacy.IsOfflinePrint = _legacy_yes_no(data.get("is_offline_print"))
    legacy.PrintQuantity = _legacy_contract_int(data.get("actual_copies") or data.get("print_quantity") or data.get("copies"))
    legacy.PrintTime = _legacy_contract_datetime(data.get("stamped_at"))
    legacy.Printer = _legacy_case_text(data.get("stamp_operator"), 20)
    legacy.PrintStatus = 1 if record.status in {"已用印", "已归档"} else 0
    legacy.SealType = _legacy_contract_int(data.get("seal_type_id") or data.get("seal_type") or _legacy_snapshot_value(data, "SealType", "seal_type_id"))
    legacy.OfficialDocumentStatus = LEGACY_OFFICIAL_DOCUMENT_STATUS.get(record.status, 0)
    legacy.ApplicationDate = _legacy_contract_datetime(data.get("application_date") or data.get("submitted_at")) or _legacy_contract_datetime(record.created_at)
    legacy.OfficialDocumentBeginDate = _legacy_contract_datetime(data.get("official_document_begin_date") or data.get("use_date"))
    legacy.OfficialDocumentEndDate = _legacy_contract_datetime(data.get("official_document_end_date") or data.get("use_date"))
    legacy.AuditFlowId = _legacy_contract_int(data.get("audit_flow_id") or _legacy_snapshot_value(data, "AuditFlowId", "audit_flow_id"))
    legacy.AuditFlowNodeId = _legacy_contract_int(data.get("audit_flow_node_id") or _legacy_snapshot_value(data, "AuditFlowNodeId", "audit_flow_node_id"))
    legacy.Remark = _legacy_case_text(data.get("remark") or record.description, 1000)
    legacy.IsActived = "N" if record.status in {"已删除", "已撤回"} else "Y"
    legacy.ChangeUser = identity["username"][:20]
    legacy.ChangeTime = now
    await db.flush()
    await _sync_legacy_official_document_files(record, legacy, identity, db)
    return legacy


async def _sync_legacy_official_audit(
    record: BusinessRecord,
    identity: dict,
    db: AsyncSession,
    status_code: int,
    comment: str = "",
) -> None:
    legacy = await _sync_legacy_official_document(record, identity, db)
    data = record.data or {}
    round_id = int(data.get("legacy_official_document_audit_round") or 0) + 1
    record.data = {**data, "legacy_official_document_audit_round": round_id}
    now = datetime.now()
    audit_values = {
        "OfficialDocumentId": legacy.OfficialDocumentId,
        "OfficialDocumentNo": record.serial_no[:20],
        "AuditFlowId": legacy.AuditFlowId,
        "AuditFlowNodeId": legacy.AuditFlowNodeId,
        "AuditRoundId": round_id,
        "Auditor": identity["username"][:20],
        "AuditDate": now,
        "AuditStatus": status_code,
        "AuditContent": comment[:200],
        "CreateUser": identity["username"][:20],
        "CreateTime": now,
        "ChangeUser": identity["username"][:20],
        "ChangeTime": now,
    }
    connection = await db.connection()
    if connection.dialect.name == "sqlite":
        audit_values["AuditId"] = int(
            await db.scalar(select(func.coalesce(func.max(LegacyOfficialDocumentAudit.AuditId), 0))) or 0
        ) + 1
    db.add(LegacyOfficialDocumentAudit(**audit_values))
    legacy.Auditor = _legacy_case_text(data.get("approver") or identity["username"], 20)
    legacy.AuditStatus = status_code
    legacy.AuditTime = now
    legacy.AuditRemark = _legacy_case_text(data.get("approval_comment") or comment, 2000)
    legacy.AuditRoundId = round_id


async def _sync_legacy_projection(record: BusinessRecord, identity: dict, db: AsyncSession) -> None:
    """Synchronize old-system projections in the caller's transaction."""
    from app.core.investigation import (
        _sync_investigation_relation_links,
    )
    if record.module == "customer":
        await _sync_legacy_customer(record, identity, db)
    elif record.module == "contract":
        await _sync_legacy_contract(record, identity, db)
    elif record.module == "case":
        await _sync_legacy_case(record, identity, db)
    elif record.module == "investigation":
        await _sync_legacy_investigation(record, identity, db)
    elif record.module == "task" and (record.data or {}).get("investigation_record_id"):
        await _sync_legacy_investigation_task(record, identity, db)
    elif record.module == "clue":
        await _sync_legacy_investigation_clue(record, identity, db)
    elif record.module == "seal":
        await _sync_legacy_official_document(record, identity, db)
    await _sync_investigation_relation_links(record, db)
