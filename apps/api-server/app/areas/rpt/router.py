"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, FinanceTransaction, HTTPException,
    IncomingPayment, Query, Response, WorkflowEvent, and_,
    csv, current_identity, date, datetime, func,
    get_db, io, or_, select, settings,
    status, timezone, uuid4,
)
from app.models_shared import (
    ReportInput,
)
from fastapi import APIRouter

router = APIRouter()


@router.get(f"{settings.api_prefix}/reports/summary")
async def report_summary(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    modules = ["customer", "contract", "case", "task", "finance", "hr", "warehouse"]
    scope_conditions = await _record_scope_conditions(identity, db)
    counts = {module: int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == module, *scope_conditions)) or 0) for module in modules}
    reports = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "report", *scope_conditions))).all()
    return {"business_counts": counts, "total_reports": len(reports), "generated": sum(x.status == "已生成" for x in reports), "published": sum(x.status == "已发布" for x in reports)}


@router.get(f"{settings.api_prefix}/reports/staff-roi")
async def report_staff_roi(
    start_date: date | None = None,
    end_date: date | None = None,
    department_id: int | None = Query(default=None, gt=0),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.system import (
        _staff_roi_report,
    )
    return await _staff_roi_report(identity, db, start_date, end_date, department_id)


@router.get(f"{settings.api_prefix}/reports/staff-roi/export")
async def export_report_staff_roi(
    start_date: date | None = None,
    end_date: date | None = None,
    department_id: int | None = Query(default=None, gt=0),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.system import (
        _staff_roi_report,
    )
    report = await _staff_roi_report(identity, db, start_date, end_date, department_id)
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["员工", "账号", "部门", "业绩", "成本", "ROI(%)"])
    for item in report["items"]:
        writer.writerow([item["employee"], item["employee_username"], item["department"], item["performance"], item["cost"], "" if item["roi"] is None else item["roi"]])
    return Response(content=("\ufeff" + output.getvalue()).encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="staff-roi-{date.today()}.csv"'})


@router.get(f"{settings.api_prefix}/reports/large-screen")
async def report_large_screen(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return one scoped, realtime snapshot for the report-centre large screen."""
    from app.core.cases import (
        _large_screen_case_is_closed, _large_screen_case_is_excluded,
    )
    from app.core.formatters import (
        _case_filing_date, _user_display_map,
    )
    from app.core.constants import CASE_EVENT_TIME_ZONE
    from app.core.permissions import (
        _identity_role_ids, _permission_payload_for_identity, _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys, _large_screen_month_keys,
    )
    permission = await _permission_payload_for_identity(identity, db)
    if not identity.get("_page_menu_capability") and "admin" not in _identity_role_ids(identity) and "reports-large-screen" not in permission.get("menu_keys", []):
        raise HTTPException(status_code=403, detail="当前角色没有报表大屏权限")

    scope = await _record_scope_conditions(identity, db)
    visible_cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", *scope,
    ))).all())
    cases = [item for item in visible_cases if not _large_screen_case_is_excluded(item)]
    closed_cases = [item for item in cases if _large_screen_case_is_closed(item)]
    active_cases = [item for item in cases if not _large_screen_case_is_closed(item)]
    customers = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "customer", *scope,
    ))).all())

    type_counts: dict[str, int] = {}
    for case in cases:
        case_type = str((case.data or {}).get("case_type") or "未分类").strip() or "未分类"
        type_counts[case_type] = type_counts.get(case_type, 0) + 1

    today = datetime.now(timezone.utc).astimezone(CASE_EVENT_TIME_ZONE).date()
    month_keys = _large_screen_month_keys(today)
    monthly_cases = {key: 0 for key in month_keys}
    employee_counts: dict[str, int] = {}
    for case in cases:
        created_at = _case_filing_date(case)
        if created_at:
            month_key = created_at.strftime("%Y-%m")
            if month_key in monthly_cases:
                monthly_cases[month_key] += 1
            if created_at.year == today.year:
                owner = str(case.owner or "").strip() or "未分配"
                employee_counts[owner] = employee_counts.get(owner, 0) + 1
    users_by_username = await _user_display_map(set(employee_counts), db)
    employee_ranking = [
        {
            "username": username,
            "name": (users_by_username.get(username.lower()).display_name if users_by_username.get(username.lower()) else username),
            "value": value,
        }
        for username, value in sorted(employee_counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]

    amount_visible = "finance.amount" in await _allowed_field_keys(identity, db)
    monthly_income = {key: None for key in month_keys}
    monthly_expense = {key: None for key in month_keys}
    finance: dict = {
        "amount_visible": amount_visible,
        "income": None,
        "expense": None,
        "income_label": "实际到账",
        "expense_label": "实际已支付",
    }
    if amount_visible:
        # IncomingPayment is the bank-arrival source of truth.  Payments are
        # recorded financial transactions, so applications and approvals do not
        # inflate either total.
        from app.core.internal_payers import not_internal_payer
        # 内部公司之间的转款不算实际到账（BUG 500784）。
        incoming = list((await db.scalars(select(IncomingPayment).where(not_internal_payer(IncomingPayment.payer_name)))).all())
        if identity.get("role") not in {"admin", "auditor"}:
            visible_customer_titles = {item.title for item in customers}
            incoming = [
                item for item in incoming
                if item.operator == identity["username"]
                or item.claimant == identity["username"]
                or item.claimed_customer in visible_customer_titles
            ]
        visible_record_ids = set((await db.scalars(select(BusinessRecord.id).where(*scope))).all())
        # “任务逾期扣款”是扣员工绩效（金额为负），不是支出（思法汇成 11-01 14:59）。
        overdue_deductions = select(BusinessRecord.id).where(
            BusinessRecord.module == "finance", BusinessRecord.data["internal_fee_type"].as_string() == "任务逾期扣款")
        transaction_conditions = [FinanceTransaction.transaction_type == "付款", or_(
            FinanceTransaction.finance_record_id.is_(None), FinanceTransaction.finance_record_id.not_in(overdue_deductions))]
        if identity.get("role") != "admin":
            transaction_conditions.append(or_(
                and_(FinanceTransaction.finance_record_id.is_not(None), FinanceTransaction.finance_record_id.in_(visible_record_ids)),
                and_(FinanceTransaction.finance_record_id.is_(None), FinanceTransaction.operator == identity["username"]),
            ))
        payments = list((await db.scalars(select(FinanceTransaction).where(*transaction_conditions))).all())
        monthly_income = {key: 0.0 for key in month_keys}
        monthly_expense = {key: 0.0 for key in month_keys}
        for item in incoming:
            month_key = item.received_date.strftime("%Y-%m")
            if month_key in monthly_income:
                monthly_income[month_key] += float(item.amount or 0)
        for item in payments:
            month_key = item.transaction_date.strftime("%Y-%m")
            if month_key in monthly_expense:
                monthly_expense[month_key] += float(item.amount or 0)
        finance["income"] = round(sum(float(item.amount or 0) for item in incoming), 2)
        finance["expense"] = round(sum(float(item.amount or 0) for item in payments), 2)

    return {
        "source": "realtime",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_summary": {"total": len(cases), "in_progress": len(active_cases), "closed": len(closed_cases)},
        "finance": finance,
        "customer_summary": {"total": len(customers)},
        "employee_ranking": employee_ranking,
        "case_type_distribution": [
            {"name": name, "value": value}
            for name, value in sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "monthly_trend": [
            {
                "month": month,
                "cases": monthly_cases[month],
                "income": round(monthly_income[month], 2) if monthly_income[month] is not None else None,
                "expense": round(monthly_expense[month], 2) if monthly_expense[month] is not None else None,
            }
            for month in month_keys
        ],
        "definitions": {
            "case_total": "当前数据范围内排除草稿、撤销、撤回、作废、删除和合并记录后的案件数",
            "case_in_progress": "有效案件中未写入办结确认、未处于结案阶段且未归档的案件数",
            "case_closed": "已写入办结确认，或状态/案件阶段属于明确结案阶段，或历史状态为已归档、亏损归档的案件数",
            "income": "可见银行到账记录的实际到账金额，包含未认领到账，不按申请或分配次数重复计算",
            "expense": "可见付款流水的实际已支付金额，不包含费用申请或审批金额",
            "employee_ranking": f"{today.year}年有效新建案件数，按案件负责人排序",
            "monthly_trend": "最近12个自然月的有效新建案件数；有财务金额权限时同时返回实际到账和实际已支付金额",
        },
    }


ANALYTICS_TEXT_PARAMS = ("customer", "court_lawyer", "handling_lawyer", "assistant", "investigator", "court", "group_mode")
ANALYTICS_DATE_PARAMS = ("source_from", "source_to", "hearing_from", "hearing_to")


async def _cached_report_analytics(identity: dict, db: AsyncSession, view: str, params: dict):
    from app.core.system import (
        _report_analytics,
    )
    from app.core.finance_query_revision import finance_revision_snapshot
    from app.core.query_cache import cached_query
    # 与财务列表、客户ROI同一套缓存：案件、费用、到账、开庭等任一表有写入，修订号变化后自动重算（BUG20261101001 性能）。
    return await cached_query(
        db, identity, "reports.analytics", {"view": view, **params},
        lambda: _report_analytics(view, identity, db, *(params[key] for key in (
            "customer", "court_lawyer", "handling_lawyer", "assistant", "investigator", "court",
            "source_from", "source_to", "hearing_from", "hearing_to", "group_mode"))),
        snapshot_reader=finance_revision_snapshot,
    )


@router.get(f"{settings.api_prefix}/reports/analytics")
async def report_analytics(view: str, customer: str = "", court_lawyer: str = "", handling_lawyer: str = "", assistant: str = "", investigator: str = "", court: str = "", source_from: date | None = None, source_to: date | None = None, hearing_from: date | None = None, hearing_to: date | None = None, group_mode: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core import query_prewarm
    params = {"customer": customer, "court_lawyer": court_lawyer, "handling_lawyer": handling_lawyer, "assistant": assistant,
              "investigator": investigator, "court": court, "source_from": source_from, "source_to": source_to,
              "hearing_from": hearing_from, "hearing_to": hearing_to, "group_mode": group_mode}
    # 登记后台预热：数据变化后提前重算，打开报表直接命中缓存（BUG20261101001，2 秒内）。
    await query_prewarm.remember(db, "reports", "analytics", identity, {
        "view": view, **{key: params[key] for key in ANALYTICS_TEXT_PARAMS},
        **{key: params[key].isoformat() if params[key] else None for key in ANALYTICS_DATE_PARAMS},
    })
    return await _cached_report_analytics(identity, db, view, params)


async def _cached_customer_roi(identity: dict, db: AsyncSession, date_from: date | None, date_to: date | None, department: str, employee: str):
    from app.core.crm import (
        _customer_roi_analytics,
    )
    from app.core.finance_query_revision import finance_revision_snapshot
    from app.core.query_cache import cached_query
    # 与财务列表同一套缓存：任一业务表（到账单、付款、案件、客户……）有写入，修订号变化后自动重算。
    return await cached_query(
        db, identity, "reports.customer_roi",
        {"date_from": date_from, "date_to": date_to, "department": department, "employee": employee},
        lambda: _customer_roi_analytics(identity, db, date_from=date_from, date_to=date_to, department=department, employee=employee),
        snapshot_reader=finance_revision_snapshot,
    )


@router.get(f"{settings.api_prefix}/reports/customer-roi")
async def customer_roi_report(date_from: date | None = None, date_to: date | None = None, department: str = "", employee: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core import query_prewarm
    # 登记后台预热：数据变化后主进程提前重算，用户打开时直接命中缓存（BUG 500784，陶威要求 2 秒内）。
    await query_prewarm.remember(db, "reports", "customer_roi", identity, {
        "date_from": date_from.isoformat() if date_from else None, "date_to": date_to.isoformat() if date_to else None,
        "department": department, "employee": employee,
    })
    return await _cached_customer_roi(identity, db, date_from, date_to, department, employee)


async def _replay_customer_roi(name, identity, parameters, db):
    parse = lambda value: date.fromisoformat(value) if value else None
    if name == "analytics":
        await _cached_report_analytics(identity, db, str(parameters.get("view") or ""), {
            **{key: str(parameters.get(key) or "") for key in ANALYTICS_TEXT_PARAMS},
            **{key: parse(parameters.get(key)) for key in ANALYTICS_DATE_PARAMS},
        })
        return
    if name != "customer_roi":
        raise ValueError("未知的报表预热登记")
    await _cached_customer_roi(identity, db, parse(parameters.get("date_from")), parse(parameters.get("date_to")),
                               str(parameters.get("department") or ""), str(parameters.get("employee") or ""))


def _register_report_prewarm():
    from app.core import query_prewarm
    query_prewarm.register("reports", _replay_customer_roi)


_register_report_prewarm()


@router.get(f"{settings.api_prefix}/reports/customer-roi/export")
async def export_customer_roi_report(date_from: date | None = None, date_to: date | None = None, department: str = "", employee: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_roi_analytics,
    )
    data = await _customer_roi_analytics(identity, db, date_from=date_from, date_to=date_to, department=department, employee=employee)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["客户编号", "客户", "部门", "员工", "收入（开票+法院退费）", "成本（付款）", "利润", "ROI", "口径"])
    for row in data["rows"]:
        writer.writerow([row["customer_no"], row["customer"], row["department"], row["employee"], row["income"], row["cost"], row["profit"], "" if row["roi"] is None else f'{row["roi"]:.2f}%', data["formula"]])
    return Response(content=("\ufeff" + output.getvalue()).encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="customer-roi-{date.today()}.csv"'})


@router.get(f"{settings.api_prefix}/reports/analytics/export")
async def export_report_analytics(view: str, customer: str = "", court_lawyer: str = "", handling_lawyer: str = "", assistant: str = "", investigator: str = "", court: str = "", source_from: date | None = None, source_to: date | None = None, hearing_from: date | None = None, hearing_to: date | None = None, group_mode: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _report_analytics,
    )
    data = await _report_analytics(view, identity, db, customer, court_lawyer, handling_lawyer, assistant, investigator, court, source_from, source_to, hearing_from, hearing_to, group_mode)
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(["统计图", "分组", "数值", "单位"])
    for chart in data["charts"]:
        for item in chart["items"]: writer.writerow([chart["title"], item["name"], item["value"], chart["unit"]])
    return Response(content=("\ufeff" + output.getvalue()).encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="report-{view}-{date.today()}.csv"'})


@router.post(f"{settings.api_prefix}/reports/generate", status_code=status.HTTP_201_CREATED)
async def generate_report(body: ReportInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    supported = {"综合经营报表", "案件统计报表", "客户统计报表", "财务统计报表", "人事统计报表", "仓库统计报表"}
    if body.report_type not in supported:
        raise HTTPException(status_code=422, detail="不支持的报表类型")
    module_labels = {"customer": "客户数量", "contract": "合同数量", "case": "案件数量", "task": "任务数量", "finance": "费用数量", "hr": "员工数量", "warehouse": "库存物品种类"}
    type_modules = {"案件统计报表": ["case"], "客户统计报表": ["customer"], "财务统计报表": ["finance"], "人事统计报表": ["hr"], "仓库统计报表": ["warehouse"]}
    modules = type_modules.get(body.report_type, list(module_labels))
    scope_conditions = await _record_scope_conditions(identity, db)
    metrics: dict[str, int | float] = {}
    for module in modules:
        metrics[module_labels[module]] = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == module, *scope_conditions)) or 0)
    if "finance" in modules and "finance.amount" in await _allowed_field_keys(identity, db):
        fees = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance", *scope_conditions))).all()
        metrics["费用总额"] = round(sum(float((x.data or {}).get("amount", 0) or 0) for x in fees), 2)
        metrics["待审批费用"] = sum(x.status == "待审批" for x in fees)
    serial = f"BB{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:4].upper()}"
    item = BusinessRecord(module="report", serial_no=serial, title=body.title, status="已生成", owner=identity["username"], department="上海分所", description=body.description, data={"report_type": body.report_type, "period": body.period, "format": body.format, "metrics": metrics, "generated_at": datetime.now().isoformat(timespec="seconds")})
    db.add(item); await db.flush()
    db.add(WorkflowEvent(record_id=item.id, action="生成报表", to_status="已生成", operator=identity["username"], comment=f"{body.report_type}｜{body.period}"))
    await db.commit(); await db.refresh(item)
    return _record_dict(item)


@router.get(f"{settings.api_prefix}/reports/{{report_id}}/download")
async def download_report(report_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    report = await _ensure_record_module(report_id, "report", identity, db)
    data = report.data or {}; metrics = data.get("metrics", {})
    lines = ["指标,数值"]
    for label, value in metrics.items():
        safe_label = str(label).replace('"', '""'); safe_value = str(value).replace('"', '""')
        lines.append(f'"{safe_label}","{safe_value}"')
    content = "\ufeff" + "\r\n".join(lines)
    return Response(content=content.encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{report.serial_no}.csv"'})


@router.get(f"{settings.api_prefix}/reports/refund-progress")
async def refund_progress_report(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    # 退费进度按律师助理统计（BUG 500789）。
    from app.core.progress_reports import refund_progress_report as build
    return await build(identity, db)


@router.get(f"{settings.api_prefix}/reports/refund-progress/cases")
async def refund_progress_report_cases(person: str = "", stage: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.progress_reports import refund_progress_cases
    return await refund_progress_cases(identity, db, person=person.strip(), stage=stage.strip())


@router.get(f"{settings.api_prefix}/reports/execution-progress")
async def execution_progress_report(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    # 执行进度按律师助理统计，合并原来的三张执行进度表（BUG 500788）。
    from app.core.progress_reports import execution_progress_report as build
    return await build(identity, db)


@router.get(f"{settings.api_prefix}/reports/execution-progress/cases")
async def execution_progress_report_cases(person: str = "", stage: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.progress_reports import execution_progress_cases
    return await execution_progress_cases(identity, db, person=person.strip(), stage=stage.strip())
