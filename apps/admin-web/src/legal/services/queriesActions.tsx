import { message } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import { api } from "../../api";
// @ts-expect-error Shared runtime helper intentionally has no declaration.
import { shouldApplyCaseClueResponse } from "../../caseClueRelationsRequestGuard.mjs";
import { resolveCaseSourcePerson } from "../../caseContractPrefill";
import type { CaseCounselSearchPayload } from "../../caseCounselSearchParity.mjs";
import { consumeCaseDetailTarget } from "../../caseDetailNavigation";
import { buildCaseFileTypeTreeOptions, resolveCaseFileTypeSelection } from "../../caseFifthBatchParity.mjs";
import type { LatestRequestGuard } from "../../caseOrdinarySearchParity.mjs";
import { buildCaseOrdinarySearchPayload, parseOrdinarySearchResult } from "../../caseOrdinarySearchParity.mjs";
import { rememberCustomerDetailTarget, resolveCustomerDetailTarget } from "../../customerDetailNavigation";
import { type FeeTypeCatalogItem } from "../../feeTypeHierarchy.mjs";
import { rememberInvestigationDetailTarget } from "../../investigationDetailNavigation";
import { noCaseDetailWriteCapability, noCaseEventCapabilities } from "../constants";
import type { AttachmentRow, CaseDetailCapabilities, CaseEventCapabilities, CaseEventRow, CaseFileTypeOption, CaseLitigantCandidate, CaseRelationCatalog, CaseRow, CaseTaskAttachment, CaseTaskHistoryItem, CaseTaskPageState, ContractRow, Hearing, ParameterRelation, Profile, TaskRow, WarehouseCatalogOption } from "../types";
/** legal queries operations; dependencies are read when each operation runs. */
export interface CaseQueriesDependencies {
    readonly setCaseActionCapabilities: React.Dispatch<React.SetStateAction<Record<number, CaseDetailCapabilities>>>;
    readonly setCaseRelations: React.Dispatch<React.SetStateAction<CaseRelationCatalog | null>>;
    readonly setLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setOrdinaryLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setOrdinaryLoadError: React.Dispatch<React.SetStateAction<string>>;
    readonly initialView: string;
    readonly setCases: React.Dispatch<React.SetStateAction<CaseRow[]>>;
    readonly isCreateView: boolean;
    readonly openCounselDetail: (row: CaseRow, preferredTab?: string | undefined) => Promise<void>;
    readonly isCaseDetailView: boolean;
    readonly detailRouteId: number;
    readonly setWarehouseCatalog: React.Dispatch<React.SetStateAction<WarehouseCatalogOption[]>>;
    readonly setContracts: React.Dispatch<React.SetStateAction<ContractRow[]>>;
    readonly setHearings: React.Dispatch<React.SetStateAction<Hearing[]>>;
    readonly setSummary: React.Dispatch<React.SetStateAction<{
        total: number;
        pending_assignment: number;
        in_progress: number;
        execution: number;
        archived: number;
    }>>;
    readonly setProfile: React.Dispatch<React.SetStateAction<Profile>>;
    readonly setFinanceRows: React.Dispatch<React.SetStateAction<CaseRow[]>>;
    readonly setAttachments: React.Dispatch<React.SetStateAction<AttachmentRow[]>>;
    readonly setCaseTypeOptions: React.Dispatch<React.SetStateAction<{
        value: string;
        label: string;
    }[]>>;
    readonly setCauseOptions: React.Dispatch<React.SetStateAction<{
        value: string;
        label: string;
    }[]>>;
    readonly setCaseFileTypeCatalog: React.Dispatch<React.SetStateAction<CaseFileTypeOption[]>>;
    readonly setCaseFileTypeOptions: React.Dispatch<React.SetStateAction<CaseFileTypeOption[]>>;
    readonly setCaseUploadCategory: React.Dispatch<React.SetStateAction<string>>;
    readonly setCounselUploadCategory: React.Dispatch<React.SetStateAction<string>>;
    readonly setCourtOptions: React.Dispatch<React.SetStateAction<{
        value: string;
        label: string;
        code?: string | undefined;
    }[]>>;
    readonly setCourtOfficerOptions: React.Dispatch<React.SetStateAction<{
        value: string;
        label: string;
        court_code?: string | undefined;
        role?: string | undefined;
        phone?: string | undefined;
    }[]>>;
    readonly setCaseLawyerOptions: React.Dispatch<React.SetStateAction<{
        value: string;
        label: string;
    }[]>>;
    readonly setCaseAssistantOptions: React.Dispatch<React.SetStateAction<{
        value: string;
        label: string;
    }[]>>;
    readonly setRightTypeOptions: React.Dispatch<React.SetStateAction<{
        value: string;
        label: string;
    }[]>>;
    readonly setCaseCustomers: React.Dispatch<React.SetStateAction<CaseRow[]>>;
    readonly setCaseClues: React.Dispatch<React.SetStateAction<CaseRow[]>>;
    readonly setFeeTypeCatalog: React.Dispatch<React.SetStateAction<FeeTypeCatalogItem[]>>;
    readonly contractPrefill: {
        id: number;
        serial_no: string;
        title: string;
        customer: string;
    } | null;
    readonly createForm: FormInstance<any>;
    readonly resolveCasePersonValue: (source: string) => string;
    readonly caseQuery: Record<string, any>;
    readonly originalPageSize: number;
    readonly ordinaryRequestGuard: LatestRequestGuard;
    readonly ordinaryCaseQueue: string;
    readonly ordinaryScope: "mine" | "department" | "company";
    readonly ordinaryCaseTypes: string[];
    readonly setOrdinaryCases: React.Dispatch<React.SetStateAction<CaseRow[]>>;
    readonly setOrdinaryTotal: React.Dispatch<React.SetStateAction<number>>;
    readonly setOrdinaryPhaseCounts: React.Dispatch<React.SetStateAction<Record<string, number>>>;
    readonly setOriginalPage: React.Dispatch<React.SetStateAction<number>>;
    readonly setOriginalPageSize: React.Dispatch<React.SetStateAction<number>>;
    readonly setSelectedCaseKeys: React.Dispatch<React.SetStateAction<React.Key[]>>;
    readonly pendingExecutionPageSize: number;
    readonly setPendingExecutionCases: React.Dispatch<React.SetStateAction<CaseRow[]>>;
    readonly setPendingExecutionTotal: React.Dispatch<React.SetStateAction<number>>;
    readonly setPendingExecutionPage: React.Dispatch<React.SetStateAction<number>>;
    readonly setPendingExecutionPageSize: React.Dispatch<React.SetStateAction<number>>;
    readonly counselPageSize: number;
    readonly counselSearchPayload: (values: Record<string, any>, page: number, pageSize: number, extra?: Record<string, any>) => CaseCounselSearchPayload;
    readonly setCounselCases: React.Dispatch<React.SetStateAction<CaseRow[]>>;
    readonly setCounselTotal: React.Dispatch<React.SetStateAction<number>>;
    readonly setCounselPage: React.Dispatch<React.SetStateAction<number>>;
    readonly setCounselPageSize: React.Dispatch<React.SetStateAction<number>>;
    readonly caseTaskPage: number;
    readonly caseTaskPageSize: number;
    readonly caseTaskVipFilter: "normal" | "all" | "vip";
    readonly applyCaseTaskPageState: (payload: any, fallbackPage: number, fallbackPageSize: number) => CaseTaskPageState;
    readonly counselDetailTaskPage: number;
    readonly counselDetailTaskPageSize: number;
    readonly counselDetailTaskVipFilter: "normal" | "all" | "vip";
    readonly applyCounselDetailTaskPageState: (payload: any, fallbackPage: number, fallbackPageSize: number) => CaseTaskPageState;
    readonly counselDetailCustomerTaskPage: number;
    readonly counselDetailCustomerTaskPageSize: number;
    readonly counselDetailCustomerTaskVipFilter: "normal" | "all" | "vip";
    readonly applyCounselDetailCustomerTaskPageState: (payload: any, fallbackPage: number, fallbackPageSize: number) => CaseTaskPageState;
    readonly counselDetailCluePage: number;
    readonly counselDetailCluePageSize: number;
    readonly counselDetailClueKeyword: string;
    readonly counselDetailClueRequestRef: React.RefObject<number>;
    readonly setCounselDetailClueLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly viewingCounselCase: CaseRow | null;
    readonly applyCounselDetailCluePageState: (payload: any, fallbackPage: number, fallbackPageSize: number) => {
        items: any;
        total: number;
        page: number;
        pageSize: number;
        pages: number;
    };
    readonly onNavigate: ((route: string) => void) | undefined;
    readonly setCaseTaskDetailLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setViewingCaseTask: React.Dispatch<React.SetStateAction<TaskRow | null>>;
    readonly setCaseTaskHistory: React.Dispatch<React.SetStateAction<CaseTaskHistoryItem[]>>;
    readonly setCaseTaskDetailMaterials: React.Dispatch<React.SetStateAction<CaseTaskAttachment[]>>;
    readonly setCaseTaskDetailFeedbacks: React.Dispatch<React.SetStateAction<CaseTaskAttachment[]>>;
    readonly setCaseClueLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly cases: CaseRow[];
    readonly setCounselCaseEvents: React.Dispatch<React.SetStateAction<CaseEventRow[]>>;
    readonly setCounselCaseEventCapabilities: React.Dispatch<React.SetStateAction<CaseEventCapabilities>>;
    readonly setSelectedCounselCaseEventKeys: React.Dispatch<React.SetStateAction<React.Key[]>>;
    readonly setCounselCaseEventsError: React.Dispatch<React.SetStateAction<string>>;
    readonly caseLitigantSearchRequestRef: React.RefObject<number>;
    readonly setCaseLitigantCandidatesLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setCaseLitigantCandidates: React.Dispatch<React.SetStateAction<CaseLitigantCandidate[]>>;
    readonly originalCases: CaseRow[];
    readonly selectedCaseKeys: React.Key[];
}
export function createCaseQueriesActions(context: CaseQueriesDependencies) {
    const loadCaseCapabilities = async (rows: CaseRow[]) => {
        const { setCaseActionCapabilities } = context;
        const uniqueRows = Array.from(new Map(rows.map((row) => [row.id, row])).values());
        if (!uniqueRows.length)
            return;
        const fallback = Object.fromEntries(uniqueRows.map((row) => [row.id, noCaseDetailWriteCapability]));
        try {
            const { data } = await api.get("/cases/action-capabilities", {
                params: { record_ids: uniqueRows.map((row) => row.id).join(",") },
            });
            setCaseActionCapabilities((previous) => ({ ...previous, ...fallback, ...(data.items || {}) }));
        }
        catch {
            setCaseActionCapabilities((previous) => ({ ...previous, ...fallback }));
        }
    };
    const loadCaseRelations = async () => {
        const { setCaseRelations } = context;
        const responses = await Promise.allSettled([
            api.get<ParameterRelation>("/system/parameter-relations/case-type-file-types"),
            api.get<ParameterRelation>("/system/parameter-relations/file-type-fee-types"),
            api.get<ParameterRelation>("/system/parameter-relations/case-type-case-phases"),
        ]);
        if (responses.every((response) => response.status === "fulfilled")) {
            const [caseTypeFileTypes, fileTypeFeeTypes, caseTypePhases] = responses.map((response) => (response as PromiseFulfilledResult<{
                data: ParameterRelation;
            }>).value.data);
            setCaseRelations({ caseTypeFileTypes, fileTypeFeeTypes, caseTypePhases });
            return;
        }
        // The existing configuration endpoint is administrator-only. Keep the current
        // server-backed controls usable when the caller cannot read configuration.
        setCaseRelations(null);
    };
    const load = async () => {
        const { setLoading, initialView, setCases, isCreateView, openCounselDetail, isCaseDetailView, detailRouteId, setWarehouseCatalog, setContracts, setHearings, setSummary, setProfile, setFinanceRows, setAttachments, setCaseTypeOptions, setCauseOptions, setCaseFileTypeCatalog, setCaseFileTypeOptions, setCaseUploadCategory, setCounselUploadCategory, setCourtOptions, setCourtOfficerOptions, setCaseLawyerOptions, setCaseAssistantOptions, setRightTypeOptions, setCaseCustomers, setCaseClues, setFeeTypeCatalog, contractPrefill, createForm, resolveCasePersonValue } = context;
        setLoading(true);
        try {
            // 关联详情不能依赖合同、排期、附件等旁路数据全部成功；否则案号跳转会
            // 只进入案件列表而没有打开目标详情。
            const archiveView = initialView === "case-archive-pending"
                ? "pending"
                : initialView === "case-archive-refused"
                    ? "refused"
                    : undefined;
            const caseRes = await api.get("/records", {
                params: { module: "case", page_size: 100, archive_view: archiveView },
            });
            setCases(caseRes.data.items);
            void loadCaseCapabilities(caseRes.data.items as CaseRow[]);
            const detailTarget = consumeCaseDetailTarget();
            if (detailTarget && !isCreateView) {
                let linkedCase = (caseRes.data.items as CaseRow[]).find((row) => (detailTarget.id && row.id === detailTarget.id) ||
                    (detailTarget.serial_no && row.serial_no === detailTarget.serial_no));
                if (!linkedCase && detailTarget.serial_no) {
                    const { data } = await api.get("/records", {
                        params: { module: "case", keyword: detailTarget.serial_no, page_size: 100 },
                    });
                    linkedCase = (data.items as CaseRow[]).find((row) => row.serial_no === detailTarget.serial_no);
                }
                if (linkedCase)
                    void openCounselDetail(linkedCase);
                else
                    message.warning("未找到关联案件或当前账号无权查看");
            }
            else if (isCaseDetailView && detailRouteId > 0) {
                let linkedCase = (caseRes.data.items as CaseRow[]).find((row) => row.id === detailRouteId);
                if (!linkedCase) {
                    try {
                        const { data } = await api.get(`/records/${detailRouteId}`);
                        if (data.module === "case")
                            linkedCase = data as CaseRow;
                    }
                    catch {
                        // The common detail loader below provides the user-facing error.
                    }
                }
                if (linkedCase)
                    void openCounselDetail(linkedCase);
                else
                    message.warning("未找到关联案件或当前账号无权查看");
            }
            // The notary editor must keep its master warehouse locations available even
            // when an unrelated optional case-center feed is temporarily unavailable.
            try {
                const warehouseResponse = await api.get("/warehouse/catalog");
                setWarehouseCatalog(warehouseResponse.data.items || []);
            }
            catch {
                setWarehouseCatalog([]);
            }
            const [contractRes, hearingRes, summaryRes, profileRes, financeRes, refundRes, attachmentRes, referenceRes, customerRes, clueRes, feeTypeRes] = await Promise.all([
                api.get("/cases/eligible-contracts"),
                api.get("/hearings"),
                api.get("/cases/summary"),
                api.get("/auth/me"),
                api.get("/records", { params: { module: "finance", page_size: 100 } }),
                api.get("/records", { params: { module: "refund", page_size: 100 } }),
                api.get("/attachments"),
                api.get("/cases/reference-options"),
                api.get("/records", { params: { module: "customer", page_size: 100 } }),
                api.get("/records", { params: { module: "clue", page_size: 100 } }),
                api.get("/system/parameters/options", { params: { category: "fee_type" } }),
            ]);
            setContracts(contractRes.data.items);
            setHearings(hearingRes.data.items);
            setSummary(summaryRes.data);
            setProfile(profileRes.data);
            setFinanceRows([...financeRes.data.items, ...refundRes.data.items]);
            setAttachments(attachmentRes.data.items);
            setCaseTypeOptions(referenceRes.data.case_types || []);
            setCauseOptions(referenceRes.data.causes || []);
            if ((referenceRes.data.case_file_types || []).length) {
                setCaseFileTypeCatalog(referenceRes.data.case_file_types);
                const nextFileTypes = buildCaseFileTypeTreeOptions(referenceRes.data.case_file_types);
                setCaseFileTypeOptions(nextFileTypes);
                setCaseUploadCategory((current) => resolveCaseFileTypeSelection(current, nextFileTypes));
                setCounselUploadCategory((current) => resolveCaseFileTypeSelection(current, nextFileTypes));
            }
            setCourtOptions(referenceRes.data.courts || []);
            setCourtOfficerOptions(referenceRes.data.court_officers || []);
            setCaseLawyerOptions(referenceRes.data.case_lawyers || []);
            setCaseAssistantOptions(referenceRes.data.case_assistants || []);
            setRightTypeOptions((referenceRes.data.right_types || []).map((value: string) => ({ value, label: value })));
            setCaseCustomers(customerRes.data.items || []);
            setCaseClues(clueRes.data.items || []);
            setFeeTypeCatalog(feeTypeRes.data.items || []);
            void loadCaseRelations();
            if (isCreateView && contractPrefill?.id) {
                const selected = contractRes.data.items.find((row: ContractRow) => row.id === contractPrefill.id);
                if (selected)
                    createForm.setFieldsValue({ customer: selected.customer, source_person: resolveCasePersonValue(resolveCaseSourcePerson(selected)) });
            }
        }
        catch {
            message.error("案件中心数据加载失败");
        }
        finally {
            setLoading(false);
        }
    };
    const loadOrdinaryCases = async (values: Record<string, any> = context.caseQuery, page = 1, pageSize = context.originalPageSize) => {
        const { caseQuery, originalPageSize, ordinaryRequestGuard, setOrdinaryLoading, setOrdinaryLoadError, ordinaryCaseQueue, ordinaryScope, ordinaryCaseTypes, setOrdinaryCases, setOrdinaryTotal, setOrdinaryPhaseCounts, setOriginalPage, setOriginalPageSize, setSelectedCaseKeys } = context;
        const requestId = ordinaryRequestGuard.begin();
        setOrdinaryLoading(true);
        setOrdinaryLoadError("");
        try {
            const searchPayload = buildCaseOrdinarySearchPayload({ ...values, case_queue: ordinaryCaseQueue }, ordinaryScope, ordinaryCaseTypes, page, pageSize);
            const { data } = await api.post("/cases/search", searchPayload);
            if (!ordinaryRequestGuard.isLatest(requestId))
                return;
            const result = parseOrdinarySearchResult(data, page, pageSize);
            setOrdinaryCases(result.items as CaseRow[]);
            void loadCaseCapabilities(result.items as CaseRow[]);
            setOrdinaryTotal(result.total);
            setOrdinaryPhaseCounts(result.phaseCounts);
            setOriginalPage(result.page);
            setOriginalPageSize(result.pageSize);
            setSelectedCaseKeys([]);
        }
        catch (error: any) {
            if (!ordinaryRequestGuard.isLatest(requestId))
                return;
            setOrdinaryCases([]);
            setOrdinaryTotal(0);
            setOrdinaryPhaseCounts({});
            setSelectedCaseKeys([]);
            const errorMessage = error?.response?.data?.detail || "案件查询失败";
            setOrdinaryLoadError(errorMessage);
            message.error(errorMessage);
        }
        finally {
            if (ordinaryRequestGuard.isLatest(requestId))
                setOrdinaryLoading(false);
        }
    };
    const loadPendingExecutionCases = async (page = 1, pageSize = context.pendingExecutionPageSize) => {
        const { pendingExecutionPageSize, setLoading, setPendingExecutionCases, setPendingExecutionTotal, setPendingExecutionPage, setPendingExecutionPageSize, setSelectedCaseKeys } = context;
        setLoading(true);
        try {
            const { data } = await api.get("/cases/pending-execution", { params: { page, page_size: pageSize } });
            setPendingExecutionCases(data.items || []);
            setPendingExecutionTotal(Number(data.total || 0));
            setPendingExecutionPage(Number(data.page || page));
            setPendingExecutionPageSize(Number(data.page_size || pageSize));
            setSelectedCaseKeys([]);
            void loadCaseCapabilities(data.items || []);
        }
        catch (error: any) {
            setPendingExecutionCases([]);
            setPendingExecutionTotal(0);
            message.error(error?.response?.data?.detail || "待执行案件加载失败");
        }
        finally {
            setLoading(false);
        }
    };
    const loadCounselCases = async (values: Record<string, any> = context.caseQuery, page = 1, pageSize = context.counselPageSize) => {
        const { caseQuery, counselPageSize, setLoading, counselSearchPayload, setCounselCases, setCounselTotal, setCounselPage, setCounselPageSize, setSelectedCaseKeys } = context;
        setLoading(true);
        try {
            const { data } = await api.post("/cases/counsel/search", counselSearchPayload(values, page, pageSize));
            setCounselCases(data.items || []);
            void loadCaseCapabilities(data.items || []);
            setCounselTotal(data.total || 0);
            setCounselPage(data.page || page);
            setCounselPageSize(data.page_size || pageSize);
            setSelectedCaseKeys([]);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "法律顾问案件加载失败");
        }
        finally {
            setLoading(false);
        }
    };
    const loadCaseTasksPage = async (row: CaseRow, nextPage = context.caseTaskPage, nextPageSize = context.caseTaskPageSize, nextVipFilter = context.caseTaskVipFilter) => {
        const { caseTaskPage, caseTaskPageSize, caseTaskVipFilter, applyCaseTaskPageState } = context;
        const { data } = await api.get(`/cases/${row.id}/tasks`, {
            params: { page: nextPage, page_size: nextPageSize, is_vip: nextVipFilter === "all" ? undefined : nextVipFilter === "vip" },
        });
        return applyCaseTaskPageState(data, nextPage, nextPageSize);
    };
    const loadCounselDetailTasksPage = async (row: CaseRow, nextPage = context.counselDetailTaskPage, nextPageSize = context.counselDetailTaskPageSize, nextVipFilter = context.counselDetailTaskVipFilter) => {
        const { counselDetailTaskPage, counselDetailTaskPageSize, counselDetailTaskVipFilter, applyCounselDetailTaskPageState } = context;
        const { data } = await api.get(`/cases/${row.id}/tasks`, {
            params: { page: nextPage, page_size: nextPageSize, scope: "case", is_vip: nextVipFilter === "all" ? undefined : nextVipFilter === "vip" },
        });
        return applyCounselDetailTaskPageState(data, nextPage, nextPageSize);
    };
    const loadCounselDetailCustomerTasksPage = async (row: CaseRow, nextPage = context.counselDetailCustomerTaskPage, nextPageSize = context.counselDetailCustomerTaskPageSize, nextVipFilter = context.counselDetailCustomerTaskVipFilter) => {
        const { counselDetailCustomerTaskPage, counselDetailCustomerTaskPageSize, counselDetailCustomerTaskVipFilter, applyCounselDetailCustomerTaskPageState } = context;
        const { data } = await api.get(`/cases/${row.id}/tasks`, {
            params: { page: nextPage, page_size: nextPageSize, scope: "customer", is_vip: nextVipFilter === "all" ? undefined : nextVipFilter === "vip" },
        });
        return applyCounselDetailCustomerTaskPageState(data, nextPage, nextPageSize);
    };
    const loadCounselDetailCluesPage = async (row: CaseRow, nextPage = context.counselDetailCluePage, nextPageSize = context.counselDetailCluePageSize, keyword = context.counselDetailClueKeyword) => {
        const { counselDetailCluePage, counselDetailCluePageSize, counselDetailClueKeyword, counselDetailClueRequestRef, setCounselDetailClueLoading, viewingCounselCase, applyCounselDetailCluePageState } = context;
        const requestId = ++counselDetailClueRequestRef.current;
        setCounselDetailClueLoading(true);
        try {
            const { data } = await api.get(`/cases/${row.id}/relations`, {
                params: { clue_page: nextPage, clue_page_size: nextPageSize, clue_keyword: keyword || undefined },
            });
            if (!shouldApplyCaseClueResponse({ requestId, currentRequestId: counselDetailClueRequestRef.current, currentCaseId: viewingCounselCase?.id, targetCaseId: row.id }))
                return null;
            return applyCounselDetailCluePageState(data, nextPage, nextPageSize);
        }
        finally {
            if (requestId === counselDetailClueRequestRef.current)
                setCounselDetailClueLoading(false);
        }
    };
    const openRelatedCustomer = async (target: {
        id?: number;
        serial_no?: string;
        title?: string;
        customer?: string;
    }) => {
        const { onNavigate } = context;
        const title = String(target.title || target.customer || "").trim();
        if (!title && !target.id && !target.serial_no) {
            message.warning("当前记录未关联客户");
            return;
        }
        const customer = await resolveCustomerDetailTarget({ id: target.id, serial_no: target.serial_no, title });
        if (!customer) {
            message.warning("未找到关联客户或当前账号无权查看");
            return;
        }
        rememberCustomerDetailTarget(customer);
        onNavigate?.("customer-company");
    };
    const loadCaseTaskDetail = async (task: TaskRow) => {
        const { setCaseTaskDetailLoading, setViewingCaseTask, setCaseTaskHistory, setCaseTaskDetailMaterials, setCaseTaskDetailFeedbacks } = context;
        setCaseTaskDetailLoading(true);
        try {
            const [recordResult, historyResult, materialResult, feedbackResult] = await Promise.all([
                api.get(`/records/${task.id}`),
                api.get(`/tasks/${task.id}/history`),
                api.get("/attachments", { params: { record_id: task.id, category: "任务资料附件", page_size: 200 } }),
                api.get("/attachments", { params: { record_id: task.id, category: "任务反馈附件", page_size: 200 } }),
            ]);
            const record = recordResult.data as TaskRow & {
                data?: Record<string, any>;
            };
            const taskData = record.data || {};
            setViewingCaseTask({
                ...task,
                ...record,
                status: task.status || record.status,
                workflow_status: task.workflow_status || record.status,
                initiator: String(taskData.initiator || task.initiator || ""),
                initiator_display_name: task.initiator_display_name || record.initiator_display_name,
                collaborators: Array.isArray(taskData.collaborators) ? taskData.collaborators : task.collaborators,
                collaborator_display_names: task.collaborator_display_names,
                case_no: String(taskData.case_no || task.case_no || ""),
                start_at: String(taskData.start_at || task.start_at || ""),
                end_at: String(taskData.end_at || task.end_at || ""),
                deadline: String(taskData.deadline || task.deadline || ""),
            });
            setCaseTaskHistory(historyResult.data.items || []);
            setCaseTaskDetailMaterials(materialResult.data.items || []);
            setCaseTaskDetailFeedbacks(feedbackResult.data.items || []);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件任务详情加载失败");
        }
        finally {
            setCaseTaskDetailLoading(false);
        }
    };
    const openRelatedClue = async (target: {
        id?: number;
        serial_no?: unknown;
    }) => {
        const { setCaseClueLoading, onNavigate } = context;
        const id = Number(target.id || 0) || undefined;
        if (!id) {
            message.warning("当前案件未关联调查线索");
            return;
        }
        setCaseClueLoading(true);
        try {
            // The case relation grants access to the association, while the
            // investigation workspace remains the authority for clue-detail access.
            await api.get(`/investigations/clues/${id}/workspace`);
            if (!onNavigate) {
                message.warning("当前页面未配置调查中心跳转");
                return;
            }
            rememberInvestigationDetailTarget({
                id,
                serial_no: String(target.serial_no || "").trim(),
                module: "clue",
            });
            onNavigate("clue-company-draft");
        }
        catch (error: any) {
            if (error?.response?.status === 403)
                message.warning("当前账号无权查看该调查线索详情");
            else if (error?.response?.status === 404)
                message.warning("关联调查线索不存在或已被删除");
            else
                message.error(error?.response?.data?.detail || "线索详情加载失败");
        }
        finally {
            setCaseClueLoading(false);
        }
    };
    const resolveVisibleCase = async (row: {
        case?: CaseRow;
        case_record_id?: number;
        serial_no?: string;
        case_no?: string;
    }) => {
        const { cases } = context;
        if (row.case?.id)
            return row.case;
        const caseRecordId = Number(row.case_record_id || 0);
        try {
            if (caseRecordId > 0) {
                const { data } = await api.get(`/records/${caseRecordId}`);
                if (data.module !== "case")
                    throw new Error("关联记录不是案件");
                return data as CaseRow;
            }
            const caseNo = String(row.case_no || row.serial_no || "").trim();
            if (!caseNo)
                return null;
            const cached = cases.find((item) => item.serial_no === caseNo);
            if (cached)
                return cached;
            const { data } = await api.get("/records", { params: { module: "case", keyword: caseNo, page_size: 100 } });
            return (data.items as CaseRow[]).find((item) => item.serial_no === caseNo) || null;
        }
        catch (error: any) {
            const detail = error?.response?.data?.detail;
            message.warning(detail || "关联案件不存在或当前账号无权查看");
            return null;
        }
    };
    const loadCounselCaseEvents = async (targetCase = context.viewingCounselCase) => {
        const { viewingCounselCase, setCounselCaseEvents, setCounselCaseEventCapabilities, setSelectedCounselCaseEventKeys, setCounselCaseEventsError } = context;
        if (!targetCase)
            return;
        try {
            const { data } = await api.get(`/cases/${targetCase.id}/events`);
            setCounselCaseEvents(data.items || []);
            setCounselCaseEventCapabilities(data.capabilities || noCaseEventCapabilities);
            setSelectedCounselCaseEventKeys([]);
            setCounselCaseEventsError("");
        }
        catch (error: any) {
            setCounselCaseEventsError(error?.response?.data?.detail || "案件事件加载失败，请重试");
            message.error(error?.response?.data?.detail || "案件事件加载失败");
        }
    };
    const loadCaseLitigantCandidates = async (keyword = "") => {
        const { caseLitigantSearchRequestRef, setCaseLitigantCandidatesLoading, setCaseLitigantCandidates } = context;
        const requestId = ++caseLitigantSearchRequestRef.current;
        setCaseLitigantCandidatesLoading(true);
        try {
            const { data } = await api.get("/case-litigant-candidates", { params: { keyword: keyword.trim() } });
            if (requestId === caseLitigantSearchRequestRef.current) {
                setCaseLitigantCandidates(Array.isArray(data.items) ? data.items : []);
            }
        }
        catch (error: any) {
            if (requestId === caseLitigantSearchRequestRef.current) {
                setCaseLitigantCandidates([]);
                message.error(error?.response?.data?.detail || "当事人候选加载失败");
            }
        }
        finally {
            if (requestId === caseLitigantSearchRequestRef.current)
                setCaseLitigantCandidatesLoading(false);
        }
    };
    const exportCases = async () => {
        const { originalCases } = context;
        if (!originalCases.length)
            return message.warning("当前查询没有可导出的案件");
        try {
            const res = await api.get("/records/export", { params: { module: "case" }, responseType: "blob" });
            const url = URL.createObjectURL(res.data), link = document.createElement("a");
            link.href = url;
            link.download = "案件资料.csv";
            link.click();
            URL.revokeObjectURL(url);
        }
        catch {
            message.error("案件导出失败");
        }
    };
    const exportCounselCases = async (selectedOnly: boolean) => {
        const { selectedCaseKeys, counselSearchPayload, caseQuery } = context;
        if (selectedOnly && !selectedCaseKeys.length)
            return message.warning("请选择需要导出的法律顾问案件");
        try {
            const response = await api.post("/cases/counsel/export", counselSearchPayload(caseQuery, 1, 200, { selected_only: selectedOnly, selected_ids: selectedOnly ? selectedCaseKeys.map(Number) : [] }), { responseType: "blob" });
            const url = URL.createObjectURL(response.data), link = document.createElement("a");
            link.href = url;
            link.download = selectedOnly ? "法律顾问案件-选中.csv" : "法律顾问案件-全部.csv";
            link.click();
            URL.revokeObjectURL(url);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "法律顾问案件导出失败");
        }
    };
    const exportSpecialRecords = async (module: string, filename: string) => {
        try {
            const res = await api.get("/records/export", { params: { module }, responseType: "blob" });
            const url = URL.createObjectURL(res.data), link = document.createElement("a");
            link.href = url;
            link.download = filename;
            link.click();
            URL.revokeObjectURL(url);
        }
        catch {
            message.error("数据导出失败");
        }
    };
    return { loadCaseCapabilities, loadCaseRelations, load, loadOrdinaryCases, loadPendingExecutionCases, loadCounselCases, loadCaseTasksPage, loadCounselDetailTasksPage, loadCounselDetailCustomerTasksPage, loadCounselDetailCluesPage, openRelatedCustomer, loadCaseTaskDetail, openRelatedClue, resolveVisibleCase, loadCounselCaseEvents, loadCaseLitigantCandidates, exportCases, exportCounselCases, exportSpecialRecords };
}
