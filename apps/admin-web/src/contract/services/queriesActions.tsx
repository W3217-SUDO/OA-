import { message } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import type { MessageType } from "antd/es/message/interface";
import dayjs from "dayjs";
import { api } from "../../api";
import { rememberCaseDetailTarget } from "../../caseDetailNavigation";
import { buildContractCustomerQueryFromRelation } from "../../contractCenterCustomerNavigation";
import { buildContractDetailRoute, consumeContractDetailTarget, sortContractObjectLogs, type ContractDetailNavigationContext } from "../../contractDetailNavigation";
import type { ContractListPagination } from "../../contractListPagination.mjs";
import { saveContractListQuery } from "../../contractListQuery";
import { CONTRACT_OBJECT_DEFAULT_PAGE_SIZE, sortContractObjectRows, sortContractRecordRows } from "../../contractObjectListPolicy.mjs";
import { filterContractIncomingPayments } from "../../contractObjectPresentation.mjs";
import { normalizeContractPaymentApplications } from "../../contractPaymentApplicationPresentation.mjs";
import { buildContractEventsRequest, buildContractListRequestParams, extractContractErrorMessage, filterContractLinkedRows, normalizeContractApprovalHistory, normalizeContractAttachment, normalizeContractEventsResponse } from "../../contractWorkflowPolicy.mjs";
import { rememberCustomerDetailTarget, resolveCustomerDetailTarget } from "../../customerDetailNavigation";
import { consumeCustomerRelationTarget } from "../../customerRelationNavigation";
import { resolveDetailRelation } from "../../detailRelationResolver";
import { CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY, CONTRACT_DETAIL_TAB_STORAGE_KEY, CONTRACT_SEAL_READY_STATUSES, consumeContractDetailTabKey, normalizeContractDetailTabKey } from "../constants";
import type { Attachment, Contract, ContractArchiveSubject, ContractArchiveSummary, ContractEvent, ContractWorkflowCapabilities, CustomerRef, DirectoryUser, HistoryEvent, Profile, SealAsset, Step } from "../types";
type ContractObjectRow = {
    id: number;
    case_record_id: number;
    case_no: string;
    case_title: string;
    case_type: string;
    case_phase: string;
    fee_type: string;
    amount: number;
    customer_manager: string;
    remark: string;
    logs: Array<{
        id: number;
        action: string;
        before: Record<string, unknown>;
        after: Record<string, unknown>;
        operator: string;
        created_at: string;
    }>;
};
/** contract queries operations; dependencies are read when each operation runs. */
export interface ContractQueriesDependencies {
    readonly isContractDetailView: boolean;
    readonly initialView: string;
    readonly query: Record<string, any>;
    readonly onNavigate: ((key: string) => void) | undefined;
    readonly setDetailActiveTab: React.Dispatch<React.SetStateAction<string>>;
    readonly viewing: Contract | null;
    readonly viewingAttachmentRequest: React.RefObject<number>;
    readonly contractEventRequestTracker: React.RefObject<{
        next(): number;
        isCurrent(requestId: number): boolean;
    }>;
    readonly setViewing: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly setViewingAttachments: React.Dispatch<React.SetStateAction<Attachment[]>>;
    readonly setSelectedAttachmentKeys: React.Dispatch<React.SetStateAction<React.Key[]>>;
    readonly setViewingAttachmentsLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setViewingAttachmentsError: React.Dispatch<React.SetStateAction<string | null>>;
    readonly setContractEventsLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setContractEventsError: React.Dispatch<React.SetStateAction<string | null>>;
    readonly setContractEvents: React.Dispatch<React.SetStateAction<ContractEvent[]>>;
    readonly setContractWorkflowEvents: React.Dispatch<React.SetStateAction<ContractEvent[]>>;
    readonly setContractEventPage: React.Dispatch<React.SetStateAction<number>>;
    readonly setContractEventPageSize: React.Dispatch<React.SetStateAction<number>>;
    readonly setContractEventTotal: React.Dispatch<React.SetStateAction<number>>;
    readonly setContractEventKeyword: React.Dispatch<React.SetStateAction<string>>;
    readonly setObjectPage: React.Dispatch<React.SetStateAction<number>>;
    readonly setObjectPageSize: React.Dispatch<React.SetStateAction<number>>;
    readonly setContractObjects: React.Dispatch<React.SetStateAction<ContractObjectRow[]>>;
    readonly setObjectCases: React.Dispatch<React.SetStateAction<{
        id: number;
        serial_no: string;
        title: string;
        customer: string;
    }[]>>;
    readonly setDetailReceipts: React.Dispatch<React.SetStateAction<any[]>>;
    readonly setDetailInvoices: React.Dispatch<React.SetStateAction<Contract[]>>;
    readonly setDetailPayments: React.Dispatch<React.SetStateAction<Contract[]>>;
    readonly setDetailApprovals: React.Dispatch<React.SetStateAction<Step[]>>;
    readonly setDetailApprovalsError: React.Dispatch<React.SetStateAction<string | null>>;
    readonly contractEventKeyword: string;
    readonly contractEventPageSize: number;
    readonly contractCapabilities: (contract?: Contract | null | undefined, options?: Record<string, unknown>) => ContractWorkflowCapabilities;
    readonly denyContractAction: () => MessageType;
    readonly setArchiveSubjectsLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setArchiveSummary: React.Dispatch<React.SetStateAction<ContractArchiveSummary | null>>;
    readonly setArchiveSubjects: React.Dispatch<React.SetStateAction<ContractArchiveSubject[]>>;
    readonly setSelectedArchiveObjectKeys: React.Dispatch<React.SetStateAction<React.Key[]>>;
    readonly setArchiveClosureComment: React.Dispatch<React.SetStateAction<string>>;
    readonly contractListRequestGuard: {
        begin(): number;
        isLatest(requestId: number): boolean;
    };
    readonly setLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly isContractInvestigationView: boolean;
    readonly contractInvestigationRouteTarget: ContractDetailNavigationContext | null;
    readonly detailTarget: ContractDetailNavigationContext | null | undefined;
    readonly contractDetailRouteTarget: ContractDetailNavigationContext | null;
    readonly customerRelationQueryViewRef: React.RefObject<string | null>;
    readonly customerRelationQueryRef: React.RefObject<Record<string, any> | null>;
    readonly queryForm: FormInstance<any>;
    readonly setQuery: React.Dispatch<React.SetStateAction<Record<string, any>>>;
    readonly listPagination: ContractListPagination;
    readonly isArchiveView: boolean;
    readonly openInvestigation: (r: Contract) => Promise<void>;
    readonly onDetailTargetHandled: (() => void) | undefined;
    readonly setAllRows: React.Dispatch<React.SetStateAction<Contract[]>>;
    readonly setListTotal: React.Dispatch<React.SetStateAction<number>>;
    readonly setProfile: React.Dispatch<React.SetStateAction<Profile>>;
    readonly setDirectory: React.Dispatch<React.SetStateAction<DirectoryUser[]>>;
    readonly setSealAssets: React.Dispatch<React.SetStateAction<SealAsset[]>>;
    readonly setCustomers: React.Dispatch<React.SetStateAction<CustomerRef[]>>;
    readonly setWizardDraft: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly setSteps: React.Dispatch<React.SetStateAction<Step[]>>;
    readonly submitForm: FormInstance<any>;
    readonly populateDraftForm: (contract: Contract) => void;
    readonly setAttachments: React.Dispatch<React.SetStateAction<Attachment[]>>;
    readonly setHistory: React.Dispatch<React.SetStateAction<HistoryEvent[]>>;
    readonly wizardDraft: Contract | null;
    readonly setWizardStep: React.Dispatch<React.SetStateAction<number>>;
    readonly sealForm: FormInstance<any>;
    readonly setContractFile: React.Dispatch<React.SetStateAction<File | null>>;
    readonly attachments: Attachment[];
    readonly buildContractExportParams: () => {
        [x: string]: unknown;
    };
    readonly buildArchiveExportParams: () => {
        contract_no: any;
        customer: any;
        archive_status: any;
        archive_date_from: any;
        archive_date_to: any;
    };
}
export function createContractQueriesActions(context: ContractQueriesDependencies) {
    const openViewing = async (contract: Contract, options: {
        detailTab?: string;
    } = {}) => {
        const { isContractDetailView, initialView, query, onNavigate, setDetailActiveTab, viewing, viewingAttachmentRequest, contractEventRequestTracker, setViewing, setViewingAttachments, setSelectedAttachmentKeys, setViewingAttachmentsLoading, setViewingAttachmentsError, setContractEventsLoading, setContractEventsError, setContractEvents, setContractWorkflowEvents, setContractEventPage, setContractEventPageSize, setContractEventTotal, setContractEventKeyword, setObjectPage, setObjectPageSize, setContractObjects, setObjectCases, setDetailReceipts, setDetailInvoices, setDetailPayments, setDetailApprovals, setDetailApprovalsError } = context;
        if (!isContractDetailView) {
            try {
                saveContractListQuery(sessionStorage, initialView, query);
                sessionStorage.setItem(CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY, initialView);
                if (options.detailTab) {
                    sessionStorage.setItem(CONTRACT_DETAIL_TAB_STORAGE_KEY, normalizeContractDetailTabKey(options.detailTab));
                }
                else {
                    sessionStorage.removeItem(CONTRACT_DETAIL_TAB_STORAGE_KEY);
                }
            }
            catch {
                // Session storage may be unavailable in embedded/private contexts.
            }
            const route = buildContractDetailRoute(contract);
            if (route)
                onNavigate?.(route);
            return;
        }
        const pendingDetailTab = options.detailTab ? normalizeContractDetailTabKey(options.detailTab) : consumeContractDetailTabKey();
        if (pendingDetailTab)
            setDetailActiveTab(pendingDetailTab);
        else if (viewing?.id !== contract.id)
            setDetailActiveTab("objects");
        const requestId = ++viewingAttachmentRequest.current;
        const eventRequestId = contractEventRequestTracker.current.next();
        setViewing(contract);
        setViewingAttachments([]);
        setSelectedAttachmentKeys([]);
        setViewingAttachmentsLoading(true);
        setViewingAttachmentsError(null);
        setContractEventsLoading(true);
        setContractEventsError(null);
        try {
            const eventRequest = buildContractEventsRequest(contract, { page: 1, pageSize: 15 });
            const [attachmentResult, eventResult, workflowHistoryResult, objectResult, caseResult, receiptResult, invoiceResult, paymentResult, approvalResult] = await Promise.allSettled([
                api.get("/attachments", { params: { record_id: contract.id } }),
                eventRequest.path ? api.get(eventRequest.path, { params: eventRequest.params }) : Promise.resolve({ data: { items: [] } }),
                api.get(`/records/${contract.id}/history`),
                api.get(`/contracts/${contract.id}/objects`),
                api.get(`/contracts/${contract.id}/object-cases`),
                api.get("/finance/incoming-payments"),
                // Invoice records are keyed by contract_record_id/contract_no rather
                // than the generic record serial/title search fields.  Query the
                // finance invoice projection so issued applications reappear in the
                // contract detail instead of falling through to an empty table.
                api.get("/finance/invoices", { params: { scope: "company", customer: contract.customer, page: 1, page_size: 100 } }),
                api.get(`/contracts/${contract.id}/payment-applications`),
                api.get(`/contracts/${contract.id}/approvals`),
            ]);
            if (requestId === viewingAttachmentRequest.current) {
                setViewingAttachments(attachmentResult.status === "fulfilled" ? (attachmentResult.value.data.items || []).map((item: Attachment) => ({ ...item, ...normalizeContractAttachment(item) })) : []);
                setViewingAttachmentsError(attachmentResult.status === "rejected" ? extractContractErrorMessage(attachmentResult.reason, "合同附件加载失败") : null);
                const eventPayload = eventResult.status === "fulfilled" ? normalizeContractEventsResponse(eventResult.value.data) : null;
                const manualEvents = eventPayload?.items.map((event) => ({ ...event, contract_record_id: contract.id })) || [];
                const workflowEvents = workflowHistoryResult.status === "fulfilled"
                    ? (workflowHistoryResult.value.data.items || []).map((event: HistoryEvent) => ({
                        id: -event.id,
                        contract_record_id: contract.id,
                        content: [event.action, event.comment].filter(Boolean).join("："),
                        operator: event.operator,
                        created_at: event.created_at,
                    }))
                    : [];
                if (contractEventRequestTracker.current.isCurrent(eventRequestId)) {
                    setContractEvents(manualEvents);
                    setContractWorkflowEvents(workflowEvents);
                    setContractEventPage(eventPayload?.page || 1);
                    setContractEventPageSize(eventPayload?.pageSize || 15);
                    setContractEventTotal(eventPayload?.total || 0);
                    setContractEventKeyword("");
                    setContractEventsError(eventResult.status === "rejected" ? extractContractErrorMessage(eventResult.reason, "合同事项加载失败") : null);
                }
                setObjectPage(1);
                setObjectPageSize(CONTRACT_OBJECT_DEFAULT_PAGE_SIZE);
                setContractObjects(objectResult.status === "fulfilled"
                    ? sortContractObjectRows((objectResult.value.data.items || []).map((item: ContractObjectRow) => ({ ...item, logs: sortContractObjectLogs(item.logs || []) })))
                    : []);
                setObjectCases(caseResult.status === "fulfilled" ? (caseResult.value.data.items || []) : []);
                setDetailReceipts(receiptResult.status === "fulfilled"
                    ? sortContractRecordRows(filterContractIncomingPayments(receiptResult.value.data.items || [], contract) as any[])
                    : []);
                setDetailInvoices(invoiceResult.status === "fulfilled"
                    ? sortContractRecordRows(filterContractLinkedRows(invoiceResult.value.data.items || [], contract))
                    : []);
                setDetailPayments(paymentResult.status === "fulfilled"
                    ? normalizeContractPaymentApplications(paymentResult.value.data, contract).slice().sort((left, right) => left.id - right.id)
                    : []);
                const approvalItems = approvalResult.status === "fulfilled" ? approvalResult.value.data.items || [] : [];
                setDetailApprovals(normalizeContractApprovalHistory(approvalItems).map((item, index) => ({ ...item, step_order: Number(approvalItems[index]?.step_order || index + 1) })) as Step[]);
                setDetailApprovalsError(approvalResult.status === "rejected" ? extractContractErrorMessage(approvalResult.reason, "合同审批信息加载失败") : null);
                if (attachmentResult.status === "rejected" || (contractEventRequestTracker.current.isCurrent(eventRequestId) && (eventResult.status === "rejected" || workflowHistoryResult.status === "rejected")) || objectResult.status === "rejected" || approvalResult.status === "rejected") {
                    message.warning("合同基础信息已打开，部分附件、事项、合同标的或审批信息暂时加载失败");
                }
            }
        }
        catch (error: any) {
            if (requestId === viewingAttachmentRequest.current) {
                message.error(error?.response?.data?.detail || "合同附件加载失败，请稍后重试");
            }
        }
        finally {
            if (requestId === viewingAttachmentRequest.current) {
                setViewingAttachmentsLoading(false);
                if (contractEventRequestTracker.current.isCurrent(eventRequestId))
                    setContractEventsLoading(false);
            }
        }
    };
    const reloadContractEvents = async (contract: Contract, page = 1, keyword = context.contractEventKeyword, pageSize = context.contractEventPageSize) => {
        const { contractEventKeyword, contractEventPageSize, contractEventRequestTracker, setContractEvents, setContractEventTotal, setContractEventsError, setContractEventsLoading, setContractEventPage, setContractEventPageSize, setContractEventKeyword } = context;
        const eventRequestId = contractEventRequestTracker.current.next();
        const eventRequest = buildContractEventsRequest(contract, { page, pageSize, keyword });
        if (!eventRequest.path) {
            if (contractEventRequestTracker.current.isCurrent(eventRequestId)) {
                setContractEvents([]);
                setContractEventTotal(0);
                setContractEventsError(null);
                setContractEventsLoading(false);
            }
            return;
        }
        setContractEventsLoading(true);
        setContractEventsError(null);
        try {
            const response = await api.get(eventRequest.path, { params: eventRequest.params });
            const payload = normalizeContractEventsResponse(response.data);
            if (contractEventRequestTracker.current.isCurrent(eventRequestId)) {
                setContractEvents(payload.items.map((event) => ({ ...event, contract_record_id: contract.id })));
                setContractEventPage(payload.page);
                setContractEventPageSize(payload.pageSize);
                setContractEventTotal(payload.total);
                setContractEventKeyword(String(keyword || "").trim());
            }
        }
        catch (error: any) {
            if (contractEventRequestTracker.current.isCurrent(eventRequestId))
                setContractEventsError(extractContractErrorMessage(error, "合同事项加载失败"));
        }
        finally {
            if (contractEventRequestTracker.current.isCurrent(eventRequestId))
                setContractEventsLoading(false);
        }
    };
    const reloadDetailApprovals = async (contract: Contract) => {
        const { setDetailApprovalsError, setDetailApprovals } = context;
        setDetailApprovalsError(null);
        try {
            const response = await api.get(`/contracts/${contract.id}/approvals`);
            const items = response.data.items || [];
            setDetailApprovals(normalizeContractApprovalHistory(items).map((item: any, index: number) => ({ ...item, step_order: Number(items[index]?.step_order || index + 1) })) as Step[]);
        }
        catch (error: any) {
            setDetailApprovalsError(extractContractErrorMessage(error, "合同审批信息加载失败"));
        }
    };
    const loadArchiveSubjects = async (contract: Contract) => {
        const { contractCapabilities, denyContractAction, setArchiveSubjectsLoading, setArchiveSummary, setArchiveSubjects, setSelectedArchiveObjectKeys, setArchiveClosureComment } = context;
        if (!contractCapabilities(contract).canArchive) {
            denyContractAction();
            return;
        }
        setArchiveSubjectsLoading(true);
        try {
            const { data } = await api.get(`/contracts/${contract.id}/archive-subjects`);
            setArchiveSummary(data.contract || null);
            setArchiveSubjects(data.items || []);
            setSelectedArchiveObjectKeys([]);
            setArchiveClosureComment("");
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "合同归档完结数据加载失败"));
        }
        finally {
            setArchiveSubjectsLoading(false);
        }
    };
    const resolveContractDetailTarget = async (target: ContractDetailNavigationContext): Promise<Contract | null> => {
        if (target.id) {
            try {
                const response = await api.get(`/records/${target.id}`);
                if (response.data?.module === "contract")
                    return response.data as Contract;
            }
            catch {
                // A deleted, out-of-scope, or stale id may still have a usable serial-number fallback below.
            }
        }
        const serialNo = String(target.serial_no || "").trim();
        if (!serialNo)
            return null;
        try {
            const response = await api.get("/records", {
                params: { module: "contract", keyword: serialNo, page: 1, page_size: 100 },
            });
            return (response.data.items || []).find((item: Contract) => item.serial_no === serialNo) || null;
        }
        catch {
            return null;
        }
    };
    const load = async (queryOverride?: Record<string, any>, paginationOverride?: {
        current: number;
        pageSize: number;
    }) => {
        const { contractListRequestGuard, setLoading, isContractInvestigationView, contractInvestigationRouteTarget, detailTarget, contractDetailRouteTarget, customerRelationQueryViewRef, initialView, customerRelationQueryRef, query, queryForm, setQuery, listPagination, isArchiveView, openInvestigation, onDetailTargetHandled, setAllRows, setListTotal, setProfile, setDirectory, setSealAssets, setCustomers } = context;
        const requestId = contractListRequestGuard.begin();
        setLoading(true);
        const target = isContractInvestigationView
            ? contractInvestigationRouteTarget
            : detailTarget || consumeContractDetailTarget() || contractDetailRouteTarget;
        if (customerRelationQueryViewRef.current && customerRelationQueryViewRef.current !== initialView) {
            customerRelationQueryRef.current = null;
            customerRelationQueryViewRef.current = null;
        }
        const consumedRelationQuery = buildContractCustomerQueryFromRelation(consumeCustomerRelationTarget("contracts"));
        const relationQuery = consumedRelationQuery || customerRelationQueryRef.current;
        // Relationship navigation carries the immutable customer identity and must
        // replace every stale filter restored from a previous list visit.
        const baseQuery = queryOverride ?? query;
        const effectiveQuery = relationQuery
            ? { ...relationQuery }
            : baseQuery;
        if (relationQuery) {
            customerRelationQueryRef.current = effectiveQuery;
            customerRelationQueryViewRef.current = initialView;
        }
        if (relationQuery) {
            queryForm.resetFields();
            queryForm.setFieldsValue(relationQuery);
            setQuery(effectiveQuery);
        }
        const currentPagination = paginationOverride || listPagination;
        const recordsParams = buildContractListRequestParams(initialView, currentPagination, effectiveQuery);
        const archiveDate = Array.isArray(effectiveQuery.archive_date) ? effectiveQuery.archive_date : [];
        const archiveParams = {
            contract_no: effectiveQuery.serial_no || undefined,
            customer: effectiveQuery.customer || undefined,
            archive_status: effectiveQuery.archive_status || undefined,
            archive_date_from: archiveDate[0]?.format?.("YYYY-MM-DD"),
            archive_date_to: archiveDate[1]?.format?.("YYYY-MM-DD"),
            page: currentPagination.current,
            page_size: currentPagination.pageSize,
        };
        const recordsRequest = isArchiveView
            ? api.get("/contracts/archive-list", { params: archiveParams })
            : api.get("/records", { params: recordsParams });
        const targetRequest = target ? resolveContractDetailTarget(target) : null;
        const auxiliaryRequests = Promise.allSettled([
            api.get("/auth/me"),
            api.get("/users/directory", { params: { purpose: "contract_approver" } }),
            api.get("/seals/assets"),
            api.get("/customers", { params: { scope: "mine", customer_type: "客户", page: 1, page_size: 200 } }),
        ]);
        // A dedicated detail route must not wait for the full contract list or
        // unrelated directory/seal/customer data before showing its target.
        if (target) {
            const targetRow = await targetRequest;
            if (targetRow) {
                if (isContractInvestigationView)
                    void openInvestigation(targetRow);
                else
                    void openViewing(targetRow);
            }
            else
                message.warning("未找到关联合同或当前账号无权查看");
            onDetailTargetHandled?.();
        }
        try {
            const recordsRes = await recordsRequest;
            if (contractListRequestGuard.isLatest(requestId)) {
                setAllRows(recordsRes.data.items || []);
                setListTotal(Number(recordsRes.data.total || 0));
            }
        }
        catch (error: any) {
            if (contractListRequestGuard.isLatest(requestId))
                message.error(extractContractErrorMessage(error, "合同数据加载失败"));
        }
        finally {
            if (contractListRequestGuard.isLatest(requestId))
                setLoading(false);
        }
        const [profileResult, directoryResult, sealResult, customerResult] = await auxiliaryRequests;
        if (profileResult.status === "fulfilled")
            setProfile(profileResult.value.data);
        if (directoryResult.status === "fulfilled")
            setDirectory((directoryResult.value.data.items || []).filter((item: DirectoryUser) => item.is_active !== false));
        if (sealResult.status === "fulfilled")
            setSealAssets((sealResult.value.data.items || []).filter((item: SealAsset) => item.status === "可用"));
        if (customerResult.status === "fulfilled")
            setCustomers(customerResult.value.data.items || []);
        if ([profileResult, directoryResult, sealResult, customerResult].some((result) => result.status === "rejected")) {
            message.warning("合同基础列表已加载，部分辅助数据暂时不可用");
        }
    };
    const loadWizardContext = async (contractId: number) => {
        const { setWizardDraft, setSteps, submitForm, populateDraftForm, setAttachments, setHistory } = context;
        const approvalRes = await api.get(`/contracts/${contractId}/approvals`);
        const contract = approvalRes.data.contract as Contract;
        setWizardDraft(contract);
        setSteps(approvalRes.data.items || []);
        submitForm.setFieldsValue({
            approvers: (approvalRes.data.items || [])[0]?.approver,
            comment: contract.data.submit_comment || "",
        });
        populateDraftForm(contract);
        const [attachmentResult, historyResult] = await Promise.allSettled([
            api.get("/attachments", { params: { record_id: contractId } }),
            api.get(`/records/${contractId}/history`),
        ]);
        const attachmentItems = attachmentResult.status === "fulfilled" ? attachmentResult.value.data.items || [] : [];
        setAttachments(attachmentItems.map((item: Attachment) => ({ ...item, ...normalizeContractAttachment(item) })));
        setHistory(historyResult.status === "fulfilled" ? historyResult.value.data.items || [] : []);
        if (attachmentResult.status === "rejected" || historyResult.status === "rejected") {
            message.warning("合同主体已加载，部分附件或历史记录暂时不可用");
        }
        return contract;
    };
    const refreshWizard = async () => {
        const { wizardDraft, setWizardStep, sealForm, setContractFile, setSelectedAttachmentKeys, attachments } = context;
        if (!wizardDraft)
            return;
        try {
            const contract = await loadWizardContext(wizardDraft.id);
            if (contract.status === "已拒绝") {
                setWizardStep(1);
                sealForm.resetFields();
                setContractFile(null);
                setSelectedAttachmentKeys([]);
            }
            else if (CONTRACT_SEAL_READY_STATUSES.includes(contract.status)) {
                setWizardStep(3);
                sealForm.setFieldsValue({
                    copies: 1,
                    use_date: dayjs().add(1, "day"),
                    delivery_method: "现场用印",
                    document_names: attachments.map((item) => item.original_name).join("、"),
                    purpose: `${contract.title}合同用印`,
                    submit: false,
                });
            }
        }
        catch {
            message.error("审批状态加载失败");
        }
    };
    const exportCsv = async () => {
        const { buildContractExportParams } = context;
        try {
            const res = await api.get("/records/export", {
                params: buildContractExportParams(),
                responseType: "blob",
            });
            const url = URL.createObjectURL(res.data);
            const link = document.createElement("a");
            link.href = url;
            link.download = "合同资料.csv";
            link.click();
            URL.revokeObjectURL(url);
        }
        catch {
            message.error("导出失败");
        }
    };
    const exportExcel = async () => {
        const { isArchiveView, buildArchiveExportParams, buildContractExportParams } = context;
        try {
            const res = await api.get(isArchiveView ? "/contracts/archive-list/export-excel" : "/records/export-excel", {
                params: isArchiveView ? buildArchiveExportParams() : buildContractExportParams(),
                responseType: "blob",
            });
            const url = URL.createObjectURL(res.data);
            const link = document.createElement("a");
            link.href = url;
            link.download = isArchiveView ? "合同归档.xls" : "合同资料.xls";
            link.click();
            URL.revokeObjectURL(url);
        }
        catch {
            message.error("导出失败");
        }
    };
    const exportContractDetailExcel = async (contract: Contract) => {
        try {
            const res = await api.get(`/contracts/${contract.id}/export`, {
                responseType: "blob",
            });
            const url = URL.createObjectURL(res.data);
            const link = document.createElement("a");
            link.href = url;
            link.download = (contract.serial_no || contract.title || "合同详情") + ".xls";
            link.click();
            URL.revokeObjectURL(url);
        }
        catch {
            message.error("导出失败");
        }
    };
    const openRelatedCustomer = async (contract: Contract) => {
        const { onNavigate } = context;
        const source = { id: Number(contract.data.customer_id) || undefined, serial_no: contract.data.customer_no, title: contract.customer };
        if (!source.id && !source.serial_no && !source.title) {
            message.warning("当前合同未关联客户");
            return;
        }
        const customer = await resolveCustomerDetailTarget(source);
        if (!customer) {
            message.warning("未找到关联客户或当前账号无权查看");
            return;
        }
        rememberCustomerDetailTarget(customer);
        onNavigate?.("customer-company");
    };
    const openRelatedCase = async (caseNo: unknown) => {
        const { onNavigate } = context;
        const serialNo = String(caseNo || "").trim();
        if (!serialNo || serialNo === "—") {
            message.warning("当前合同未关联案件");
            return;
        }
        try {
            const record = await resolveDetailRelation("case", { serial_no: serialNo });
            if (!record) {
                message.warning("未找到关联案件或当前账号无权查看");
                return;
            }
            rememberCaseDetailTarget({ id: record.id, serial_no: record.serial_no });
            onNavigate?.("case-company");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "关联案件加载失败");
        }
    };
    return { openViewing, reloadContractEvents, reloadDetailApprovals, loadArchiveSubjects, resolveContractDetailTarget, load, loadWizardContext, refreshWizard, exportCsv, exportExcel, exportContractDetailExcel, openRelatedCustomer, openRelatedCase };
}
