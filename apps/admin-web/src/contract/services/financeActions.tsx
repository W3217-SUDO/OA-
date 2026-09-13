import { message } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import type { MessageType } from "antd/es/message/interface";
import dayjs from "dayjs";
import { api } from "../../api";
import type { ContractMutationGate } from "../../contractMutationGate.mjs";
import { extractContractErrorMessage, normalizeContractActionResponse } from "../../contractWorkflowPolicy.mjs";
import { formatRequiredDate } from "../../formSafety";
import { contractPaymentCandidateKey, findContractPaymentCandidate } from "../contractPaymentCandidateKey";
import type { Contract, ContractPaymentCandidate, ContractWorkflowCapabilities, PaymentTypeOption } from "../types";
/** contract finance operations; dependencies are read when each operation runs. */
export interface ContractFinanceDependencies {
    readonly contractCapabilities: (contract?: Contract | null | undefined, options?: Record<string, unknown>) => ContractWorkflowCapabilities;
    readonly denyContractAction: () => MessageType;
    readonly paymentForm: FormInstance<any>;
    readonly setPaymentTarget: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly setPaymentCandidates: React.Dispatch<React.SetStateAction<ContractPaymentCandidate[]>>;
    readonly setPaymentTypes: React.Dispatch<React.SetStateAction<PaymentTypeOption[]>>;
    readonly setSelectedPaymentObjectKeys: React.Dispatch<React.SetStateAction<React.Key[]>>;
    readonly setPaymentAmounts: React.Dispatch<React.SetStateAction<Record<string, number>>>;
    readonly paymentTarget: Contract | null;
    readonly setPaymentTypeCreating: React.Dispatch<React.SetStateAction<boolean>>;
    readonly paymentTypeCreateForm: FormInstance<any>;
    readonly setPaymentTypeCreateOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setPaymentTypeSearch: React.Dispatch<React.SetStateAction<string>>;
    readonly contractMutationGates: React.RefObject<{
        submit: ContractMutationGate;
        payment: ContractMutationGate;
        invoice: ContractMutationGate;
        attachment: ContractMutationGate;
    }>;
    readonly setPaymentSaving: React.Dispatch<React.SetStateAction<boolean>>;
    readonly selectedPaymentObjectKeys: React.Key[];
    readonly paymentAmounts: Record<string, number>;
    readonly paymentCandidates: ContractPaymentCandidate[];
    readonly viewing: Contract | null;
    readonly openViewing: (contract: Contract, options?: {
        detailTab?: string | undefined;
    }) => Promise<void>;
    readonly onNavigate?: (key: string) => void;
    readonly invoiceTarget: Contract | null;
    readonly setInvoiceSaving: React.Dispatch<React.SetStateAction<boolean>>;
    readonly invoiceForm: FormInstance<any>;
    readonly setInvoiceTarget: React.Dispatch<React.SetStateAction<Contract | null>>;
    readonly invoiceSubjects: Array<{ fee_id: number; case_no: string; invoiceable_amount: number }>;
    readonly selectedInvoiceObjectKeys: React.Key[];
}
export function createContractFinanceActions(context: ContractFinanceDependencies) {
    const openContractPayment = async (contract: Contract) => {
        const { contractCapabilities, denyContractAction, paymentForm, setPaymentTarget, setPaymentCandidates, setPaymentTypes, setSelectedPaymentObjectKeys, setPaymentAmounts } = context;
        if (!contractCapabilities(contract).canPayment) {
            denyContractAction();
            return;
        }
        paymentForm.resetFields();
        setPaymentTarget(contract);
        setPaymentCandidates([]);
        setPaymentTypes([]);
        setSelectedPaymentObjectKeys([]);
        setPaymentAmounts({});
        try {
            const { data } = await api.get(`/contracts/${contract.id}/payment-candidates`);
            const types = data.payment_types || [];
            setPaymentCandidates(data.items || []);
            setPaymentTypes(types);
            if (types.length)
                paymentForm.setFieldsValue({ payment_type_id: types[0].value, application_date: dayjs(), remark: "" });
            else
                paymentForm.setFieldsValue({ application_date: dayjs(), remark: "" });
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "合同付款候选加载失败");
        }
    };
    const createContractPaymentType = async () => {
        const { paymentTarget, setPaymentTypeCreating, paymentTypeCreateForm, setPaymentTypes, paymentForm, setPaymentTypeCreateOpen, setPaymentTypeSearch } = context;
        if (!paymentTarget)
            return;
        setPaymentTypeCreating(true);
        try {
            const values = await paymentTypeCreateForm.validateFields();
            const { data } = await api.post(`/contracts/${paymentTarget.id}/payment-types`, values);
            setPaymentTypes((items) => [...items.filter((item) => item.value !== data.value), data]);
            paymentForm.setFieldValue("payment_type_id", data.value);
            setPaymentTypeCreateOpen(false);
            paymentTypeCreateForm.resetFields();
            setPaymentTypeSearch("");
            message.success("付款单位已新增并保存到系统参数-付款类型");
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "付款单位新增失败");
        }
        finally {
            setPaymentTypeCreating(false);
        }
    };
    const createContractPayment = async () => {
        const { paymentTarget, contractMutationGates, contractCapabilities, denyContractAction, setPaymentSaving, paymentForm, selectedPaymentObjectKeys, paymentAmounts, paymentCandidates, viewing, openViewing, setPaymentTarget, setPaymentCandidates, setPaymentTypes, setSelectedPaymentObjectKeys, setPaymentAmounts } = context;
        if (!paymentTarget || !contractMutationGates.current.payment.tryEnter())
            return;
        if (!contractCapabilities(paymentTarget).canPayment) {
            contractMutationGates.current.payment.leave();
            denyContractAction();
            return;
        }
        setPaymentSaving(true);
        try {
            const values = await paymentForm.validateFields();
            const lines = selectedPaymentObjectKeys.map((key) => {
                const row = findContractPaymentCandidate(paymentCandidates, key);
                return { contract_object_id: row?.contract_object_id ?? null, case_fee_id: row?.case_fee_id ?? null, amount: Number(paymentAmounts[String(key)] || 0) };
            });
            if (!lines.length) {
                message.error("请至少选择一笔案件费用");
                return;
            }
            if (lines.some((line) => !line.amount || line.amount <= 0)) {
                message.error("请选择案件费用并填写本次支付金额");
                return;
            }
            const exceeding = lines.find((line) => line.amount > Number(findContractPaymentCandidate(paymentCandidates, contractPaymentCandidateKey(line))?.remaining_amount || 0) + 0.0001);
            if (exceeding) {
                message.error("本次支付金额不能超过待付余额");
                return;
            }
            const response = await api.post(`/contracts/${paymentTarget.id}/payment-applications`, {
                ...values,
                application_date: formatRequiredDate(values.application_date, "申请日期"),
                lines,
            });
            const feedback = normalizeContractActionResponse(response, "合同付款申请创建失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            const { data } = response;
            message.success(`合同付款申请 ${data.serial_no} 已提交审批`);
            if (viewing?.id === paymentTarget.id)
                await openViewing(paymentTarget);
            setPaymentTarget(null);
            paymentForm.resetFields();
            setPaymentCandidates([]);
            setPaymentTypes([]);
            setSelectedPaymentObjectKeys([]);
            setPaymentAmounts({});
        }
        catch (error: any) {
            if (error?.errorFields)
                return;
            message.error(extractContractErrorMessage(error, "合同付款申请创建失败"));
        }
        finally {
            contractMutationGates.current.payment.leave();
            setPaymentSaving(false);
        }
    };
    const createContractInvoice = async () => {
        const { invoiceTarget, contractMutationGates, contractCapabilities, denyContractAction, setInvoiceSaving, invoiceForm, viewing, openViewing, onNavigate, setInvoiceTarget, invoiceSubjects, selectedInvoiceObjectKeys } = context;
        if (!invoiceTarget || !contractMutationGates.current.invoice.tryEnter())
            return;
        if (!contractCapabilities(invoiceTarget).canInvoice) {
            contractMutationGates.current.invoice.leave();
            denyContractAction();
            return;
        }
        setInvoiceSaving(true);
        try {
            const values = await invoiceForm.validateFields();
            const selectedObjects = invoiceSubjects.filter((item) => selectedInvoiceObjectKeys.includes(item.fee_id));
            const caseFeeIds = selectedObjects.map((item) => item.fee_id);
            if (!caseFeeIds.length) {
                message.warning("请至少选择一笔合同名下的案件费用");
                return;
            }
            const caseNos = [...new Set(selectedObjects.map((item) => item.case_no).filter(Boolean))];
            if (caseNos.length > 1) {
                message.warning("同一张发票只能选择同一案件的费用");
                return;
            }
            const availableAmount = selectedObjects.reduce((sum, item) => sum + Number(item.invoiceable_amount || 0), 0);
            if (Number(values.amount || 0) > availableAmount + 0.0001) {
                message.warning(`开票金额不能超过所选费用合计 ${availableAmount.toFixed(2)} 元`);
                return;
            }
            const response = await api.post("/finance/invoices", {
                ...values,
                case_fee_ids: caseFeeIds,
                customer: invoiceTarget.customer,
                case_no: caseNos[0] || invoiceTarget.data.case_no || "",
                contract_record_id: invoiceTarget.id,
                remark: `来源合同 ${invoiceTarget.serial_no}${values.remark ? `；${values.remark}` : ""}`,
            });
            const feedback = normalizeContractActionResponse(response, "合同开票申请创建失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            const { data } = response;
            const refreshViewingContract = async () => {
                if (viewing?.id !== invoiceTarget.id)
                    return;
                try {
                    await openViewing(invoiceTarget);
                }
                catch {
                    message.warning("合同详情刷新失败，请稍后手动刷新");
                }
            };
            try {
                await api.post(`/finance/invoices/${data.id}/submit`, { comment: String(values.remark || "").trim() });
            }
            catch (submitError: any) {
                message.error(`发票申请 ${data.serial_no} 已创建为草稿，但提交审批失败：${extractContractErrorMessage(submitError, "请在我的开票继续提交该草稿")}。系统未重复创建草稿。`);
                setInvoiceTarget(null);
                invoiceForm.resetFields();
                await refreshViewingContract();
                onNavigate?.("finance-invoice-mine");
                return;
            }
            setInvoiceTarget(null);
            invoiceForm.resetFields();
            message.success(`发票申请 ${data.serial_no} 已提交审批并关联合同`);
            await refreshViewingContract();
        }
        catch (error: any) {
            if (error?.errorFields)
                return;
            message.error(extractContractErrorMessage(error, "合同开票申请创建失败"));
        }
        finally {
            contractMutationGates.current.invoice.leave();
            setInvoiceSaving(false);
        }
    };
    return { openContractPayment, createContractPaymentType, createContractPayment, createContractInvoice };
}
