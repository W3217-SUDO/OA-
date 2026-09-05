import type { UploadFile } from "antd";
import { message, Modal } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import type { MessageType } from "antd/es/message/interface";
import dayjs, { type Dayjs } from "dayjs";
import type { Key } from "react";
import { api } from "../../api";
import { rememberCaseDetailTarget } from "../../caseDetailNavigation";
import { getCaseReminderDateValidationError } from "../../caseFifthBatchParity.mjs";
import { buildCaseCreatePayload, buildCaseDuplicateRequest, buildCaseExecutionStatusPayload, buildCaseMergePayload, buildCasePhaseChangePayload, buildCaseProgressPayload, buildClueConversionPayload, getCaseCreateValidationError, getCaseEditValidationError, getCaseMutationBlockReason, getClueConversionIssues, normalizeCaseEditPayload } from "../../caseSecondBatchParity";
import { buildCaseHearingPayload, buildCaseUnarchiveReviewPayload, getCaseArchiveReviewValidationError, getCaseHearingValidationError, getCaseUnarchiveReviewValidationError } from "../../caseWorkflowFrontendParity.mjs";
import { formatRequiredDate } from "../../formSafety";
import { ARCHIVE_LOCKED_STATUSES, CASE_LITIGANT_PARTY_LABELS, CASE_TASK_DEFAULT_PAGE, CASE_TASK_DEFAULT_PAGE_SIZE, getCompanyScheduleCourtLevels, isCompanyCaseListRoute, noCaseDetailWriteCapability, noCaseEventCapabilities } from "../constants";
import type { AttachmentRow, CaseAssistedFee, CaseClueEvidenceRow, CaseClueWorkspace, CaseDetailCapabilities, CaseEventCapabilities, CaseEventRow, CaseFileTypeOption, CaseLitigantCandidate, CaseLitigantPartyField, CaseLogKind, CaseLogRow, CasePhaseOption, CaseReminderRow, CaseRow, CaseTaskKind, CaseTaskPageState, ContractRow, Profile } from "../types";
/** legal workflow operations; dependencies are read when each operation runs. */
export interface CaseWorkflowDependencies {
    readonly createDefendantEditorForm: FormInstance<any>;
    readonly createForm: FormInstance<any>;
    readonly setCreateDefendantEditorOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly createStep: number;
    readonly isCounselCreate: boolean;
    readonly setCreateSubmitting: React.Dispatch<React.SetStateAction<boolean>>;
    readonly createRouteType: "刑事案件" | "行政案件及国家赔偿" | "法律顾问" | "仲裁" | "民事案件";
    readonly profile: Profile;
    readonly setCreatedCaseId: React.Dispatch<React.SetStateAction<number | null>>;
    readonly setCreateStep: React.Dispatch<React.SetStateAction<number>>;
    readonly createdCaseId: number | null;
    readonly redirectAfterCreate: () => void;
    readonly assigning: CaseRow | null;
    readonly assignForm: FormInstance<any>;
    readonly setAssigning: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly load: () => Promise<void>;
    readonly hearingForm: FormInstance<any>;
    readonly setHearingOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly getCaseCapability: (row?: CaseRow | null | undefined) => CaseDetailCapabilities;
    readonly archiveForm: FormInstance<any>;
    readonly setArchiveChecks: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
    readonly setArchiveType: React.Dispatch<React.SetStateAction<"normal" | "deficit">>;
    readonly setArchiving: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly archiving: CaseRow | null;
    readonly archiveType: "normal" | "deficit";
    readonly reviewing: {
        row: CaseRow;
        rows?: CaseRow[];
        approved: boolean;
    } | null;
    readonly reviewForm: FormInstance<any>;
    readonly setReviewing: React.Dispatch<React.SetStateAction<{
        row: CaseRow;
        rows?: CaseRow[];
        approved: boolean;
    } | null>>;
    readonly setSelectedCaseKeys: React.Dispatch<React.SetStateAction<React.Key[]>>;
    readonly initialView: string;
    readonly loadOrdinaryCases: (values?: Record<string, any>, page?: number, pageSize?: number) => Promise<void>;
    readonly caseQuery: Record<string, any>;
    readonly originalPage: number;
    readonly originalPageSize: number;
    readonly loadCaseTasksPage: (row: CaseRow, nextPage?: number, nextPageSize?: number, nextVipFilter?: "normal" | "all" | "vip") => Promise<CaseTaskPageState>;
    readonly taskForm: FormInstance<any>;
    readonly setCaseTaskMaterialFiles: React.Dispatch<React.SetStateAction<UploadFile<any>[]>>;
    readonly setTaskCase: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly isCaseDetailView: boolean;
    readonly onNavigate: ((route: string) => void) | undefined;
    readonly counselDetailClueRequestRef: React.RefObject<number>;
    readonly setCounselDetailClues: React.Dispatch<React.SetStateAction<CaseRow[]>>;
    readonly setCounselDetailClueKeyword: React.Dispatch<React.SetStateAction<string>>;
    readonly setCounselDetailClueSearchInput: React.Dispatch<React.SetStateAction<string>>;
    readonly setCounselDetailCluePage: React.Dispatch<React.SetStateAction<number>>;
    readonly setCounselDetailCluePageSize: React.Dispatch<React.SetStateAction<number>>;
    readonly setCounselDetailClueTotal: React.Dispatch<React.SetStateAction<number>>;
    readonly setCounselDetailCluePages: React.Dispatch<React.SetStateAction<number>>;
    readonly setActiveCounselDetailTab: React.Dispatch<React.SetStateAction<string>>;
    readonly setViewingCounselCase: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly counselDetailCaseIdRef: React.RefObject<number | null>;
    readonly setCounselDetailAssistedFees: React.Dispatch<React.SetStateAction<CaseAssistedFee[]>>;
    readonly setCounselDetailAssistedFeeTotal: React.Dispatch<React.SetStateAction<number>>;
    readonly loadCounselDetailAssistedFees: (caseId: number, page?: number, pageSize?: number) => Promise<void>;
    readonly counselDetailAssistedFeePageSize: number;
    readonly setLegacyLsHistoryCaseIds: React.Dispatch<React.SetStateAction<Record<number, number>>>;
    readonly setSelectedCounselAttachmentKeys: React.Dispatch<React.SetStateAction<React.Key[]>>;
    readonly setSelectedCounselCaseEventKeys: React.Dispatch<React.SetStateAction<React.Key[]>>;
    readonly setActiveCounselDocCategory: React.Dispatch<React.SetStateAction<string>>;
    readonly setExpandedCounselDocGroups: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
    readonly contracts: ContractRow[];
    readonly caseCustomers: CaseRow[];
    readonly counselDetailTaskVipFilter: "normal" | "all" | "vip";
    readonly counselDetailCustomerTaskVipFilter: "normal" | "all" | "vip";
    readonly setCounselDetailHistory: React.Dispatch<React.SetStateAction<any[]>>;
    readonly applyCounselDetailTaskPageState: (payload: any, fallbackPage: number, fallbackPageSize: number) => CaseTaskPageState;
    readonly applyCounselDetailCustomerTaskPageState: (payload: any, fallbackPage: number, fallbackPageSize: number) => CaseTaskPageState;
    readonly setCounselDetailAttachments: React.Dispatch<React.SetStateAction<AttachmentRow[]>>;
    readonly setCounselDetailCustomerAttachments: React.Dispatch<React.SetStateAction<AttachmentRow[]>>;
    readonly setCounselDetailContractAttachments: React.Dispatch<React.SetStateAction<AttachmentRow[]>>;
    readonly setCounselDocumentFolderTree: React.Dispatch<React.SetStateAction<CaseFileTypeOption[]>>;
    readonly setCounselReminders: React.Dispatch<React.SetStateAction<CaseReminderRow[]>>;
    readonly setCounselCaseEvents: React.Dispatch<React.SetStateAction<CaseEventRow[]>>;
    readonly setCounselCaseEventCapabilities: React.Dispatch<React.SetStateAction<CaseEventCapabilities>>;
    readonly setCounselCaseEventsError: React.Dispatch<React.SetStateAction<string>>;
    readonly setCounselLogs: React.Dispatch<React.SetStateAction<CaseLogRow[]>>;
    readonly setCounselDetailCapabilities: React.Dispatch<React.SetStateAction<CaseDetailCapabilities>>;
    readonly setCounselDetailFinance: React.Dispatch<React.SetStateAction<CaseRow[]>>;
    readonly applyCounselDetailCluePageState: (payload: any, fallbackPage: number, fallbackPageSize: number) => {
        items: any;
        total: number;
        page: number;
        pageSize: number;
        pages: number;
    };
    readonly mergingCase: CaseRow | null;
    readonly mergeCaseForm: FormInstance<any>;
    readonly setMergingCase: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly notaryInfoCase: CaseRow | null;
    readonly notaryInfoForm: FormInstance<any>;
    readonly setNotaryInfoCase: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly setCaseClueLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setViewingCaseClue: React.Dispatch<React.SetStateAction<CaseClueWorkspace | null>>;
    readonly setSelectedCaseClueEvidenceId: React.Dispatch<React.SetStateAction<number | null>>;
    readonly editingCaseClueEvidence: CaseClueEvidenceRow | null;
    readonly viewingCaseClue: CaseClueWorkspace | null;
    readonly caseClueEvidenceForm: FormInstance<any>;
    readonly setEditingCaseClueEvidence: React.Dispatch<React.SetStateAction<CaseClueEvidenceRow | null>>;
    readonly clueConversionForm: FormInstance<any>;
    readonly caseClues: CaseRow[];
    readonly setClueConversionOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly resolveVisibleCase: (row: {
        case?: CaseRow | undefined;
        case_record_id?: number | undefined;
        serial_no?: string | undefined;
        case_no?: string | undefined;
    }) => Promise<CaseRow | null>;
    readonly viewingCounselCase: CaseRow | null;
    readonly reminderForm: FormInstance<any>;
    readonly setReminderOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly caseEventSubmitting: boolean;
    readonly caseEventForm: FormInstance<any>;
    readonly editingCaseEvent: CaseEventRow | null;
    readonly setCaseEventSubmitting: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setCaseEventOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setEditingCaseEvent: React.Dispatch<React.SetStateAction<CaseEventRow | null>>;
    readonly loadCounselCaseEvents: (targetCase?: CaseRow | null) => Promise<void>;
    readonly caseLogTarget: CaseRow | null;
    readonly caseLogForm: FormInstance<any>;
    readonly caseLogKind: CaseLogKind;
    readonly setCaseLogOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setCaseLogTarget: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly batchUpdateForm: FormInstance<any>;
    readonly selectedCaseKeys: React.Key[];
    readonly setBatchUpdateOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly counselListMode: boolean;
    readonly loadCounselCases: (values?: Record<string, any>, page?: number, pageSize?: number) => Promise<void>;
    readonly counselPage: number;
    readonly counselPageSize: number;
    readonly editingCounselCase: CaseRow | null;
    readonly counselEditForm: FormInstance<any>;
    readonly setEditingCounselCase: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly setCaseCustomers: React.Dispatch<React.SetStateAction<CaseRow[]>>;
    readonly isNormalEditableCase: (row: CaseRow) => boolean;
    readonly normalCaseEditForm: FormInstance<any>;
    readonly resolveCasePersonValues: (sources: unknown) => string[];
    readonly resolveCasePersonValue: (source: string) => string;
    readonly setEditingNormalCase: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly editingNormalCase: CaseRow | null;
    readonly loadCounselDetailCluesPage: (row: CaseRow, nextPage?: number, nextPageSize?: number, keyword?: string) => Promise<{
        items: any;
        total: number;
        page: number;
        pageSize: number;
        pages: number;
    } | null>;
    readonly counselDetailCluePageSize: number;
    readonly arbitrationBasicForm: FormInstance<any>;
    readonly setEditingArbitrationCase: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly editingArbitrationCase: CaseRow | null;
    readonly criminalMaintenance: {
        row: CaseRow;
        kind: "litigants" | "public-security" | "procuratorates" | "courts";
    } | null;
    readonly criminalMaintenanceForm: FormInstance<any>;
    readonly setCriminalMaintenance: React.Dispatch<React.SetStateAction<{
        row: CaseRow;
        kind: "litigants" | "public-security" | "procuratorates" | "courts";
    } | null>>;
    readonly creatingCasePartyRole: CaseLitigantPartyField | null;
    readonly casePartyCreateForm: FormInstance<any>;
    readonly setCreatingCasePartySubmitting: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setCaseLitigantCandidates: React.Dispatch<React.SetStateAction<CaseLitigantCandidate[]>>;
    readonly caseLitigantsForm: FormInstance<any>;
    readonly setCreatingCasePartyRole: React.Dispatch<React.SetStateAction<CaseLitigantPartyField | null>>;
    readonly editingCaseLitigants: CaseRow | null;
    readonly setEditingCaseLitigants: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly editingCaseHearingLawyer: CaseRow | null;
    readonly caseHearingLawyerForm: FormInstance<any>;
    readonly setEditingCaseHearingLawyer: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly taskCase: CaseRow | null;
    readonly caseTaskCreateCase: CaseRow | null;
    readonly caseTaskKind: CaseTaskKind;
    readonly caseTaskMaterialFiles: UploadFile<any>[];
    readonly setCaseTaskCreateCase: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly setPhaseOptions: React.Dispatch<React.SetStateAction<CasePhaseOption[]>>;
    readonly phaseForm: FormInstance<any>;
    readonly setPhaseEditing: React.Dispatch<React.SetStateAction<CaseRow[] | null>>;
    readonly companyScheduleCourtInfo: {
        row: CaseRow;
        level: "first" | "second" | "execution" | "retrial";
    } | null;
    readonly companyScheduleCourtInfoForm: FormInstance<any>;
    readonly cancelCompanyScheduleCourtInfo: () => void;
    readonly progressEditing: CaseRow | null;
    readonly progressForm: FormInstance<any>;
    readonly setProgressEditing: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly phaseEditing: CaseRow[] | null;
    readonly phaseOptions: CasePhaseOption[];
    readonly executionStatusEditing: CaseRow[] | null;
    readonly executionStatusForm: FormInstance<any>;
    readonly setExecutionStatusEditing: React.Dispatch<React.SetStateAction<CaseRow[] | null>>;
    readonly selectedSpecialRow: any;
    readonly openHearing: (row: CaseRow) => MessageType | undefined;
}
export function createCaseWorkflowActions(context: CaseWorkflowDependencies) {
    const saveCreateDefendants = async () => {
        const { createDefendantEditorForm, createForm, setCreateDefendantEditorOpen } = context;
        const values = await createDefendantEditorForm.validateFields();
        createForm.setFieldValue("defendants", values.defendants);
        setCreateDefendantEditorOpen(false);
    };
    const advanceCreateStep = async () => {
        const { createStep, createForm, isCounselCreate, setCreateSubmitting, createRouteType, profile, setCreatedCaseId, setCreateStep, createdCaseId } = context;
        if (createStep === 0) {
            const values = createForm.getFieldsValue(true);
            const warning = getCaseCreateValidationError(values, isCounselCreate ? "counsel" : "normal");
            if (warning) {
                Modal.info({ title: "提示", content: warning, okText: "确定" });
                return;
            }
            setCreateSubmitting(true);
            try {
                const response = await api.post("/cases", buildCaseCreatePayload(values, {
                    mode: isCounselCreate ? "counsel" : "normal",
                    routeType: createRouteType,
                    owner: profile.username || "admin",
                    counselStart: values.counsel_range?.[0],
                    counselEnd: values.counsel_range?.[1],
                }));
                const newCaseId = Number(response.data?.id);
                if (!Number.isInteger(newCaseId) || newCaseId <= 0) {
                    throw new Error("案件创建接口没有返回有效案件 ID");
                }
                setCreatedCaseId(newCaseId);
                const customer = String(values.customer || "").trim();
                const customerIsDefendant = ["被告人/犯罪嫌疑人", "被告/被申请人"].includes(values.client_position);
                const customerIsThirdParty = values.client_position === "第三人";
                createForm.setFieldsValue({
                    plaintiffs: !isCounselCreate && customer && !customerIsDefendant && !customerIsThirdParty ? [customer] : [],
                    plaintiff_agents: [],
                    defendants: customer && customerIsDefendant ? [customer] : [],
                    defendant_agents: [],
                    third_parties: customer && customerIsThirdParty ? [customer] : [],
                    third_party_agents: [],
                    litigant_comment: "",
                });
                setCreateStep(1);
            }
            catch (error: any) {
                message.error(error?.response?.data?.detail || error?.message || "案件创建失败");
            }
            finally {
                setCreateSubmitting(false);
            }
            return;
        }
        if (!createdCaseId) {
            message.error("案件尚未创建，请重新进入新建案件页面");
            return;
        }
        await saveLitigants(false);
    };
    const saveLitigants = async (complete: boolean) => {
        const { createdCaseId, createForm, isCounselCreate, setCreateSubmitting, redirectAfterCreate, setCreateStep } = context;
        if (!createdCaseId) {
            message.error("案件尚未创建，请重新进入新建案件页面");
            return;
        }
        const values = createForm.getFieldsValue(true);
        if (!isCounselCreate && (!Array.isArray(values.defendants) || !values.defendants.some((item: unknown) => String(item || "").trim()))) {
            Modal.info({ title: "提示", content: "请输入至少一名被告", okText: "确定" });
            return;
        }
        setCreateSubmitting(true);
        try {
            await api.put(`/cases/${createdCaseId}/litigants`, {
                plaintiffs: values.plaintiffs || [],
                plaintiff_agents: values.plaintiff_agents || [],
                defendants: values.defendants || [],
                defendant_agents: values.defendant_agents || [],
                third_parties: values.third_parties || [],
                third_party_agents: values.third_party_agents || [],
                comment: values.litigant_comment || "",
            });
            if (complete) {
                if (isCounselCreate) {
                    await api.put(`/cases/${createdCaseId}/complete-creation`, { comment: values.litigant_comment || "" });
                }
                else {
                    await api.put(`/cases/${createdCaseId}/judicial`, {});
                }
                message.success("案件信息已完成");
                redirectAfterCreate();
            }
            else {
                setCreateStep(2);
            }
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "当事人信息保存失败");
        }
        finally {
            setCreateSubmitting(false);
        }
    };
    const finishCreateFlow = async () => {
        const { createdCaseId, createForm, setCreateSubmitting, redirectAfterCreate } = context;
        if (!createdCaseId) {
            message.error("案件尚未创建，请重新进入新建案件页面");
            return;
        }
        const values = createForm.getFieldsValue(true);
        setCreateSubmitting(true);
        try {
            await api.put(`/cases/${createdCaseId}/judicial`, {
                court: values.court || "",
                court_case_no: values.court_case_no || "",
                judge: values.judge || "",
                judge_phone: values.judge_phone || "",
                filing_date: values.filing_date?.format("YYYY-MM-DD") || null,
                hearing_date: values.hearing_date?.format("YYYY-MM-DD") || null,
                hearing_time: values.hearing_time?.format("HH:mm") || "",
                courtroom: values.courtroom || "",
                judicial_remark: values.judicial_remark || "",
                description: values.description || "",
                public_security_name: values.public_security_name || "",
                public_security_case_no: values.public_security_case_no || "",
                public_security_address: values.public_security_address || "",
                public_security_phone: values.public_security_phone || "",
                public_security_operator: values.public_security_operator || "",
                first_procuratorate_name: values.first_procuratorate_name || "",
                first_procuratorate_case_no: values.first_procuratorate_case_no || "",
                first_procuratorate_address: values.first_procuratorate_address || "",
                first_procuratorate_phone: values.first_procuratorate_phone || "",
                first_procuratorate_operator: values.first_procuratorate_operator || "",
                second_procuratorate_name: values.second_procuratorate_name || "",
                second_procuratorate_case_no: values.second_procuratorate_case_no || "",
                second_procuratorate_address: values.second_procuratorate_address || "",
                second_procuratorate_phone: values.second_procuratorate_phone || "",
                second_procuratorate_operator: values.second_procuratorate_operator || "",
                retrial_procuratorate_name: values.retrial_procuratorate_name || "",
                retrial_procuratorate_case_no: values.retrial_procuratorate_case_no || "",
                retrial_procuratorate_address: values.retrial_procuratorate_address || "",
                retrial_procuratorate_phone: values.retrial_procuratorate_phone || "",
                retrial_procuratorate_operator: values.retrial_procuratorate_operator || "",
                first_court_enabled: Boolean(values.first_court_enabled),
                first_court_name: values.first_court_name || "",
                first_court_case_no: values.first_court_case_no || "",
                first_court_courtroom: values.first_court_courtroom || "",
                first_court_judge: values.first_court_judge || "",
                first_court_clerk: values.first_court_clerk || "",
                first_court_filing_date: values.first_court_filing_date?.format("YYYY-MM-DD") || null,
                first_court_hearing_date: values.first_court_hearing_date?.format("YYYY-MM-DD") || null,
                second_court_enabled: Boolean(values.second_court_enabled),
                second_court_name: values.second_court_name || "",
                second_court_case_no: values.second_court_case_no || "",
                second_court_courtroom: values.second_court_courtroom || "",
                second_court_judge: values.second_court_judge || "",
                second_court_clerk: values.second_court_clerk || "",
                second_court_filing_date: values.second_court_filing_date?.format("YYYY-MM-DD") || null,
                second_court_hearing_date: values.second_court_hearing_date?.format("YYYY-MM-DD") || null,
                retrial_court_enabled: Boolean(values.retrial_court_enabled),
                retrial_court_name: values.retrial_court_name || "",
                retrial_court_case_no: values.retrial_court_case_no || "",
                retrial_court_courtroom: values.retrial_court_courtroom || "",
                retrial_court_judge: values.retrial_court_judge || "",
                retrial_court_clerk: values.retrial_court_clerk || "",
                retrial_court_filing_date: values.retrial_court_filing_date?.format("YYYY-MM-DD") || null,
                retrial_court_hearing_date: values.retrial_court_hearing_date?.format("YYYY-MM-DD") || null,
            });
            message.success("案件信息已完成");
            redirectAfterCreate();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "司法机关信息保存失败");
        }
        finally {
            setCreateSubmitting(false);
        }
    };
    const assign = async () => {
        const { assigning, assignForm, setAssigning, load } = context;
        if (!assigning)
            return;
        const v = await assignForm.validateFields();
        try {
            await api.post(`/cases/${assigning.id}/assign`, v);
            message.success("案件人员分配成功");
            setAssigning(null);
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "分配失败");
        }
    };
    const createHearing = async () => {
        const { hearingForm, setHearingOpen, load } = context;
        const v = await hearingForm.validateFields();
        const hearingValidationError = getCaseHearingValidationError(v);
        if (hearingValidationError)
            return message.warning(hearingValidationError);
        const hearingPayload = buildCaseHearingPayload({
            ...v,
            hearing_date: formatRequiredDate(v.hearing_date, "开庭日期"),
            hearing_time: formatRequiredDate(v.hearing_time, "开庭时间", "HH:mm"),
        });
        try {
            await api.post("/hearings", hearingPayload);
            message.success("开庭排期已创建");
            setHearingOpen(false);
            hearingForm.resetFields();
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "排期失败");
        }
    };
    const openArchive = async (row: CaseRow, type: "normal" | "deficit" = "normal") => {
        const { getCaseCapability, archiveForm, setArchiveChecks, setArchiveType, setArchiving } = context;
        if (!getCaseCapability(row).can_archive)
            return message.warning("当前账号没有案件归档权限");
        try {
            const { data } = await api.get(`/cases/${row.id}/archive-readiness`);
            archiveForm.setFieldsValue({
                ...data.checks,
                archive_no: data.archive_no,
                paper_archive_location: data.paper_archive_location,
                paper_volume_count: data.paper_volume_count || 1,
                archive_type: type,
                comment: "",
            });
            setArchiveChecks(data.checks || {});
            setArchiveType(type);
            setArchiving(row);
        }
        catch {
            message.error("归档检查加载失败");
        }
    };
    const closeCase = async () => {
        const { archiving, load } = context;
        if (!archiving)
            return;
        try {
            await api.post(`/cases/${archiving.id}/close`, { comment: "归档前确认案件已经办结" });
            message.success("案件办结已由系统记录");
            await openArchive(archiving);
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件办结失败");
        }
    };
    const archive = async (submit: boolean) => {
        const { archiving, archiveForm, archiveType, setArchiving, load } = context;
        if (!archiving)
            return;
        const v = await archiveForm.validateFields();
        try {
            await api.post(`/cases/${archiving.id}/archive`, { ...v, archive_type: archiveType, submit });
            message.success(submit ? (archiveType === "deficit" ? "已提交亏损归档内部审核" : "已提交归档审核") : "归档检查已保存");
            setArchiving(null);
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "归档操作失败");
        }
    };
    const reviewArchive = async (approved = context.reviewing?.approved ?? true) => {
        const { reviewing, profile, reviewForm, setReviewing, load } = context;
        if (!reviewing)
            return;
        const rows = reviewing.rows || [reviewing.row];
        for (const row of rows) {
            const permissionError = getCaseArchiveReviewValidationError({ role: profile.role, status: row.status });
            if (permissionError) return message.warning(`${row.serial_no}：${permissionError}`);
        }
        try {
            const values = await reviewForm.validateFields();
            const items = rows.map(row => ({case_id: row.id, approved,
                comment: String(values.items?.[String(row.id)]?.comment || "").trim(),
                archive_no: approved ? String(values.items?.[String(row.id)]?.archive_no || "").trim() : "",
            }));
            for (const [index, row] of rows.entries()) {
                if (approved && row.status !== "亏损内审" && (row.data.archive_type || "normal") !== "deficit" && !items[index].archive_no)
                    return message.warning(`${row.serial_no}：请填写归档号`);
            }
            if (items.length === 1) {
                const {case_id, ...body} = items[0];
                await api.post(`/cases/${case_id}/archive/review`, body);
            } else {
                await api.post("/cases/archive/batch-review", {items});
            }
            message.success(`已${approved ? "同意" : "拒绝"} ${items.length} 条归档审核`);
            setReviewing(null);
            reviewForm.resetFields();
            await load();
        }
        catch (error: any) {
            if (error?.errorFields) return;
            message.error(error?.response?.data?.detail || "归档审核失败");
        }
    };
    const reviewCaseCreation = async (row: CaseRow, approved: boolean) => {
        const { setSelectedCaseKeys, load } = context;
        try {
            await api.post(`/cases/${row.id}/creation/review`, { approved, comment: approved ? "案件资料完整，同意立案" : "案件资料不完整，请补充后重新提交" });
            message.success(approved ? "立案审批已通过，固定任务已生成" : "立案审批已驳回");
            setSelectedCaseKeys([]);
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "立案审批失败");
        }
    };
    const deleteCompanyCase = async (row: CaseRow) => {
        const { initialView, getCaseCapability, setSelectedCaseKeys, loadOrdinaryCases, caseQuery, originalPage, originalPageSize } = context;
        if (!isCompanyCaseListRoute(initialView) || !getCaseCapability(row).can_delete_case) {
            return message.warning("当前账号没有删除该案件的权限");
        }
        Modal.confirm({
            title: "删除案件",
            content: `确认删除案件“${row.serial_no} ${row.title}”吗？案件任务、附件、费用、排期和操作记录也会一并删除。`,
            okText: "删除",
            cancelText: "取消",
            okButtonProps: { danger: true },
            onOk: async () => {
                try {
                    await api.delete(`/cases/${row.id}`);
                    message.success("案件已删除");
                    setSelectedCaseKeys([]);
                    await loadOrdinaryCases(caseQuery, originalPage, originalPageSize);
                }
                catch (error: any) {
                    message.error(error?.response?.data?.detail || "案件删除失败");
                    throw error;
                }
            },
        });
    };
    const reviewUnarchive = async (row: CaseRow, approved: boolean, comment = "") => {
        const { profile, setSelectedCaseKeys, load } = context;
        const reviewPayload = buildCaseUnarchiveReviewPayload({
            approved,
            comment: approved ? "同意解档并恢复办理" : comment,
        });
        const permissionError = getCaseUnarchiveReviewValidationError({
            role: profile.role,
            status: row.status,
            requestStatus: row.data.unarchive_request?.status,
            requestedBy: row.data.unarchive_request?.requested_by,
            currentUsername: profile.username,
            approved,
            comment: reviewPayload.comment,
        });
        if (permissionError)
            return message.warning(permissionError);
        try {
            await api.post(`/cases/${row.id}/unarchive/review`, reviewPayload);
            message.success(approved ? "解档审批已通过" : "解档审批已驳回");
            setSelectedCaseKeys([]);
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "解档审批失败");
        }
    };
    const openCaseTasks = async (row: CaseRow) => {
        const { loadCaseTasksPage, taskForm, profile, setCaseTaskMaterialFiles, setTaskCase } = context;
        try {
            await loadCaseTasksPage(row, CASE_TASK_DEFAULT_PAGE, CASE_TASK_DEFAULT_PAGE_SIZE);
            taskForm.resetFields();
            const startAt = dayjs().second(0);
            taskForm.setFieldsValue({
                owner: profile.username || row.owner,
                start_at: startAt,
                end_at: startAt.add(7, "day"),
                priority: "普通",
                collaborators: [], is_vip: false,
            });
            setCaseTaskMaterialFiles([]);
            setTaskCase(row);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件任务加载失败");
        }
    };
    const openCounselDetail = async (row: CaseRow, preferredTab?: string) => {
        const { isCaseDetailView, initialView, originalPage, originalPageSize, caseQuery, onNavigate, counselDetailClueRequestRef, setCounselDetailClues, setCounselDetailClueKeyword, setCounselDetailClueSearchInput, setCounselDetailCluePage, setCounselDetailCluePageSize, setCounselDetailClueTotal, setCounselDetailCluePages, setActiveCounselDetailTab, setViewingCounselCase, counselDetailCaseIdRef, setCounselDetailAssistedFees, setCounselDetailAssistedFeeTotal, loadCounselDetailAssistedFees, counselDetailAssistedFeePageSize, setLegacyLsHistoryCaseIds, setSelectedCounselAttachmentKeys, setSelectedCounselCaseEventKeys, setActiveCounselDocCategory, setExpandedCounselDocGroups, contracts, caseCustomers, counselDetailTaskVipFilter, counselDetailCustomerTaskVipFilter, setCounselDetailHistory, applyCounselDetailTaskPageState, applyCounselDetailCustomerTaskPageState, setCounselDetailAttachments, setCounselDetailCustomerAttachments, setCounselDetailContractAttachments, setCounselDocumentFolderTree, setCounselReminders, setCounselCaseEvents, setCounselCaseEventCapabilities, setCounselCaseEventsError, setCounselLogs, setCounselDetailCapabilities, setCounselDetailFinance, applyCounselDetailCluePageState } = context;
        if (!isCaseDetailView) {
            sessionStorage.setItem("sunhold:case-detail-tab", preferredTab || "documents");
            const serialNo = String(row.serial_no || `案件-${row.id}`).trim();
            rememberCaseDetailTarget({ id: row.id, serial_no: serialNo });
            sessionStorage.setItem("sunhold:case-list-return", JSON.stringify({ route: initialView, page: originalPage, pageSize: originalPageSize, query: caseQuery }));
            onNavigate?.(`case-detail-${row.id}-${encodeURIComponent(serialNo)}`);
            return;
        }
        try {
            const clueRequestId = ++counselDetailClueRequestRef.current;
            setCounselDetailClues([]);
            setCounselDetailClueKeyword("");
            setCounselDetailClueSearchInput("");
            setCounselDetailCluePage(1);
            setCounselDetailCluePageSize(10);
            setCounselDetailClueTotal(0);
            setCounselDetailCluePages(0);
            const storedTab = sessionStorage.getItem("sunhold:case-detail-tab");
            if (preferredTab || storedTab)
                setActiveCounselDetailTab(preferredTab || storedTab || "documents");
            if (storedTab)
                sessionStorage.removeItem("sunhold:case-detail-tab");
            // 基础案件详情必须先打开；历史、附件、提醒等附加面板不能因为单点失败
            // 阻断案号关联、搜索或通知进入详情。
            const recordRes = await api.get(`/records/${row.id}`);
            if (clueRequestId !== counselDetailClueRequestRef.current)
                return;
            const detailRecord = recordRes.data as CaseRow;
            setViewingCounselCase(detailRecord);
            counselDetailCaseIdRef.current = detailRecord.id;
            setCounselDetailAssistedFees([]);
            setCounselDetailAssistedFeeTotal(0);
            void loadCounselDetailAssistedFees(detailRecord.id, 1, counselDetailAssistedFeePageSize);
            void api.get<{
                legacy_case_id: number;
            }>(`/legacy-ls-history/current-records/${detailRecord.id}`)
                .then((response) => setLegacyLsHistoryCaseIds((current) => ({ ...current, [detailRecord.id]: response.data.legacy_case_id })))
                .catch(() => setLegacyLsHistoryCaseIds((current) => {
                if (!(detailRecord.id in current))
                    return current;
                const next = { ...current };
                delete next[detailRecord.id];
                return next;
            }));
            document.querySelector<HTMLElement>(".content")?.scrollTo({ top: 0, left: 0 });
            setSelectedCounselAttachmentKeys([]);
            setSelectedCounselCaseEventKeys([]);
            setActiveCounselDocCategory("");
            setExpandedCounselDocGroups({ "调查文档全部": true, "案件文档全部": true });
            const contractRecordId = Number(detailRecord.data.contract_record_id || detailRecord.data.contract_id)
                || contracts.find((item) => item.serial_no === detailRecord.data.contract_no)?.id;
            const customerRecordId = Number(detailRecord.data.customer_record_id || detailRecord.data.customer_id)
                || caseCustomers.find((item) => item.title === detailRecord.customer)?.id;
            const emptyAttachmentResponse = { data: { items: [] } };
            const [historyRes, taskRes, customerTaskRes, attachmentRes, reminderRes, eventRes, logRes, capabilityRes, relationRes, customerAttachmentRes, contractAttachmentRes, folderRes] = await Promise.allSettled([
                api.get(`/records/${row.id}/history`),
                api.get(`/cases/${row.id}/tasks`, {
                    params: { page: CASE_TASK_DEFAULT_PAGE, page_size: CASE_TASK_DEFAULT_PAGE_SIZE, scope: "case", is_vip: counselDetailTaskVipFilter === "all" ? undefined : counselDetailTaskVipFilter === "vip" },
                }),
                api.get(`/cases/${row.id}/tasks`, {
                    params: { page: CASE_TASK_DEFAULT_PAGE, page_size: CASE_TASK_DEFAULT_PAGE_SIZE, scope: "customer", is_vip: counselDetailCustomerTaskVipFilter === "all" ? undefined : counselDetailCustomerTaskVipFilter === "vip" },
                }),
                api.get("/attachments", { params: { record_id: row.id, page_size: 200 } }),
                api.get(`/cases/${row.id}/reminders`),
                api.get(`/cases/${row.id}/events`),
                api.get(`/cases/${row.id}/logs`),
                api.get(`/cases/${row.id}/action-capabilities`),
                api.get(`/cases/${row.id}/relations`, { params: { clue_page: 1, clue_page_size: 10 } }),
                customerRecordId ? api.get("/attachments", { params: { record_id: customerRecordId, page_size: 200 } }) : Promise.resolve(emptyAttachmentResponse),
                contractRecordId ? api.get("/attachments", { params: { record_id: contractRecordId, page_size: 200 } }) : Promise.resolve(emptyAttachmentResponse),
                api.get(`/cases/${row.id}/document-folders`),
            ]);
            setCounselDetailHistory(historyRes.status === "fulfilled" ? historyRes.value.data.items || [] : []);
            if (taskRes.status === "fulfilled") {
                applyCounselDetailTaskPageState(taskRes.value.data, CASE_TASK_DEFAULT_PAGE, CASE_TASK_DEFAULT_PAGE_SIZE);
            }
            else {
                applyCounselDetailTaskPageState({ items: [], total: 0, page: CASE_TASK_DEFAULT_PAGE, page_size: CASE_TASK_DEFAULT_PAGE_SIZE, pages: 0 }, CASE_TASK_DEFAULT_PAGE, CASE_TASK_DEFAULT_PAGE_SIZE);
            }
            if (customerTaskRes.status === "fulfilled") {
                applyCounselDetailCustomerTaskPageState(customerTaskRes.value.data, CASE_TASK_DEFAULT_PAGE, CASE_TASK_DEFAULT_PAGE_SIZE);
            }
            else {
                applyCounselDetailCustomerTaskPageState({ items: [], total: 0, page: CASE_TASK_DEFAULT_PAGE, page_size: CASE_TASK_DEFAULT_PAGE_SIZE, pages: 0 }, CASE_TASK_DEFAULT_PAGE, CASE_TASK_DEFAULT_PAGE_SIZE);
            }
            setCounselDetailAttachments(attachmentRes.status === "fulfilled" ? attachmentRes.value.data.items || [] : []);
            setCounselDetailCustomerAttachments(customerAttachmentRes.status === "fulfilled" ? customerAttachmentRes.value.data.items || [] : []);
            setCounselDetailContractAttachments(contractAttachmentRes.status === "fulfilled" ? contractAttachmentRes.value.data.items || [] : []);
            setCounselDocumentFolderTree(folderRes.status === "fulfilled" && Array.isArray(folderRes.value.data?.tree) ? folderRes.value.data.tree : []);
            setCounselReminders(reminderRes.status === "fulfilled" ? reminderRes.value.data.items || [] : []);
            setCounselCaseEvents(eventRes.status === "fulfilled" ? eventRes.value.data.items || [] : []);
            setCounselCaseEventCapabilities(eventRes.status === "fulfilled" ? eventRes.value.data.capabilities || noCaseEventCapabilities : noCaseEventCapabilities);
            setCounselCaseEventsError(eventRes.status === "rejected" ? "案件事件加载失败，请重试" : "");
            setCounselLogs(logRes.status === "fulfilled" ? logRes.value.data.items || [] : []);
            setCounselDetailCapabilities(capabilityRes.status === "fulfilled" ? capabilityRes.value.data || noCaseDetailWriteCapability : noCaseDetailWriteCapability);
            setCounselDetailFinance(relationRes.status === "fulfilled" ? relationRes.value.data.fees || [] : []);
            setCounselDetailClues(relationRes.status === "fulfilled" ? relationRes.value.data.clues || [] : []);
            if (relationRes.status === "fulfilled" && clueRequestId === counselDetailClueRequestRef.current) {
                applyCounselDetailCluePageState(relationRes.value.data, 1, 10);
            }
            else if (relationRes.status === "rejected" && clueRequestId === counselDetailClueRequestRef.current) {
                applyCounselDetailCluePageState({ clues: [], clue_total: 0 }, 1, 10);
            }
            if ([historyRes, taskRes, customerTaskRes, attachmentRes, reminderRes, eventRes, logRes, capabilityRes, relationRes, customerAttachmentRes, contractAttachmentRes, folderRes].some((result) => result.status === "rejected")) {
                message.warning("部分案件附加信息加载失败，已打开基础详情");
            }
        }
        catch (error: any) {
            setCounselDetailCapabilities(noCaseDetailWriteCapability);
            message.error(error?.response?.data?.detail || "案件详情加载失败");
        }
    };
    const duplicateCase = async (row: CaseRow) => {
        const { load } = context;
        const blocked = getCaseMutationBlockReason(row.status);
        if (blocked)
            return message.warning(blocked);
        try {
            const { data } = await api.post(buildCaseDuplicateRequest(row).path);
            message.success(`已复制为新案件：${data.serial_no}`);
            await openCounselDetail(data);
            void load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件复制失败");
        }
    };
    const submitCaseMerge = async () => {
        const { mergingCase, mergeCaseForm, setMergingCase, load } = context;
        if (!mergingCase)
            return;
        const blocked = getCaseMutationBlockReason(mergingCase.status);
        if (blocked)
            return message.warning(blocked);
        try {
            const values = await mergeCaseForm.validateFields();
            const { data } = await api.post(`/cases/${mergingCase.id}/merge`, buildCaseMergePayload(values));
            message.success(`已合并案件 ${data.source.serial_no}：迁移费用 ${data.moved_fees} 条、案件文件 ${data.moved_attachments} 个`);
            setMergingCase(null);
            mergeCaseForm.resetFields();
            await openCounselDetail(data.target);
            void load();
        }
        catch (error: any) {
            if (error?.errorFields)
                return;
            message.error(error?.response?.data?.detail || "案件合并失败");
        }
    };
    const submitNotaryInfo = async () => {
        const { notaryInfoCase, notaryInfoForm, setNotaryInfoCase, load } = context;
        if (!notaryInfoCase)
            return;
        try {
            const values = await notaryInfoForm.validateFields();
            const { data } = await api.put(`/cases/${notaryInfoCase.id}/notary-info`, values);
            message.success("公证信息已更新");
            setNotaryInfoCase(null);
            notaryInfoForm.resetFields();
            await openCounselDetail(data);
            void load();
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "公证信息更新失败");
        }
    };
    const openCaseClueWorkspace = async (target: {
        id?: number;
    }) => {
        const { setCaseClueLoading, setViewingCaseClue, setSelectedCaseClueEvidenceId } = context;
        const id = Number(target.id || 0) || undefined;
        if (!id)
            return message.warning("当前案件未关联调查线索");
        setCaseClueLoading(true);
        try {
            const { data } = await api.get(`/investigations/clues/${id}/workspace`);
            setViewingCaseClue(data);
            setSelectedCaseClueEvidenceId(null);
        }
        catch (error: any) {
            if (error?.response?.status === 403)
                message.warning("当前账号无权查看该调查线索详情");
            else if (error?.response?.status === 404)
                message.warning("关联调查线索不存在或已被删除");
            else
                message.error(error?.response?.data?.detail || "线索取证信息加载失败");
        }
        finally {
            setCaseClueLoading(false);
        }
    };
    const saveCaseClueEvidence = async () => {
        const { editingCaseClueEvidence, viewingCaseClue, caseClueEvidenceForm, setViewingCaseClue, setEditingCaseClueEvidence } = context;
        if (!editingCaseClueEvidence || !viewingCaseClue)
            return;
        try {
            const values = await caseClueEvidenceForm.validateFields();
            await api.put(`/investigations/evidence/${editingCaseClueEvidence.id}`, {
                ...values,
                collected_at: values.collected_at ? formatRequiredDate(values.collected_at, "取证时间") : null,
            });
            const { data } = await api.get(`/investigations/clues/${viewingCaseClue.clue.id}/workspace`);
            setViewingCaseClue(data);
            setEditingCaseClueEvidence(null);
            caseClueEvidenceForm.resetFields();
            message.success("取证信息已修改");
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "取证信息修改失败");
        }
    };
    const submitClueConversion = async () => {
        const { clueConversionForm, caseClues, setClueConversionOpen, load } = context;
        const values = await clueConversionForm.validateFields();
        const issues = getClueConversionIssues({ clueIds: values.clue_ids, contractRecordId: values.contract_record_id, clues: caseClues });
        if (issues.length)
            return message.warning(issues[0]);
        try {
            const { data } = await api.post("/investigations/clues/batch-cases", buildClueConversionPayload(values));
            setClueConversionOpen(false);
            clueConversionForm.resetFields();
            if (data.failed)
                message.warning(`已生成 ${data.created || 0} 件案件，${data.failed} 条线索未转案`);
            else
                message.success(`已从线索生成 ${data.created || 0} 件案件`);
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "线索转案件失败");
        }
    };
    const openSpecialCaseDetail = async (row: {
        case?: CaseRow;
        case_record_id?: number;
        serial_no?: string;
        case_no?: string;
    }) => {
        const { resolveVisibleCase } = context;
        const target = await resolveVisibleCase(row);
        if (!target) {
            if (!row.case_record_id && !row.case_no && !row.serial_no)
                message.warning("当前记录未关联案件");
            return;
        }
        await openCounselDetail(target);
    };
    const openSpecialCaseTasks = async (row: {
        case?: CaseRow;
        case_record_id?: number;
        serial_no?: string;
        case_no?: string;
    }) => {
        const { resolveVisibleCase } = context;
        const target = await resolveVisibleCase(row);
        if (!target)
            return;
        await openCaseTasks(target);
    };
    const createCounselReminder = async () => {
        const { viewingCounselCase, reminderForm, setReminderOpen } = context;
        if (!viewingCounselCase)
            return;
        const values = await reminderForm.validateFields();
        const dateError = getCaseReminderDateValidationError(values.reminder_date, values.deadline);
        if (dateError)
            return message.error(dateError);
        try {
            await api.post(`/cases/${viewingCounselCase.id}/reminders`, {
                reminder_date: formatRequiredDate(values.reminder_date, "提醒日期"),
                deadline: formatRequiredDate(values.deadline, "截止日期"),
                content: values.content.trim(),
            });
            message.success("案件提醒已创建");
            setReminderOpen(false);
            reminderForm.resetFields();
            await openCounselDetail(viewingCounselCase);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件提醒创建失败");
        }
    };
    const saveCaseEvent = async () => {
        const { viewingCounselCase, caseEventSubmitting, caseEventForm, editingCaseEvent, setCaseEventSubmitting, setCaseEventOpen, setEditingCaseEvent, loadCounselCaseEvents } = context;
        if (!viewingCounselCase)
            return;
        if (caseEventSubmitting)
            return;
        try {
            const values = await caseEventForm.validateFields();
            if (!String(values.event_type || "").trim())
                return message.warning("请输入事件类型");
            if (!String(values.content || "").trim())
                return message.warning("请输入事件内容");
            const payload = {
                event_type: String(values.event_type || "").trim(),
                content: String(values.content || "").trim(),
                event_time: dayjs(values.event_time).toISOString(),
                deadline: values.deadline ? formatRequiredDate(values.deadline, "截止日期") : undefined,
                reminder_enabled: Boolean(values.reminder_enabled),
                remind_at: values.reminder_enabled && values.remind_at ? dayjs(values.remind_at).toISOString() : null,
                ...(editingCaseEvent ? { status: values.status } : {}),
            };
            setCaseEventSubmitting(true);
            if (editingCaseEvent) {
                await api.patch(`/cases/${viewingCounselCase.id}/events/${editingCaseEvent.id}`, payload);
                message.success("案件事件已更新");
            }
            else {
                await api.post(`/cases/${viewingCounselCase.id}/events`, payload);
                message.success("案件事件已创建");
            }
            setCaseEventOpen(false);
            setEditingCaseEvent(null);
            caseEventForm.resetFields();
            await loadCounselCaseEvents(viewingCounselCase);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || (editingCaseEvent ? "更新案件事件失败" : "创建案件事件失败"));
        }
        finally {
            setCaseEventSubmitting(false);
        }
    };
    const createCounselLog = async () => {
        const { caseLogTarget, viewingCounselCase, caseLogForm, caseLogKind, setCaseLogOpen, setCaseLogTarget } = context;
        const targetCase = caseLogTarget || viewingCounselCase;
        if (!targetCase)
            return;
        const values = await caseLogForm.validateFields();
        try {
            const logContent = caseLogKind === "refund" ? `退费日志：${values.content.trim()}` : values.content.trim();
            await api.post(`/cases/${targetCase.id}/logs`, { content: logContent });
            message.success(caseLogKind === "refund" ? "退费日志已保存" : "案件日志已保存");
            setCaseLogOpen(false);
            caseLogForm.resetFields();
            setCaseLogTarget(null);
            if (viewingCounselCase?.id === targetCase.id)
                await openCounselDetail(targetCase);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件日志保存失败");
        }
    };
    const submitCounselBatchUpdate = async () => {
        const { batchUpdateForm, selectedCaseKeys, setBatchUpdateOpen, counselListMode, loadCounselCases, caseQuery, counselPage, counselPageSize, loadOrdinaryCases, originalPage, originalPageSize } = context;
        const values = await batchUpdateForm.validateFields();
        const caseIds = selectedCaseKeys.map(Number);
        if (!caseIds.length)
            return message.warning("请选择需要修改的案件");
        const payload: any = { case_ids: caseIds, comment: values.comment || "" };
        if (values.hearing_lawyer !== undefined)
            payload.hearing_lawyer = values.hearing_lawyer;
        if (values.handling_lawyers !== undefined)
            payload.handling_lawyers = values.handling_lawyers;
        if (values.assistant !== undefined)
            payload.assistant = values.assistant;
        if (values.case_stage !== undefined)
            payload.case_stage = values.case_stage;
        if (payload.hearing_lawyer === undefined && payload.handling_lawyers === undefined && payload.assistant === undefined && payload.case_stage === undefined)
            return message.warning("请至少填写一个需要修改的字段");
        try {
            const { data } = await api.post("/cases/batch-update", payload);
            message.success(`已修改 ${data.updated} 个案件`);
            setBatchUpdateOpen(false);
            batchUpdateForm.resetFields();
            if (counselListMode)
                await loadCounselCases(caseQuery, counselPage, counselPageSize);
            else
                await loadOrdinaryCases(caseQuery, originalPage, originalPageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "批量修改失败");
        }
    };
    const saveCounselBasic = async () => {
        const { editingCounselCase, counselEditForm, setEditingCounselCase, setViewingCounselCase, load, loadCounselCases, caseQuery, counselPage, counselPageSize } = context;
        if (!editingCounselCase)
            return;
        const values = await counselEditForm.validateFields();
        try {
            const { data } = await api.put(`/cases/${editingCounselCase.id}/counsel-basic`, {
                title: values.title.trim(),
                counsel_type: values.counsel_type.trim(),
                counsel_start: values.counsel_range[0].format("YYYY-MM-DD"),
                counsel_end: values.counsel_range[1].format("YYYY-MM-DD"),
                handling_lawyers: values.handling_lawyers || [],
                assistant: values.assistant || "",
                comment: values.comment || "",
            });
            message.success("法律顾问案件基本信息已保存");
            setEditingCounselCase(null);
            setViewingCounselCase(data);
            await load();
            await loadCounselCases(caseQuery, counselPage, counselPageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "法律顾问案件基本信息保存失败");
        }
    };
    const ensureCaseCustomerOption = async (row: CaseRow) => {
        const { caseCustomers, setCaseCustomers } = context;
        let customerId = Number(row.data.customer_record_id || row.data.customer_id) || caseCustomers.find((item) => item.title === row.customer)?.id || 0;
        if (customerId && !caseCustomers.some((item) => item.id === customerId)) {
            try {
                const { data } = await api.get(`/records/${customerId}`);
                if (data?.module === "customer") {
                    setCaseCustomers((current) => current.some((item) => item.id === data.id) ? current : [...current, data]);
                    return Number(data.id) || customerId;
                }
            }
            catch {
                // Fall through to the name lookup for legacy cases without a usable link.
            }
        }
        if (!customerId && row.customer) {
            try {
                const { data } = await api.get("/records", { params: { module: "customer", keyword: row.customer, page_size: 100 } });
                const match = (data.items || []).find((item: CaseRow) => item.title === row.customer);
                if (match) {
                    customerId = Number(match.id);
                    setCaseCustomers((current) => current.some((item) => item.id === match.id) ? current : [...current, match]);
                }
            }
            catch {
                // Keep the standard validation error when the linked customer is not visible.
            }
        }
        if (!customerId && row.customer) {
            const legacyCustomerId = -Math.max(Number(row.id) || 1, 1);
            setCaseCustomers((current) => current.some((item) => item.id === legacyCustomerId) ? current : [...current, { id: legacyCustomerId, serial_no: "", title: row.customer, status: "正常", data: {} } as CaseRow]);
            return legacyCustomerId;
        }
        return customerId;
    };
    const openNormalCaseEdit = async (row: CaseRow) => {
        const { isNormalEditableCase, normalCaseEditForm, resolveCasePersonValues, resolveCasePersonValue, setEditingNormalCase } = context;
        if (!isNormalEditableCase(row))
            return message.warning("当前案件类型没有普通案件基本信息修改入口");
        const customerRecordId = await ensureCaseCustomerOption(row);
        const clueIds = Array.isArray(row.data.investigation_clue_ids) ? row.data.investigation_clue_ids.map(Number).filter(Boolean) : (Number(row.data.investigation_clue_id || row.data.clue_record_id) ? [Number(row.data.investigation_clue_id || row.data.clue_record_id)] : []);
        normalCaseEditForm.setFieldsValue({
            customer_record_id: customerRecordId || undefined,
            title: row.title,
            case_phase: row.status,
            cause_or_charge: row.data.cause_or_charge || "",
            handling_lawyers: resolveCasePersonValues(row.data.handling_lawyers || []),
            assistants: resolveCasePersonValues(row.data.assistant_usernames || row.data.assistants || (row.data.assistant ? [row.data.assistant] : [])),
            business_owner: resolveCasePersonValue(row.data.business_owner || row.data.source_person || ""),
            investigator: resolveCasePersonValue(row.data.investigator || ""),
            investigation_clue_ids: clueIds,
            right_type: row.data.right_type || "",
            comment: "",
        });
        setEditingNormalCase(row);
    };
    const saveNormalCaseBasic = async () => {
        const { editingNormalCase, normalCaseEditForm, setEditingNormalCase, setViewingCounselCase, viewingCounselCase, loadCounselDetailCluesPage, counselDetailCluePageSize, load } = context;
        if (!editingNormalCase)
            return;
        const values = await normalCaseEditForm.validateFields();
        const validationError = getCaseEditValidationError(Number(editingNormalCase.data.customer_record_id || editingNormalCase.data.customer_id) ? values : { ...values, customer_record_id: 1 });
        if (validationError)
            return message.warning(validationError);
        try {
            const { data } = await api.put(`/cases/${editingNormalCase.id}/normal-basic`, normalizeCaseEditPayload({ ...values, customer_record_id: Number(values.customer_record_id) > 0 ? values.customer_record_id : null, legacy_case_edit: true }, "normal"));
            message.success("案件基本信息已保存");
            setEditingNormalCase(null);
            setViewingCounselCase(data);
            if (viewingCounselCase?.id === data.id) {
                void loadCounselDetailCluesPage(data, 1, counselDetailCluePageSize)
                    .catch((error: any) => message.error(error?.response?.data?.detail || "关联线索刷新失败"));
            }
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件基本信息保存失败");
        }
    };
    const openArbitrationBasicEdit = async (row: CaseRow) => {
        const { arbitrationBasicForm, resolveCasePersonValues, resolveCasePersonValue, setEditingArbitrationCase } = context;
        if (row.data.case_type !== "仲裁")
            return message.warning("当前案件不是仲裁案件");
        const customerRecordId = await ensureCaseCustomerOption(row);
        arbitrationBasicForm.setFieldsValue({
            customer_record_id: customerRecordId || undefined,
            title: row.title, case_phase: row.status, cause_or_charge: row.data.cause_or_charge || "",
            handling_lawyers: resolveCasePersonValues(row.data.handling_lawyers || []), assistant: resolveCasePersonValue(row.data.assistant || ""), investigator: resolveCasePersonValue(row.data.investigator || ""),
            investigation_clue_ids: Array.isArray(row.data.investigation_clue_ids) ? row.data.investigation_clue_ids : [], comment: "",
        });
        setEditingArbitrationCase(row);
    };
    const saveArbitrationBasic = async () => {
        const { editingArbitrationCase, arbitrationBasicForm, setEditingArbitrationCase, setViewingCounselCase, viewingCounselCase, loadCounselDetailCluesPage, counselDetailCluePageSize, load } = context;
        if (!editingArbitrationCase)
            return;
        const values = await arbitrationBasicForm.validateFields();
        const validationError = getCaseEditValidationError(Number(editingArbitrationCase.data.customer_record_id || editingArbitrationCase.data.customer_id) ? values : { ...values, customer_record_id: 1 });
        if (validationError)
            return message.warning(validationError);
        try {
            const { data } = await api.put(`/cases/${editingArbitrationCase.id}/arbitration-basic`, normalizeCaseEditPayload({ ...values, customer_record_id: Number(values.customer_record_id) > 0 ? values.customer_record_id : null, legacy_case_edit: true }, "arbitration"));
            message.success("仲裁案件基本信息已保存");
            setEditingArbitrationCase(null);
            setViewingCounselCase(data);
            if (viewingCounselCase?.id === data.id) {
                void loadCounselDetailCluesPage(data, 1, counselDetailCluePageSize)
                    .catch((error: any) => message.error(error?.response?.data?.detail || "关联线索刷新失败"));
            }
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "仲裁案件基本信息保存失败");
        }
    };
    const saveCriminalMaintenance = async () => {
        const { criminalMaintenance, criminalMaintenanceForm, setCriminalMaintenance, setViewingCounselCase, load } = context;
        if (!criminalMaintenance)
            return;
        const values = await criminalMaintenanceForm.validateFields();
        const dateFields = ["first_court_filing_date", "first_court_hearing_date", "second_court_filing_date", "second_court_hearing_date", "execution_court_filing_date", "execution_court_hearing_date", "retrial_court_filing_date", "retrial_court_hearing_date"];
        const payload = { ...values, ...Object.fromEntries(dateFields.map(key => [key, values[key]?.format?.("YYYY-MM-DD") || null])) };
        try {
            const { data } = await api.put(`/cases/${criminalMaintenance.row.id}/criminal/${criminalMaintenance.kind}`, payload);
            message.success("刑事案件资料已保存");
            setCriminalMaintenance(null);
            setViewingCounselCase(data);
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "刑事案件资料保存失败");
        }
    };
    const saveCaseParty = async () => {
        const { creatingCasePartyRole, casePartyCreateForm, setCreatingCasePartySubmitting, setCaseLitigantCandidates, setCaseCustomers, caseLitigantsForm, setCreatingCasePartyRole } = context;
        if (!creatingCasePartyRole)
            return;
        const values = await casePartyCreateForm.validateFields();
        setCreatingCasePartySubmitting(true);
        try {
            const { data } = await api.post("/customers", {
                title: String(values.title || "").trim(),
                customer_type: "当事人",
                status: "潜在",
                credit_code: String(values.credit_code || "").trim(),
                phone: String(values.phone || "").trim(),
                legal_representative: String(values.legal_representative || "").trim(),
                registered_address: String(values.registered_address || "").trim(),
            });
            const candidate: CaseLitigantCandidate = {
                id: Number(data.id),
                serial_no: String(data.serial_no || ""),
                title: String(data.title || values.title).trim(),
                customer_type: String(data.data?.customer_type || "当事人"),
            };
            setCaseLitigantCandidates((current) => [candidate, ...current.filter((item) => item.id !== candidate.id)]);
            setCaseCustomers((current) => current.some((item) => item.id === data.id) ? current : [data, ...current]);
            const currentValues = caseLitigantsForm.getFieldValue(creatingCasePartyRole) || [];
            caseLitigantsForm.setFieldValue(creatingCasePartyRole, Array.from(new Set([...currentValues, candidate.title])));
            message.success(`${CASE_LITIGANT_PARTY_LABELS[creatingCasePartyRole]}当事人已新增并选中`);
            setCreatingCasePartyRole(null);
            casePartyCreateForm.resetFields();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "新增当事人失败");
        }
        finally {
            setCreatingCasePartySubmitting(false);
        }
    };
    const saveCaseLitigants = async () => {
        const { editingCaseLitigants, caseLitigantsForm, setEditingCaseLitigants, setViewingCounselCase, load } = context;
        if (!editingCaseLitigants)
            return;
        const values = await caseLitigantsForm.validateFields();
        try {
            const { data } = await api.put(`/cases/${editingCaseLitigants.id}/litigants-detail`, values);
            message.success("当事人信息已保存");
            setEditingCaseLitigants(null);
            setViewingCounselCase(data);
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "当事人信息保存失败");
        }
    };
    const saveCaseHearingLawyer = async () => {
        const { editingCaseHearingLawyer, caseHearingLawyerForm, setEditingCaseHearingLawyer, setViewingCounselCase, load } = context;
        if (!editingCaseHearingLawyer)
            return;
        const values = await caseHearingLawyerForm.validateFields();
        try {
            const { data } = await api.put(`/cases/${editingCaseHearingLawyer.id}/hearing-lawyer`, {
                hearing_lawyer: values.hearing_lawyer || "",
                comment: values.comment || "",
            });
            message.success("开庭律师已保存");
            setEditingCaseHearingLawyer(null);
            setViewingCounselCase(data);
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "开庭律师保存失败");
        }
    };
    const createCaseTask = async () => {
        const { taskCase, caseTaskCreateCase, getCaseCapability, caseTaskKind, taskForm, caseTaskMaterialFiles, setCaseTaskCreateCase, setCaseTaskMaterialFiles, viewingCounselCase } = context;
        const targetCase = taskCase || caseTaskCreateCase;
        if (!targetCase)
            return;
        if (!getCaseCapability(targetCase).can_create_case_task)
            return message.warning("当前账号没有创建该案件任务的权限");
        const taskKind: CaseTaskKind = taskCase ? "案件任务" : caseTaskKind;
        const v = await taskForm.validateFields();
        try {
            const startAt = v.start_at as Dayjs;
            const endAt = v.end_at as Dayjs;
            const { data: createdTask } = await api.post("/tasks", {
                title: v.title,
                customer: targetCase.customer,
                owner: v.owner,
                collaborators: v.collaborators || [],
                case_no: targetCase.serial_no,
                start_at: startAt.format("YYYY-MM-DDTHH:mm:ss"),
                end_at: endAt.format("YYYY-MM-DDTHH:mm:ss"),
                deadline: formatRequiredDate(endAt, "结束时间"),
                priority: v.priority || "普通",
                source: taskKind,
                task_type: "手动任务",
                description: v.description || "",
                is_vip: Boolean(v.is_vip),
            });
            if (caseTaskMaterialFiles.length) {
                const materialBody = new FormData();
                for (const file of caseTaskMaterialFiles) {
                    const source = file.originFileObj || (file as unknown as File);
                    if (source && typeof (source as Blob).arrayBuffer === "function")
                        materialBody.append("files", source);
                }
                try {
                    await api.post(`/tasks/${createdTask.id}/materials`, materialBody);
                }
                catch (error: any) {
                    message.error(error?.response?.data?.detail || `${taskKind}已创建，但任务附件上传失败`);
                    setCaseTaskCreateCase(null);
                    taskForm.resetFields();
                    setCaseTaskMaterialFiles([]);
                    if (taskCase)
                        await openCaseTasks(targetCase);
                    else if (viewingCounselCase)
                        await openCounselDetail(targetCase);
                    return;
                }
            }
            message.success(caseTaskMaterialFiles.length ? `${taskKind}及附件已创建` : `${taskKind}已创建`);
            setCaseTaskCreateCase(null);
            taskForm.resetFields();
            setCaseTaskMaterialFiles([]);
            if (taskCase)
                await openCaseTasks(targetCase);
            else if (viewingCounselCase)
                await openCounselDetail(targetCase);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || `${taskKind}创建失败`);
        }
    };
    const openPhaseChange = async (rows: CaseRow[]) => {
        const { setPhaseOptions, phaseForm, setPhaseEditing } = context;
        const selected = rows.filter(Boolean);
        if (!selected.length)
            return message.warning("请先选择案件");
        const selectedCaseTypes = Array.from(new Set(selected.map((row) => String(row.data.case_type || "").trim())));
        if (selectedCaseTypes.length > 1)
            return message.warning("不同案件类型的阶段范围不同，请分别修改");
        if (selected.some((row) => [...ARCHIVE_LOCKED_STATUSES, "已合并"].includes(row.status)))
            return message.warning("归档中、已归档或已合并案件不能修改案件阶段");
        try {
            const { data } = await api.get("/cases/phases", { params: { case_type: selectedCaseTypes[0] || "" } });
            // The endpoint has already applied the case-type relation. Re-filtering
            // here can erase valid phases for historical case-type aliases.
            const options = (Array.isArray(data?.items) ? data.items : []) as CasePhaseOption[];
            if (!options.length)
                return message.error("案件阶段加载失败");
            setPhaseOptions(options);
            const current = selected[0];
            const currentOption = options.find((option) => Number(current.data.case_phase_id) === option.id || option.canonical_name === current.status || option.name === current.status);
            phaseForm.resetFields();
            phaseForm.setFieldsValue({ case_phase_id: currentOption?.id || options[0].id, comment: "" });
            setPhaseEditing(selected);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件阶段加载失败");
        }
    };
    const submitCompanyScheduleCourtInfo = async () => {
        const { companyScheduleCourtInfo, companyScheduleCourtInfoForm, cancelCompanyScheduleCourtInfo, load } = context;
        if (!companyScheduleCourtInfo)
            return;
        try {
            const values = await companyScheduleCourtInfoForm.validateFields();
            const readCourtField = (name: string) => {
                const formValue = values[name];
                if (typeof formValue === "string" && formValue.trim())
                    return formValue;
                const inputValue = (document.querySelector(`.ant-modal-root input#${name}`) as HTMLInputElement | null)?.value || "";
                return inputValue || formValue || "";
            };
            const courtValue = readCourtField("court");
            const caseNoValue = readCourtField("case_no");
            const courtroomValue = readCourtField("courtroom");
            const judgeValue = readCourtField("judge");
            const clerkValue = readCourtField("clerk");
            const firstInstance = companyScheduleCourtInfo.level === "first";
            const levelLabel = getCompanyScheduleCourtLevels().find(([key]) => key === companyScheduleCourtInfo.level)?.[1] || "";
            const data = companyScheduleCourtInfo.row.data || {};
            const levelPrefix = `${companyScheduleCourtInfo.level}_court`;
            const payload: Record<string, unknown> = {
                first_instance_court: firstInstance ? values.court || "" : data.first_instance_court || "",
                first_instance_case_no: firstInstance ? values.case_no || "" : data.first_instance_case_no || "",
                second_instance_court: companyScheduleCourtInfo.level === "second" ? values.court || "" : data.second_instance_court || "",
                second_instance_case_no: companyScheduleCourtInfo.level === "second" ? values.case_no || "" : data.second_instance_case_no || "",
                execution_court_name: companyScheduleCourtInfo.level === "execution" ? courtValue : data.execution_court_name || "",
                execution_court_case_no: companyScheduleCourtInfo.level === "execution" ? caseNoValue : data.execution_court_case_no || "",
                retrial_court_name: companyScheduleCourtInfo.level === "retrial" ? courtValue : data.retrial_court_name || "",
                retrial_court_case_no: companyScheduleCourtInfo.level === "retrial" ? caseNoValue : data.retrial_court_case_no || "",
                courtroom: firstInstance ? courtroomValue : data.courtroom || "",
                judge: firstInstance ? judgeValue : data.judge || "",
                clerk: firstInstance ? clerkValue : data.clerk || "",
                judgment_date: firstInstance ? values.judgment_date?.format("YYYY-MM-DD") || null : data.judgment_date || null,
                [`${levelPrefix}_name`]: courtValue,
                [`${levelPrefix}_case_no`]: caseNoValue,
                [`${levelPrefix}_courtroom`]: courtroomValue,
                [`${levelPrefix}_judge`]: judgeValue,
                [`${levelPrefix}_clerk`]: clerkValue,
                [`${levelPrefix}_filing_date`]: values.filing_date?.format("YYYY-MM-DD") || null,
                [`${levelPrefix}_hearing_date`]: values.hearing_date?.format("YYYY-MM-DD HH:mm:ss") || null,
                [`${levelPrefix}_judgment_date`]: values.judgment_date?.format("YYYY-MM-DD") || null,
                comment: `修改${levelLabel}法院信息`,
            };
            const { data: updatedCase } = await api.put(`/cases/${companyScheduleCourtInfo.row.id}/court-info`, payload);
            message.success(`${levelLabel}法院信息已更新`);
            cancelCompanyScheduleCourtInfo();
            await openCounselDetail(updatedCase);
            void load();
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "法院信息更新失败");
        }
    };
    const saveProgress = async () => {
        const { progressEditing, progressForm, setProgressEditing, load } = context;
        if (!progressEditing)
            return;
        const v = await progressForm.validateFields();
        try {
            await api.post(`/cases/${progressEditing.id}/progress`, buildCaseProgressPayload(v));
            message.success("案件进展已保存，阶段已按要素自动更新");
            setProgressEditing(null);
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件进展保存失败");
        }
    };
    const savePhaseChange = async () => {
        const { phaseEditing, phaseForm, phaseOptions, setPhaseEditing, setSelectedCaseKeys, isCaseDetailView, viewingCounselCase, load } = context;
        if (!phaseEditing?.length)
            return;
        const values = await phaseForm.validateFields();
        const option = phaseOptions.find((item) => item.id === Number(values.case_phase_id));
        if (!option)
            return message.error("案件阶段不存在或已停用");
        try {
            const changedCases = phaseEditing;
            const { data } = await api.post("/cases/phase-change", buildCasePhaseChangePayload(changedCases.map((row) => row.serial_no), option.id, option.name, values.comment));
            message.success("修改成功！");
            setPhaseEditing(null);
            phaseForm.resetFields();
            setSelectedCaseKeys([]);
            const currentDetailChanged = isCaseDetailView && viewingCounselCase
                && changedCases.some((row) => row.id === viewingCounselCase.id);
            if (currentDetailChanged) {
                const updatedDetail = (Array.isArray(data?.items) ? data.items : [])
                    .find((row: CaseRow) => row.id === viewingCounselCase.id) || viewingCounselCase;
                await openCounselDetail(updatedDetail);
            }
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "修改失败！");
        }
    };
    const saveExecutionStatus = async () => {
        const { executionStatusEditing, executionStatusForm, setExecutionStatusEditing, setSelectedCaseKeys, load } = context;
        if (!executionStatusEditing?.length)
            return;
        const values = await executionStatusForm.validateFields();
        try {
            await api.post("/cases/execution-status", buildCaseExecutionStatusPayload(executionStatusEditing.map((row) => row.serial_no), values.execution_status, values.comment));
            message.success("修改成功！");
            setExecutionStatusEditing(null);
            executionStatusForm.resetFields();
            setSelectedCaseKeys([]);
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "修改失败！");
        }
    };
    const downloadCaseExport = async (path: string, filename: string, ids: Key[], emptyMessage: string) => {
        const selectedIds = ids.map(Number).filter((id) => Number.isInteger(id) && id > 0);
        if (!selectedIds.length)
            return message.warning(emptyMessage);
        try {
            const response = await api.get(path, { params: { ids: selectedIds.join(",") }, responseType: "blob" });
            const url = URL.createObjectURL(response.data);
            const link = document.createElement("a");
            link.href = url;
            link.download = filename;
            link.click();
            URL.revokeObjectURL(url);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件文件导出失败");
        }
    };
    const openSelectedScheduleHearing = async () => {
        const { selectedSpecialRow, resolveVisibleCase, openHearing } = context;
        if (!selectedSpecialRow)
            return message.warning("请先选择案件");
        const target = await resolveVisibleCase({ case: selectedSpecialRow.case, case_record_id: selectedSpecialRow.case_record_id, case_no: selectedSpecialRow.case_no });
        if (target)
            openHearing(target);
    };
    return { saveCreateDefendants, advanceCreateStep, saveLitigants, finishCreateFlow, assign, createHearing, openArchive, closeCase, archive, reviewArchive, reviewCaseCreation, deleteCompanyCase, reviewUnarchive, openCaseTasks, openCounselDetail, duplicateCase, submitCaseMerge, submitNotaryInfo, openCaseClueWorkspace, saveCaseClueEvidence, submitClueConversion, openSpecialCaseDetail, openSpecialCaseTasks, createCounselReminder, saveCaseEvent, createCounselLog, submitCounselBatchUpdate, saveCounselBasic, ensureCaseCustomerOption, openNormalCaseEdit, saveNormalCaseBasic, openArbitrationBasicEdit, saveArbitrationBasic, saveCriminalMaintenance, saveCaseParty, saveCaseLitigants, saveCaseHearingLawyer, createCaseTask, openPhaseChange, submitCompanyScheduleCourtInfo, saveProgress, savePhaseChange, saveExecutionStatus, downloadCaseExport, openSelectedScheduleHearing };
}
