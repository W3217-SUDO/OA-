"""逐项登记财务纯查询，在认证及参数解析之后接入共享缓存。"""

from collections import defaultdict
from functools import wraps
from inspect import iscoroutinefunction, signature

from fastapi import FastAPI
from fastapi.routing import APIRoute
from sqlalchemy import select

from app.config import settings
from app.models import BusinessRecord


FINANCE_JSON_QUERIES = {
    "/finance/jar-fees": "list_jar_fees",
    "/finance/jar-fees/{jar_fee_id}": "get_jar_fee",
    "/finance/jar-fees/{jar_fee_id}/files": "list_jar_fee_files",
    "/finance/jar-fees/{jar_fee_id}/operation-logs": "list_jar_fee_operation_logs",
    "/finance/fees/{fee_id}/informs": "list_finance_fee_informs",
    "/finance/payment-source/{source_id}": "get_finance_payment_source",
    "/receivables": "list_receivables",
    "/receivables/detail": "list_receivable_details",
    "/finance/invoices": "list_invoice_applications",
    "/finance/case-fees/invoice-status": "list_invoice_case_fees",
    "/finance/case-fees/refunds": "query_refund_case_fees",
    "/finance/case-fees/refunds/logs": "list_refund_case_fee_logs",
    "/finance/fees/query": "query_finance_fees",
    "/finance/refunds/query": "query_refund_applications",
    "/finance/internal-fees": "list_internal_fees",
    "/finance/internal-review-requests": "list_internal_review_requests",
    "/finance/legacy-history": "list_legacy_finance_history",
    "/finance/legacy-history/summary": "legacy_finance_history_summary",
    "/finance/legacy-history/{record_id}": "get_legacy_finance_history_record",
    "/finance/summary": "finance_summary",
    "/finance/incoming-payments": "list_incoming_payments",
    "/finance/customer-options": "list_finance_customer_options",
    "/finance/incoming-payments/{payment_id}": "get_incoming_payment",
    "/finance/incoming-payments/{payment_id}/view-assigned": "view_assigned_incoming_payment",
    "/finance/incoming-payments/{payment_id}/allocation-candidates": "incoming_payment_allocation_candidates",
    "/finance/incoming-payments/{payment_id}/refund-candidates": "incoming_payment_refund_candidates",
    "/finance/incoming-payments/{payment_id}/allocation-records": "get_allocation_records",
    "/finance/ar-summary": "finance_ar_summary",
    "/finance/contract-ledger/{contract_id}": "finance_contract_ledger",
    "/finance/general-settlements/pending": "list_general_settlement_candidates",
    "/finance/archive-settlements/pending": "list_pending_archive_settlements",
    "/finance/archive-settlements/payment": "list_archive_settlement_payments",
    "/finance/archive-settlements/paid": "list_paid_archive_settlements",
    "/finance/archive-settlements/rejected": "list_rejected_archive_settlements",
    "/finance/general-settlements/applications": "list_general_settlement_applications",
    "/finance/settlements/pending": "list_pending_finance_settlements",
    "/finance/fees/refund-review-candidates": "list_internal_refund_review_candidates",
    "/finance/payment-packages": "list_internal_payment_packages",
    "/finance/payment-packages/candidates": "list_internal_payment_package_candidates",
    "/finance/payment-packages/{package_id}": "get_internal_payment_package",
    "/finance/fees/{fee_id}/readiness": "finance_fee_readiness",
    "/finance/fees/{fee_id}/payment-types": "list_finance_fee_payment_types",
    "/finance/transactions": "list_finance_transactions",
    "/finance/reconciliations": "list_reconciliations",
    "/finance/payment-types": "list_finance_payment_types",
    "/finance/invoices/{invoice_id}": "get_invoice_application",
    "/finance/invoice-context": "invoice_application_context",
    "/finance/payment-workflow/list": "list_workflow_payments",
    "/finance/payment-workflow/{record_id}/document": "get_payment_document",
    "/finance/receipt-files/fees": "list_receipt_fees",
    "/finance/legacy-payment-history": "list_legacy_payment_history",
    "/finance/projection/fees": "list_unified_finance_projection",
    "/finance/projection/transactions": "list_unified_finance_transactions_projection",
    "/finance/payment-applications/query": "query_payment_applications",
    "/contract-payment-applications/{payment_id}/edit-context": "contract_payment_edit_context",
    "/people/options": "list_active_people_options",
}

