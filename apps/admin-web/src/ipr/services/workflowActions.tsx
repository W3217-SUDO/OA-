import { message } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import dayjs from "dayjs";
import { api } from "../../api";
import { formatRequiredDate } from "../../formSafety";
import { buildIprCaseContactPayload, buildIprCaseCustomerPayload, buildIprCaseLawFirmPayload, buildIprDeadlineFromOffset, getIprApiErrorMessage, getIprCaseCustomerValidationError } from "../../iprCaseDetailParity.mjs";
import { buildIprCaseActionPayload, getIprCaseActionErrorMessage, getIprCaseActionValidationError, normalizeIprCaseActionResponse, } from "../../iprCaseWorkflowParity.mjs";
import { IPR_LAWSUIT_FIELDS } from "../constants";
import type { CustomerContact, IprBatchCreateError, IprCaseCustomer, IprCaseCustomerCandidate, IprCaseEvent, IprLawFirmCandidate, IprLawsuitCourt, IprLawsuitParty, IprRecord, IprReminderType, IprWarning, IprWarningRule } from "../types";
/** ipr workflow operations; dependencies are read when each operation runs. */
export interface IprWorkflowDependencies {
    readonly reminderTypeForm: FormInstance<any>;
    readonly editingReminderType: IprReminderType | null;
    readonly setReminderTypeEditorOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setEditingReminderType: React.Dispatch<React.SetStateAction<IprReminderType | null>>;
    readonly loadReminderTypes: () => Promise<void>;
    readonly deadlineOffsetForm: FormInstance<any>;
    readonly form: FormInstance<any>;
    readonly setDeadlineOffsetOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly editing: IprRecord | null;
    readonly setCreateOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setEditing: React.Dispatch<React.SetStateAction<IprRecord | null>>;
    readonly load: (nextPage?: number, nextPageSize?: number, nextKeyword?: string, nextReminderTypeId?: number | null) => Promise<void>;
    readonly detail: IprRecord | null;
    readonly courtInfoForm: FormInstance<any>;
    readonly setCourtInfoOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setDetail: React.Dispatch<React.SetStateAction<IprRecord | null>>;
    readonly lawsuitCourtForm: FormInstance<any>;
    readonly editingLawsuitCourt: IprLawsuitCourt | null;
    readonly setLawsuitCourtOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setEditingLawsuitCourt: React.Dispatch<React.SetStateAction<IprLawsuitCourt | null>>;
    readonly loadLawsuitManagement: (caseId: number) => Promise<void>;
    readonly lawsuitPartyForm: FormInstance<any>;
    readonly editingLawsuitParty: IprLawsuitParty | null;
    readonly setLawsuitPartyOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setEditingLawsuitParty: React.Dispatch<React.SetStateAction<IprLawsuitParty | null>>;
    readonly iprBatchCreateForm: FormInstance<any>;
    readonly setIprBatchCreateErrors: React.Dispatch<React.SetStateAction<IprBatchCreateError[]>>;
    readonly pageSize: number;
    readonly setIprBatchCreateOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setIprRebootPreview: React.Dispatch<React.SetStateAction<{
        source_case_id: number;
        source_case_no: string;
        source_title: string;
        source_status: string;
        next_serial_no: string;
    } | null>>;
    readonly iprRebootForm: FormInstance<any>;
    readonly setIprRebootOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly iprRebootPreview: {
        source_case_id: number;
        source_case_no: string;
        source_title: string;
        source_status: string;
        next_serial_no: string;
    } | null;
    readonly openDetail: (record: IprRecord) => Promise<void>;
    readonly setLawFirmCandidates: React.Dispatch<React.SetStateAction<IprLawFirmCandidate[]>>;
    readonly setLawFirmSelection: React.Dispatch<React.SetStateAction<number[]>>;
    readonly setLawFirmOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly lawFirmSelection: number[];
    readonly loadCaseLawFirms: (caseId: number) => Promise<void>;
    readonly iprLogForm: FormInstance<any>;
    readonly setIprLogOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly loadIprLogs: (caseId: number) => Promise<void>;
    readonly setCustomerCandidates: React.Dispatch<React.SetStateAction<IprCaseCustomerCandidate[]>>;
    readonly setCustomerSelection: React.Dispatch<React.SetStateAction<number[]>>;
    readonly setPrimaryCustomerId: React.Dispatch<React.SetStateAction<number | null>>;
    readonly setCustomerOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly customerSelection: number[];
    readonly primaryCustomerId: number | null;
    readonly loadCaseCustomers: (caseId: number) => Promise<void>;
    readonly loadCaseContacts: (caseId: number) => Promise<void>;
    readonly setContactCustomer: React.Dispatch<React.SetStateAction<IprCaseCustomer | null>>;
    readonly setContactCandidates: React.Dispatch<React.SetStateAction<CustomerContact[]>>;
    readonly setDocumentContactIds: React.Dispatch<React.SetStateAction<string[]>>;
    readonly setTechnologyContactIds: React.Dispatch<React.SetStateAction<string[]>>;
    readonly setContactOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly contactCustomer: IprCaseCustomer | null;
    readonly documentContactIds: string[];
    readonly technologyContactIds: string[];
    readonly iprEventForm: FormInstance<any>;
    readonly editingIprEvent: IprCaseEvent | null;
    readonly setIprEventOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setEditingIprEvent: React.Dispatch<React.SetStateAction<IprCaseEvent | null>>;
    readonly loadIprCaseEvents: (caseId: number, nextPage?: number, nextPageSize?: number) => Promise<void>;
    readonly iprTaskForm: FormInstance<any>;
    readonly setIprTaskOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly loadIprCaseTasks: (caseId: number, nextPage?: number, nextPageSize?: number) => Promise<void>;
    readonly suppressedIds: number[];
    readonly setSuppressionOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly loadReminderSuppressions: (caseId: number) => Promise<void>;
    readonly maintenanceTarget: IprRecord | null;
    readonly maintenanceForm: FormInstance<any>;
    readonly setMaintenanceTarget: React.Dispatch<React.SetStateAction<IprRecord | null>>;
    readonly iprMaintenanceForm: FormInstance<any>;
    readonly selectedIprCaseIds: number[];
    readonly setIprMaintenanceOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setSelectedIprCaseIds: React.Dispatch<React.SetStateAction<number[]>>;
    readonly profile: {
        role?: string | undefined;
        username?: string | undefined;
    };
    readonly loadWarnings: (nextPage?: number) => Promise<void>;
    readonly warningRuleForm: FormInstance<any>;
    readonly editingWarningRule: IprWarningRule | null;
    readonly setWarningRuleEditorOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly loadWarningRules: () => Promise<void>;
    readonly processingWarning: IprWarning | null;
    readonly warningProcessForm: FormInstance<any>;
    readonly setProcessingWarning: React.Dispatch<React.SetStateAction<IprWarning | null>>;
}
export function createIprWorkflowActions(context: IprWorkflowDependencies) {
    const saveReminderType = async () => {
        const { reminderTypeForm, editingReminderType, setReminderTypeEditorOpen, setEditingReminderType, loadReminderTypes } = context;
        try {
            const values = await reminderTypeForm.validateFields();
            const payload = {
                name: String(values.name || "").trim(),
                query_object: {
                    case_kind: values.case_kind || "",
                    case_type: String(values.case_type || "").trim(),
                    case_phase: String(values.case_phase || "").trim(),
                    statuses: values.statuses || [],
                    event_type_ids: values.event_type_ids || [],
                    annual_fee_monitoring: values.annual_fee_monitoring ?? null,
                    deadline_from: values.deadline_from
                        ? formatRequiredDate(values.deadline_from, "起始期限")
                        : null,
                    deadline_to: values.deadline_to
                        ? formatRequiredDate(values.deadline_to, "结束期限")
                        : null,
                    deadline_within_days: values.deadline_within_days ?? null,
                },
                is_default: !!values.is_default,
                is_active: !!values.is_active,
                sort_order: Number(values.sort_order || 0),
            };
            if (editingReminderType) {
                await api.patch(`/ipr/reminder-types/${editingReminderType.id}`, payload);
                message.success("案件提醒类型已更新");
            }
            else {
                await api.post("/ipr/reminder-types", payload);
                message.success("案件提醒类型已创建");
            }
            setReminderTypeEditorOpen(false);
            setEditingReminderType(null);
            await loadReminderTypes();
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "保存案件提醒类型失败");
        }
    };
    const applyDeadlineOffset = async () => {
        const { deadlineOffsetForm, form, setDeadlineOffsetOpen } = context;
        try {
            const values = await deadlineOffsetForm.validateFields();
            const deadline = buildIprDeadlineFromOffset({
                baseDate: values.base_date?.format("YYYY-MM-DD"),
                years: values.years,
                months: values.months,
                days: values.days,
            });
            if (!deadline) {
                message.warning("请选择基准日期");
                return;
            }
            form.setFieldValue("deadline", dayjs(deadline));
            setDeadlineOffsetOpen(false);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(getIprApiErrorMessage(error, "截止日期计算失败"));
        }
    };
    const create = async () => {
        const { form, editing, setCreateOpen, setEditing, load } = context;
        try {
            const values = await form.validateFields();
            const payload = {
                ...values,
                application_date: values.application_date?.format("YYYY-MM-DD"),
                deadline: values.deadline?.format("YYYY-MM-DD"),
            };
            if (payload.case_category !== "litigation") {
                IPR_LAWSUIT_FIELDS.forEach((field) => delete payload[field]);
            }
            if (editing) {
                await api.patch(`/ipr/cases/${editing.id}`, payload);
                message.success("Draft updated");
            }
            else {
                await api.post("/ipr/cases", payload);
                message.success("Draft created");
            }
            setCreateOpen(false);
            setEditing(null);
            void load();
        }
        catch (e: any) {
            if (!e?.errorFields)
                message.error(e?.response?.data?.detail ||
                    (editing ? "Update failed" : "Create failed"));
        }
    };
    const saveCourtInfo = async () => {
        const { detail, courtInfoForm, setCourtInfoOpen, setDetail } = context;
        if (!detail)
            return;
        try {
            const values = await courtInfoForm.validateFields();
            await api.put(`/ipr/lawsuit/cases/${detail.id}/court-info`, values);
            message.success("诉讼基本信息已保存");
            setCourtInfoOpen(false);
            const { data } = await api.get<IprRecord>(`/ipr/cases/${detail.id}`);
            setDetail(data);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "诉讼基本信息保存失败");
        }
    };
    const saveLawsuitCourt = async () => {
        const { detail, lawsuitCourtForm, editingLawsuitCourt, setLawsuitCourtOpen, setEditingLawsuitCourt, loadLawsuitManagement } = context;
        if (!detail)
            return;
        try {
            const values = await lawsuitCourtForm.validateFields();
            const payload = {
                ...values,
                filing_date: values.filing_date?.format("YYYY-MM-DD"),
                hearing_date: values.hearing_date?.format("YYYY-MM-DD"),
            };
            if (editingLawsuitCourt)
                await api.put(`/ipr/lawsuit/cases/${detail.id}/courts/${editingLawsuitCourt.id}`, payload);
            else
                await api.post(`/ipr/lawsuit/cases/${detail.id}/courts`, payload);
            message.success(editingLawsuitCourt ? "法院信息已更新" : "法院信息已添加");
            setLawsuitCourtOpen(false);
            setEditingLawsuitCourt(null);
            await loadLawsuitManagement(detail.id);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "法院信息保存失败");
        }
    };
    const saveLawsuitParty = async () => {
        const { detail, lawsuitPartyForm, editingLawsuitParty, setLawsuitPartyOpen, setEditingLawsuitParty, loadLawsuitManagement } = context;
        if (!detail)
            return;
        try {
            const values = await lawsuitPartyForm.validateFields();
            if (editingLawsuitParty)
                await api.put(`/ipr/lawsuit/cases/${detail.id}/parties/${editingLawsuitParty.id}`, values);
            else
                await api.post(`/ipr/lawsuit/cases/${detail.id}/parties`, values);
            message.success(editingLawsuitParty ? "当事人已更新" : "当事人已添加");
            setLawsuitPartyOpen(false);
            setEditingLawsuitParty(null);
            await loadLawsuitManagement(detail.id);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "当事人保存失败");
        }
    };
    const createIprCasesBatch = async () => {
        const { iprBatchCreateForm, setIprBatchCreateErrors, load, pageSize, setIprBatchCreateOpen } = context;
        try {
            const values = await iprBatchCreateForm.validateFields();
            const payload = {
                customer: values.customer,
                case_kind: values.case_kind,
                rows: (values.rows || []).map((row: Record<string, any>) => ({
                    ...row,
                    case_register_date: row.case_register_date?.format("YYYY-MM-DD") || "",
                    deadline: row.deadline?.format("YYYY-MM-DD") || "",
                })),
            };
            const { data } = await api.post("/ipr/cases/batch-create", payload);
            const rowErrors = data.errors || [];
            setIprBatchCreateErrors(rowErrors);
            if (data.created_count) {
                message.success(`已创建 ${data.created_count} 件知识产权案件`);
                void load(1, pageSize);
            }
            if (!rowErrors.length)
                setIprBatchCreateOpen(false);
            else {
                const failedRows = rowErrors
                    .map((item: IprBatchCreateError) => values.rows?.[item.row_no - 1])
                    .filter(Boolean);
                iprBatchCreateForm.setFieldsValue({
                    ...values,
                    rows: failedRows,
                });
                message.warning(`${rowErrors.length} 行未创建，请按行提示修改后重新提交`);
            }
        }
        catch (error: any) {
            const detail = error?.response?.data?.detail;
            const rowErrors = Array.isArray(detail?.errors)
                ? detail.errors
                : [];
            if (rowErrors.length)
                setIprBatchCreateErrors(rowErrors);
            message.error(detail?.message || detail || "批量创建知识产权案件失败");
        }
    };
    const openIprReboot = async (record: IprRecord) => {
        const { setIprRebootPreview, iprRebootForm, setIprRebootOpen } = context;
        try {
            const { data } = await api.get(`/ipr/cases/${record.id}/reboot-preview`);
            setIprRebootPreview(data);
            iprRebootForm.resetFields();
            setIprRebootOpen(true);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "无法获取案件重提信息");
        }
    };
    const createIprReboot = async () => {
        const { iprRebootPreview, iprRebootForm, setIprRebootOpen, setIprRebootPreview, openDetail, load, pageSize } = context;
        if (!iprRebootPreview)
            return;
        try {
            const values = await iprRebootForm.validateFields();
            const { data } = await api.post(`/ipr/cases/${iprRebootPreview.source_case_id}/reboot`, {
                reason: String(values.reason || "").trim(),
            });
            message.success(`已重提为新案件 ${data.serial_no}`);
            setIprRebootOpen(false);
            setIprRebootPreview(null);
            await openDetail(data);
            void load(1, pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件重提失败");
        }
    };
    const openLawFirmSelector = async () => {
        const { detail, setLawFirmCandidates, setLawFirmSelection, setLawFirmOpen } = context;
        if (!detail)
            return;
        try {
            const { data } = await api.get<{
                items: IprLawFirmCandidate[];
                selected_ids: number[];
            }>(`/ipr/cases/${detail.id}/law-firms/candidates`);
            setLawFirmCandidates(data.items || []);
            setLawFirmSelection(data.selected_ids || []);
            setLawFirmOpen(true);
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "协作律所候选加载失败");
        }
    };
    const saveCaseLawFirms = async () => {
        const { detail, lawFirmSelection, setLawFirmOpen, loadCaseLawFirms } = context;
        if (!detail)
            return;
        try {
            await api.put(`/ipr/cases/${detail.id}/law-firms`, buildIprCaseLawFirmPayload({ lawFirmIds: lawFirmSelection }));
            message.success("协作律所已保存");
            setLawFirmOpen(false);
            await loadCaseLawFirms(detail.id);
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "协作律所保存失败");
        }
    };
    const createIprLog = async () => {
        const { detail, iprLogForm, setIprLogOpen, loadIprLogs } = context;
        if (!detail)
            return;
        try {
            const values = await iprLogForm.validateFields();
            await api.post(`/ipr/cases/${detail.id}/logs`, {
                content: values.content,
            });
            message.success("案件业务日志已保存");
            setIprLogOpen(false);
            iprLogForm.resetFields();
            await loadIprLogs(detail.id);
        }
        catch (e: any) {
            if (!e?.errorFields)
                message.error(e?.response?.data?.detail || "案件业务日志保存失败");
        }
    };
    const deleteIprLog = async (logId: number) => {
        const { detail, loadIprLogs } = context;
        if (!detail)
            return;
        try {
            await api.delete(`/ipr/cases/${detail.id}/logs/${logId}`);
            message.success("案件业务日志已删除");
            await loadIprLogs(detail.id);
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "案件业务日志删除失败");
        }
    };
    const openCustomerSelector = async () => {
        const { detail, setCustomerCandidates, setCustomerSelection, setPrimaryCustomerId, setCustomerOpen } = context;
        if (!detail)
            return;
        try {
            const { data } = await api.get<{
                items: IprCaseCustomerCandidate[];
                selected_ids: number[];
                primary_customer_id: number | null;
            }>(`/ipr/cases/${detail.id}/customers/candidates`);
            setCustomerCandidates(data.items || []);
            setCustomerSelection(data.selected_ids || []);
            setPrimaryCustomerId(data.primary_customer_id || data.selected_ids?.[0] || null);
            setCustomerOpen(true);
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "客户候选加载失败");
        }
    };
    const saveCaseCustomers = async () => {
        const { detail, customerSelection, primaryCustomerId, setCustomerOpen, loadCaseCustomers, loadCaseContacts } = context;
        if (!detail)
            return;
        const validationError = getIprCaseCustomerValidationError({
            customerIds: customerSelection,
            primaryCustomerId,
        });
        if (validationError) {
            message.warning(validationError);
            return;
        }
        try {
            await api.put(`/ipr/cases/${detail.id}/customers`, buildIprCaseCustomerPayload({
                customerIds: customerSelection,
                primaryCustomerId,
            }));
            message.success("案件客户已保存");
            setCustomerOpen(false);
            await Promise.all([
                loadCaseCustomers(detail.id),
                loadCaseContacts(detail.id),
            ]);
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "案件客户保存失败");
        }
    };
    const openContactSelector = async (customer: IprCaseCustomer) => {
        const { detail, setContactCustomer, setContactCandidates, setDocumentContactIds, setTechnologyContactIds, setContactOpen } = context;
        if (!detail)
            return;
        try {
            const { data } = await api.get<{
                items: CustomerContact[];
                document_contact_ids: string[];
                technology_contact_ids: string[];
            }>(`/ipr/cases/${detail.id}/customers/${customer.customer_id}/contact-candidates`);
            setContactCustomer(customer);
            setContactCandidates(data.items || []);
            setDocumentContactIds(data.document_contact_ids || []);
            setTechnologyContactIds(data.technology_contact_ids || []);
            setContactOpen(true);
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "案件联系人候选加载失败");
        }
    };
    const saveCaseContacts = async () => {
        const { detail, contactCustomer, documentContactIds, technologyContactIds, setContactOpen, loadCaseContacts } = context;
        if (!detail || !contactCustomer)
            return;
        try {
            await api.put(`/ipr/cases/${detail.id}/customer-contacts`, buildIprCaseContactPayload({
                customerId: contactCustomer.customer_id,
                documentContactIds,
                technologyContactIds,
            }));
            message.success("案件联系人已保存");
            setContactOpen(false);
            await loadCaseContacts(detail.id);
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "案件联系人保存失败");
        }
    };
    const saveIprCaseEvent = async () => {
        const { detail, iprEventForm, editingIprEvent, setIprEventOpen, setEditingIprEvent, loadIprCaseEvents } = context;
        if (!detail)
            return;
        try {
            const values = await iprEventForm.validateFields();
            const payload = {
                event_type_id: Number(values.event_type_id),
                event_date: formatRequiredDate(values.event_date, "事件日期"),
                deadline: formatRequiredDate(values.deadline, "截止日期"),
                content: String(values.content || "").trim(),
            };
            if (editingIprEvent) {
                await api.patch(`/ipr/cases/${detail.id}/events/${editingIprEvent.id}`, payload);
                message.success("案件事件已更新");
            }
            else {
                await api.post(`/ipr/cases/${detail.id}/events`, payload);
                message.success("案件事件已创建");
            }
            setIprEventOpen(false);
            setEditingIprEvent(null);
            iprEventForm.resetFields();
            await loadIprCaseEvents(detail.id);
        }
        catch (e: any) {
            if (!e?.errorFields)
                message.error(e?.response?.data?.detail ||
                    (editingIprEvent
                        ? "更新案件事件失败"
                        : "创建案件事件失败"));
        }
    };
    const deleteIprCaseEvent = async (row: IprCaseEvent) => {
        const { detail, loadIprCaseEvents } = context;
        if (!detail)
            return;
        try {
            await api.delete(`/ipr/cases/${detail.id}/events/${row.id}`);
            message.success("案件事件已删除");
            await loadIprCaseEvents(detail.id);
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "删除案件事件失败");
        }
    };
    const createIprCaseTask = async () => {
        const { detail, iprTaskForm, setIprTaskOpen, loadIprCaseTasks } = context;
        if (!detail)
            return;
        try {
            const values = await iprTaskForm.validateFields();
            await api.post(`/ipr/cases/${detail.id}/tasks`, {
                title: String(values.title || "").trim(),
                owner: String(values.owner || "").trim(),
                deadline: formatRequiredDate(values.deadline, "任务截止日期"),
                priority: values.priority || "普通",
                description: String(values.description || "").trim(),
                source: "案件任务",
                case_record_id: detail.id,
                case_module: "ipr_case",
            });
            message.success("案件任务已创建");
            setIprTaskOpen(false);
            iprTaskForm.resetFields();
            await loadIprCaseTasks(detail.id);
        }
        catch (e: any) {
            if (!e?.errorFields)
                message.error(e?.response?.data?.detail || "创建案件任务失败");
        }
    };
    const saveSuppressions = async () => {
        const { detail, suppressedIds, setSuppressionOpen, loadReminderSuppressions } = context;
        if (!detail)
            return;
        try {
            await api.put(`/ipr/cases/${detail.id}/reminder-suppressions`, {
                event_type_ids: suppressedIds,
            });
            message.success("不监控提醒类型已保存");
            setSuppressionOpen(false);
            await loadReminderSuppressions(detail.id);
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "保存不监控设置失败");
        }
    };
    const saveMaintenance = async () => {
        const { maintenanceTarget, maintenanceForm, setMaintenanceTarget, setDetail, load } = context;
        if (!maintenanceTarget)
            return;
        try {
            const values = await maintenanceForm.validateFields();
            await api.post(`/ipr/cases/${maintenanceTarget.id}/maintenance`, {
                ...values,
                deadline: values.deadline
                    ? formatRequiredDate(values.deadline, "办理期限")
                    : undefined,
            });
            message.success("期限、年费和费率已维护");
            setMaintenanceTarget(null);
            setDetail(null);
            void load();
        }
        catch (e: any) {
            if (!e?.errorFields)
                message.error(e?.response?.data?.detail || "案件维护失败");
        }
    };
    const saveBatchMaintenance = async () => {
        const { iprMaintenanceForm, selectedIprCaseIds, setIprMaintenanceOpen, setSelectedIprCaseIds, load } = context;
        try {
            const values = await iprMaintenanceForm.validateFields();
            const hasValue = Object.entries(values).some(([key, value]) => key !== "comment" &&
                value !== undefined &&
                value !== null &&
                value !== "");
            if (!hasValue) {
                message.warning("请至少填写一项批量维护字段");
                return;
            }
            const { data } = await api.post("/ipr/cases/batch-maintenance", {
                ...values,
                case_ids: selectedIprCaseIds,
                deadline: values.deadline
                    ? formatRequiredDate(values.deadline, "办理期限")
                    : undefined,
            });
            message.success(`已维护 ${data.updated} 个案件`);
            setIprMaintenanceOpen(false);
            setSelectedIprCaseIds([]);
            void load();
        }
        catch (e: any) {
            if (!e?.errorFields)
                message.error(e?.response?.data?.detail || "批量维护失败");
        }
    };
    const action = async (record: IprRecord, name: "submit" | "close" | "reopen" | "review", approved?: boolean) => {
        const { profile, setDetail, load } = context;
        let comment = "";
        if (name === "review" && !approved) {
            const prompted = window.prompt("请填写驳回原因");
            if (prompted === null)
                return;
            comment = prompted;
        }
        const validationError = getIprCaseActionValidationError({
            action: name,
            role: profile.role,
            status: record.status,
            applicationNo: record.data?.application_no,
            approved,
            comment,
        });
        if (validationError) {
            message.warning(validationError);
            return;
        }
        const payload = buildIprCaseActionPayload({
            action: name,
            approved,
            comment,
        });
        try {
            const response = await api.post(`/ipr/cases/${record.id}/${name}`, payload);
            const actionResult = normalizeIprCaseActionResponse(response, "操作成功");
            if (!actionResult.ok)
                throw new Error(actionResult.message);
            message.success(actionResult.message);
            setDetail(null);
            void load();
        }
        catch (e: any) {
            message.error(getIprCaseActionErrorMessage(e, "操作失败"));
        }
    };
    const generateWarnings = async () => {
        const { loadWarnings } = context;
        try {
            const { data } = await api.post<{
                created: number;
                total: number;
            }>("/ipr/warnings/generate");
            message.success(data.created
                ? `已生成 ${data.created} 条案件预警`
                : "预警已按当前规则更新");
            await loadWarnings(1);
            window.dispatchEvent(new Event("sunhold:notifications-updated"));
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "生成案件预警失败");
        }
    };
    const saveWarningRule = async () => {
        const { warningRuleForm, editingWarningRule, setWarningRuleEditorOpen, loadWarningRules, loadWarnings } = context;
        try {
            const values = await warningRuleForm.validateFields();
            const payload = {
                name: String(values.name || "").trim(),
                case_kind: values.case_kind || "",
                case_type: String(values.case_type || "").trim(),
                case_phase: String(values.case_phase || "").trim(),
                time_node: values.time_node,
                event_type_id: values.time_node === "reminder_deadline"
                    ? Number(values.event_type_id ?? 0)
                    : 0,
                days_before: Number(values.days_before),
                is_active: !!values.is_active,
            };
            if (editingWarningRule)
                await api.patch(`/ipr/warning-rules/${editingWarningRule.id}`, payload);
            else
                await api.post("/ipr/warning-rules", payload);
            message.success(editingWarningRule ? "预警规则已更新" : "预警规则已创建");
            setWarningRuleEditorOpen(false);
            await Promise.all([loadWarningRules(), loadWarnings(1)]);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "保存预警规则失败");
        }
    };
    const markWarningRead = async (warning: IprWarning) => {
        const { loadWarnings } = context;
        if (warning.is_read)
            return;
        try {
            await api.post(`/ipr/warnings/${warning.id}/read`);
            await loadWarnings();
            window.dispatchEvent(new Event("sunhold:notifications-updated"));
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "标记已读失败");
        }
    };
    const processWarning = async () => {
        const { processingWarning, warningProcessForm, setProcessingWarning, loadWarnings } = context;
        if (!processingWarning)
            return;
        try {
            const values = await warningProcessForm.validateFields();
            await api.post(`/ipr/warnings/${processingWarning.id}/process`, {
                comment: String(values.comment || "").trim(),
            });
            message.success("案件预警已处理");
            setProcessingWarning(null);
            warningProcessForm.resetFields();
            await loadWarnings();
            window.dispatchEvent(new Event("sunhold:notifications-updated"));
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "处理案件预警失败");
        }
    };
    return { saveReminderType, applyDeadlineOffset, create, saveCourtInfo, saveLawsuitCourt, saveLawsuitParty, createIprCasesBatch, openIprReboot, createIprReboot, openLawFirmSelector, saveCaseLawFirms, createIprLog, deleteIprLog, openCustomerSelector, saveCaseCustomers, openContactSelector, saveCaseContacts, saveIprCaseEvent, deleteIprCaseEvent, createIprCaseTask, saveSuppressions, saveMaintenance, saveBatchMaintenance, action, generateWarnings, saveWarningRule, markWarningRead, processWarning };
}
