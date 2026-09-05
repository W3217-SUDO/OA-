import { message } from "antd";
import { api } from "../../api";
import type { Fee, FinanceFlow } from "../types";
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
/** finance workflow operations; dependencies are read when each operation runs. */
export interface FinanceWorkflowDependencies {
    readonly load: () => Promise<void>;
    readonly bankUploadRef: React.RefObject<HTMLInputElement | null>;
    readonly claimCustomerSearchRequest: React.RefObject<number>;
    readonly setClaimCustomersLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setClaimCustomers: React.Dispatch<React.SetStateAction<{
        id: number;
        title: string;
        serial_no: string;
    }[]>>;
    readonly refreshRefundList: (page?: number) => Promise<{
        applied: boolean;
        response: any;
    } | null>;
    readonly setSettlementActionLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setSettlementContextRows: React.Dispatch<React.SetStateAction<any[]>>;
    readonly setSettlementContext: React.Dispatch<React.SetStateAction<{
        mode: "logs" | "tasks" | "log-create" | "task-create";
        caseRecords: Fee[];
    } | null>>;
}
export function createFinanceWorkflowActions(context: FinanceWorkflowDependencies) {
    const importBankStatement = async (file?: File) => {
        const { load, bankUploadRef } = context;
        if (!file)
            return;
        const body = new FormData();
        body.append("file", file);
        try {
            const { data } = await api.post("/finance/incoming-payments/import", body, { headers: { "Content-Type": "multipart/form-data" } });
            if (data.errors?.length) {
                message.warning(`成功导入 ${data.created} 条，${data.errors.length} 条未导入`);
            }
            else {
                message.success(`成功导入 ${data.created} 条银行到账`);
            }
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "银行流水导入失败");
        }
        finally {
            if (bankUploadRef.current)
                bankUploadRef.current.value = "";
        }
    };
    const searchClaimCustomers = async (keyword = "") => {
        const { claimCustomerSearchRequest, setClaimCustomersLoading, setClaimCustomers } = context;
        const requestId = ++claimCustomerSearchRequest.current;
        setClaimCustomersLoading(true);
        try {
            const { data } = await api.get("/finance/customer-options", {
                params: { keyword },
            });
            if (requestId === claimCustomerSearchRequest.current) {
                setClaimCustomers(data.items || []);
            }
        }
        catch {
            if (requestId === claimCustomerSearchRequest.current) {
                setClaimCustomers([]);
            }
        }
        finally {
            if (requestId === claimCustomerSearchRequest.current) {
                setClaimCustomersLoading(false);
            }
        }
    };
    const submitFlow = async (kind: "invoices" | "refunds", row: FinanceFlow) => {
        const { refreshRefundList, load } = context;
        try {
            await api.post(`/finance/${kind}/${row.id}/submit`, {
                comment: "提交财务审批",
            });
            message.success("已提交审批");
            if (kind === "refunds") {
                await refreshRefundList();
            }
            else {
                await load();
            }
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "提交失败");
        }
    };
    const openRowCaseLogs = async (row: Fee) => {
        const { setSettlementActionLoading, setSettlementContextRows, setSettlementContext } = context;
        const caseId = row.data?.case_id;
        if (!caseId) {
            message.warning("无法获取关联案件");
            return;
        }
        setSettlementActionLoading(true);
        try {
            const { data } = await api.get(`/records/${caseId}/history`);
            const items = (data.items || []).map((item: any) => ({
                ...item,
                source_case_no: row.data?.case_no || row.serial_no || "",
            }));
            setSettlementContextRows(items);
            setSettlementContext({ mode: "logs", caseRecords: [row] });
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件日志加载失败");
        }
        finally {
            setSettlementActionLoading(false);
        }
    };
    return { importBankStatement, searchClaimCustomers, submitFlow, openRowCaseLogs };
}