# 文件内容、下载权限及响应头必须由原入口实时生成，不缓存文件响应。
FINANCE_FILE_QUERIES = {
    "/finance/jar-fees/export",
    "/finance/jar-fees/{jar_fee_id}/files/{attachment_id}/download",
    "/finance/fee-informs/{inform_id}/bill/download",
    "/finance/invoices/export",
    "/finance/case-fees/invoice-status/export",
    "/finance/case-fees/refunds/export",
    "/finance/fees/query/export",
    "/finance/refunds/export",
    "/finance/refunds/export-selected",
    "/finance/internal-fees/export",
    "/finance/incoming-payments/export",
    "/finance/incoming-payments/query/export",
    "/finance/archive-settlements/export",
    "/finance/archive-settlements/payment/export",
    "/finance/archive-settlements/paid/export",
    "/finance/archive-settlements/rejected/export",
    "/finance/general-settlements/export",
    "/finance/payment-packages/{package_no}/print-word",
}

FINANCE_CONDITIONAL_QUERIES = {
    "/records": "list_records",
    "/records/{record_id}": "get_record",
    "/records/{record_id}/history": "record_history",
    "/system/parameters/options": "list_system_parameter_options",
}

FINANCIAL_RECORD_MODULES = frozenset({
    "finance", "contract_payment", "invoice", "refund", "finance_package",
    "finance_settlement", "finance_fee_inform", "jar_fee",
})
FINANCE_RECORD_LIST_MODULES = FINANCIAL_RECORD_MODULES | {"case", "customer", "contract"}
FINANCE_PARAMETER_CATEGORIES = frozenset({"fee_type", "case_file_type"})


async def _financial_query_branch(path, values):
    if path == "/system/parameters/options":
        return values["category"] in FINANCE_PARAMETER_CATEGORIES
    if path == "/records":
        return values["module"] in FINANCE_RECORD_LIST_MODULES
    # 只投影模块名，不向缓存流程或可释放的只读会话传递 ORM 对象。
    # audit 使用线索审核的专用可见范围，不属于本轮财务详情登记。
    if values.get("scope") == "audit":
        return False
    module = await values["db"].scalar(select(BusinessRecord.module).where(
        BusinessRecord.id == values["record_id"],
    ))
    return module in FINANCIAL_RECORD_MODULES


def _wrap_query(endpoint, path):
    endpoint_signature = signature(endpoint)

    @wraps(endpoint)
    async def cached_endpoint(**values):
        bound = endpoint_signature.bind(**values)
        arguments = bound.arguments
        if path in FINANCE_CONDITIONAL_QUERIES and not await _financial_query_branch(path, arguments):
            return await endpoint(**arguments)
        from app.core.query_cache import cached_query

        parameters = {key: value for key, value in arguments.items() if key not in {"db", "identity"}}
        return await cached_query(
            arguments["db"], arguments["identity"], f"finance.{endpoint.__name__}",
            parameters, lambda: endpoint(**arguments),
        )

    return cached_endpoint


def install_finance_query_cache(app: FastAPI) -> None:
    """在全部 include_router 完成后登记，原依赖树及响应元数据不变。"""
    routes_by_path = defaultdict(list)
    prefix = settings.api_prefix
    for route in app.routes:
        if isinstance(route, APIRoute) and route.methods == {"GET"} and route.path.startswith(prefix + "/"):
            routes_by_path[route.path[len(prefix):]].append(route)
    expected = {**FINANCE_JSON_QUERIES, **FINANCE_CONDITIONAL_QUERIES}
    audited = set(expected) | FINANCE_FILE_QUERIES
    finance_paths = {path for path in routes_by_path if path.startswith("/finance/") or path in {"/receivables", "/receivables/detail"}}
    unaudited = finance_paths - audited
    missing = audited - set(routes_by_path)
    if unaudited or missing:
        raise RuntimeError(f"财务查询缓存登记不完整：未审计={sorted(unaudited)}；未挂载={sorted(missing)}")
    for path, name in expected.items():
        routes = routes_by_path[path]
        if len(routes) != 1:
            raise RuntimeError(f"财务查询入口重复挂载：{path}")
        route = routes[0]
        endpoint = route.endpoint
        if endpoint.__name__ != name or route.dependant.call is not endpoint or not iscoroutinefunction(endpoint):
            raise RuntimeError(f"财务查询入口实现与登记不一致：{path}")
        dependencies = {dependency.name for dependency in route.dependant.dependencies}
        if dependencies != {"identity", "db"}:
            raise RuntimeError(f"财务缓存入口含未审计依赖：{path}")
        parsed_parameters = {field.name for field in route.dependant.path_params + route.dependant.query_params}
        if set(signature(endpoint).parameters) != parsed_parameters | dependencies:
            raise RuntimeError(f"财务缓存入口含非查询参数：{path}")
        # FastAPI 已生成的 handler 持有此 dependant；仅改执行函数，不重建或跳过认证依赖。
        route.dependant.call = _wrap_query(endpoint, path)
