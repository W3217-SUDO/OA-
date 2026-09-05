import type { UploadFile } from "antd";
import { message, Modal } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import type { MessageType } from "antd/es/message/interface";
import dayjs from "dayjs";
import type { Key } from "react";
import { api } from "../../api";
import { rememberBusinessRecordDetailTarget } from "../../businessRecordDetailNavigation";
import { buildCaseFeeContractOptions } from "../../caseFeeContractOptions.mjs";
import { resolveCaseFeeInvoiceEligibility } from "../../caseFeeInvoiceEligibility.mjs";
import { resolveCaseFileTypeSelection } from "../../caseFifthBatchParity.mjs";
import { buildExternalPaymentRequestPayload } from "../../casePaymentUnitParity.mjs";
import { PLATFORM_AGENCY_FEE_SUBTYPE } from "../../caseRelationConsumption.mjs";
import { buildCasePaymentContext } from "../../caseSecondBatchParity";
import { feeTypeSelection, initialFeeTypeId, type FeeTypeCatalogItem } from "../../feeTypeHierarchy.mjs";
import { formatRequiredDate } from "../../formSafety";
import type { AttachmentRow, CaseAssistedFee, CaseCommissionPreview, CaseCommissionPreviewRow, CaseCommissionResult, CaseDetailCapabilities, CaseFileTypeOption, CasePaymentTypeOption, CaseRow, ContractRow, PaymentTypeCreateTarget, Profile, TaskRow } from "../types";
/** legal finance operations; dependencies are read when each operation runs. */
export interface CaseFinanceDependencies {
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
    readonly setCounselDetailHistory: React.Dispatch<React.SetStateAction<any[]>>;
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
    readonly closeCaseFeeCreator: () => void;
    readonly courtRefundFee: CaseRow | null;
    readonly courtRefundForm: FormInstance<any>;
    readonly setCourtRefundFee: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly counselDetailCapabilities: CaseDetailCapabilities;
    readonly setPaymentRequestFee: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly paymentRequestFee: CaseRow | null;
    readonly setPaymentPackageLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setPaymentPackagePreview: React.Dispatch<any>;
    readonly paymentPackagePreview: any;
    readonly paymentPackageLoading: boolean;
    readonly invoiceRows: AttachmentRow[];
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
        const { counselDetailAssistedFeePage, counselDetailAssistedFeePageSize, counselDetailAssistedFeeRequestRef, counselDetailCaseIdRef, setCounselDetailAssistedFees, setCounselDetailAssistedFeePage, setCounselDetailAssistedFeePageSize, setCounselDetailAssistedFeeTotal } = context;
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
        const { viewingCounselCase, setAssistedFeeSaving, assistedFeeForm, assistedFeeEditor, setCounselDetailHistory, setAssistedFeeModalOpen, setAssistedFeeEditor, counselDetailAssistedFeePageSize } = context;
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
            const historyResponse = await api.get(`/records/${viewingCounselCase.id}/history`);
            setCounselDetailHistory(historyResponse.data.items || []);
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
        const { viewingCounselCase, assistedFeeConfirming, setAssistedFeeSaving, assistedFeeConfirmForm, setCounselDetailHistory, setAssistedFeeConfirming, counselDetailAssistedFeePage, counselDetailAssistedFeePageSize } = context;
        if (!viewingCounselCase || !assistedFeeConfirming)
            return;
        setAssistedFeeSaving(true);
        try {
            const values = await assistedFeeConfirmForm.validateFields();
            await api.post(`/cases/${viewingCounselCase.id}/assisted-fees/${assistedFeeConfirming.id}/confirm`, {
                confirmed_date: formatRequiredDate(values.confirmed_date, "确认日期"),
                remark: String(values.remark || "").trim(),
            });
            const historyResponse = await api.get(`/records/${viewingCounselCase.id}/history`);
            setCounselDetailHistory(historyResponse.data.items || []);
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
        try {
            const { data } = await api.post("/cases/batch-fees", { case_ids: caseIds, amount: values.amount, fee_type_id: values.fee_type_id, expense_scope: values.expense_scope, expense_subtype: values.expense_subtype, handler: values.handler || profile.username, description: values.description || "" });
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
        const linkedContractId = Number(row.data.contract_record_id || row.data.contract_id) || undefined;
        const initialContractId = eligibleContracts.some((option) => option.value === linkedContractId)
            ? linkedContractId
            : eligibleContracts[0]?.value;
        feeForm.resetFields();
        feeForm.setFieldsValue({ source_file_type: sourceFileType, items: [{
                    title: `${row.title}案件费用`, amount: row.data.amount || undefined,
                    contract_record_id: initialContractId,
                    expense_scope: expenseScope, fee_type_id: initialTypeId,
                    expense_subtype: initialType?.name,
                    fee_type: initialType?.base_fee_type,
                    commission_details: [],
                    handler: profile.username || row.owner, court: row.data.court || "", payee: expenseScope === "内部" ? undefined : row.data.court || "",
                    deadline: undefined, description: "",
                }] });
        setCaseFeeCreateStep(0);
        setCreatedCaseFees([]);
        setCaseFeePaymentDrafts([]);
        setFeeCase(row);
    };
    const loadCasePaymentTypes = async (feeId: number) => {
        const { setCasePaymentTypesLoading, setCasePaymentTypes } = context;
        setCasePaymentTypesLoading(true);
        try {
            const { data } = await api.get(`/finance/fees/${feeId}/payment-types`);
            const items = Array.isArray(data?.items) ? data.items : [];
            setCasePaymentTypes(items);
            return items as CasePaymentTypeOption[];
        }
        catch (error: any) {
            setCasePaymentTypes([]);
            message.error(error?.response?.data?.detail || "付款单位加载失败");
            return [];
        }
        finally {
            setCasePaymentTypesLoading(false);
        }
    };
    const createCasePaymentType = async () => {
        const { paymentTypeCreateTarget, paymentTypeCreateForm, setPaymentTypeCreating, setCasePaymentTypes, setCaseFeePaymentDrafts, paymentRequestForm, setPaymentTypeCreateTarget, setPaymentTypeSearch } = context;
        if (!paymentTypeCreateTarget)
            return;
        const values = await paymentTypeCreateForm.validateFields();
        setPaymentTypeCreating(true);
        try {
            const { data } = await api.post(`/finance/fees/${paymentTypeCreateTarget.feeId}/payment-types`, values);
            const created = data as CasePaymentTypeOption;
            setCasePaymentTypes((items) => [...items.filter((item) => item.id !== created.id), created]);
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
        const { feeCase, editingFeeRow, viewingCounselCase, feeForm, isInternalCaseFee, setEditingFeeRow, load, openCounselDetail, setCreatedCaseFees, setCaseFeePaymentDrafts, setCaseFeeCreateStep } = context;
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
                const payload = { ...feeValues, ...commonPayload, deadline: feeValues.deadline ? formatRequiredDate(feeValues.deadline, "截止日期") : undefined };
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
                    const payload = { ...item, ...commonPayload, deadline: item.deadline ? formatRequiredDate(item.deadline, "截止日期") : undefined };
                    const endpoint = item.expense_scope === "内部" ? "/finance/internal-fees" : "/finance/fees";
                    const { data } = await api.post(endpoint, payload);
                    created.push(data);
                }
                message.success(`已创建 ${created.length} 条费用草稿`);
                setCreatedCaseFees(created);
                setCaseFeePaymentDrafts(created.map((row) => ({
                    payment_remark: "",
                    payment_payee: row.data.expense_scope === "内部" ? String(row.data.payee || row.owner || "") : undefined,
                    payment_account: row.data.expense_scope === "内部" ? String(row.data.payee || row.owner || "") : undefined,
                })));
                if (created[0] && created[0].data.expense_scope !== "内部")
                    await loadCasePaymentTypes(created[0].id);
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
        const { caseFeePaymentDrafts, createdCaseFees, setCaseFeeSubmitting, feeCase, closeCaseFeeCreator, load, viewingCounselCase, openCounselDetail } = context;
        if (caseFeePaymentDrafts.some((item, index) => createdCaseFees[index]?.data.expense_scope !== "内部" && !item.payment_type_id)) {
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
        try {
            const values = await courtRefundForm.validateFields();
            await api.post("/finance/refunds", {
                fee_record_id: courtRefundFee.id,
                case_no: viewingCounselCase.serial_no,
                customer: viewingCounselCase.customer,
                court: courtRefundFee.data.court || viewingCounselCase.data.court || "",
                original_payment_no: courtRefundFee.data.document_no || courtRefundFee.serial_no,
                amount: Number(values.amount),
                applicant: profile.display_name || profile.username,
                reason: "诉讼费退款",
            });
            message.success("法院退费申请已创建");
            setCourtRefundFee(null);
            courtRefundForm.resetFields();
            await openCounselDetail(viewingCounselCase);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "法院退费申请创建失败");
        }
    };
    const openPaymentRequest = async (row: CaseRow) => {
        const { counselDetailCapabilities, paymentRequestForm, setPaymentTypeSearch, setPaymentRequestFee } = context;
        if (!counselDetailCapabilities.can_create_finance)
            return message.warning("当前账号没有申请付款权限");
        if (!["草稿", "已退回", "已审批", "部分付款"].includes(row.status)) {
            return message.warning(`当前费用状态“${row.status}”不能申请付款`);
        }
        const paid = Number(row.data.paid_amount || 0);
        const requested = Number(row.data.payment_requested_amount || 0);
        const remaining = Math.max(Number(row.data.amount || 0) - paid - requested, 0);
        const options = await loadCasePaymentTypes(row.id);
        const storedPaymentTypeId = Number(row.data.payment_type_id) || undefined;
        paymentRequestForm.resetFields();
        paymentRequestForm.setFieldsValue({
            amount: remaining || Number(row.data.amount || 0),
            payment_remark: row.data.payment_remark || row.description || "",
            payment_type_id: options.some((item) => item.id === storedPaymentTypeId) ? storedPaymentTypeId : undefined,
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
    const previewInternalPayment = async (row: CaseRow) => {
        const { counselDetailCapabilities, setPaymentPackageLoading, viewingCounselCase, setPaymentPackagePreview } = context;
        if (row.status !== "已审批")
            return message.warning("仅已审批内部费用可以申请付款");
        if (!counselDetailCapabilities.can_create_finance)
            return message.warning("当前账号没有申请付款权限");
        setPaymentPackageLoading(true);
        try {
            const { data } = await api.post("/finance/payment-packages/preview", { fee_ids: [row.id] });
            const caseContext = buildCasePaymentContext({
                caseRecordId: row.data.case_id || row.data.case_record_id || viewingCounselCase?.id,
                caseNo: row.data.case_no || viewingCounselCase?.serial_no,
                feeId: row.id,
                feeNo: row.serial_no,
            });
            setPaymentPackagePreview({ ...data, source: { ...caseContext, request_no: row.serial_no, customer: row.customer, amount: row.data.amount, title: row.title } });
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "付款申请预览失败");
        }
        finally {
            setPaymentPackageLoading(false);
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
    const submitInternalPayment = async () => {
        const { paymentPackagePreview, paymentPackageLoading, setPaymentPackageLoading, setPaymentPackagePreview, load, onNavigate } = context;
        if (!paymentPackagePreview || paymentPackageLoading)
            return;
        setPaymentPackageLoading(true);
        try {
            const { data } = await api.post("/finance/payment-packages", { fee_ids: [paymentPackagePreview.source.fee_id], package_no: paymentPackagePreview.package_no, comment: `案件 ${paymentPackagePreview.source.case_no} 内部费用付款申请` });
            message.success(`付款申请 ${data.serial_no || paymentPackagePreview.package_no} 已提交`);
            setPaymentPackagePreview(null);
            await load();
            onNavigate?.("finance-payment-mine");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "付款申请提交失败");
        }
        finally {
            setPaymentPackageLoading(false);
        }
    };
    const startCaseInvoiceImport = async () => {
        const { invoiceRows, load } = context;
        if (!invoiceRows.length)
            return message.warning("请先上传发票文件");
        try {
            const { data } = await api.post("/cases/invoice-files/import");
            if (data.unmatched)
                message.warning(`已处理 ${data.processed} 个文件，匹配案件 ${data.matched} 个，${data.unmatched} 个文件名未识别案件编号`);
            else
                message.success(`已完成 ${data.processed} 个发票文件导入并匹配案件`);
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "发票文件导入失败");
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
    const downloadFeeInformBill = async (row: CaseRow) => {
        try {
            const inform = await loadLatestFeeInform(row);
            if (!inform)
                return;
            const response = await api.get(`/finance/fee-informs/${inform.id}/bill/download`, { responseType: "blob" });
            const url = URL.createObjectURL(response.data);
            const link = document.createElement("a");
            link.href = url;
            link.download = inform.receipt_attachment?.original_name || "费用通知票据";
            link.click();
            URL.revokeObjectURL(url);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "查看票据文件失败");
        }
    };
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
        if (!requireSingleFee(keys, selectedFee, key === "refund" ? "办理法院退费" : key === "payment" ? "申请付款" : key === "invoice" ? "申请开票" : key === "edit" ? "修改" : key === "delete" ? "删除" : key === "inform" ? "新建费用通知" : key === "arrival" ? "到账确认" : key === "bill" ? "上传票据" : key === "download-bill" ? "查看票据文件" : key === "unlock-inform" ? "费用通知解锁" : key === "link-inform" ? "关联费用信息" : key === "delete-inform" ? "删除费用通知" : "标记不缴费"))
            return;
        if (key === "inform")
            return openFeeInformCreator(selectedFee!);
        if (key === "arrival")
            return void openFeeInformArrival(selectedFee!);
        if (key === "bill")
            return void openFeeInformBill(selectedFee!);
        if (key === "download-bill")
            return void downloadFeeInformBill(selectedFee!);
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
        const feeTypes = [
            selectedFirmFee!.data.expense_subtype,
            selectedFirmFee!.data.fee_type,
            selectedFirmFee!.data.base_fee_type,
            selectedFirmFee!.title,
        ].map((value) => String(value || "").trim()).filter(Boolean);
        if (!feeTypes.some((feeType) => feeType.includes("代理费"))) {
            message.warning("新建提成必须选择一条代理费");
            return;
        }
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
    return { loadCounselDetailAssistedFees, saveCounselDetailAssistedFee, confirmCounselDetailAssistedFee, submitSettlementAmount, submitCaseTaskFeedback, openRelatedFee, submitCounselBatchFee, openCaseFee, loadCasePaymentTypes, createCasePaymentType, createCaseFee, submitCreatedCaseFeePayments, createCourtRefund, openPaymentRequest, submitPaymentRequest, previewInternalPayment, submitCaseFeePayment, submitInternalPayment, startCaseInvoiceImport, completeRefund, submitInformDateBatchUpdate, refreshCaseFeeDetail, createFeeInform, loadLatestFeeInform, openFeeInformArrival, confirmFeeInformArrival, openFeeInformBill, uploadFeeInformBill, downloadFeeInformBill, unlockFeeInform, openFeeInformLinks, saveFeeInformLinks, deleteFeeInform, handleExternalFeeOperation, openCaseCommission, submitCaseCommissions };
}
