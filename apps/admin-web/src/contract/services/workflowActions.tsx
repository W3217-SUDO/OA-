import { message } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import type { MessageType } from "antd/es/message/interface";
import dayjs from "dayjs";
import { api } from "../../api";
import { selectContractCurrentApprovalStep } from "../../contractApprovalCurrentStep.mjs";
import { createContractNumber, type LinkedCustomerContext } from "../../contractCreateContext";
import { buildContractDetailRoute } from "../../contractDetailNavigation";
import { saveContractListQuery } from "../../contractListQuery";
import type { ContractMutationGate } from "../../contractMutationGate.mjs";
import { buildContractApprovalPayload, buildContractEventsRequest, extractContractErrorMessage, normalizeContractActionResponse, normalizeContractAttachment, validateContractApprovalSubmission, validateContractAttachment, validateContractDraftValues } from "../../contractWorkflowPolicy.mjs";
import { formatRequiredDate } from "../../formSafety";
import { CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY, CONTRACT_SEAL_READY_STATUSES, WIZARD_STORAGE_KEY } from "../constants";
import type { ApproverSetting, Attachment, Change, Contract, ContractArchiveSubject, ContractWorkflowCapabilities, CustomerRef, DirectoryUser, Profile, Step } from "../types";
/** contract workflow operations; dependencies are read when each operation runs. */
export interface ContractWorkflowDependencies {
    readonly viewing: Contract | null;
    readonly contractCapabilities: (contract?: Contract | null | undefined, options?: Record<string, unknown>) => ContractWorkflowCapabilities;
    readonly denyContractAction: () => MessageType;
    readonly archiveSubjects: ContractArchiveSubject[];
    readonly selectedArchiveObjectKeys: React.Key[];
    readonly setArchiveClosureSaving: React.Dispatch<React.SetStateAction<boolean>>;
    readonly archiveClosureComment: string;
    readonly loadArchiveSubjects: (contract: Contract) => Promise<void>;
    readonly load: (queryOverride?: Record<string, any> | undefined, paginationOverride?: {
        current: number;
        pageSize: number;
    } | undefined) => Promise<void>;
    readonly objectEditing: {
        id?: number | undefined;
    } | null;
    readonly objectForm: FormInstance<any>;
    readonly setObjectEditing: React.Dispatch<React.SetStateAction<{
        id?: number | undefined;
    } | null>>;
    readonly openViewing: (contract: Contract, options?: {
        detailTab?: string | undefined;
    }) => Promise<void>;
    readonly loadWizardContext: (contractId: number) => Promise<Contract>;
    readonly setOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly onNavigate: ((key: string) => void) | undefined;
    readonly setWizardStep: React.Dispatch<React.SetStateAction<number>>;
    readonly startCreate: (context?: LinkedCustomerContext | null) => void;
    readonly canOpenSubmitWizard: (contract?: Contract | null | undefined) => boolean;
    readonly setEditing: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly setSubmitting: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly setChanging: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly editing: Contract | null;
    readonly wizardDraft: Contract | null;
    readonly form: FormInstance<any>;
    readonly customers: CustomerRef[];
    readonly resolveCustomerRef: (customerId: number | undefined) => CustomerRef | null;
    readonly contractFile: File | null;
    readonly setSavingContract: React.Dispatch<React.SetStateAction<boolean>>;
    readonly profile: Profile;
    readonly setWizardDraft: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly setContractFile: React.Dispatch<React.SetStateAction<File | null>>;
    readonly submitForm: FormInstance<any>;
    readonly setAttachments: React.Dispatch<React.SetStateAction<Attachment[]>>;
    readonly setSubmittingWizard: React.Dispatch<React.SetStateAction<boolean>>;
    readonly approvalOptions: {
        value: string;
        label: string;
    }[];
    readonly personName: (value: unknown) => string;
    readonly sealForm: FormInstance<any>;
    readonly canActOnCurrentApproval: boolean;
    readonly reviewForm: FormInstance<any>;
    readonly setSelectedAttachmentKeys: React.Dispatch<React.SetStateAction<React.Key[]>>;
    readonly attachments: Attachment[];
    readonly submitting: Contract | null;
    readonly contractMutationGates: React.RefObject<{
        submit: ContractMutationGate;
        payment: ContractMutationGate;
        invoice: ContractMutationGate;
        attachment: ContractMutationGate;
    }>;
    readonly setSubmitSaving: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setReviewing: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly setSteps: React.Dispatch<React.SetStateAction<Step[]>>;
    readonly setReviewCurrentStep: React.Dispatch<React.SetStateAction<Step | null>>;
    readonly reviewing: Contract | null;
    readonly setViewing: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly reloadViewingAttachments: (contract: Contract) => Promise<void>;
    readonly reloadDetailApprovals: (contract: Contract) => Promise<void>;
    readonly changing: Contract | null;
    readonly changeForm: FormInstance<any>;
    readonly changeFile: File | null;
    readonly setChangeFile: React.Dispatch<React.SetStateAction<File | null>>;
    readonly setSelectedRowKeys: React.Dispatch<React.SetStateAction<React.Key[]>>;
    readonly setChanges: React.Dispatch<React.SetStateAction<Change[]>>;
    readonly setChangeHistory: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly eventTarget: Contract | null;
    readonly contractEventSubmitGate: React.RefObject<{
        tryEnter(): boolean;
        leave(): void;
    }>;
    readonly setEventSaving: React.Dispatch<React.SetStateAction<boolean>>;
    readonly eventForm: FormInstance<any>;
    readonly setEventTarget: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly isContractInvestigationView: boolean;
    readonly initialView: string;
    readonly query: Record<string, any>;
    readonly setInvestigationError: React.Dispatch<React.SetStateAction<string>>;
    readonly investigationForm: FormInstance<any>;
    readonly setSelectedInvestigationRegions: React.Dispatch<React.SetStateAction<string[]>>;
    readonly setInvestigationWizardStep: React.Dispatch<React.SetStateAction<number>>;
    readonly setInvestigationDraftValues: React.Dispatch<React.SetStateAction<Record<string, any> | null>>;
    readonly setCreatedInvestigation: React.Dispatch<React.SetStateAction<{
        id: number;
        serial_no: string;
        title: string;
    } | null>>;
    readonly setInvestigationSupervisor: React.Dispatch<React.SetStateAction<{
        username: string;
        display_name: string;
    } | null>>;
    readonly setInvestigating: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly investigating: Contract | null;
    readonly investigationDraftValues: Record<string, any> | null;
    readonly setInvestigationSubmitting: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setApproverSettingsOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setApproverSettingsLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setApproverSettings: React.Dispatch<React.SetStateAction<ApproverSetting[]>>;
    readonly approverSettingsTargetUsername: string;
    readonly setSelectedApproverUsernames: React.Dispatch<React.SetStateAction<string[]>>;
    readonly setApproverSettingsSaving: React.Dispatch<React.SetStateAction<boolean>>;
    readonly selectedApproverUsernames: string[];
    readonly setDirectory: React.Dispatch<React.SetStateAction<DirectoryUser[]>>;
}
export function createContractWorkflowActions(context: ContractWorkflowDependencies) {
    const submitArchiveClosure = async () => {
        const { viewing, contractCapabilities, denyContractAction, archiveSubjects, selectedArchiveObjectKeys, setArchiveClosureSaving, archiveClosureComment, loadArchiveSubjects, load } = context;
        if (!viewing)
            return;
        if (!contractCapabilities(viewing).canArchive) {
            denyContractAction();
            return;
        }
        const selectedSubjects = archiveSubjects.filter((item) => selectedArchiveObjectKeys.includes(item.contract_object_id));
        const caseFeeIds = Array.from(new Set(selectedSubjects.flatMap((item) => item.case_fee_ids || [])));
        if (!caseFeeIds.length) {
            message.warning("请选择至少一条可完结的案件费用");
            return;
        }
        setArchiveClosureSaving(true);
        try {
            const { data } = await api.post(`/contracts/${viewing.id}/archive-closure`, {
                case_fee_ids: caseFeeIds,
                fee_archived: true,
                comment: archiveClosureComment.trim(),
            });
            message.success(`已完结 ${data.updated} 条案件费用${data.changed ? `，其中 ${data.changed} 条状态已变更` : ""}`);
            await Promise.all([loadArchiveSubjects(viewing), load()]);
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "合同归档完结提交失败"));
        }
        finally {
            setArchiveClosureSaving(false);
        }
    };
    const saveContractObject = async () => {
        const { viewing, objectEditing, contractCapabilities, denyContractAction, objectForm, setObjectEditing, openViewing } = context;
        if (!viewing || !objectEditing)
            return;
        if (!contractCapabilities(viewing).canEdit) {
            denyContractAction();
            return;
        }
        try {
            const values = await objectForm.validateFields();
            const request = objectEditing.id ? api.patch(`/contracts/${viewing.id}/objects/${objectEditing.id}`, values) : api.post(`/contracts/${viewing.id}/objects`, values);
            const response = await request;
            const feedback = normalizeContractActionResponse(response, "合同标的保存失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            message.success(objectEditing.id ? "合同标的已修改" : "合同标的已新增");
            setObjectEditing(null);
            objectForm.resetFields();
            await openViewing(viewing);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(extractContractErrorMessage(error, "合同标的保存失败"));
        }
    };
    const deleteContractObject = async (objectId: number) => {
        const { viewing, contractCapabilities, denyContractAction, openViewing } = context;
        if (!viewing)
            return;
        if (!contractCapabilities(viewing).canEdit) {
            denyContractAction();
            return;
        }
        try {
            const response = await api.delete(`/contracts/${viewing.id}/objects/${objectId}`);
            const feedback = normalizeContractActionResponse(response, "合同标的删除失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            message.success("合同标的已删除");
            await openViewing(viewing);
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "合同标的删除失败"));
        }
    };
    const recoverWizard = async (contractId: number) => {
        const { loadWizardContext, setOpen, onNavigate, setWizardStep, startCreate } = context;
        try {
            const contract = await loadWizardContext(contractId);
            if (!["草稿", "已拒绝"].includes(contract.status)) {
                localStorage.removeItem(WIZARD_STORAGE_KEY);
                setOpen(false);
                const detailRoute = buildContractDetailRoute(contract);
                if (detailRoute)
                    onNavigate?.(detailRoute);
                return;
            }
            setWizardStep(1);
            setOpen(true);
        }
        catch {
            localStorage.removeItem(WIZARD_STORAGE_KEY);
            startCreate();
        }
    };
    const openSubmitWizardFromList = async (contract: Contract) => {
        const { contractCapabilities, denyContractAction, canOpenSubmitWizard, setEditing, setSubmitting, setChanging, loadWizardContext, setWizardStep, setOpen } = context;
        if (!contractCapabilities(contract).canSubmit) {
            denyContractAction();
            return;
        }
        if (!canOpenSubmitWizard(contract)) {
            message.warning("仅草稿或已拒绝合同可以提交审批");
            return;
        }
        try {
            setEditing(null);
            setSubmitting(null);
            setChanging(null);
            await loadWizardContext(contract.id);
            localStorage.setItem(WIZARD_STORAGE_KEY, String(contract.id));
            setWizardStep(1);
            setOpen(true);
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "合同提交审批信息加载失败"));
        }
    };
    const save = async () => {
        const { editing, wizardDraft, contractCapabilities, denyContractAction, form, customers, resolveCustomerRef, contractFile, setSavingContract, profile, setWizardDraft, setContractFile, setOpen, loadWizardContext, setWizardStep, load } = context;
        const target = editing || wizardDraft;
        if (!(target ? contractCapabilities(target).canEdit : contractCapabilities().canCreate)) {
            denyContractAction();
            return;
        }
        let v: any;
        try {
            v = await form.validateFields();
        }
        catch {
            message.warning("请先补全红色提示的合同必填信息");
            return;
        }
        const draftErrors = validateContractDraftValues(v);
        if (draftErrors.length) {
            if (draftErrors.includes("customer_id"))
                form.setFields([{ name: "customer_id", errors: ["请选择客户"] }]);
            if (draftErrors.includes("title"))
                form.setFields([{ name: "title", errors: ["请输入合同名称"] }]);
            message.warning("请先补全合同必填信息");
            return;
        }
        const selectedCustomer = customers.find((customer) => customer.id === Number(v.customer_id)) || resolveCustomerRef(Number(v.customer_id));
        if (!selectedCustomer) {
            form.setFields([{ name: "customer_id", errors: ["请从客户列表中选择准确客户"] }]);
            message.warning("请输入客户关键字，并从匹配结果中选择客户");
            return;
        }
        const contractFileError = validateContractAttachment(contractFile);
        if (contractFile && contractFileError) {
            message.warning(contractFileError);
            return;
        }
        setSavingContract(true);
        try {
            const sourceData: Contract["data"] = target?.data || { amount: 0, signed_at: "", type: "" };
            const signedAt = dayjs.isDayjs(v.signed_at)
                ? v.signed_at
                : sourceData.signed_at
                    ? dayjs(sourceData.signed_at)
                    : dayjs();
            const externalNumbers = v.external_contract_numbers || sourceData.external_contract_numbers || [];
            const data = {
                ...sourceData,
                amount: Number(v.amount ?? sourceData.amount ?? 0),
                signed_at: signedAt.format("YYYY-MM-DD"),
                type: v.type || sourceData.type || "法律顾问合同",
                contract_body: v.contract_body || sourceData.contract_body || "律所",
                fee_type: v.fee_type || sourceData.fee_type || "固定收费",
                external_contract_numbers: externalNumbers,
                external_contract_no: externalNumbers[0] || "",
                customer_id: selectedCustomer.id,
                customer_no: selectedCustomer.serial_no,
                customer_manager: (selectedCustomer.data.customer_managers || [selectedCustomer.owner]).join("、"),
            };
            const payload = {
                serial_no: target ? v.serial_no || target.serial_no || createContractNumber() : "",
                title: v.title,
                customer: selectedCustomer.title,
                owner: v.owner || target?.owner || profile.username || "admin",
                department: v.department || target?.department || profile.department || "上海分所",
                description: v.description || "",
                data,
            };
            const response = target
                ? await api.patch(`/contracts/${target.id}`, payload)
                : await api.post("/contracts", payload);
            const feedback = normalizeContractActionResponse(response, "保存失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            if (!editing) {
                setWizardDraft(response.data);
                localStorage.setItem(WIZARD_STORAGE_KEY, String(response.data.id));
            }
            if (contractFile) {
                const attachment = new FormData();
                attachment.append("file", contractFile);
                attachment.append("record_id", String(response.data.id));
                attachment.append("category", "合同附件");
                attachment.append("remark", "合同起草时上传");
                const attachmentResponse = await api.post("/attachments", attachment);
                const attachmentFeedback = normalizeContractActionResponse(attachmentResponse, "合同附件上传失败");
                if (!attachmentFeedback.ok)
                    throw new Error(attachmentFeedback.message);
            }
            message.success(editing ? "合同已更新" : "合同草稿已保存，进入提交审批");
            sessionStorage.removeItem("sunhold:contract-customer");
            setContractFile(null);
            if (editing) {
                setOpen(false);
            }
            else {
                await loadWizardContext(response.data.id);
                setWizardStep(1);
            }
            await load();
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "保存失败"));
        }
        finally {
            setSavingContract(false);
        }
    };
    const submitWizard = async () => {
        const { wizardDraft, contractCapabilities, denyContractAction, submitForm, setAttachments, setSubmittingWizard, loadWizardContext, approvalOptions, personName, sealForm, setWizardStep, setOpen, onNavigate, load } = context;
        if (!wizardDraft)
            return;
        if (!contractCapabilities(wizardDraft).canSubmit) {
            denyContractAction();
            return;
        }
        try {
            const values = await submitForm.validateFields();
            const syncSealRequested = Boolean(values.sync_seal);
            const attachmentResponse = await api.get("/attachments", { params: { record_id: wizardDraft.id } });
            const currentAttachments = (attachmentResponse.data.items || []).map((item: Attachment) => ({ ...item, ...normalizeContractAttachment(item) }));
            setAttachments(currentAttachments);
            const submissionErrors = validateContractApprovalSubmission(wizardDraft.status, values.approvers, currentAttachments.length);
            if (submissionErrors.includes("status")) {
                message.warning("仅草稿或已拒绝合同可以提交审批");
                return;
            }
            if (submissionErrors.includes("approver")) {
                message.warning("请选择一名合同审批人");
                return;
            }
            if (submissionErrors.includes("attachment")) {
                message.warning("请先上传至少一份合同附件后再提交审批");
                return;
            }
            setSubmittingWizard(true);
            const response = await api.post(`/contracts/${wizardDraft.id}/submit`, { approvers: values.approvers ? [values.approvers] : [], comment: values.comment || "", sync_seal: syncSealRequested });
            const feedback = normalizeContractActionResponse(response, "提交审批失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            const contract = await loadWizardContext(wizardDraft.id);
            const approverName = approvalOptions.find((option) => option.value === values.approvers)?.label || personName(values.approvers);
            message.success(`合同已进入 ${approverName} 的待审批列表`);
            if (syncSealRequested) {
                sealForm.setFieldsValue({
                    copies: 1,
                    use_date: dayjs().add(1, "day"),
                    delivery_method: "现场用印",
                    document_names: currentAttachments.map((item: Attachment) => item.original_name).join("、"),
                    purpose: `${contract.title}合同用印`,
                    submit: false,
                });
                setWizardStep(3);
                message.info("已同步进入申请用印，请填写用印信息后生成用印申请");
            }
            else {
                localStorage.removeItem(WIZARD_STORAGE_KEY);
                setOpen(false);
                onNavigate?.(`contract-detail-${contract.id}-${encodeURIComponent(contract.serial_no)}`);
            }
            await load();
        }
        catch (error: any) {
            if (error?.errorFields)
                return;
            message.error(extractContractErrorMessage(error, "提交审批失败"));
        }
        finally {
            setSubmittingWizard(false);
        }
    };
    const approveWizard = async (approved: boolean) => {
        const { wizardDraft, canActOnCurrentApproval, reviewForm, loadWizardContext, setWizardStep, sealForm, setContractFile, setSelectedAttachmentKeys, attachments, load } = context;
        if (!wizardDraft)
            return;
        if (!canActOnCurrentApproval) {
            message.warning("当前账号不是该审批节点指定审批人");
            return;
        }
        const values = await reviewForm.validateFields();
        if (!approved && !String(values.comment || "").trim()) {
            message.warning("拒绝时必须填写审批意见");
            return;
        }
        try {
            const response = await api.post(`/contracts/${wizardDraft.id}/approve`, buildContractApprovalPayload(approved, values.comment));
            const feedback = normalizeContractActionResponse(response, "审批失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            reviewForm.resetFields();
            const contract = await loadWizardContext(wizardDraft.id);
            if (!approved || contract.status === "已拒绝") {
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
            message.success(approved ? "当前审批节点已通过" : "合同审批已拒绝");
            await load();
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "审批失败"));
        }
    };
    const createSealApplication = async (forcedSubmit?: boolean) => {
        const { wizardDraft, sealForm, attachments, loadWizardContext, setWizardDraft, load, setOpen, onNavigate } = context;
        if (!wizardDraft)
            return;
        try {
            const values = await sealForm.validateFields();
            const { submit: submitFromForm, ...sealValues } = values;
            const submitApplication = forcedSubmit ?? Boolean(submitFromForm);
            const { data } = await api.post(`/contracts/${wizardDraft.id}/seal-application`, {
                ...sealValues,
                source_attachment_ids: attachments.map((item) => Number(item.id)).filter(Boolean),
                submit: Boolean(submitApplication),
                use_date: formatRequiredDate(values.use_date, "计划用印日期"),
            });
            const contract = await loadWizardContext(wizardDraft.id);
            if (contract.status !== "审批中")
                localStorage.removeItem(WIZARD_STORAGE_KEY);
            message.success(submitApplication
                ? (data.status === "待审批" ? "合同审批与用印申请已分别提交至对应审批渠道" : "合同用印申请已创建")
                : "合同用印申请草稿已创建，请到用印中心提交审批");
            setWizardDraft(contract);
            await load();
            if (submitApplication) {
                localStorage.removeItem(WIZARD_STORAGE_KEY);
                setOpen(false);
                const route = buildContractDetailRoute(contract);
                if (route)
                    onNavigate?.(route);
            }
            return data;
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "合同用印申请创建失败");
        }
    };
    const submit = async () => {
        const { submitting, contractMutationGates, contractCapabilities, denyContractAction, setSubmitSaving, submitForm, approvalOptions, personName, setSubmitting, load } = context;
        if (!submitting || !contractMutationGates.current.submit.tryEnter())
            return;
        if (!contractCapabilities(submitting).canSubmit) {
            contractMutationGates.current.submit.leave();
            denyContractAction();
            return;
        }
        setSubmitSaving(true);
        try {
            const v = await submitForm.validateFields();
            const response = await api.post(`/contracts/${submitting.id}/submit`, { approvers: v.approvers ? [v.approvers] : [], comment: v.comment || "" });
            const feedback = normalizeContractActionResponse(response, "提交审批失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            const approverName = approvalOptions.find((option) => option.value === v.approvers)?.label || personName(v.approvers);
            message.success(`已提交至 ${approverName} 的待审批列表`);
            setSubmitting(null);
            await load();
        }
        catch (error: any) {
            if (error?.errorFields)
                return;
            message.error(extractContractErrorMessage(error, "提交失败"));
        }
        finally {
            contractMutationGates.current.submit.leave();
            setSubmitSaving(false);
        }
    };
    const openReview = async (r: Contract) => {
        const { contractCapabilities, denyContractAction, setReviewing, setSteps, setReviewCurrentStep } = context;
        if (!contractCapabilities(r).canOpenApproval) {
            denyContractAction();
            return;
        }
        try {
            const { data } = await api.get(`/contracts/${r.id}/approvals`);
            setReviewing(r);
            setSteps(data.items);
            setReviewCurrentStep(selectContractCurrentApprovalStep<Step>(data));
        }
        catch {
            message.error("审批节点加载失败");
        }
    };
    const approve = async (approved: boolean) => {
        const { reviewing, canActOnCurrentApproval, reviewForm, setSteps, setReviewing, setReviewCurrentStep, sealForm, setContractFile, setSelectedAttachmentKeys, viewing, setViewing, reloadViewingAttachments, reloadDetailApprovals, load } = context;
        if (!reviewing)
            return;
        if (!canActOnCurrentApproval) {
            message.warning("当前账号不是该审批节点指定审批人");
            return;
        }
        const v = await reviewForm.validateFields();
        try {
            const response = await api.post(`/contracts/${reviewing.id}/approve`, buildContractApprovalPayload(approved, v.comment));
            const feedback = normalizeContractActionResponse(response, "审批失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            message.success(approved ? "当前审批节点已通过" : "合同已拒绝");
            reviewForm.resetFields();
            const { data } = await api.get(`/contracts/${reviewing.id}/approvals`);
            setSteps(data.items);
            setReviewing(data.contract);
            setReviewCurrentStep(selectContractCurrentApprovalStep<Step>(data));
            if (!approved || data.contract?.status === "已拒绝") {
                sealForm.resetFields();
                setContractFile(null);
                setSelectedAttachmentKeys([]);
            }
            if (viewing?.id === data.contract?.id) {
                setViewing(data.contract);
                await reloadViewingAttachments(data.contract);
                await reloadDetailApprovals(data.contract);
            }
            await load();
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "审批失败"));
        }
    };
    const saveChange = async () => {
        const { changing, contractCapabilities, denyContractAction, changeForm, changeFile, setChanging, setChangeFile, load } = context;
        if (!changing)
            return;
        if (!contractCapabilities(changing).canChange) {
            denyContractAction();
            return;
        }
        const v = await changeForm.validateFields();
        try {
            const response = await api.post(`/contracts/${changing.id}/changes`, {
                ...v,
                end_date: v.end_date?.format("YYYY-MM-DD"),
            });
            const feedback = normalizeContractActionResponse(response, "合同变更失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            if (changeFile) {
                const attachment = new FormData();
                attachment.append("file", changeFile);
                attachment.append("record_id", String(changing.id));
                attachment.append("category", "合同变更附件");
                attachment.append("remark", "合同变更时上传");
                const attachmentResponse = await api.post("/attachments", attachment);
                const attachmentFeedback = normalizeContractActionResponse(attachmentResponse, "合同变更附件上传失败");
                if (!attachmentFeedback.ok)
                    throw new Error(attachmentFeedback.message);
            }
            message.success("合同变更已提交审批");
            setChanging(null);
            setChangeFile(null);
            load();
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "合同变更失败"));
        }
    };
    const reviewChange = async (contract: Contract, approved: boolean) => {
        const { contractCapabilities, denyContractAction, setSelectedRowKeys, load } = context;
        if (!contractCapabilities(contract).canReviewChange) {
            denyContractAction();
            return;
        }
        try {
            const response = await api.post(`/contracts/${contract.id}/changes/review`, { approved, comment: approved ? "同意合同变更" : "变更内容需补充后重新提交" });
            const feedback = normalizeContractActionResponse(response, "合同变更审批失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            message.success(approved ? "合同变更已审批通过" : "合同变更已驳回");
            setSelectedRowKeys([]);
            await load();
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "合同变更审批失败"));
        }
    };
    const openChanges = async (r: Contract) => {
        const { setChanges, setChangeHistory } = context;
        try {
            const { data } = await api.get(`/contracts/${r.id}/changes`);
            setChanges(data.items);
            setChangeHistory(r);
        }
        catch {
            message.error("变更记录加载失败");
        }
    };
    const createContractEvent = async () => {
        const { eventTarget, contractEventSubmitGate, setEventSaving, eventForm, setEventTarget, viewing, openViewing } = context;
        if (!eventTarget || !contractEventSubmitGate.current.tryEnter())
            return;
        setEventSaving(true);
        try {
            const values = await eventForm.validateFields();
            const eventRequest = buildContractEventsRequest(eventTarget, { page: 1, pageSize: 15 });
            if (!eventRequest.path)
                throw new Error("合同事项缺少合同标识");
            const response = await api.post(eventRequest.path, { content: values.content });
            const feedback = normalizeContractActionResponse(response, "合同事项记录失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            message.success("合同事项已记录");
            setEventTarget(null);
            eventForm.resetFields();
            if (viewing?.id === eventTarget.id)
                await openViewing(eventTarget);
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "合同事项记录失败"));
        }
        finally {
            contractEventSubmitGate.current.leave();
            setEventSaving(false);
        }
    };
    const openInvestigation = async (r: Contract) => {
        const { isContractInvestigationView, initialView, query, onNavigate, setInvestigationError, investigationForm, setSelectedInvestigationRegions, setInvestigationWizardStep, setInvestigationDraftValues, setCreatedInvestigation, setInvestigationSupervisor, setInvestigating } = context;
        if (!isContractInvestigationView) {
            try {
                saveContractListQuery(sessionStorage, initialView, query);
                sessionStorage.setItem(CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY, initialView);
            }
            catch {
                // The dedicated work page can still open when session storage is unavailable.
            }
            onNavigate?.(`contract-investigation-${r.id}-${encodeURIComponent(r.serial_no)}`);
            return;
        }
        setInvestigationError("");
        investigationForm.resetFields();
        setSelectedInvestigationRegions([]);
        setInvestigationWizardStep(0);
        setInvestigationDraftValues(null);
        setCreatedInvestigation(null);
        try {
            const { data: supervisor } = await api.get("/investigations/assignment-supervisor");
            setInvestigationSupervisor(supervisor);
            investigationForm.setFieldsValue({
                title: `${r.title}调查任务`,
                owner: supervisor.username,
                authorized_from: dayjs(),
                authorized_to: dayjs().add(30, "day"),
                right_type: "商标",
                customer_review: false,
                region: "全国",
                authorization_scope: "全国",
                description: `来源合同 ${r.serial_no}`,
            });
            setInvestigating(r);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "调查主管配置加载失败");
        }
    };
    const createInvestigation = async () => {
        const { investigating, investigationDraftValues, investigationForm, setInvestigationSubmitting, contractFile, setContractFile, setInvestigationError, setCreatedInvestigation, setInvestigationWizardStep, setSelectedRowKeys } = context;
        if (!investigating || !investigationDraftValues)
            return;
        const assignmentValues = await investigationForm.validateFields(["owner"]);
        const values = { ...investigationDraftValues, ...assignmentValues };
        setInvestigationSubmitting(true);
        try {
            const { data } = await api.post(`/contracts/${investigating.id}/investigation`, {
                ...values,
                authorized_from: formatRequiredDate(values.authorized_from, "授权开始日期"),
                authorized_to: formatRequiredDate(values.authorized_to, "授权结束日期"),
            });
            if (contractFile) {
                const attachment = new FormData();
                attachment.append("file", contractFile);
                attachment.append("record_id", String(data.id));
                attachment.append("category", "调查资料");
                await api.post("/attachments", attachment);
                setContractFile(null);
            }
            message.success(`调查任务 ${data.serial_no} 已创建`);
            setInvestigationError("");
            setCreatedInvestigation(data);
            setInvestigationWizardStep(2);
            setSelectedRowKeys([]);
        }
        catch (error: any) {
            const detail = error?.response?.data?.detail || error?.message || "调查任务创建失败";
            setInvestigationError(detail);
            message.error(detail);
        }
        finally {
            setInvestigationSubmitting(false);
        }
    };
    const advanceInvestigationWizard = async () => {
        const { investigationForm, setInvestigationDraftValues, setInvestigationError, setInvestigationWizardStep } = context;
        try {
            const values = await investigationForm.validateFields([
                "title", "right_type", "customer_review", "authorized_from", "authorized_to", "region", "authorization_scope", "description",
            ]);
            setInvestigationDraftValues(values);
            setInvestigationError("");
            setInvestigationWizardStep(1);
        }
        catch {
            setInvestigationError("请先完整填写调查授权信息");
        }
    };
    const startSelectedSeal = async (contract: Contract) => {
        const { loadWizardContext, setWizardStep, sealForm, setOpen } = context;
        if (!CONTRACT_SEAL_READY_STATUSES.includes(contract.status)) {
            message.warning("当前合同状态不支持申请用印");
            return;
        }
        try {
            const current = await loadWizardContext(contract.id);
            setWizardStep(3);
            sealForm.setFieldsValue({
                copies: 1,
                use_date: dayjs().add(1, "day"),
                delivery_method: "现场用印",
                document_names: "",
                purpose: `${current.title}合同用印`,
                submit: false,
            });
            setOpen(true);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "合同用印上下文加载失败");
        }
    };
    const openApproverSettings = async () => {
        const { profile, setApproverSettingsOpen, setApproverSettingsLoading, setApproverSettings, approverSettingsTargetUsername, setSelectedApproverUsernames } = context;
        if (profile.role !== "admin")
            return;
        setApproverSettingsOpen(true);
        setApproverSettingsLoading(true);
        try {
            const response = await api.get("/contracts/approver-settings");
            const items = (response.data.items || []) as ApproverSetting[];
            setApproverSettings(items);
            const selected = items.filter((item) => item.selected).map((item) => item.username);
            const target = approverSettingsTargetUsername && items.some((item) => item.username === approverSettingsTargetUsername)
                ? [approverSettingsTargetUsername, ...selected.filter((username) => username !== approverSettingsTargetUsername)]
                : selected;
            setSelectedApproverUsernames(target);
        }
        catch (error: any) {
            setApproverSettingsOpen(false);
            message.error(error?.response?.data?.detail || "合同审批人配置加载失败");
        }
        finally {
            setApproverSettingsLoading(false);
        }
    };
    const saveApproverSettings = async () => {
        const { setApproverSettingsSaving, selectedApproverUsernames, setDirectory, setApproverSettingsOpen } = context;
        setApproverSettingsSaving(true);
        try {
            const response = await api.put("/contracts/approver-settings", { usernames: selectedApproverUsernames });
            const feedback = normalizeContractActionResponse(response, "合同审批人设置保存失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            const directoryResponse = await api.get("/users/directory", { params: { purpose: "contract_approver" } });
            setDirectory((directoryResponse.data.items || []).filter((item: DirectoryUser) => item.is_active !== false));
            setApproverSettingsOpen(false);
            message.success("合同审批人设置已保存");
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "合同审批人设置保存失败"));
        }
        finally {
            setApproverSettingsSaving(false);
        }
    };
    return { submitArchiveClosure, saveContractObject, deleteContractObject, recoverWizard, openSubmitWizardFromList, save, submitWizard, approveWizard, createSealApplication, submit, openReview, approve, saveChange, reviewChange, openChanges, createContractEvent, openInvestigation, createInvestigation, advanceInvestigationWizard, startSelectedSeal, openApproverSettings, saveApproverSettings };
}
