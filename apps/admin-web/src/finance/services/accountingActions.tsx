import { message } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import { api } from "../../api";
import { formatRequiredDate } from "../../formSafety";
import { money } from "../constants";
import type { AllocationCandidate, Fee, IncomingPayment, Reconciliation, Transaction } from "../types";
type OriginalFieldSpec = {
    label: string;
    key?: string;
    control?: "date" | "money" | "multi";
    options?: string[];
    defaultValue?: any;
    disabled?: boolean;
    readOnly?: boolean;
    pickerLabel?: string;
};
type OriginalRouteConfig = {
    fields: OriginalFieldSpec[];
    headers: string[];
    source: "fees" | "incoming" | "invoices" | "settlements" | "generalSettlements" | "archiveSettlements" | "feeQuery" | "refundReviewFees" | "paymentPackages" | "unissuedFees";
    selectable?: boolean;
    clear?: boolean;
    upload?: boolean;
    export?: boolean;
    note?: string;
};
/** finance accounting operations; dependencies are read when each operation runs. */
export interface FinanceAccountingDependencies {
    readonly incomingForm: FormInstance<any>;
    readonly setIncomingOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly load: () => Promise<void>;
    readonly claimTarget: IncomingPayment | null;
    readonly claimForm: FormInstance<any>;
    readonly setClaimTarget: React.Dispatch<React.SetStateAction<IncomingPayment | null>>;
    readonly setAllocateTarget: React.Dispatch<React.SetStateAction<IncomingPayment | null>>;
    readonly setAllocationLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setSelectedAllocationKeys: React.Dispatch<React.SetStateAction<(string | number)[]>>;
    readonly setAllocationAmounts: React.Dispatch<React.SetStateAction<Record<string, number>>>;
    readonly setAllocationKeyword: React.Dispatch<React.SetStateAction<string>>;
    readonly setAllocationStage: React.Dispatch<React.SetStateAction<string>>;
    readonly setAllocationFeeType: React.Dispatch<React.SetStateAction<string>>;
    readonly setAllocationComment: React.Dispatch<React.SetStateAction<string>>;
    readonly setAllocationValidationError: React.Dispatch<React.SetStateAction<string>>;
    readonly setAllocationCandidates: React.Dispatch<React.SetStateAction<AllocationCandidate[]>>;
    readonly allocateTarget: IncomingPayment | null;
    readonly allocationCandidates: AllocationCandidate[];
    readonly selectedAllocationKeys: (string | number)[];
    readonly allocationAmounts: Record<string, number>;
    readonly allocationComment: string;
    readonly transactionForm: FormInstance<any>;
    readonly contractPayments: Fee[];
    readonly setTransactionOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly openVouchers: (row: Transaction) => void;
    readonly reconcileForm: FormInstance<any>;
    readonly setReconcileOpen: React.Dispatch<React.SetStateAction<boolean>>;
}
export function createFinanceAccountingActions(context: FinanceAccountingDependencies) {
    const createIncoming = async () => {
        const { incomingForm, setIncomingOpen, load } = context;
        const v = await incomingForm.validateFields();
        try {
            await api.post("/finance/incoming-payments", {
                ...v,
                received_date: formatRequiredDate(v.received_date, "到账日期"),
            });
            message.success("银行到账已登记，等待客户认领");
            setIncomingOpen(false);
            incomingForm.resetFields();
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "银行到账登记失败");
        }
    };
    const claimIncoming = async () => {
        const { claimTarget, claimForm, setClaimTarget, load } = context;
        if (!claimTarget)
            return;
        const v = await claimForm.validateFields();
        try {
            await api.post(`/finance/incoming-payments/${claimTarget.id}/claim`, v);
            message.success("到账已认领到客户，等待分配");
            setClaimTarget(null);
            claimForm.resetFields();
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "到账认领失败");
        }
    };
    const openIncomingAllocation = async (payment: IncomingPayment) => {
        const { setAllocateTarget, setAllocationLoading, setSelectedAllocationKeys, setAllocationAmounts, setAllocationKeyword, setAllocationStage, setAllocationFeeType, setAllocationComment, setAllocationValidationError, setAllocationCandidates } = context;
        setAllocateTarget(payment);
        setAllocationLoading(true);
        setSelectedAllocationKeys([]);
        setAllocationAmounts({});
        setAllocationKeyword("");
        setAllocationStage("");
        setAllocationFeeType("");
        setAllocationComment("");
        setAllocationValidationError("");
        try {
            const response = await api.get(`/finance/incoming-payments/${payment.id}/allocation-candidates`);
            const rows = Array.isArray(response.data?.items) ? response.data.items : [];
            setAllocationCandidates(rows);
            setAllocationAmounts(Object.fromEntries(rows.map((row: AllocationCandidate) => [row.key, row.remaining_amount])));
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "可分配案件费用加载失败");
            setAllocationCandidates([]);
        }
        finally {
            setAllocationLoading(false);
        }
    };
    const allocateIncoming = async () => {
        const { allocateTarget, allocationCandidates, selectedAllocationKeys, setAllocationValidationError, allocationAmounts, allocationComment, setAllocateTarget, setAllocationCandidates, setSelectedAllocationKeys, load } = context;
        if (!allocateTarget)
            return;
        const selected = allocationCandidates.filter((row) => selectedAllocationKeys.includes(row.key));
        if (!selected.length) {
            const detail = "请至少选择一笔待回款案件费用";
            setAllocationValidationError(detail);
            message.warning(detail);
            return;
        }
        const allocations = selected.map((row) => ({
            receivable_plan_id: row.receivable_plan_id,
            fee_record_id: row.fee_record_id || undefined,
            amount: Number(allocationAmounts[row.key] || 0),
            case_no: row.case_no || "",
            settlement_items: [{
                    fee_record_id: row.fee_record_id || undefined,
                    fee_type: row.fee_type || "代理费",
                    amount: Number(allocationAmounts[row.key] || 0),
                    settlement_amount: Number(allocationAmounts[row.key] || 0),
                    archive_fee: 0,
                }],
        }));
        if (allocations.some((entry) => entry.amount <= 0)) {
            const detail = "所选费用的本次回款金额必须大于 0";
            setAllocationValidationError(detail);
            message.warning(detail);
            return;
        }
        const total = allocations.reduce((sum, entry) => sum + entry.amount, 0);
        if (allocateTarget.remaining_amount != null && total > allocateTarget.remaining_amount + 0.001) {
            const detail = `本次分配合计不能超过未分配余额 ${money(allocateTarget.remaining_amount)}`;
            setAllocationValidationError(detail);
            message.warning(detail);
            return;
        }
        try {
            setAllocationValidationError("");
            await api.post(`/finance/incoming-payments/${allocateTarget.id}/allocate`, {
                allocations,
                comment: allocationComment,
            });
            message.success("回款已分配并同步更新合同应收");
            setAllocateTarget(null);
            setAllocationCandidates([]);
            setSelectedAllocationKeys([]);
            setAllocationValidationError("");
            load();
        }
        catch (error: any) {
            const detail = error?.response?.data?.detail || "回款分配失败";
            setAllocationValidationError(detail);
            message.error(detail);
        }
    };
    const deleteIncoming = async (row: IncomingPayment) => {
        const { load } = context;
        try {
            await api.delete(`/finance/incoming-payments/${row.id}`);
            message.success("到账记录及其分配已撤销");
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "删除失败");
        }
    };
    const createTransaction = async () => {
        const { transactionForm, contractPayments, setTransactionOpen, load, openVouchers } = context;
        const v = await transactionForm.validateFields();
        try {
            const contractPayment = contractPayments.find((item) => item.id === Number(v.finance_record_id));
            if (contractPayment) {
                await api.post(`/contract-payment-applications/${contractPayment.id}/pay`, {
                    paid_date: formatRequiredDate(v.transaction_date, "交易日期"),
                    voucher_no: v.voucher_no || "",
                    comment: v.remark || "",
                });
                message.success("合同付款已登记");
                setTransactionOpen(false);
                transactionForm.resetFields();
                await load();
                return;
            }
            const { data } = await api.post("/finance/transactions", {
                ...v,
                transaction_date: formatRequiredDate(v.transaction_date, "交易日期"),
            });
            message.success("财务流水已登记，请上传对应凭证");
            setTransactionOpen(false);
            transactionForm.resetFields();
            openVouchers({
                ...data,
                voucher_count: 0,
                voucher_categories: [],
                vouchers: [],
            });
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "登记失败");
        }
    };
    const createReconciliation = async () => {
        const { reconcileForm, setReconcileOpen, load } = context;
        const v = await reconcileForm.validateFields();
        const { period, ...fields } = v;
        try {
            await api.post("/finance/reconciliations", {
                ...fields,
                date_from: period[0].format("YYYY-MM-DD"),
                date_to: period[1].format("YYYY-MM-DD"),
            });
            message.success("对账单已生成");
            setReconcileOpen(false);
            reconcileForm.resetFields();
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "生成失败");
        }
    };
    const confirmReconciliation = async (row: Reconciliation) => {
        const { load } = context;
        try {
            await api.post(`/finance/reconciliations/${row.id}/confirm`, {
                comment: "财务核对无误",
            });
            message.success("对账单已确认");
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "确认失败");
        }
    };
    return { createIncoming, claimIncoming, openIncomingAllocation, allocateIncoming, deleteIncoming, createTransaction, createReconciliation, confirmReconciliation };
}
