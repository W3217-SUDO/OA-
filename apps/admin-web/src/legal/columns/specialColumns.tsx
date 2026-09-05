import { Button, Space } from "antd";
import type { MessageType } from "antd/es/message/interface";
import type { AttachmentRow, CaseDetailCapabilities, CaseRow } from "../types";
export function createSpecialColumns(context: {
    readonly openSpecialCaseDetail: (row: {
        case?: CaseRow | undefined;
        case_record_id?: number | undefined;
        serial_no?: string | undefined;
        case_no?: string | undefined;
    }) => Promise<void>;
    readonly casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
    readonly casePersonDisplayNames: (sources: unknown) => string;
    readonly caseAssistantDisplayNames: (data: Record<string, unknown> | null | undefined) => string;
    readonly getCaseCapability: (row?: CaseRow | null | undefined) => CaseDetailCapabilities;
    readonly openProgress: (row: CaseRow) => MessageType | undefined;
    readonly openExecutionStatus: (rows: CaseRow[]) => MessageType | undefined;
    readonly openCaseLogViewer: (row: CaseRow) => void;
    readonly openCaseListLogCreator: (row: CaseRow) => MessageType | undefined;
    readonly openRelatedCustomer: (target: {
        id?: number | undefined;
        serial_no?: string | undefined;
        title?: string | undefined;
        customer?: string | undefined;
    }) => Promise<void>;
    readonly invoiceCase: (row: AttachmentRow) => CaseRow | undefined;
    readonly relatedFinance: (id: number) => CaseRow | undefined;
}): Record<string, any[]> {
    return {
        schedule: [
            { title: "星期", dataIndex: "weekday" },
            { title: "开庭日期", dataIndex: "hearing_date" },
            { title: "时间", dataIndex: "hearing_time" },
            {
                title: "案件编号",
                render: (_: unknown, row: any) => (<Button type="link" className="case-cell-link" onClick={() => context.openSpecialCaseDetail(row)}>
            {row.case_no || row.case?.serial_no || ""}
          </Button>),
            },
            { title: "案件阶段", render: (_: unknown, row: any) => row.case?.status || "" },
            { title: "法院名称", dataIndex: "court" },
            { title: "法庭", dataIndex: "courtroom" },
            { title: "原告", render: (_: unknown, row: any) => row.case?.data.plaintiff || row.customer },
            { title: "被告", render: (_: unknown, row: any) => row.case?.data.opponent || "" },
            { title: "开庭律师", dataIndex: "hearing_lawyer", render: (value: string) => context.casePersonDisplayName(value) },
            { title: "经办律师", render: (_: unknown, row: any) => context.casePersonDisplayNames(row.case?.data.handling_lawyers) },
            { title: "律师助理", render: (_: unknown, row: any) => context.caseAssistantDisplayNames(row.case?.data) },
        ],
        execution: [{ title: "基本信息", render: (_: unknown, row: CaseRow) => <><p><Button type="link" className="case-cell-link" onClick={() => context.openSpecialCaseDetail(row)}>{row.serial_no}</Button></p><p>阶段:{row.status}</p><p>执行状态:{row.data.execution_status || "—"}</p></> }, { title: "当事人信息", render: (_: unknown, row: CaseRow) => <><p>原告:{row.data.plaintiff || row.customer}</p><p>被告:{row.data.opponent || ""}</p></> }, { title: "法院信息", render: (_: unknown, row: CaseRow) => <><p>法院:{row.data.court || ""}</p><p>案号:{row.data.court_case_no || ""}</p></> }, { title: "法官信息", render: (_: unknown, row: CaseRow) => row.data.judge || "" }, { title: "委托律师", render: (_: unknown, row: CaseRow) => context.casePersonDisplayNames(row.data.handling_lawyers) }, { title: "判决信息", render: (_: unknown, row: CaseRow) => row.data.judgment_result || "" }, { title: "进度时长", render: (_: unknown, row: CaseRow) => row.data.execution_days ?? 0 }, { title: "操作", render: (_: unknown, row: CaseRow) => <Space size={0}>{context.getCaseCapability(row).can_update_progress && <><Button type="link" onClick={() => context.openProgress(row)}>修改进度</Button><Button type="link" onClick={() => context.openExecutionStatus([row])}>执行状态</Button></>}<Button type="link" onClick={() => context.openCaseLogViewer(row)}>查看日志</Button>{context.getCaseCapability(row).can_create_log && <Button type="link" onClick={() => context.openCaseListLogCreator(row)}>新增日志</Button>}</Space> }],
        unclaimed: ["案号", "原告", "被告", "金额", "回款单位", "到账金额", "到账时间", "结算状态", "案件阶段", "案源人", "开庭律师", "律师助理", "调查员", "品管"].map((title, i) => ({ title, key: String(i), render: (_: unknown, row: CaseRow) => i === 0 ? <Button type="link" className="case-cell-link" onClick={() => context.openSpecialCaseDetail(row)}>{row.serial_no}</Button> : [row.data.plaintiff || row.customer, row.data.opponent, row.data.amount, row.data.payer, row.data.received_amount, row.data.received_at, row.data.settlement_status, row.status, context.casePersonDisplayName(row.data.source_person || row.owner, row.data.source_person_display_name || row.owner_display_name), context.casePersonDisplayName(row.data.hearing_lawyer, row.data.hearing_lawyer_display_name), context.caseAssistantDisplayNames(row.data), context.casePersonDisplayName(row.data.investigator, row.data.investigator_display_name), context.casePersonDisplayName(row.data.quality_manager, row.data.quality_manager_display_name)][i - 1] || "" })),
        stage: [{ title: "姓名", dataIndex: "name" }, { title: "日期", dataIndex: "date" }, { title: "立案进度", dataIndex: "filing" }, { title: "退费进度", dataIndex: "refund" }, { title: "执行进度", dataIndex: "execution" }, { title: "线索进度", dataIndex: "clue" }],
        refund: ["案号", "原告", "被告", "案件阶段", "律师助理", "开庭律师", "费用类型", "金额", "退费金额", "新建时间", "法院名称", "退费进度", "进度时长", "操作"].map((title, i) => ({ title, key: String(i), render: (_: unknown, row: CaseRow) => i === 0 ? <Button type="link" className="case-cell-link" onClick={() => context.openSpecialCaseDetail({ case_no: row.data.case_no || row.serial_no })}>{row.data.case_no || row.serial_no}</Button> : [row.data.plaintiff || row.customer, row.data.opponent, row.data.case_stage || row.status, context.caseAssistantDisplayNames(row.data), context.casePersonDisplayName(row.data.hearing_lawyer, row.data.hearing_lawyer_display_name), row.data.fee_type, row.data.amount, row.data.refund_amount, row.data.created_at || "", row.data.court, row.data.refund_status, row.data.progress_days, "查看"][i - 1] || "" })),
        receipt: ["案号", "案件名称", "客户", "费用类型", "金额", "申请人", "通知日期", "已收", "已付", "已开票"].map((title, i) => ({ title, key: String(i), render: (_: unknown, row: CaseRow) => i === 0 ? <Button type="link" className="case-cell-link" onClick={() => context.openSpecialCaseDetail(row)}>{row.serial_no}</Button> : i === 2 && row.customer ? <Button type="link" className="case-cell-link" onClick={() => context.openRelatedCustomer({ id: Number(row.data.customer_id) || undefined, serial_no: row.data.customer_no, title: row.customer })}>{row.customer}</Button> : [row.title, row.customer, row.data.fee_type, row.data.amount, context.casePersonDisplayName(row.owner, row.owner_display_name), row.data.notice_date, row.data.received_amount, row.data.paid_amount, row.data.invoiced_amount][i - 1] || "" })),
        invoice: [{ title: "文件名", dataIndex: "original_name" }, { title: "案件编号", render: (_: unknown, row: AttachmentRow) => { const target = context.invoiceCase(row); const caseNo = target?.serial_no || context.relatedFinance(row.record_id || 0)?.data?.case_no || ""; return caseNo ? <Button type="link" className="case-cell-link" onClick={() => context.openSpecialCaseDetail(target || { case_no: caseNo })}>{caseNo}</Button> : ""; } }, { title: "案件类型", render: (_: unknown, row: AttachmentRow) => context.invoiceCase(row)?.data.case_type || "" }, { title: "发票申请人", render: (_: unknown, row: AttachmentRow) => context.casePersonDisplayName(row.uploader, row.uploader_display_name) }, { title: "费用类型", render: (_: unknown, row: AttachmentRow) => context.relatedFinance(row.record_id || 0)?.data?.fee_type || row.category }, { title: "费用金额", render: (_: unknown, row: AttachmentRow) => context.relatedFinance(row.record_id || 0)?.data?.amount ?? "" }, { title: "票据编号", render: (_: unknown, row: AttachmentRow) => context.relatedFinance(row.record_id || 0)?.data?.invoice_no || row.remark || "" }, { title: "票据金额", render: (_: unknown, row: AttachmentRow) => context.relatedFinance(row.record_id || 0)?.data?.invoice_amount ?? context.relatedFinance(row.record_id || 0)?.data?.amount ?? "" }, { title: "票据日期", render: (_: unknown, row: AttachmentRow) => context.relatedFinance(row.record_id || 0)?.data?.invoice_date || row.created_at }],
    };
}
