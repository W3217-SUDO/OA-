import { message } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import type { MessageType } from "antd/es/message/interface";
import dayjs from "dayjs";
import { api } from "../../api";
import type { ContractMutationGate } from "../../contractMutationGate.mjs";
import { extractContractErrorMessage, normalizeContractActionResponse } from "../../contractWorkflowPolicy.mjs";
import { formatRequiredDate } from "../../formSafety";
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
    readonly setPaymentAmounts: React.Dispatch<React.SetStateAction<Record<number, number>>>;
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
    readonly paymentAmounts: Record<number, number>;
    readonly paymentCandidates: ContractPaymentCandidate[];
    readonly viewing: Contract | null;
    readonly openViewing: (contract: Contract, options?: {
        detailTab?: string | undefined;
    }) => Promise<void>;
    readonly invoiceTarget: Contract | null;
    readonly setInvoiceSaving: React.Dispatch<React.SetStateAction<boolean>>;
    readonly invoiceForm: FormInstance<any>;
    readonly setInvoiceTarget: React.Dispatch<React.SetStateAction<Contract | null>>;
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
            const lines = selectedPaymentObjectKeys.map((key) => ({ contract_object_id: Number(key), amount: Number(paymentAmounts[Number(key)] || 0) }));
            if (!lines.length) {
                message.error("请至少选择一条合同标的");
                return;
            }
            if (lines.some((line) => !line.amount || line.amount <= 0)) {
                message.error("请选择合同标的并填写本次支付金额");
                return;
            }
            const exceeding = lines.find((line) => line.amount > Number(paymentCandidates.find((item) => item.contract_object_id === line.contract_object_id)?.remaining_amount || 0) + 0.0001);
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
        const { invoiceTarget, contractMutationGates, contractCapabilities, denyContractAction, setInvoiceSaving, invoiceForm, viewing, openViewing, setInvoiceTarget } = context;
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
            const response = await api.post("/finance/invoices", {
                ...values,
                customer: invoiceTarget.customer,
                case_no: invoiceTarget.data.case_no || "",
                contract_record_id: invoiceTarget.id,
                remark: `来源合同 ${invoiceTarget.serial_no}${values.remark ? `；${values.remark}` : ""}`,
            });
            const feedback = normalizeContractActionResponse(response, "合同开票申请创建失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            const { data } = response;
            message.success(`发票申请 ${data.serial_no} 已创建并关联合同`);
            if (viewing?.id === invoiceTarget.id)
                await openViewing(invoiceTarget);
            setInvoiceTarget(null);
            invoiceForm.resetFields();
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
