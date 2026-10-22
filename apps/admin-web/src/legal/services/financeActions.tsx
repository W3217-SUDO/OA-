import type { UploadFile } from "antd";
import { message, Modal } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import type { MessageType } from "antd/es/message/interface";
import dayjs from "dayjs";
import type { Key } from "react";
import { api } from "../../api";
import { rememberBusinessRecordDetailTarget } from "../../businessRecordDetailNavigation";
import { buildCaseFeeContractOptions, defaultCaseFeeContractId } from "../../caseFeeContractOptions.mjs";
import { resolveCaseFeeInvoiceEligibility } from "../../caseFeeInvoiceEligibility.mjs";
import { resolveCaseFileTypeSelection } from "../../caseFifthBatchParity.mjs";
import { buildExternalPaymentRequestPayload } from "../../casePaymentUnitParity.mjs";
import { PLATFORM_AGENCY_FEE_SUBTYPE } from "../../caseRelationConsumption.mjs";
import { feeTypeSelection, initialFeeTypeId, type FeeTypeCatalogItem } from "../../feeTypeHierarchy.mjs";
import { formatRequiredDate } from "../../formSafety";
import { caseReceiptFiles } from "../caseReceiptFiles";
import { openCaseFeeFilesDialog } from "./caseFeeFilesDialog";
import { prepareInternalFeePayment, submitPreparedInternalPayments } from "./caseInternalFeePayment";
import type { CaseAssistedFee, CaseCommissionPreview, CaseCommissionPreviewRow, CaseCommissionResult, CaseDetailCapabilities, CaseFileTypeOption, CasePaymentTypeOption, CaseRow, ContractRow, PaymentTypeCreateTarget, Profile, TaskRow } from "../types";
import type { CaseInvoiceBatch, CaseInvoiceImportResult, LoadCaseInvoiceBatch } from "../hooks/useCaseInvoiceBatch";
/** legal finance operations; dependencies are read when each operation runs. */
export interface CaseFinanceDependencies {
    readonly invoiceBatch: CaseInvoiceBatch;
    readonly loadCaseInvoiceBatch: LoadCaseInvoiceBatch;
    readonly counselDetailAssistedFeePage: number;
    readonly counselDetailAssistedFeePageSize: number;
    readonly counselDetailAssistedFeeRequestRef: React.RefObject<number>;
    readonly counselDetailCaseIdRef: React.RefObject<number | null>;
    readonly setCounselDetailAssistedFees: React.Dispatch<React.SetStateAction<CaseAssistedFee[]>>;
    readonly setCounselDetailAssistedFeePage: React.Dispatch<React.SetStateAction<number>>;
    readonly setCounselDetailAssistedFeePageSize: React.Dispatch<React.SetStateAction<number>>;
    readonly setCounselDetailAssistedFeeTotal: React.Dispatch<React.SetStateAction<number>>;
    readonly viewingCounselCase: CaseRow | null;
    readonly setAssistedFeeSaving: React.Dispatch<React.SetStateAction<boolean>>;
    readonly assistedFeeForm: FormInstance<any>;
    readonly assistedFeeEditor: CaseAssistedFee | null;
    readonly refreshCounselSystemLogs: () => void;
    readonly setAssistedFeeModalOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setAssistedFeeEditor: React.Dispatch<React.SetStateAction<CaseAssistedFee | null>>;
    readonly assistedFeeConfirming: CaseAssistedFee | null;
    readonly assistedFeeConfirmForm: FormInstance<any>;
    readonly setAssistedFeeConfirming: React.Dispatch<React.SetStateAction<CaseAssistedFee | null>>;
    readonly settlementAmountCase: CaseRow | null;
    readonly settlementAmountForm: FormInstance<any>;
    readonly setSettlementAmountCase: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly openCounselDetail: (row: CaseRow, preferredTab?: string | undefined) => Promise<void>;
    readonly load: () => Promise<void>;
    readonly viewingCaseTask: TaskRow | null;
    readonly caseTaskFeedbackText: string;
    readonly setCaseTaskDetailLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly caseTaskFeedbackFiles: UploadFile<any>[];
    readonly setCaseTaskFeedbackText: React.Dispatch<React.SetStateAction<string>>;
    readonly setCaseTaskFeedbackFiles: React.Dispatch<React.SetStateAction<UploadFile<any>[]>>;
    readonly loadCaseTaskDetail: (task: TaskRow) => Promise<void>;
    readonly onNavigate: ((route: string) => void) | undefined;
    readonly batchFeeForm: FormInstance<any>;
    readonly selectedCaseKeys: React.Key[];
    readonly profile: Profile;
    readonly setBatchFeeOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly getCaseCapability: (row?: CaseRow | null | undefined) => CaseDetailCapabilities;
    readonly contracts: ContractRow[];
    readonly setContracts: React.Dispatch<React.SetStateAction<ContractRow[]>>;
    readonly fileTypeOptionsForCase: (caseType: unknown) => CaseFileTypeOption[];
    readonly setFeeSubtypePreset: React.Dispatch<React.SetStateAction<"" | "official" | "third-party" | "agency" | "other">>;
    readonly feeTypeCatalog: FeeTypeCatalogItem[];
    readonly feeForm: FormInstance<any>;
    readonly setCaseFeeCreateStep: React.Dispatch<React.SetStateAction<number>>;
    readonly setCreatedCaseFees: React.Dispatch<React.SetStateAction<CaseRow[]>>;
    readonly setCaseFeePaymentDrafts: React.Dispatch<React.SetStateAction<{
        payment_remark: string;
        payment_type_id?: number | undefined;
        payment_payee?: string | undefined;
        payment_account?: string | undefined;
    }[]>>;
    readonly setFeeCase: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly setCasePaymentTypesLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setCasePaymentTypes: React.Dispatch<React.SetStateAction<CasePaymentTypeOption[]>>;
    readonly setCasePaymentTypesError: React.Dispatch<React.SetStateAction<string>>;
    readonly casePaymentTypeRequestRef: React.RefObject<number>;
    readonly casePaymentTypeFeeRef: React.RefObject<number | null>;
    readonly paymentTypeCreateTarget: PaymentTypeCreateTarget | null;
    readonly paymentTypeCreateForm: FormInstance<any>;
    readonly setPaymentTypeCreating: React.Dispatch<React.SetStateAction<boolean>>;
    readonly paymentRequestForm: FormInstance<any>;
    readonly setPaymentTypeCreateTarget: React.Dispatch<React.SetStateAction<PaymentTypeCreateTarget | null>>;
    readonly setPaymentTypeSearch: React.Dispatch<React.SetStateAction<string>>;
    readonly feeCase: CaseRow | null;
    readonly editingFeeRow: CaseRow | null;
    readonly isInternalCaseFee: (row: CaseRow) => boolean;
    readonly setEditingFeeRow: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly caseFeePaymentDrafts: {
        payment_remark: string;
        payment_type_id?: number | undefined;
        payment_payee?: string | undefined;
        payment_account?: string | undefined;
    }[];
    readonly createdCaseFees: CaseRow[];
    readonly setCaseFeeSubmitting: React.Dispatch<React.SetStateAction<boolean>>;
    readonly caseFeeSubmitting: boolean;
    readonly closeCaseFeeCreator: () => void;
    readonly courtRefundFee: CaseRow | null;
    readonly courtRefundForm: FormInstance<any>;
    readonly setCourtRefundFee: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly counselDetailCapabilities: CaseDetailCapabilities;
    readonly setPaymentRequestFee: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly paymentRequestFee: CaseRow | null;
    readonly refundCompleting: CaseRow | null;
    readonly refundCompleteForm: FormInstance<any>;
    readonly setRefundCompleting: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly informDateForm: FormInstance<any>;
    readonly informDateFeeKeys: React.Key[] | null;
    readonly setInformDateFeeKeys: React.Dispatch<React.SetStateAction<React.Key[] | null>>;
    readonly feeInformTarget: CaseRow | null;
    readonly feeInformForm: FormInstance<any>;
    readonly setFeeInformSubmitting: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setFeeInformRecord: React.Dispatch<any>;
    readonly setFeeInformTarget: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly feeInformArrivalForm: FormInstance<any>;
    readonly setFeeInformArrivalOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly feeInformRecord: any;
    readonly feeInformBillForm: FormInstance<any>;
    readonly setFeeInformFile: React.Dispatch<React.SetStateAction<UploadFile<any>[]>>;
    readonly setFeeInformBillOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly feeInformFile: UploadFile<any>[];
    readonly feeInformLinkForm: FormInstance<any>;
    readonly setFeeInformLinkOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly openInformDateBatchUpdate: (keys: React.Key[]) => void;
    readonly requireSingleFee: (keys: React.Key[], row: CaseRow | undefined, action: string) => boolean;
    readonly openFeeInformCreator: (row: CaseRow) => void;
    readonly editCaseFee: (row: CaseRow) => MessageType | undefined;
    readonly deleteCaseFee: (row: CaseRow) => MessageType | undefined;
    readonly markCaseFeeNoPayment: (row: CaseRow) => MessageType | undefined;
    readonly markCaseFeeRefundNotRequired: (row: CaseRow) => MessageType | undefined;
    readonly selectedFirmFeeKeys: React.Key[];
    readonly selectedFirmFee: CaseRow | undefined;
    readonly setCaseCommissionLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setCaseCommissionPreview: React.Dispatch<React.SetStateAction<CaseCommissionPreview | null>>;
    readonly setCaseCommissionResult: React.Dispatch<React.SetStateAction<CaseCommissionResult | null>>;
    readonly setCaseCommissionRows: React.Dispatch<React.SetStateAction<CaseCommissionPreviewRow[]>>;
    readonly caseCommissionPreview: CaseCommissionPreview | null;
    readonly caseCommissionRows: CaseCommissionPreviewRow[];
    readonly setCaseCommissionSubmitting: React.Dispatch<React.SetStateAction<boolean>>;
}
export function createCaseFinanceActions(context: CaseFinanceDependencies) {
    const loadCounselDetailAssistedFees = async (caseId: number, page = context.counselDetailAssistedFeePage, pageSize = context.counselDetailAssistedFeePageSize) => {
        const { counselDetailAssistedFeeRequestRef, counselDetailCaseIdRef, setCounselDetailAssistedFees, setCounselDetailAssistedFeePage, setCounselDetailAssistedFeePageSize, setCounselDetailAssistedFeeTotal } = context;
        const requestId = ++counselDetailAssistedFeeRequestRef.current;
        try {
            const { data } = await api.get(`/cases/${caseId}/assisted-fees`, { params: { page, page_size: pageSize } });
            if (requestId !== counselDetailAssistedFeeRequestRef.current || counselDetailCaseIdRef.current !== caseId)
                return;
            const items = Array.isArray(data?.items) ? data.items : [];
            setCounselDetailAssistedFees(items);
            setCounselDetailAssistedFeePage(Number(data?.page) || page);
            setCounselDetailAssistedFeePageSize(Number(data?.page_size) || pageSize);
            setCounselDetailAssistedFeeTotal(Number(data?.total) || items.length);
        }
        catch (error: any) {
            if (requestId !== counselDetailAssistedFeeRequestRef.current || counselDetailCaseIdRef.current !== caseId)
                return;
            setCounselDetailAssistedFees([]);
            setCounselDetailAssistedFeeTotal(0);
            message.error(error?.response?.data?.detail || "资助费用加载失败");
        }
    };
    const saveCounselDetailAssistedFee = async () => {
        const { viewingCounselCase, setAssistedFeeSaving, assistedFeeForm, assistedFeeEditor, refreshCounselSystemLogs, setAssistedFeeModalOpen, setAssistedFeeEditor, counselDetailAssistedFeePageSize } = context;
        if (!viewingCounselCase)
            return;
        setAssistedFeeSaving(true);
        try {
            const values = await assistedFeeForm.validateFields();
            const payload = {
                assisted_type: String(values.assisted_type || "").trim(),
                ...(assistedFeeEditor
                    ? { amount: values.amount === undefined || values.amount === null ? null : Number(values.amount) }
                    : values.amount === undefined || values.amount === null ? {} : { amount: Number(values.amount) }),
                remark: String(values.remark || "").trim(),
            };
            if (assistedFeeEditor) {
                await api.put(`/cases/${viewingCounselCase.id}/assisted-fees/${assistedFeeEditor.id}`, payload);
                message.success("资助费用已修改");
            }
            else {
                await api.post(`/cases/${viewingCounselCase.id}/assisted-fees`, payload);
                message.success("资助费用已提交，等待办理确认");
            }
            refreshCounselSystemLogs();
            setAssistedFeeModalOpen(false);
            setAssistedFeeEditor(null);
            assistedFeeForm.resetFields();
            await loadCounselDetailAssistedFees(viewingCounselCase.id, 1, counselDetailAssistedFeePageSize);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || (assistedFeeEditor ? "修改资助费用失败" : "新建资助费用失败"));
        }
        finally {
            setAssistedFeeSaving(false);
        }
    };
    const confirmCounselDetailAssistedFee = async () => {
        const { viewingCounselCase, assistedFeeConfirming, setAssistedFeeSaving, assistedFeeConfirmForm, refreshCounselSystemLogs, setAssistedFeeConfirming, counselDetailAssistedFeePage, counselDetailAssistedFeePageSize } = context;
        if (!viewingCounselCase || !assistedFeeConfirming)
            return;
        setAssistedFeeSaving(true);
        try {
            const values = await assistedFeeConfirmForm.validateFields();
            await api.post(`/cases/${viewingCounselCase.id}/assisted-fees/${assistedFeeConfirming.id}/confirm`, {
                confirmed_date: formatRequiredDate(values.confirmed_date, "确认日期"),
                remark: String(values.remark || "").trim(),
            });
            refreshCounselSystemLogs();
            message.success("资助费用已确认办理");
            setAssistedFeeConfirming(null);
            assistedFeeConfirmForm.resetFields();
            await loadCounselDetailAssistedFees(viewingCounselCase.id, counselDetailAssistedFeePage, counselDetailAssistedFeePageSize);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "确认办理资助费用失败");
        }
        finally {
            setAssistedFeeSaving(false);
        }
    };
    const submitSettlementAmount = async () => {
        const { settlementAmountCase, settlementAmountForm, setSettlementAmountCase, openCounselDetail, load } = context;
        if (!settlementAmountCase)
            return;
        try {
            const values = await settlementAmountForm.validateFields();
            const { data } = await api.put(`/cases/${settlementAmountCase.id}/settlement-amount`, values);
            message.success("诉讼或判决金额已更新");
            setSettlementAmountCase(null);
            settlementAmountForm.resetFields();
            await openCounselDetail(data);
            void load();
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "金额更新失败");
        }
    };
    const submitCaseTaskFeedback = async () => {
        const { viewingCaseTask, caseTaskFeedbackText, setCaseTaskDetailLoading, caseTaskFeedbackFiles, setCaseTaskFeedbackText, setCaseTaskFeedbackFiles, loadCaseTaskDetail } = context;
        if (!viewingCaseTask)
            return;
        if (!caseTaskFeedbackText.trim())
            return message.warning("请输入留言内容");
        setCaseTaskDetailLoading(true);
        try {
            const body = new FormData();
            body.append("comment", caseTaskFeedbackText.trim());
            for (const file of caseTaskFeedbackFiles) {
                const source = file.originFileObj || (file as unknown as File);
                if (source && typeof (source as Blob).arrayBuffer === "function")
                    body.append("files", source);
            }
            await api.post(`/tasks/${viewingCaseTask.id}/feedback`, body);
            message.success("留言及附件已保存");
            setCaseTaskFeedbackText("");
            setCaseTaskFeedbackFiles([]);
            await loadCaseTaskDetail(viewingCaseTask);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "留言保存失败");
        }
        finally {
            setCaseTaskDetailLoading(false);
        }
    };
    const openRelatedFee = async (fee: CaseRow) => {
        const { onNavigate } = context;
        if (!fee.id) {
            message.warning("当前费用记录不存在或无权查看");
            return;
        }
        try {
            const { data } = await api.get(`/records/${fee.id}`);
            if (data.module !== "finance")
                throw new Error("关联记录不是费用申请");
            if (!rememberBusinessRecordDetailTarget({ id: data.id, module: "finance" })) {
                message.warning("当前费用记录不存在或无权查看");
                return;
            }
            onNavigate?.("finance-fee-query");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || error?.message || "费用记录不存在或无权查看");
        }
    };
    const submitCounselBatchFee = async () => {
        const { batchFeeForm, selectedCaseKeys, profile, setBatchFeeOpen, load } = context;
        const values = await batchFeeForm.validateFields();
        const caseIds = selectedCaseKeys.map(Number);
        if (!caseIds.length)
            return message.warning("请选择需要新增费用的法律顾问案件");
        const caseContracts: Array<{ case_id: number; contract_record_id: number }> = Array.isArray(values.case_contracts)
            ? values.case_contracts.map((item: any) => ({
                case_id: Number(item?.case_id),
                contract_record_id: Number(item?.contract_record_id),
            }))
            : [];
        if (values.expense_scope !== "内部") {
            const selectedCaseIds = new Set(caseIds);
            const uniqueCaseIds = new Set(caseContracts.map((item: { case_id: number; contract_record_id: number }) => item.case_id));
            if (caseContracts.length !== caseIds.length
                || caseContracts.some((item: { case_id: number; contract_record_id: number }) => !selectedCaseIds.has(item.case_id) || !item.contract_record_id)
                || uniqueCaseIds.size !== caseIds.length) {
                return message.warning("请为每个案件分别选择当前客户名下的有效合同");
            }
        }
        try {
            const { data } = await api.post("/cases/batch-fees", {
                case_ids: caseIds,
                ...(values.expense_scope === "内部" ? {} : { case_contracts: caseContracts }),
                amount: values.amount,
                fee_type_id: values.fee_type_id,
                expense_scope: values.expense_scope,
                expense_subtype: values.expense_subtype,
                handler: values.handler || profile.username,
                description: values.description || "",
            });
            message.success(`已为 ${data.created} 个案件创建费用草稿`);
            setBatchFeeOpen(false);
            batchFeeForm.resetFields();
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "批量新增费用失败");
        }
    };
    const openCaseFee = async (row: CaseRow, expenseScope: "律所" | "平台" | "内部" = "律所", expenseSubtype?: string) => {
        const { getCaseCapability, contracts, setContracts, fileTypeOptionsForCase, setFeeSubtypePreset, feeTypeCatalog, feeForm, profile, setCaseFeeCreateStep, setCreatedCaseFees, setCaseFeePaymentDrafts, setFeeCase } = context;
        if (!getCaseCapability(row).can_create_finance)
            return message.warning("当前账号没有新增案件费用权限");
        let availableContracts = contracts;
        if (expenseScope === "律所" || expenseScope === "平台") {
            try {
                const response = await api.get(`/cases/${row.id}/fee-contracts`, { params: { expense_scope: expenseScope } });
                availableContracts = Array.from(new Map([
                    ...contracts,
                    ...(response.data.items || []),
                ].map((contract: CaseRow) => [contract.id, contract])).values());
                setContracts(availableContracts);
            }
            catch (error: any) {
                return message.error(error?.response?.data?.detail || `加载${expenseScope}合同失败`);
            }
        }
        const eligibleContracts = buildCaseFeeContractOptions(availableContracts, row, null, expenseScope);
        if ((expenseScope === "律所" || expenseScope === "平台") && !eligibleContracts.length) {
            return message.warning(`当前案件客户名下没有${expenseScope}合同，无法新增${expenseScope}费用`);
        }
        const sourceFileType = resolveCaseFileTypeSelection("", fileTypeOptionsForCase(row.data.case_type));
        const officialPreset = expenseSubtype === "官费";
        const thirdPartyPreset = expenseSubtype === "第三方费用";
        const agencyPreset = expenseSubtype === "代理费" || expenseSubtype === PLATFORM_AGENCY_FEE_SUBTYPE;
        const otherPreset = expenseSubtype === "其他费用";
        setFeeSubtypePreset(officialPreset ? "official" : thirdPartyPreset ? "third-party" : agencyPreset ? "agency" : otherPreset ? "other" : "");
        const preset = officialPreset ? "official" : thirdPartyPreset ? "third-party" : agencyPreset ? "agency" : otherPreset ? "other" : "";
        const preferredSubtype = expenseScope === "平台" && agencyPreset ? PLATFORM_AGENCY_FEE_SUBTYPE : expenseSubtype || "";
        const initialTypeId = initialFeeTypeId(feeTypeCatalog, expenseScope, preset, preferredSubtype);
        const initialType = feeTypeSelection(feeTypeCatalog, initialTypeId);
        feeForm.resetFields();
        feeForm.setFieldsValue({ source_file_type: sourceFileType, items: [{
                    title: `${row.title}案件费用`, amount: row.data.amount || undefined,
                    // 首次带入案件绑定，用户仍可为本笔费用改选合同。
                    contract_record_id: defaultCaseFeeContractId(availableContracts, row, expenseScope),
                    expense_scope: expenseScope, fee_type_id: initialTypeId,
                    expense_subtype: initialType?.name,
                    fee_type: initialType?.base_fee_type,
                    handler: profile.username || row.owner, court: row.data.court || "", payee: expenseScope === "内部" ? undefined : row.data.court || "",
                    deadline: undefined, description: "",
                }] });
        setCaseFeeCreateStep(0);
        setCreatedCaseFees([]);
        setCaseFeePaymentDrafts([]);
        setFeeCase(row);
    };
    const loadCasePaymentTypes = async (feeId: number, keyword = "") => {
        const { setCasePaymentTypesLoading, setCasePaymentTypes, setCasePaymentTypesError, casePaymentTypeRequestRef, casePaymentTypeFeeRef } = context;
        const requestId = ++casePaymentTypeRequestRef.current;
        casePaymentTypeFeeRef.current = feeId;
        setCasePaymentTypesLoading(true);
        setCasePaymentTypesError("");
        setCasePaymentTypes([]);
        try {
            const { data } = await api.get(`/finance/fees/${feeId}/payment-types`, { params: { keyword } });
            const items = Array.isArray(data?.items) ? data.items : [];
            if (requestId === casePaymentTypeRequestRef.current)
                setCasePaymentTypes(items);
            return items as CasePaymentTypeOption[];
        }
        catch (error: any) {
            if (requestId === casePaymentTypeRequestRef.current)
                setCasePaymentTypesError(error?.response?.data?.detail || "付款单位加载失败，请重试");
            return null;
        }
        finally {
            if (requestId === casePaymentTypeRequestRef.current)
                setCasePaymentTypesLoading(false);
        }
    };
    const createCasePaymentType = async () => {
        const { paymentTypeCreateTarget, paymentTypeCreateForm, setPaymentTypeCreating, setCasePaymentTypes, setCasePaymentTypesError, setCaseFeePaymentDrafts, paymentRequestForm, setPaymentTypeCreateTarget, setPaymentTypeSearch } = context;
        if (!paymentTypeCreateTarget)
            return;
        const values = await paymentTypeCreateForm.validateFields();
        setPaymentTypeCreating(true);
        try {
            const { data } = await api.post(`/finance/fees/${paymentTypeCreateTarget.feeId}/payment-types`, values);
            const created = data as CasePaymentTypeOption;
            setCasePaymentTypes((items) => [...items.filter((item) => item.id !== created.id), created]);
            setCasePaymentTypesError("");
            if (paymentTypeCreateTarget.draftIndex !== undefined) {
                setCaseFeePaymentDrafts((items) => items.map((item, index) => index === paymentTypeCreateTarget.draftIndex ? { ...item, payment_type_id: created.id } : item));
            }
            else {
                paymentRequestForm.setFieldValue("payment_type_id", created.id);
            }
            message.success("付款单位已新增并保存到系统参数-付款类型");
            setPaymentTypeCreateTarget(null);
            setPaymentTypeSearch("");
            paymentTypeCreateForm.resetFields();
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "付款单位新增失败");
        }
        finally {
            setPaymentTypeCreating(false);
        }
    };
    const createCaseFee = async () => {
        const { feeCase, editingFeeRow, viewingCounselCase, feeForm, isInternalCaseFee, setEditingFeeRow, load, openCounselDetail, setCreatedCaseFees, setCaseFeePaymentDrafts, setCaseFeeCreateStep, closeCaseFeeCreator } = context;
        const caseSource = feeCase || (editingFeeRow ? viewingCounselCase : null);
        if (!caseSource)
            return;
        const values = await feeForm.validateFields();
        const { source_file_type: sourceFileType, ...feeValues } = values;
        // This selector constrains the UI only; the current finance API has no source-file-type field.
        void sourceFileType;
        try {
            const commonPayload = { customer: feeCase?.customer || editingFeeRow?.customer || "", case_no: feeCase?.serial_no || editingFeeRow?.data.case_no || "", case_record_id: feeCase?.id || editingFeeRow?.data.case_id };
            if (editingFeeRow) {
                const { commission_mode, commission_details, ...feePayload } = feeValues;
                void commission_mode;
                void commission_details;
                const payload = {
                    ...feePayload,
                    ...commonPayload,
                    deadline: feeValues.deadline ? formatRequiredDate(feeValues.deadline, "截止日期") : undefined,
                };
                const endpoint = isInternalCaseFee(editingFeeRow) ? `/finance/internal-fees/${editingFeeRow.id}` : `/finance/fees/${editingFeeRow.id}`;
                const { data } = await api.put(endpoint, payload);
                message.success(`费用 ${data.serial_no} 已保存`);
                setEditingFeeRow(null);
                feeForm.resetFields();
                await load();
                if (viewingCounselCase)
                    await openCounselDetail(viewingCounselCase);
            }
            else {
                const created: CaseRow[] = [];
                for (const item of feeValues.items || []) {
                    const { commission_mode, commission_details, ...feePayload } = item;
                    void commission_mode;
                    void commission_details;
                    const payload = {
                        ...feePayload,
                        ...commonPayload,
                        deadline: item.deadline ? formatRequiredDate(item.deadline, "截止日期") : undefined,
                    };
                    const endpoint = item.expense_scope === "内部" ? "/finance/internal-fees" : "/finance/fees";
                    const { data } = await api.post(endpoint, payload);
                    created.push(data);
                }
                message.success(`已创建 ${created.length} 条费用草稿`);
                const payable = created.filter((row) => row.data.fee_type !== "代理费");
                if (!payable.length) {
                    message.info("代理费已保存；新增提成请先勾选该代理费，再选择“新增案件费用 > 新建提成(选择费用)”");
                    closeCaseFeeCreator();
                    await load();
                    if (viewingCounselCase)
                        await openCounselDetail(viewingCounselCase);
                    return;
                }
                setCreatedCaseFees(payable);
                setCaseFeePaymentDrafts(payable.map((row) => ({
                    payment_remark: "",
                    payment_payee: row.data.expense_scope === "内部" ? String(row.data.payee || row.owner || "") : undefined,
                    payment_account: row.data.expense_scope === "内部" ? String(row.data.payee || row.owner || "") : undefined,
                })));
                if (payable[0] && payable[0].data.expense_scope !== "内部")
                    await loadCasePaymentTypes(payable[0].id);
                setCaseFeeCreateStep(1);
                await load();
                if (viewingCounselCase)
                    await openCounselDetail(viewingCounselCase);
            }
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "费用保存失败");
        }
    };
    const submitCreatedCaseFeePayments = async () => {
        const { caseFeePaymentDrafts, createdCaseFees, setCaseFeeSubmitting, feeCase, closeCaseFeeCreator, load, viewingCounselCase, openCounselDetail, isInternalCaseFee } = context;
        if (createdCaseFees.length && createdCaseFees.every(isInternalCaseFee)) return submitPreparedInternalPayments(context);
        if (caseFeePaymentDrafts.some((item, index) => createdCaseFees[index]?.data.expense_scope !== "内部" && createdCaseFees[index]?.data.fee_type !== "官方费用" && !item.payment_type_id)) {
            message.warning("请选择系统付款单位");
            return;
        }
        if (caseFeePaymentDrafts.some((item, index) => createdCaseFees[index]?.data.expense_scope === "内部" && (!item.payment_payee?.trim() || !item.payment_account?.trim()))) {
            message.warning("请输入内部费用收款人和付款账号");
            return;
        }
        setCaseFeeSubmitting(true);
        try {
            for (const [index, row] of createdCaseFees.entries()) {
                const item = caseFeePaymentDrafts[index];
                await api.post(`/finance/fees/${row.id}/submit`, {
                    amount: Number(row.data.amount || 0),
                    ...(row.data.expense_scope === "内部" ? {
                        payment_payee: String(item.payment_payee || "").trim(),
                        payment_account: String(item.payment_account || "").trim(),
                    } : { payment_type_id: item.payment_type_id }),
                    payment_remark: String(item.payment_remark || "").trim(),
                    comment: String(item.payment_remark || `案件 ${feeCase?.serial_no || ""} 申请付款`).trim(),
                });
            }
            message.success(`已提交 ${createdCaseFees.length} 条付款申请`);
            closeCaseFeeCreator();
            await load();
            if (viewingCounselCase)
                await openCounselDetail(viewingCounselCase);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "付款申请提交失败");
        }
        finally {
            setCaseFeeSubmitting(false);
        }
    };
    const createCourtRefund = async () => {
        const { courtRefundFee, viewingCounselCase, courtRefundForm, profile, setCourtRefundFee, openCounselDetail } = context;
        if (!courtRefundFee || !viewingCounselCase)
            return;
        if (courtRefundForm.getFieldValue("court_refund_submitting"))
            return;
        if (courtRefundForm.getFieldValue("court_refund_confirmed_request"))
            return message.warning("上次请求已核实，当前修改未提交，请关闭并重新打开后申请");
        const storageKey = `sunhold:court-refund-pending:${profile.username}:${courtRefundFee.id}`;
        let checkingPrevious = false;
        courtRefundForm.setFieldValue("court_refund_submitting", true);
        try {
            const values = await courtRefundForm.validateFields();
            const requestKey = courtRefundForm.getFieldValue("request_key");
            if (!requestKey)
                throw new Error("退款请求标识缺失，请关闭并重新打开后申请");
            const currentRequest = {
                request_key: requestKey,
                fee_record_id: courtRefundFee.id,
                case_no: viewingCounselCase.serial_no,
                customer: viewingCounselCase.customer,
                court: courtRefundFee.data.court || viewingCounselCase.data.court || "",
                original_payment_no: courtRefundFee.data.document_no || courtRefundFee.serial_no,
                amount: Number(values.amount),
                applicant: profile.display_name || profile.username,
                reason: courtRefundFee.data.fee_type === "代理费" ? "代理费法院退费" : "诉讼费退款",
            };
            const saved = window.sessionStorage.getItem(storageKey);
            const request: typeof currentRequest = saved ? JSON.parse(saved) : currentRequest;
            checkingPrevious = Boolean(saved);
            if (request.fee_record_id !== courtRefundFee.id)
                throw new Error("待核对请求的来源费用不一致，不能继续提交");
            let response;
            if (checkingPrevious) {
                // 未知结果只查证原请求，不能换键或按当前修改再次写入。
                response = request.amount === 0
                    ? await api.get(`/records/${courtRefundFee.id}`)
                    : await api.get(`/finance/fees/${courtRefundFee.id}/court-refund/request`, {
                        params: { request_key: request.request_key },
                    });
            } else {
                window.sessionStorage.setItem(storageKey, JSON.stringify(request));
                response = request.amount === 0
                    ? await api.post(`/finance/fees/${courtRefundFee.id}/court-refund/clear-projection`)
                    : await api.post("/finance/refunds", request);
            }
            const result = response.data;
            const verified = request.amount === 0
                ? result?.module === "finance" && result.id === request.fee_record_id
                    && result.data?.refund_amount_override === 0 && result.data?.refund_requested_amount_override === 0
                : result?.module === "refund" && Number(result.id) > 0
                    && Object.entries(request).every(([key, value]) => result.data?.[key] === value);
            if (!verified)
                throw new Error("退款处理结果尚未核实，请再次确认以只读核对，勿重复申请");
            courtRefundForm.setFieldValue("court_refund_confirmed_request", true);
            window.sessionStorage.removeItem(storageKey);
            if (checkingPrevious && request.amount !== currentRequest.amount) {
                message.warning(`已核实上次金额${request.amount}的处理结果；当前金额${currentRequest.amount}未提交，请关闭并重新打开后申请`);
                return;
            }
            message.success(request.amount === 0 ? "法院退费金额已归零" : "法院退费申请已创建");
            setCourtRefundFee(null);
            courtRefundForm.resetFields();
            await openCounselDetail(viewingCounselCase);
        }
        catch (error: any) {
            if (!error?.errorFields) {
                const status = error?.response?.status;
                if (!checkingPrevious && status >= 400 && status < 500)
                    window.sessionStorage.removeItem(storageKey);
                message.error(checkingPrevious && status === 404
                    ? "尚未查到上次请求，结果仍未确认，请稍后核对，勿重复申请"
                    : !status || status >= 500
                        ? `退款处理结果未确认，请再次确认以只读核对，勿重复申请${error?.message ? `：${error.message}` : ""}`
                        : error?.response?.data?.detail || "退款申请失败");
            }
        }
        finally {
            courtRefundForm.setFieldValue("court_refund_submitting", false);
        }
    };
    const openPaymentRequest = async (row: CaseRow) => {
        const { counselDetailCapabilities, paymentRequestForm, setPaymentTypeSearch, setPaymentRequestFee } = context;
        if (!counselDetailCapabilities.can_create_finance)
            return message.warning("当前账号没有申请付款权限");
        if (!["草稿", "已退回", "已审批", "部分付款", "已驳回", "已撤回"].includes(row.status)) {
            return message.warning(`当前费用状态“${row.status}”不能申请付款`);
        }
        const paid = Number(row.data.paid_amount || 0);
        const requested = Number(row.data.payment_requested_amount || 0);
        const remaining = Number(row.data.payment_remaining_amount ?? Math.max(Number(row.data.amount || 0) - Math.max(paid, requested), 0));
        if (remaining <= 0)
            return message.warning("该费用没有可申请付款的余额");
        const options = await loadCasePaymentTypes(row.id);
        const storedPaymentTypeId = Number(row.data.payment_type_id) || undefined;
        paymentRequestForm.resetFields();
        paymentRequestForm.setFieldsValue({
            amount: remaining,
            payment_remark: row.data.payment_remark || row.description || "",
            payment_type_id: options?.some((item) => item.id === storedPaymentTypeId) ? storedPaymentTypeId : undefined,
        });
        setPaymentTypeSearch("");
        setPaymentRequestFee(row);
    };
    const submitPaymentRequest = async () => {
        const { paymentRequestFee, paymentRequestForm, viewingCounselCase, setPaymentRequestFee, openCounselDetail } = context;
        if (!paymentRequestFee)
            return;
        try {
            const values = await paymentRequestForm.validateFields();
            await api.post(`/finance/fees/${paymentRequestFee.id}/submit`, buildExternalPaymentRequestPayload(values, `案件 ${paymentRequestFee.data.case_no || viewingCounselCase?.serial_no || ""} 申请付款`));
            message.success("付款申请已提交审批");
            setPaymentRequestFee(null);
            paymentRequestForm.resetFields();
            if (viewingCounselCase)
                await openCounselDetail(viewingCounselCase);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "付款申请提交失败");
        }
    };
    const previewInternalPayment = async (selection: CaseRow | CaseRow[]) => {
        const { counselDetailCapabilities, viewingCounselCase, profile, onNavigate, caseFeeSubmitting,
            setCaseFeeSubmitting, setCreatedCaseFees, setCaseFeePaymentDrafts, setCaseFeeCreateStep,
            setFeeCase, setEditingFeeRow, feeForm } = context;
        if (!counselDetailCapabilities.can_apply_fee_payment)
            return message.warning("当前账号没有申请付款权限");
        if (!viewingCounselCase || caseFeeSubmitting) return;
        setCaseFeeSubmitting(true);
        try {
            const rows = await prepareInternalFeePayment(Array.isArray(selection) ? selection : [selection], viewingCounselCase, profile.username, onNavigate);
            if (!rows) return;
            setEditingFeeRow(null);
            feeForm.resetFields();
            feeForm.setFieldsValue({ items: rows.map((row) => ({ ...row.data, expense_scope: "内部" })) });
            setCreatedCaseFees(rows);
            setCaseFeePaymentDrafts(rows.map((row) => ({ payment_remark: String(row.data.payment_remark || ""),
                payment_payee: String(row.data.payment_payee || row.data.payee || ""),
                payment_account: String(row.data.payment_account || "") })));
            setCaseFeeCreateStep(1);
            setFeeCase(viewingCounselCase);
        } catch (error: any) {
            message.error(error?.response?.data?.detail || error?.message || "内部费用申请信息读取失败");
        } finally {
            setCaseFeeSubmitting(false);
        }
    };
    const submitCaseFeePayment = async (row: CaseRow) => {
        const { onNavigate } = context;
        if (row.data.expense_scope === "内部" || row.data.fee_type === "内部费用") {
            await previewInternalPayment(row);
            return;
        }
        if (["待审批", "已付款"].includes(row.status)) {
            const labels: Record<string, string> = {
                待审批: "付款申请已经提交，正在等待审批",
                已审批: "付款申请已经审批，可由财务登记付款",
                部分付款: "付款申请正在分次付款",
                已付款: "该费用已经付款",
            };
            message.info(labels[row.status]);
            rememberBusinessRecordDetailTarget({ id: row.id, module: "finance" });
            onNavigate?.("finance-payment-mine");
            return;
        }
        openPaymentRequest(row);
    };
    const startCaseInvoiceImport = async () => {
        const { invoiceBatch, loadCaseInvoiceBatch } = context;
        const batch = invoiceBatch.current.current;
        if (batch.loading) return;
        const sourceIds = batch.sourceAttachmentIds.filter(id => batch.rows.some(row => row.id === id && row.record_id === null));
        if (batch.resultUnconfirmed)
            return message.warning("导入结果尚未确认，不能重复提交；源文件查询不能恢复完整结果清单");
        if (batch.error || !sourceIds.length)
            return message.warning("请先上传发票文件");
        const requestId = invoiceBatch.begin();
        if (requestId === undefined) return;
        let confirmedResult = false;
        try {
            const { data } = await api.post<CaseInvoiceImportResult>("/cases/invoice-files/import", { attachment_ids: sourceIds });
            if (!invoiceBatch.isCurrent(requestId)) return;
            if (data.processed !== sourceIds.length || !Number.isSafeInteger(data.matched) || data.matched < 0 ||
                !Number.isSafeInteger(data.unmatched) || data.unmatched < 0 || data.matched + data.unmatched !== data.processed ||
                !Array.isArray(data.result_attachment_ids) || !data.result_attachment_ids.length ||
                data.result_attachment_ids.some(id => !Number.isSafeInteger(id) || id <= 0) ||
                sourceIds.some(id => !data.result_attachment_ids.includes(id)) ||
                new Set(data.result_attachment_ids).size !== data.result_attachment_ids.length)
                throw new Error("导入响应缺少有效结果附件编号，请查询当前批次状态，勿重复提交");
            confirmedResult = true;
            invoiceBatch.update(requestId, { attachmentIds: data.result_attachment_ids });
            if (data.unmatched)
                message.warning(`已处理 ${data.processed} 个文件，匹配发票申请 ${data.matched} 个，${data.unmatched} 个导入失败，请查看导入状态`);
            else
                message.success(`已完成 ${data.processed} 个发票文件导入并关联申请费用`);
            await loadCaseInvoiceBatch(data.result_attachment_ids, requestId);
        }
        catch (error: any) {
            if (!invoiceBatch.isCurrent(requestId)) return;
            const detail = error?.response?.data?.detail || error?.message || "发票文件导入失败，请先查询当前批次状态";
            const errorMessage = typeof detail === "string" ? detail : "发票文件导入失败，请先查询当前批次状态";
            const rejectedBeforeImport = [400, 401, 403, 404, 409, 422].includes(error?.response?.status);
            invoiceBatch.update(requestId, { error: errorMessage, resultUnconfirmed: !confirmedResult && !rejectedBeforeImport });
            message.error(errorMessage);
        }
        finally {
            invoiceBatch.update(requestId, { loading: false });
        }
    };
    const completeRefund = async () => {
        const { refundCompleting, refundCompleteForm, setRefundCompleting, load } = context;
        if (!refundCompleting)
            return;
        const values = await refundCompleteForm.validateFields();
        await api.post(`/finance/refunds/${refundCompleting.id}/complete`, {
            actual_date: formatRequiredDate(values.actual_date, "实际退款日期"),
            voucher_no: values.voucher_no,
            comment: values.comment || "",
        });
        message.success("退款到账登记完成");
        setRefundCompleting(null);
        refundCompleteForm.resetFields();
        await load();
    };
    const submitInformDateBatchUpdate = async () => {
        const { informDateForm, informDateFeeKeys, setInformDateFeeKeys, viewingCounselCase, openCounselDetail } = context;
        const values = await informDateForm.validateFields();
        const feeIds = (informDateFeeKeys || []).map(Number).filter(id => Number.isInteger(id) && id > 0);
        if (!feeIds.length)
            return message.warning("请选择需要修改通知日期的费用记录");
        try {
            const { data } = await api.post("/finance/case-fees/batch-update", {
                fee_ids: feeIds,
                inform_date: formatRequiredDate(values.inform_date, "通知日期"),
            });
            message.success(`已修改 ${data.updated ?? feeIds.length} 条费用的通知日期`);
            setInformDateFeeKeys(null);
            informDateForm.resetFields();
            if (viewingCounselCase)
                await openCounselDetail(viewingCounselCase);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "批量修改通知日期失败");
        }
    };
    const refreshCaseFeeDetail = async () => {
        const { load, viewingCounselCase, openCounselDetail } = context;
        await load();
        if (viewingCounselCase)
            await openCounselDetail(viewingCounselCase);
    };
    const createFeeInform = async () => {
        const { feeInformTarget, feeInformForm, setFeeInformSubmitting, setFeeInformRecord } = context;
        if (!feeInformTarget)
            return;
        try {
            const values = await feeInformForm.validateFields();
            setFeeInformSubmitting(true);
            const { data } = await api.post(`/finance/fees/${feeInformTarget.id}/informs`, {
                inform_date: formatRequiredDate(values.inform_date, "通知日期"), remark: String(values.remark || "").trim(),
            });
            setFeeInformRecord(data);
            message.success("费用通知已新建");
            await refreshCaseFeeDetail();
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "新建费用通知失败");
        }
        finally {
            setFeeInformSubmitting(false);
        }
    };
    const loadLatestFeeInform = async (row: CaseRow) => {
        const { setFeeInformTarget, setFeeInformRecord } = context;
        const { data } = await api.get(`/finance/fees/${row.id}/informs`);
        const latest = Array.isArray(data?.items) ? data.items[0] : null;
        if (!latest) {
            message.warning("请先新建费用通知");
            return null;
        }
        setFeeInformTarget(row);
        setFeeInformRecord(latest);
        return latest;
    };
    const openFeeInformArrival = async (row: CaseRow) => {
        const { feeInformArrivalForm, setFeeInformArrivalOpen } = context;
        try {
            const inform = await loadLatestFeeInform(row);
            if (!inform)
                return;
            feeInformArrivalForm.resetFields();
            feeInformArrivalForm.setFieldsValue({ receivable_amount: inform.data?.receivable_amount, received_amount: inform.data?.receivable_amount, received_date: dayjs(), remark: "" });
            setFeeInformArrivalOpen(true);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "加载费用通知失败");
        }
    };
    const confirmFeeInformArrival = async () => {
        const { feeInformRecord, feeInformArrivalForm, setFeeInformSubmitting, setFeeInformArrivalOpen } = context;
        if (!feeInformRecord)
            return;
        try {
            const values = await feeInformArrivalForm.validateFields();
            setFeeInformSubmitting(true);
            await api.post(`/finance/fee-informs/${feeInformRecord.id}/arrival`, { ...values, received_date: formatRequiredDate(values.received_date, "到账日期"), remark: String(values.remark || "").trim() });
            message.success("费用通知到账已确认");
            setFeeInformArrivalOpen(false);
            await refreshCaseFeeDetail();
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "到账确认失败");
        }
        finally {
            setFeeInformSubmitting(false);
        }
    };
    const openFeeInformBill = async (row: CaseRow) => {
        const { feeInformBillForm, setFeeInformFile, setFeeInformBillOpen } = context;
        try {
            const inform = await loadLatestFeeInform(row);
            if (!inform)
                return;
            feeInformBillForm.resetFields();
            feeInformBillForm.setFieldsValue({ bill_amount: inform.data?.received_amount, bill_date: dayjs() });
            setFeeInformFile([]);
            setFeeInformBillOpen(true);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "加载费用通知失败");
        }
    };
    const uploadFeeInformBill = async () => {
        const { feeInformRecord, feeInformBillForm, feeInformFile, setFeeInformSubmitting, setFeeInformBillOpen, setFeeInformFile } = context;
        if (!feeInformRecord)
            return;
        try {
            const values = await feeInformBillForm.validateFields();
            const source = feeInformFile[0]?.originFileObj || (feeInformFile[0] as unknown as File);
            if (!source || typeof (source as Blob).arrayBuffer !== "function")
                return message.warning("请上传票据文件");
            const body = new FormData();
            body.append("file", source);
            body.append("bill_no", String(values.bill_no).trim());
            body.append("bill_amount", String(values.bill_amount));
            body.append("bill_date", formatRequiredDate(values.bill_date, "票据日期"));
            setFeeInformSubmitting(true);
            await api.post(`/finance/fee-informs/${feeInformRecord.id}/bill`, body);
            message.success("费用通知票据已上传");
            setFeeInformBillOpen(false);
            setFeeInformFile([]);
            await refreshCaseFeeDetail();
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "上传票据失败");
        }
        finally {
            setFeeInformSubmitting(false);
        }
    };
    const downloadBillFile = async (path: string, filename: string) => {
        const response = await api.get(path, { responseType: "blob" });
        const url = URL.createObjectURL(response.data);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(url);
    };
    const downloadFeeInformBill = async (row: CaseRow) => {
        try {
            const inform = await loadLatestFeeInform(row);
            if (!inform)
                return;
            await downloadBillFile(`/finance/fee-informs/${inform.id}/bill/download`, inform.receipt_attachment?.original_name || "费用通知票据");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "查看票据文件失败");
        }
    };
    const showCaseFeeFiles = async (row: CaseRow, invoicesOnly = false) => {
        const caseId = context.viewingCounselCase?.id;
        if (!caseId) {
            message.error("请先打开所属案件再查看票据");
            return;
        }
        try {
            await openCaseFeeFilesDialog({
                caseId, feeId: row.id, serialNo: row.serial_no, invoicesOnly,
                download: downloadBillFile,
                onChanged: async () => {
                    if (context.viewingCounselCase?.id === caseId) await refreshCaseFeeDetail();
                },
            });
        } catch (error: any) {
            message.error(error?.response?.data?.detail || "加载票据文件失败");
        }
    };
    const openCaseReceiptFiles = (row: CaseRow) => showCaseFeeFiles(row);
    const openCaseInvoiceFiles = (row: CaseRow) => showCaseFeeFiles(row, true);
    const unlockFeeInform = async (row: CaseRow) => {
        try {
            const inform = await loadLatestFeeInform(row);
            if (!inform)
                return;
            Modal.confirm({ title: "费用通知解锁", content: "解锁后可重新上传票据，原票据保留在通知审计记录中。", onOk: async () => { await api.post(`/finance/fee-informs/${inform.id}/unlock`); message.success("费用通知已解锁"); await refreshCaseFeeDetail(); } });
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "费用通知解锁失败");
        }
    };
    const openFeeInformLinks = async (row: CaseRow) => {
        const { feeInformLinkForm, setFeeInformLinkOpen } = context;
        try {
            const inform = await loadLatestFeeInform(row);
            if (!inform)
                return;
            feeInformLinkForm.resetFields();
            feeInformLinkForm.setFieldsValue({ fee_ids: inform.data?.linked_fee_ids || [] });
            setFeeInformLinkOpen(true);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "加载费用通知失败");
        }
    };
    const saveFeeInformLinks = async () => {
        const { feeInformRecord, feeInformLinkForm, setFeeInformSubmitting, setFeeInformLinkOpen } = context;
        if (!feeInformRecord)
            return;
        try {
            const values = await feeInformLinkForm.validateFields();
            setFeeInformSubmitting(true);
            await api.post(`/finance/fee-informs/${feeInformRecord.id}/links`, values);
            message.success("费用信息已关联");
            setFeeInformLinkOpen(false);
            await refreshCaseFeeDetail();
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "关联费用信息失败");
        }
        finally {
            setFeeInformSubmitting(false);
        }
    };
    const deleteFeeInform = async (row: CaseRow) => {
        try {
            const inform = await loadLatestFeeInform(row);
            if (!inform)
                return;
            Modal.confirm({ title: "删除费用通知", content: "仅未确认票据的费用通知可以删除。", okButtonProps: { danger: true }, onOk: async () => { await api.delete(`/finance/fee-informs/${inform.id}`); message.success("费用通知已删除"); await refreshCaseFeeDetail(); } });
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "删除费用通知失败");
        }
    };
    const handleExternalFeeOperation = async (keys: Key[], selectedFee: CaseRow | undefined, key: string) => {
        const { openInformDateBatchUpdate, requireSingleFee, openFeeInformCreator, editCaseFee, deleteCaseFee, markCaseFeeNoPayment, markCaseFeeRefundNotRequired, viewingCounselCase, onNavigate } = context;
        if (key === "inform-date")
            return openInformDateBatchUpdate(keys);
        if (!requireSingleFee(keys, selectedFee, key === "refund" ? "办理法院退费" : key === "payment" ? "申请付款" : key === "invoice" ? "申请开票" : key === "edit" ? "修改" : key === "delete" ? "删除" : key === "inform" ? "新建费用通知" : key === "arrival" ? "到账确认" : key === "bill" ? "上传票据" : key === "download-bill" ? "查看票据文件" : key === "invoice-files" ? "查看发票文件" : key === "unlock-inform" ? "费用通知解锁" : key === "link-inform" ? "关联费用信息" : key === "delete-inform" ? "删除费用通知" : "标记不缴费"))
            return;
        if (key === "inform")
            return openFeeInformCreator(selectedFee!);
        if (key === "arrival")
            return void openFeeInformArrival(selectedFee!);
        if (key === "bill")
            return void openFeeInformBill(selectedFee!);
        if (key === "invoice-files") return void openCaseInvoiceFiles(selectedFee!);
        if (key === "download-bill") {
            const files = selectedFee!.data.case_fee_files;
            const hasFiles = Array.isArray(files) ? files.length > 0 : caseReceiptFiles(selectedFee!.data).length > 0;
            return hasFiles ? openCaseReceiptFiles(selectedFee!) : downloadFeeInformBill(selectedFee!);
        }
        if (key === "unlock-inform")
            return void unlockFeeInform(selectedFee!);
        if (key === "link-inform")
            return void openFeeInformLinks(selectedFee!);
        if (key === "delete-inform")
            return void deleteFeeInform(selectedFee!);
        if (key === "payment")
            return openPaymentRequest(selectedFee!);
        if (key === "edit")
            return editCaseFee(selectedFee!);
        if (key === "delete")
            return deleteCaseFee(selectedFee!);
        if (key === "no-payment")
            return markCaseFeeNoPayment(selectedFee!);
        if (key === "refund-not-required")
            return markCaseFeeRefundNotRequired(selectedFee!);
        if (key === "invoice") {
            try {
                const { data } = await api.get("/finance/case-fees/invoice-status", { params: { scope: "company", invoice_status: "未开票", case_no: selectedFee!.data.case_no || viewingCounselCase?.serial_no || "", fee_types: "", page: 1, page_size: 200 } });
                const eligibility = resolveCaseFeeInvoiceEligibility(selectedFee!.id, Array.isArray(data?.items) ? data.items : []);
                if (!eligibility.ok) {
                    message.warning(eligibility.error);
                    return;
                }
            }
            catch (error: any) {
                message.error(error?.response?.data?.detail || "开票资格检查失败");
                return;
            }
        }
        rememberBusinessRecordDetailTarget({
            id: selectedFee!.id,
            module: "finance",
            action: key === "invoice" ? "create_invoice" : "create_refund",
        });
        onNavigate?.(key === "invoice" ? "finance-invoice-mine" : "finance-refund");
    };
    const openCaseCommission = async () => {
        const { viewingCounselCase, requireSingleFee, selectedFirmFeeKeys, selectedFirmFee, setCaseCommissionLoading, setCaseCommissionPreview, setCaseCommissionResult, setCaseCommissionRows } = context;
        if (!viewingCounselCase || !requireSingleFee(selectedFirmFeeKeys, selectedFirmFee, "新建提成"))
            return;
        setCaseCommissionLoading(true);
        try {
            const { data } = await api.get(`/cases/${viewingCounselCase.id}/commission-preview`, {
                params: { source_fee_id: selectedFirmFee!.id },
            });
            const preview = data as CaseCommissionPreview;
            setCaseCommissionPreview(preview);
            setCaseCommissionResult(null);
            setCaseCommissionRows((preview.items || []).map((item, index) => ({ ...item, client_key: `${item.preview_key}:${index}` })));
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "提成预览加载失败");
        }
        finally {
            setCaseCommissionLoading(false);
        }
    };
    const submitCaseCommissions = async () => {
        const { caseCommissionPreview, viewingCounselCase, caseCommissionRows, setCaseCommissionSubmitting, setCaseCommissionResult, openCounselDetail } = context;
        if (!caseCommissionPreview || !viewingCounselCase)
            return;
        if (!caseCommissionRows.length) {
            message.warning("没有可提交的提成项目");
            return;
        }
        if (caseCommissionRows.some((row) => Number(row.actual_amount || 0) <= 0)) {
            message.warning("实际金额必须大于 0");
            return;
        }
        setCaseCommissionSubmitting(true);
        try {
            const { data } = await api.post(`/cases/${viewingCounselCase.id}/commissions`, {
                source_fee_id: caseCommissionPreview.source_fee.id,
                items: caseCommissionRows.map((row) => ({
                    preview_key: row.preview_key,
                    base_amount: row.base_amount,
                    actual_amount: row.actual_amount,
                    remark: row.remark || "",
                })),
            });
            setCaseCommissionResult(data as CaseCommissionResult);
            message.success(`付款申请 ${data.application_no} 已提交`);
            await openCounselDetail(viewingCounselCase, "internal-fees");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "新建提成失败");
        }
        finally {
            setCaseCommissionSubmitting(false);
        }
    };
    return { loadCounselDetailAssistedFees, saveCounselDetailAssistedFee, confirmCounselDetailAssistedFee, submitSettlementAmount, submitCaseTaskFeedback, openRelatedFee, submitCounselBatchFee, openCaseFee, loadCasePaymentTypes, createCasePaymentType, createCaseFee, submitCreatedCaseFeePayments, createCourtRefund, openPaymentRequest, submitPaymentRequest, previewInternalPayment, submitCaseFeePayment, startCaseInvoiceImport, completeRefund, submitInformDateBatchUpdate, refreshCaseFeeDetail, createFeeInform, loadLatestFeeInform, openFeeInformArrival, confirmFeeInformArrival, openFeeInformBill, uploadFeeInformBill, downloadFeeInformBill, openCaseReceiptFiles, unlockFeeInform, openFeeInformLinks, saveFeeInformLinks, deleteFeeInform, handleExternalFeeOperation, openCaseCommission, submitCaseCommissions };
}
