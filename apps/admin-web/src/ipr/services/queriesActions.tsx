import { message } from "antd";
import { api } from "../../api";
import { rememberCustomerDetailTarget, resolveCustomerDetailTarget, } from "../../customerDetailNavigation";
import { getIprApiErrorMessage } from "../../iprCaseDetailParity.mjs";
import { IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE, isIprLawsuit, lawsuitFeeFromRecord } from "../constants";
import type { AnnualFee, AssistedFee, Attachment, CpcApplication, IprBusinessLog, IprCaseContact, IprCaseCustomer, IprCaseEvent, IprCaseTask, IprDetailPagePayload, IprDetailPageState, IprHistoryItem, IprLawFirm, IprLawsuitCourt, IprLawsuitFee, IprLawsuitParty, IprOperationLog, IprRecord, IprReminderEventOption, IprReminderType, IprWarning, IprWarningRule, LegacyIprCaseListItem, ReminderEventType } from "../types";
/** ipr queries operations; dependencies are read when each operation runs. */
export interface IprQueriesDependencies {
    readonly page: number;
    readonly pageSize: number;
    readonly keyword: string;
    readonly reminderTypeId: number | null;
    readonly setLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly kind: "" | "商标" | "专利";
    readonly caseCategoryFilter: "" | "litigation" | "non_litigation";
    readonly reviewView: boolean;
    readonly roleView: {
        roleView: string;
        label: string;
    };
    readonly annualFeeMonitoringFilter: "" | "true" | "false";
    readonly setItems: React.Dispatch<React.SetStateAction<IprRecord[]>>;
    readonly setTotal: React.Dispatch<React.SetStateAction<number>>;
    readonly setPage: React.Dispatch<React.SetStateAction<number>>;
    readonly setPageSize: React.Dispatch<React.SetStateAction<number>>;
    readonly setPages: React.Dispatch<React.SetStateAction<number>>;
    readonly legacyHistoryKeyword: string;
    readonly setLegacyHistoryLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setLegacyHistoryItems: React.Dispatch<React.SetStateAction<LegacyIprCaseListItem[]>>;
    readonly setLegacyHistoryTotal: React.Dispatch<React.SetStateAction<number>>;
    readonly setReminderTypeLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly canManageReminderTypes: boolean;
    readonly setReminderTypes: React.Dispatch<React.SetStateAction<IprReminderType[]>>;
    readonly setReminderTypeEventOptions: React.Dispatch<React.SetStateAction<IprReminderEventOption[]>>;
    readonly setLawsuitCourts: React.Dispatch<React.SetStateAction<IprLawsuitCourt[]>>;
    readonly setLawsuitParties: React.Dispatch<React.SetStateAction<IprLawsuitParty[]>>;
    readonly setLawsuitFees: React.Dispatch<React.SetStateAction<IprLawsuitFee[]>>;
    readonly remindersPageState: IprDetailPageState;
    readonly setIprCaseEvents: React.Dispatch<React.SetStateAction<IprCaseEvent[]>>;
    readonly setRemindersPageState: React.Dispatch<React.SetStateAction<IprDetailPageState>>;
    readonly clearIprSectionError: (section: "files" | "logs" | "reminders" | "tasks" | "assistedFees" | "annualFees") => void;
    readonly setIprSectionError: (section: "files" | "logs" | "reminders" | "tasks" | "assistedFees" | "annualFees", error: unknown) => void;
    readonly iprTasksPageState: IprDetailPageState;
    readonly setIprCaseTasks: React.Dispatch<React.SetStateAction<IprCaseTask[]>>;
    readonly setIprTasksPageState: React.Dispatch<React.SetStateAction<IprDetailPageState>>;
    readonly setReminderEventTypes: React.Dispatch<React.SetStateAction<ReminderEventType[]>>;
    readonly setSuppressedIds: React.Dispatch<React.SetStateAction<number[]>>;
    readonly setCaseLawFirms: React.Dispatch<React.SetStateAction<IprLawFirm[]>>;
    readonly setCaseCustomers: React.Dispatch<React.SetStateAction<IprCaseCustomer[]>>;
    readonly setCaseContacts: React.Dispatch<React.SetStateAction<IprCaseContact[]>>;
    readonly setIprBusinessLogs: React.Dispatch<React.SetStateAction<IprBusinessLog[]>>;
    readonly setIprOperationLogs: React.Dispatch<React.SetStateAction<IprOperationLog[]>>;
    readonly setIprHistory: React.Dispatch<React.SetStateAction<IprHistoryItem[]>>;
    readonly onNavigate: ((route: string) => void) | undefined;
    readonly activeIprDetailId: React.RefObject<number | null>;
    readonly cpcHistoryRequest: React.RefObject<number>;
    readonly setDetail: React.Dispatch<React.SetStateAction<IprRecord | null>>;
    readonly setIprDetailTab: React.Dispatch<React.SetStateAction<string>>;
    readonly setAttachments: React.Dispatch<React.SetStateAction<Attachment[]>>;
    readonly setCpcApplications: React.Dispatch<React.SetStateAction<CpcApplication[]>>;
    readonly setCpcApplicationsError: React.Dispatch<React.SetStateAction<string>>;
    readonly setAssistedFees: React.Dispatch<React.SetStateAction<AssistedFee[]>>;
    readonly setCanManageAssistedFees: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setAnnualFees: React.Dispatch<React.SetStateAction<AnnualFee[]>>;
    readonly setAnnualFeesCanManage: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setAnnualFeeYearFilter: React.Dispatch<React.SetStateAction<number | undefined>>;
    readonly setFilesPageState: React.Dispatch<React.SetStateAction<IprDetailPageState>>;
    readonly setAssistedFeesPageState: React.Dispatch<React.SetStateAction<IprDetailPageState>>;
    readonly setAnnualFeesPageState: React.Dispatch<React.SetStateAction<IprDetailPageState>>;
    readonly setIprSectionErrors: React.Dispatch<React.SetStateAction<{
        files: string;
        logs: string;
        reminders: string;
        tasks: string;
        assistedFees: string;
        annualFees: string;
    }>>;
    readonly loadIprFiles: (caseId: number, nextPage?: number, nextPageSize?: number) => Promise<void>;
    readonly loadCpcApplications: (caseId: number) => Promise<void>;
    readonly loadAssistedFees: (caseId: number, nextPage?: number, nextPageSize?: number) => Promise<void>;
    readonly loadAnnualFees: (caseId: number, nextPage?: number, nextPageSize?: number, nextFeeYear?: number | undefined) => Promise<void>;
    readonly setWarningRulesLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setWarningRules: React.Dispatch<React.SetStateAction<IprWarningRule[]>>;
    readonly warningPage: number;
    readonly setWarningLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly warningStatus: "" | "未读" | "已读" | "已处理";
    readonly warningCaseKind: "" | "商标" | "专利";
    readonly setWarnings: React.Dispatch<React.SetStateAction<IprWarning[]>>;
    readonly setWarningTotal: React.Dispatch<React.SetStateAction<number>>;
    readonly setWarningUnread: React.Dispatch<React.SetStateAction<number>>;
    readonly setWarningPage: React.Dispatch<React.SetStateAction<number>>;
    readonly profile: {
        role?: string | undefined;
        username?: string | undefined;
    };
    readonly markWarningRead: (warning: IprWarning) => Promise<void>;
}
export function createIprQueriesActions(context: IprQueriesDependencies) {
    const load = async (nextPage = context.page, nextPageSize = context.pageSize, nextKeyword = context.keyword, nextReminderTypeId = context.reminderTypeId) => {
        const { page, pageSize, keyword, reminderTypeId, setLoading, kind, caseCategoryFilter, reviewView, roleView, annualFeeMonitoringFilter, setItems, setTotal, setPage, setPageSize, setPages } = context;
        setLoading(true);
        try {
            const { data } = await api.get("/ipr/cases", {
                params: {
                    case_kind: kind,
                    case_category: caseCategoryFilter || undefined,
                    record_status: reviewView ? "待立案审核" : "",
                    role_view: roleView?.roleView,
                    keyword: nextKeyword,
                    annual_fee_monitoring: annualFeeMonitoringFilter || undefined,
                    reminder_type_id: nextReminderTypeId || undefined,
                    page: nextPage,
                    page_size: nextPageSize,
                },
            });
            setItems(data.items || []);
            setTotal(data.total);
            setPage(data.page ?? nextPage);
            setPageSize(data.page_size ?? nextPageSize);
            setPages(data.pages ??
                (data.total ? Math.ceil(data.total / nextPageSize) : 0));
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "知识产权案件加载失败");
        }
        finally {
            setLoading(false);
        }
    };
    const loadLegacyHistory = async (nextKeyword = context.legacyHistoryKeyword) => {
        const { legacyHistoryKeyword, setLegacyHistoryLoading, setLegacyHistoryItems, setLegacyHistoryTotal } = context;
        setLegacyHistoryLoading(true);
        try {
            const { data } = await api.get<{
                items: LegacyIprCaseListItem[];
                total: number;
            }>("/legacy-ipr-history/cases", {
                params: { keyword: nextKeyword, page: 1, page_size: 100 },
            });
            setLegacyHistoryItems(data.items || []);
            setLegacyHistoryTotal(data.total || 0);
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail ||
                "Historical IPR cases are unavailable");
        }
        finally {
            setLegacyHistoryLoading(false);
        }
    };
    const loadReminderTypes = async () => {
        const { setReminderTypeLoading, canManageReminderTypes, setReminderTypes } = context;
        setReminderTypeLoading(true);
        try {
            const { data } = await api.get<{
                items: IprReminderType[];
            }>("/ipr/reminder-types", {
                params: {
                    include_inactive: canManageReminderTypes || undefined,
                },
            });
            setReminderTypes(data.items || []);
        }
        catch (error: any) {
            setReminderTypes([]);
            message.error(error?.response?.data?.detail || "案件提醒类型加载失败");
        }
        finally {
            setReminderTypeLoading(false);
        }
    };
    const loadReminderEventTypes = async () => {
        const { setReminderTypeEventOptions } = context;
        try {
            const { data } = await api.get<{
                items: IprReminderEventOption[];
            }>("/ipr/reminder-event-types");
            setReminderTypeEventOptions(data.items || []);
        }
        catch (error: any) {
            setReminderTypeEventOptions([]);
            message.error(error?.response?.data?.detail || "案件提醒事件类型加载失败");
        }
    };
    const loadLawsuitManagement = async (caseId: number) => {
        const { setLawsuitCourts, setLawsuitParties, setLawsuitFees } = context;
        const results = await Promise.allSettled([
            api.get<{
                items: IprLawsuitCourt[];
            }>(`/ipr/lawsuit/cases/${caseId}/courts`),
            api.get<{
                items: IprLawsuitParty[];
            }>(`/ipr/lawsuit/cases/${caseId}/parties`),
            api.get<IprDetailPagePayload<IprRecord>>(`/ipr/cases/${caseId}/fees`),
        ]);
        const [courtsResult, partiesResult, feesResult] = results;
        if (courtsResult.status === "fulfilled")
            setLawsuitCourts(courtsResult.value.data.items || []);
        else
            message.error((courtsResult.reason as any)?.response?.data?.detail ||
                "诉讼法院信息加载失败");
        if (partiesResult.status === "fulfilled")
            setLawsuitParties(partiesResult.value.data.items || []);
        else
            message.error((partiesResult.reason as any)?.response?.data?.detail ||
                "诉讼当事人加载失败");
        if (feesResult.status === "fulfilled")
            setLawsuitFees((feesResult.value.data.items || []).map(lawsuitFeeFromRecord));
        else
            message.error((feesResult.reason as any)?.response?.data?.detail ||
                "诉讼费用加载失败");
    };
    const loadIprCaseEvents = async (caseId: number, nextPage = context.remindersPageState.page, nextPageSize = context.remindersPageState.pageSize) => {
        const { remindersPageState, setIprCaseEvents, setRemindersPageState, clearIprSectionError, setIprSectionError } = context;
        try {
            const { data } = await api.get<IprDetailPagePayload<IprCaseEvent>>(`/ipr/cases/${caseId}/events`, {
                params: { page: nextPage, page_size: nextPageSize },
            });
            setIprCaseEvents(data.items || []);
            setRemindersPageState({
                page: data.page ?? nextPage,
                pageSize: data.page_size ?? nextPageSize,
                total: data.total ?? data.items?.length ?? 0,
                pages: data.pages ?? 0,
            });
            clearIprSectionError("reminders");
        }
        catch (error) {
            setIprSectionError("reminders", error);
        }
    };
    const loadIprCaseTasks = async (caseId: number, nextPage = context.iprTasksPageState.page, nextPageSize = context.iprTasksPageState.pageSize) => {
        const { iprTasksPageState, setIprCaseTasks, setIprTasksPageState, clearIprSectionError, setIprSectionError } = context;
        try {
            const { data } = await api.get<IprDetailPagePayload<IprCaseTask>>(`/ipr/cases/${caseId}/tasks`, {
                params: { page: nextPage, page_size: nextPageSize },
            });
            setIprCaseTasks(data.items || []);
            setIprTasksPageState({
                page: data.page ?? nextPage,
                pageSize: data.page_size ?? nextPageSize,
                total: data.total ?? data.items?.length ?? 0,
                pages: data.pages ?? 0,
            });
            clearIprSectionError("tasks");
        }
        catch (error) {
            setIprSectionError("tasks", error);
        }
    };
    const loadReminderSuppressions = async (caseId: number) => {
        const { setReminderEventTypes, setSuppressedIds } = context;
        try {
            const { data } = await api.get<{
                event_types: ReminderEventType[];
                suppressed_ids: number[];
            }>(`/ipr/cases/${caseId}/reminder-suppressions`);
            setReminderEventTypes(data.event_types || []);
            setSuppressedIds(data.suppressed_ids || []);
        }
        catch {
            setReminderEventTypes([]);
            setSuppressedIds([]);
        }
    };
    const loadCaseLawFirms = async (caseId: number) => {
        const { setCaseLawFirms } = context;
        try {
            const { data } = await api.get<{
                items: IprLawFirm[];
            }>(`/ipr/cases/${caseId}/law-firms`);
            setCaseLawFirms(data.items || []);
        }
        catch {
            setCaseLawFirms([]);
        }
    };
    const loadCaseCustomers = async (caseId: number) => {
        const { setCaseCustomers } = context;
        try {
            const { data } = await api.get<{
                items: IprCaseCustomer[];
            }>(`/ipr/cases/${caseId}/customers`);
            setCaseCustomers(data.items || []);
        }
        catch {
            setCaseCustomers([]);
        }
    };
    const loadCaseContacts = async (caseId: number) => {
        const { setCaseContacts } = context;
        try {
            const { data } = await api.get<{
                items: IprCaseContact[];
            }>(`/ipr/cases/${caseId}/customer-contacts`);
            setCaseContacts(data.items || []);
        }
        catch {
            setCaseContacts([]);
        }
    };
    const loadIprLogs = async (caseId: number) => {
        const { setIprBusinessLogs, setIprOperationLogs, clearIprSectionError, setIprSectionError } = context;
        try {
            const { data } = await api.get<{
                business_logs: IprBusinessLog[];
                operation_logs: IprOperationLog[];
            }>(`/ipr/cases/${caseId}/logs`);
            setIprBusinessLogs(data.business_logs || []);
            setIprOperationLogs(data.operation_logs || []);
            clearIprSectionError("logs");
        }
        catch (error) {
            setIprSectionError("logs", error);
        }
    };
    const loadIprHistory = async (caseId: number) => {
        const { setIprHistory } = context;
        try {
            const { data } = await api.get<{
                items: IprHistoryItem[];
            }>(`/records/${caseId}/history`);
            setIprHistory(data.items || []);
        }
        catch (e: any) {
            setIprHistory([]);
            message.error(e?.response?.data?.detail || "案件事项记录加载失败");
        }
    };
    const openLinkedCaseCustomer = async (customer: IprCaseCustomer) => {
        const { onNavigate } = context;
        try {
            const target = await resolveCustomerDetailTarget({
                id: customer.customer_id,
                serial_no: customer.customer_no,
                title: customer.name,
            });
            if (!target) {
                message.warning("未找到关联客户或当前账号无权查看");
                return;
            }
            rememberCustomerDetailTarget(target);
            onNavigate?.("customer-company");
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "关联客户加载失败");
        }
    };
    const openLegacyIprCurrentCustomer = async (customerRecordId: number) => {
        const { onNavigate } = context;
        try {
            const target = await resolveCustomerDetailTarget({
                id: customerRecordId,
            });
            if (!target) {
                message.warning("关联客户不存在或无权查看");
                return;
            }
            rememberCustomerDetailTarget(target);
            onNavigate?.("customer-company");
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "关联客户加载失败");
        }
    };
    const openDetail = async (record: IprRecord) => {
        const { activeIprDetailId, cpcHistoryRequest, setDetail, setIprDetailTab, setLawsuitCourts, setLawsuitParties, setLawsuitFees, setAttachments, setIprBusinessLogs, setIprOperationLogs, setCpcApplications, setCpcApplicationsError, setAssistedFees, setCanManageAssistedFees, setAnnualFees, setAnnualFeesCanManage, setAnnualFeeYearFilter, setIprCaseEvents, setIprCaseTasks, setFilesPageState, setRemindersPageState, setIprTasksPageState, setAssistedFeesPageState, setAnnualFeesPageState, setIprSectionErrors, loadIprFiles, loadCpcApplications, loadAssistedFees, loadAnnualFees } = context;
        activeIprDetailId.current = record.id;
        cpcHistoryRequest.current += 1;
        setDetail(record);
        setIprDetailTab("files");
        setLawsuitCourts([]);
        setLawsuitParties([]);
        setLawsuitFees([]);
        setAttachments([]);
        setIprBusinessLogs([]);
        setIprOperationLogs([]);
        setCpcApplications([]);
        setCpcApplicationsError("");
        setAssistedFees([]);
        setCanManageAssistedFees(false);
        setAnnualFees([]);
        setAnnualFeesCanManage(false);
        setAnnualFeeYearFilter(undefined);
        setIprCaseEvents([]);
        setIprCaseTasks([]);
        setFilesPageState({
            page: IPR_DETAIL_DEFAULT_PAGE,
            pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
            total: 0,
            pages: 0,
        });
        setRemindersPageState({
            page: IPR_DETAIL_DEFAULT_PAGE,
            pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
            total: 0,
            pages: 0,
        });
        setIprTasksPageState({
            page: IPR_DETAIL_DEFAULT_PAGE,
            pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
            total: 0,
            pages: 0,
        });
        setAssistedFeesPageState({
            page: IPR_DETAIL_DEFAULT_PAGE,
            pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
            total: 0,
            pages: 0,
        });
        setAnnualFeesPageState({
            page: IPR_DETAIL_DEFAULT_PAGE,
            pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
            total: 0,
            pages: 0,
        });
        setIprSectionErrors({
            files: "",
            logs: "",
            reminders: "",
            tasks: "",
            assistedFees: "",
            annualFees: "",
        });
        try {
            await Promise.all([
                loadIprFiles(record.id, IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE),
                loadCaseLawFirms(record.id),
                loadCaseCustomers(record.id),
                loadCaseContacts(record.id),
                loadIprLogs(record.id),
                loadIprHistory(record.id),
                ...(record.data?.case_kind === "专利"
                    ? [loadCpcApplications(record.id)]
                    : []),
                loadAssistedFees(record.id, IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE),
                loadAnnualFees(record.id, IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE, undefined),
                loadIprCaseEvents(record.id, IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE),
                loadIprCaseTasks(record.id, IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE),
                loadReminderSuppressions(record.id),
                ...(isIprLawsuit(record)
                    ? [loadLawsuitManagement(record.id)]
                    : []),
            ]);
        }
        catch (error) {
            message.error(getIprApiErrorMessage(error, "案件详情加载失败"));
        }
    };
    const exportExcel = async () => {
        const { kind, reviewView, roleView, keyword, annualFeeMonitoringFilter, reminderTypeId } = context;
        try {
            const response = await api.get("/ipr/cases/export/excel", {
                params: {
                    case_kind: kind,
                    record_status: reviewView ? "待立案审核" : "",
                    role_view: roleView?.roleView,
                    keyword,
                    annual_fee_monitoring: annualFeeMonitoringFilter || undefined,
                    reminder_type_id: reminderTypeId || undefined,
                },
                responseType: "blob",
            });
            const url = URL.createObjectURL(response.data);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `${roleView?.label || kind || "知识产权"}案件清单.xls`;
            anchor.click();
            URL.revokeObjectURL(url);
            message.success("案件清单已导出");
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "案件清单导出失败");
        }
    };
    const loadWarningRules = async () => {
        const { setWarningRulesLoading, setWarningRules } = context;
        setWarningRulesLoading(true);
        try {
            const { data } = await api.get<{
                items: IprWarningRule[];
            }>("/ipr/warning-rules");
            setWarningRules(data.items || []);
        }
        catch (error: any) {
            setWarningRules([]);
            message.error(error?.response?.data?.detail || "预警规则加载失败");
        }
        finally {
            setWarningRulesLoading(false);
        }
    };
    const loadWarnings = async (nextPage = context.warningPage) => {
        const { warningPage, setWarningLoading, warningStatus, warningCaseKind, setWarnings, setWarningTotal, setWarningUnread, setWarningPage } = context;
        setWarningLoading(true);
        try {
            const { data } = await api.get<{
                items: IprWarning[];
                total: number;
                unread: number;
                page?: number;
            }>("/ipr/warnings", {
                params: {
                    status: warningStatus || undefined,
                    case_kind: warningCaseKind || undefined,
                    page: nextPage,
                    page_size: 15,
                },
            });
            setWarnings(data.items || []);
            setWarningTotal(data.total || 0);
            setWarningUnread(data.unread || 0);
            setWarningPage(data.page || nextPage);
        }
        catch (error: any) {
            setWarnings([]);
            message.error(error?.response?.data?.detail || "案件预警加载失败");
        }
        finally {
            setWarningLoading(false);
        }
    };
    const openWarningCase = async (warning: IprWarning) => {
        const { profile, markWarningRead } = context;
        if (!warning.is_read &&
            (profile.role === "admin" ||
                warning.recipient === profile.username))
            await markWarningRead(warning);
        try {
            const { data } = await api.get<IprRecord>(`/ipr/cases/${warning.case_id}`);
            await openDetail(data);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail ||
                "关联知识产权案件不可查看或已不存在");
        }
    };
    const openRebootCase = async (caseId: number) => {
        try {
            const { data } = await api.get<IprRecord>(`/ipr/cases/${caseId}`);
            await openDetail(data);
        }
        catch {
            message.error("关联案件不可查看或已不存在");
        }
    };
    return { load, loadLegacyHistory, loadReminderTypes, loadReminderEventTypes, loadLawsuitManagement, loadIprCaseEvents, loadIprCaseTasks, loadReminderSuppressions, loadCaseLawFirms, loadCaseCustomers, loadCaseContacts, loadIprLogs, loadIprHistory, openLinkedCaseCustomer, openLegacyIprCurrentCustomer, openDetail, exportExcel, loadWarningRules, loadWarnings, openWarningCase, openRebootCase };
}
