"""通用业务记录查询接口。"""
from app.core.dependencies import (
    AsyncSession, BusinessRecord, ContractApprovalStep, Depends, Query, User, and_, current_identity, false, func, get_db, or_, select, settings,
)
from fastapi import APIRouter

router = APIRouter()


@router.get(f"{settings.api_prefix}/records")
async def list_records(
    module: str = Query(min_length=1, max_length=32),
    keyword: str = "", record_status: str = "", scope: str = Query("all", pattern="^(all|mine|recycle|department|company|audit)$"), statuses: str = "",
    customer_id: int | None = Query(default=None, gt=0), customer: str = "", customer_no: str = "", exclude_archived: bool = False,
    title: str = "", serial_no: str = "", record_type: str = Query("", alias="type"),
    case_no: str = "", fee_type: str = "", contract_body: str = "", source_person: str = "",
    finance_view: str = Query("", pattern="^(|external)$"),
    case_type: str = "", case_stage: str = "", contract_no: str = "", fee_group: str = "",
    receipt_status: str = "", notary_no: str = "", package_no: str = "",
    signed_at_start: str = "", signed_at_end: str = "",
    investigation_view: str = Query("", pattern="^(|published|assigned|unassigned)$"),
    archive_view: str = Query("", pattern="^(|pending|refused)$"),
    pending_approver_only: bool = False,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_action_granted,
    )
    from app.core.contracts import (
        _contract_customer_record_dicts,
    )
    from app.core.crm import (
        _customer_or_404,
    )
    from app.core.permissions import (
        _case_mine_scope_condition, _investigation_supervisor_condition, _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    actual_role_ids = identity.get("_actual_role_ids")
    if isinstance(actual_role_ids, (list, tuple, set)):
        actual_admin = "admin" in {str(value).strip() for value in actual_role_ids}
    else:
        actual_role = identity.get("_actual_role")
        actual_admin = (
            str(actual_role).strip() == "admin"
            if actual_role is not None
            else identity.get("role") == "admin"
        )
    await _require_record_module_menu(module, identity, db, action="查看")
    clue_audit_scope = module == "clue" and scope == "audit"
    conditions = [BusinessRecord.module == module]
    if clue_audit_scope:
        from app.core.clue_audit_scope import clue_audit_condition
        conditions.append(await clue_audit_condition(identity, db))
    if module == "case":
        conditions.append(BusinessRecord.status != "已合并")
    if module == "finance":
        conditions.append(BusinessRecord.status != "已删除")
        if finance_view == "external":
            from app.core.internal_requests import external_finance_condition

            conditions.append(external_finance_condition())
    relation_customer = None
    if module == "contract" and customer_id:
        relation_customer = await _customer_or_404(customer_id, identity, db)
    elif not (
        module == "contract"
        and scope == "department"
        and identity.get("role") in {"admin", "manager"}
    ) and not clue_audit_scope:
        # Department contracts are classified by the linked customer's active
        # managers below. Applying the contract row's stamped department first
        # would discard rows whose legacy department is stale.
        conditions.extend(await _record_scope_conditions(identity, db))
    if keyword:
        like = f"%{keyword}%"
        conditions.append(or_(BusinessRecord.serial_no.ilike(like), BusinessRecord.title.ilike(like), BusinessRecord.customer.ilike(like), BusinessRecord.owner.ilike(like)))
    if record_status:
        conditions.append(BusinessRecord.status == record_status)
    if module == "case":
        case_text_filters = (
            (BusinessRecord.serial_no, serial_no),
            (BusinessRecord.customer, customer),
            (BusinessRecord.data["case_type"].as_string(), case_type),
            (BusinessRecord.status, case_stage),
            (BusinessRecord.data["contract_no"].as_string(), contract_no),
            (BusinessRecord.data["fee_group"].as_string(), fee_group),
            (BusinessRecord.data["fee_type"].as_string(), fee_type),
            (BusinessRecord.data["receipt_status"].as_string(), receipt_status),
            (BusinessRecord.data["notary_no"].as_string(), notary_no),
            (BusinessRecord.data["package_no"].as_string(), package_no),
        )
        for column, value in case_text_filters:
            if value.strip():
                conditions.append(column.ilike(f"%{value.strip()}%"))
    if module == "case" and archive_view:
        archive_submitter = func.trim(func.coalesce(BusinessRecord.data["archive_submitter"].as_string(), ""))
        if archive_view == "pending":
            if not await _case_action_granted(identity, db, "case.archive.review"):
                return {"items": [], "total": 0, "page": page, "page_size": page_size, "pages": 0}
            archive_reviewer = func.trim(func.coalesce(BusinessRecord.data["archive_reviewer"].as_string(), ""))
            archive_internal_reviewer = func.trim(func.coalesce(BusinessRecord.data["archive_internal_reviewer"].as_string(), ""))
            conditions.extend([
                BusinessRecord.status.in_({"待归档审核", "亏损内审", "亏损审核"}),
                or_(
                    archive_reviewer == identity["username"],
                    archive_internal_reviewer == identity["username"],
                    and_(
                        archive_reviewer == "",
                        archive_internal_reviewer == "",
                        BusinessRecord.owner == identity["username"],
                    ),
                ),
                archive_submitter != identity["username"],
            ])
        else:
            conditions.extend([
                archive_submitter == identity["username"],
                or_(
                    BusinessRecord.status == "亏损归档拒绝",
                    func.trim(func.coalesce(BusinessRecord.data["archive_reject_reason"].as_string(), "")) != "",
                ),
            ])
    if module == "case" and scope == "mine":
        conditions.append(await _case_mine_scope_condition(identity, db))
    if module == "clue" and statuses:
        requested_statuses = [value.strip() for value in statuses.split(",") if value.strip()]
        if requested_statuses:
            conditions.append(BusinessRecord.status.in_(requested_statuses))
    if module == "clue" and scope == "mine":
        # "My investigation clues" is an actor projection for every role,
        # including administrators.  Elevated data access must not turn a
        # personal queue into the company-wide clue list.
        conditions.append(func.lower(BusinessRecord.owner) == identity["username"].lower())
    if module in {"investigation", "task"} and investigation_view:
        publisher_expr = func.lower(func.coalesce(BusinessRecord.data["publisher"].as_string(), ""))
        legacy_publisher_missing = or_(
            BusinessRecord.data["publisher"].as_string().is_(None),
            BusinessRecord.data["publisher"].as_string() == "",
        )
        if module == "investigation" and investigation_view == "published":
            conditions.append(or_(
                publisher_expr == identity["username"].lower(),
                and_(legacy_publisher_missing, BusinessRecord.owner == identity["username"]),
            ))
        elif module == "investigation" and investigation_view == "unassigned":
            conditions.extend([
                _investigation_supervisor_condition(identity["username"]),
                BusinessRecord.status.not_in({"已完成", "已取消"}),
            ])
        elif module == "task":
            investigation_subtask = or_(
                BusinessRecord.data["investigation_record_id"].as_integer() > 0,
                func.coalesce(BusinessRecord.data["investigation_no"].as_string(), "") != "",
                BusinessRecord.data["investigation_module"].as_string() == "investigation",
            )
            conditions.append(investigation_subtask)
            if investigation_view == "published" and not actual_admin:
                publisher_expr = func.lower(func.coalesce(
                    BusinessRecord.data["initiator"].as_string(),
                    BusinessRecord.data["publisher"].as_string(),
                    BusinessRecord.data["assigned_by"].as_string(),
                    "",
                ))
                legacy_publisher_missing = and_(
                    or_(BusinessRecord.data["initiator"].as_string().is_(None), BusinessRecord.data["initiator"].as_string() == ""),
                    or_(BusinessRecord.data["publisher"].as_string().is_(None), BusinessRecord.data["publisher"].as_string() == ""),
                    or_(BusinessRecord.data["assigned_by"].as_string().is_(None), BusinessRecord.data["assigned_by"].as_string() == ""),
                )
                conditions.append(or_(
                    publisher_expr == identity["username"].lower(),
                    and_(legacy_publisher_missing, func.lower(BusinessRecord.owner) == identity["username"].lower()),
                ))
            elif investigation_view == "assigned" and not actual_admin:
                # "My investigation tasks" must be private to the assignee.
                # The normal data scope may include a supervisor's department,
                # tasks they initiated, or records shared for collaboration,
                # none of which makes another investigator's child task a
                # personal task.
                conditions.append(func.lower(BusinessRecord.owner) == identity["username"].lower())
        elif investigation_view == "assigned" and not actual_admin:
            # "My investigation tasks" must be private to the assignee.  The
            # normal data scope may include a supervisor's department, tasks
            # they initiated, or records shared for collaboration, none of
            # which makes another investigator's child task a personal task.
            conditions.append(func.lower(BusinessRecord.owner) == identity["username"].lower())
    if module == "contract":
        # Contract views pass scope/statuses from the frontend parity round; apply
        # them server-side so mine/dept/company/audit/recycle stay isolated.
        if title.strip():
            conditions.append(BusinessRecord.title.ilike(f"%{title.strip()}%"))
        if serial_no.strip():
            conditions.append(BusinessRecord.serial_no.ilike(f"%{serial_no.strip()}%"))
        if record_type.strip():
            conditions.append(BusinessRecord.data["type"].as_string() == record_type.strip())
        if case_no.strip():
            conditions.append(BusinessRecord.data["case_no"].as_string().ilike(f"%{case_no.strip()}%"))
        if fee_type.strip():
            conditions.append(BusinessRecord.data["fee_type"].as_string() == fee_type.strip())
        if contract_body.strip():
            conditions.append(BusinessRecord.data["contract_body"].as_string() == contract_body.strip())
        if source_person.strip():
            source_like = f"%{source_person.strip()}%"
            conditions.append(or_(
                BusinessRecord.data["source_person"].as_string().ilike(source_like),
                BusinessRecord.data["source_person_display_name"].as_string().ilike(source_like),
                BusinessRecord.owner.ilike(source_like),
            ))
        signed_at = func.substr(BusinessRecord.data["signed_at"].as_string(), 1, 10)
        if signed_at_start.strip():
            conditions.append(signed_at >= signed_at_start.strip())
        if signed_at_end.strip():
            conditions.append(signed_at <= signed_at_end.strip())
        if scope == "audit" and pending_approver_only:
            conditions.append(select(ContractApprovalStep.id).where(
                ContractApprovalStep.contract_record_id == BusinessRecord.id,
                ContractApprovalStep.approver == identity["username"],
                ContractApprovalStep.status == "待审批",
            ).exists())
        if statuses:
            requested_statuses = [value.strip() for value in statuses.split(",") if value.strip()]
            if requested_statuses:
                conditions.append(BusinessRecord.status.in_(requested_statuses))
        if scope == "recycle":
            conditions.append(BusinessRecord.status == "已回收")
        elif scope == "mine" and relation_customer is None:
            conditions.append(BusinessRecord.owner == identity["username"])
        elif scope == "department" and relation_customer is None:
            current_user = await db.scalar(select(User).where(User.username == identity["username"]))
            if current_user:
                department_users = (await db.scalars(select(User).where(
                    User.is_active.is_(True), User.department == current_user.department,
                ))).all()
                department_tokens = {
                    value
                    for user in department_users
                    for value in (str(user.username or "").strip(), str(user.display_name or "").strip())
                    if value
                }
                customers = (await db.scalars(select(BusinessRecord).where(
                    BusinessRecord.module == "customer",
                    BusinessRecord.status.not_in({"已回收", "公海"}),
                ))).all()
                customer_links = []
                for customer_record in customers:
                    managers = (customer_record.data or {}).get("customer_managers")
                    if not isinstance(managers, list) or not managers:
                        managers = [customer_record.owner]
                    if not (set(str(value).strip() for value in managers if str(value).strip()) & department_tokens):
                        continue
                    customer_links.append(BusinessRecord.data["customer_id"].as_integer() == customer_record.id)
                    if str(customer_record.serial_no or "").strip():
                        customer_links.append(BusinessRecord.data["customer_no"].as_string() == customer_record.serial_no)
                    if str(customer_record.title or "").strip():
                        customer_links.append(BusinessRecord.customer == customer_record.title)
                conditions.append(or_(*customer_links) if customer_links else false())
        if relation_customer is not None:
            relation_no = str(relation_customer.serial_no or "").strip()
            relation_name = str(relation_customer.title or "").strip()
            conditions.append(or_(
                BusinessRecord.data["customer_id"].as_integer() == relation_customer.id,
                BusinessRecord.data["customer_no"].as_string() == relation_no,
                func.lower(func.trim(BusinessRecord.customer)) == relation_name.casefold(),
            ))
        elif customer.strip():
            customer_like = f"%{customer.strip()}%"
            matching_customers = list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.module == "customer",
                BusinessRecord.title.ilike(customer_like),
            ))).all())
            customer_ids = [item.id for item in matching_customers]
            customer_nos = [
                str(item.serial_no or "").strip()
                for item in matching_customers
                if str(item.serial_no or "").strip()
            ]
            customer_conditions = [BusinessRecord.customer.ilike(customer_like)]
            if customer_ids:
                customer_conditions.extend([
                    BusinessRecord.data["customer_id"].as_integer().in_(customer_ids),
                    BusinessRecord.data["customer_record_id"].as_integer().in_(customer_ids),
                ])
            if customer_nos:
                customer_conditions.append(BusinessRecord.data["customer_no"].as_string().in_(customer_nos))
            conditions.append(or_(*customer_conditions))
        if relation_customer is None and customer_no.strip():
            conditions.append(BusinessRecord.data["customer_no"].as_string() == customer_no.strip())
        if exclude_archived:
            conditions.append(BusinessRecord.status.notin_(["已归档", "Archived", "archived"]))
    total = await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions))
    result = list((await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc()).offset((page - 1) * page_size).limit(page_size))).all())
    allowed_fields = await _allowed_field_keys(identity, db)
    return {
        "items": await _contract_customer_record_dicts(result, allowed_fields, db, identity),
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }
