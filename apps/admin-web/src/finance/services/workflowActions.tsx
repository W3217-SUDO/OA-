import { message, Modal, Alert } from "antd";
import Table from "../../components/ResizableTable";
import { api } from "../../api";
import type { Fee, FinanceFlow } from "../types";

export type FinanceLinkedRecord = Fee & { module: string; owner_display_name?: string };

export async function loadFinanceLinkedRecord(recordId: number, signal?: AbortSignal): Promise<FinanceLinkedRecord> {
    const { data } = await api.get<FinanceLinkedRecord>(`/records/${recordId}`, { signal });
    return data;
}

export async function reviewFinanceFlowRequest(kind: "invoices" | "refunds", rowId: number, approved: boolean): Promise<void> {
    await api.post(`/finance/${kind}/${rowId}/review`, {
        approved,
        comment: approved ? "财务审核通过" : "资料不完整，退回修改",
    });
}
/** finance workflow operations; dependencies are read when each operation runs. */
export interface FinanceWorkflowDependencies {
    readonly bankSource: string;
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
}
export function createFinanceWorkflowActions(context: FinanceWorkflowDependencies) {
    const importBankStatement = async (file?: File) => {
        const { load, bankUploadRef } = context;
        if (!file)
            return;
        if (bankUploadRef.current?.disabled) return;
        if (file.size > 100 * 1024 * 1024) {
            message.error("银行流水文件不能超过100MB，请拆分后上传");
            if (bankUploadRef.current) bankUploadRef.current.value = "";
            return;
        }
        const closeProgress = message.loading("正在上传并解析银行流水，大文件可能需要几分钟，请勿重复上传", 0);
        if (bankUploadRef.current) bankUploadRef.current.disabled = true;
        const body = new FormData();
        const bankSource = context.bankSource;
        body.append("file", file);
        body.append("bank_source", bankSource);
        try {
            const { data } = await api.post("/finance/incoming-payments/import", body, { headers: { "Content-Type": "multipart/form-data" } });
            if (data.requires_confirmation) {
                Modal.confirm({
                    title: "核对银行流水识别结果", width: 1080, okText: "确认导入", cancelText: "取消",
                    okButtonProps: { disabled: !data.valid_count },
                    content: <div>
                        <Alert type="warning" showIcon message="尚未写入回款。请逐笔核对付款方、日期、金额和银行流水号；识别有误请取消并调整原文件。" />
                        <p>{file.name}：可导入 {data.valid_count} 笔，跳过支出 {data.skipped} 笔，{data.errors?.length || 0} 笔校验未通过。</p>
                        <Table size="small" rowKey={(_, index) => String(index)} dataSource={data.items}
                            pagination={{pageSize: 10}} scroll={{x: 900, y: 300}}
                            columns={[
                                {title: "来源页", dataIndex: "source", width: 180},
                                {title: "付款方", dataIndex: "payer_name", width: 160},
                                {title: "银行流水号", dataIndex: "bank_reference", width: 200},
                                {title: "到账日期", dataIndex: "received_date", width: 110},
                                {title: "到账金额", dataIndex: "amount", width: 110},
                                {title: "备注", dataIndex: "remark", width: 180},
                            ]} />
                        {data.errors?.length > 0 && <details><summary>查看未通过的流水</summary>
                            <div style={{maxHeight: 160, overflow: "auto"}}>{data.errors.map((item: any, index: number) => <div key={index}>{item.sheet} 第{item.row}行：{item.error}</div>)}</div>
                        </details>}
                    </div>,
                    onOk: async () => {
                        const confirmed = new FormData();
                        confirmed.append("bank_source", bankSource);
                        confirmed.append("confirmed_rows", JSON.stringify(data.rows));
                        confirmed.append("confirmation_token", data.confirmation_token);
                        try {
                            const response = await api.post("/finance/incoming-payments/import", confirmed);
                            if (response.data.created > 0) message.success(`已导入 ${response.data.created} 笔回款`);
                            else message.warning("没有新增回款，请查看校验结果");
                            if (response.data.errors?.length) Modal.warning({title: "部分流水未导入", content:
                                <div style={{maxHeight: 300, overflow: "auto"}}>{response.data.errors.map((item: any, index: number) => <div key={index}>{item.sheet} 第{item.row}行：{item.error}</div>)}</div>});
                            await load();
                        } catch (error: any) {
                            message.error(error?.response?.data?.detail || "确认导入失败，请刷新列表核对结果后再操作");
                            throw error;
                        }
                    },
                });
                return;
            }
            if (data.errors?.length) {
                Modal.warning({title:`导入 ${data.created} 条，${data.errors.length} 条未导入`,
                    content:<div style={{maxHeight:360,overflow:"auto"}}>{data.errors.map((item:any,index:number)=><div key={index}>{item.sheet || ""} 第{item.row}行：{item.error}</div>)}</div>});
            }
            else {
                if (data.created > 0) message.success(`成功导入 ${data.created} 条银行到账${data.skipped ? `，跳过 ${data.skipped} 条支出` : ""}`);
                else message.warning("文件中没有可导入的收入流水");
            }
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.status === 413
                ? "文件超过服务器上传上限，银行流水单文件最多100MB"
                : error?.response?.data?.detail || ([502, 504].includes(error?.response?.status)
                    ? "导入连接超时，请先刷新列表确认结果，避免重复提交"
                    : "银行流水导入失败，请检查网络；重试前请先刷新列表确认结果"));
        }
        finally {
            closeProgress();
            if (bankUploadRef.current) {
                bankUploadRef.current.value = "";
                bankUploadRef.current.disabled = false;
            }
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
    return { importBankStatement, searchClaimCustomers, submitFlow };
}
