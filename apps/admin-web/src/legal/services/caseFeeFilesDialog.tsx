import { Button, message, Modal, Space } from "antd";
import Table from "../../components/ResizableTable";
import { api } from "../../api";
import { openAttachmentOnlinePreview } from "../../attachmentOnlinePreview.mjs";
import { displayFinancialValue } from "../../financialValueDisplay";
import type { CaseFeeFile } from "../caseReceiptFiles";

export async function openCaseFeeFilesDialog(options: {
    caseId: number;
    feeId: number;
    serialNo: string;
    invoicesOnly?: boolean;
    download: (path: string, name: string) => Promise<void>;
    onChanged: () => Promise<void>;
}) {
    const path = `/cases/${options.caseId}/fees/${options.feeId}/files`;
    const { data } = await api.get<{ items: CaseFeeFile[]; can_delete: boolean }>(path);
    let rows = options.invoicesOnly ? data.items.filter(item => item.kind === "invoice") : data.items;
    const pending = new Set<number>();
    let closed = false;
    const content = () => <Table size="small" rowKey="attachment_id" pagination={{ pageSize: 10 }} scroll={{ x: 980 }} dataSource={rows} columns={[
        { title: "来源", dataIndex: "source", width: 110, render: (value: string) => displayFinancialValue(value) },
        { title: "票据号", dataIndex: "bill_no", width: 150, render: (value: string) => displayFinancialValue(value) || "—" },
        { title: "日期", dataIndex: "bill_date", width: 110, render: (value: string) => displayFinancialValue(value) || "—" },
        { title: "文件", dataIndex: "original_name", ellipsis: true, render: (value: string) => displayFinancialValue(value) },
        { title: "导入说明", dataIndex: "remark", width: 220, ellipsis: true, render: (value: string) => displayFinancialValue(value) },
        { title: "操作", width: 190, render: (_: unknown, item: CaseFeeFile) => <Space size={0}>
            <Button type="link" onClick={() => void openAttachmentOnlinePreview(api, { id: item.attachment_id, original_name: item.original_name }).catch((error: any) => message.error(error?.response?.data?.detail || error?.message || "查看票据失败"))}>查看</Button>
            <Button type="link" onClick={() => void options.download(`/attachments/${item.attachment_id}/download`, item.original_name).catch((error: any) => message.error(error?.response?.data?.detail || "下载票据失败"))}>下载</Button>
            {data.can_delete && <Button type="link" danger disabled={pending.has(item.attachment_id)} onClick={() => {
                if (closed || pending.has(item.attachment_id)) return;
                pending.add(item.attachment_id);
                dialog.update({ content: content() });
                const release = () => { pending.delete(item.attachment_id); if (!closed) dialog.update({ content: content() }); };
                Modal.confirm({ title: "删除费用票据附件", content: `确认删除“${displayFinancialValue(item.original_name)}”的附件记录及关联？存储原件保留，费用金额和审批状态不变。`, okText: "删除", okButtonProps: { danger: true }, cancelText: "取消",
                    onCancel: release,
                    onOk: async () => {
                        try { await api.delete(`${path}/${item.attachment_id}`); }
                        catch (error: any) { message.error(error?.response?.data?.detail || "删除未确认，请刷新后核对附件状态"); release(); throw error; }
                        rows = rows.filter(row => row.attachment_id !== item.attachment_id);
                        release();
                        message.success("附件记录及关联已删除");
                        try { await options.onChanged(); }
                        catch (error: any) { message.error(error?.response?.data?.detail || "附件已删除，但费用列表刷新失败，请刷新页面"); }
                    },
                });
            }}>删除</Button>}
        </Space> },
    ]} />;
    const dialog = Modal.info({ title: `${options.invoicesOnly ? "发票文件" : "票据文件"}：${options.serialNo}`, width: 860, okText: "关闭", content: content(), afterClose: () => { closed = true; } });
}
