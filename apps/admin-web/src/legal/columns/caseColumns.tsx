import { CalendarOutlined, CheckSquareOutlined, EditOutlined, FileTextOutlined, TeamOutlined } from "@ant-design/icons";
import { Button, Space, Tag } from "antd";
import type { MessageType } from "antd/es/message/interface";
import { useMemo } from "react";
import { ARCHIVE_LOCKED_STATUSES, statusColors } from "../constants";
import type { CaseDetailCapabilities, CaseRow } from "../types";
export function createCaseColumns(context: {
    readonly openCounselDetail: (row: CaseRow, preferredTab?: string | undefined) => Promise<void>;
    readonly openRelatedContract: (target: unknown) => void;
    readonly openRelatedCustomer: (target: {
        id?: number | undefined;
        serial_no?: string | undefined;
        title?: string | undefined;
        customer?: string | undefined;
    }) => Promise<void>;
    readonly casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
    readonly casePersonDisplayNames: (sources: unknown) => string;
    readonly caseAssistantDisplayNames: (data: Record<string, unknown> | null | undefined) => string;
    readonly getCaseCapability: (row?: CaseRow | null | undefined) => CaseDetailCapabilities;
    readonly openAssign: (row: CaseRow) => MessageType | undefined;
    readonly openProgress: (row: CaseRow) => MessageType | undefined;
    readonly openCaseTasks: (row: CaseRow) => Promise<void>;
    readonly openCaseFee: (row: CaseRow, expenseScope?: "律所" | "平台" | "内部", expenseSubtype?: string | undefined) => Promise<boolean | undefined>;
    readonly openHearing: (row: CaseRow) => MessageType | undefined;
    readonly openArchive: (row: CaseRow, type?: "normal" | "deficit") => Promise<boolean | undefined>;
    readonly caseActionCapabilities: Record<number, CaseDetailCapabilities>;
    readonly cases: CaseRow[];
}) {
    return useMemo(() => [
        {
            title: "案号",
            dataIndex: "serial_no",
            width: 150,
            render: (value: string, row: CaseRow) => (<Button type="link" className="case-cell-link" onClick={() => void context.openCounselDetail(row)}>
            {value}
          </Button>),
        },
        { title: "案件名称", dataIndex: "title", width: 220, ellipsis: true },
        {
            title: "关联合同",
            key: "contract",
            width: 165,
            ellipsis: true,
            render: (_: unknown, r: CaseRow) => r.data.contract_no ? <Button type="link" className="case-cell-link" onClick={() => context.openRelatedContract({ id: Number(r.data.contract_record_id) || undefined, serial_no: r.data.contract_no })}>{r.data.contract_no}</Button> : <Tag color="warning">系统转案待补</Tag>,
        },
        { title: "客户", dataIndex: "customer", width: 180, ellipsis: true, render: (value: string, r: CaseRow) => value ? <Button type="link" className="case-cell-link" onClick={() => context.openRelatedCustomer({ id: Number(r.data.customer_id) || undefined, serial_no: r.data.customer_no, title: value })}>{value}</Button> : "—" },
        {
            title: "案件类型",
            key: "type",
            width: 100,
            render: (_: unknown, r: CaseRow) => r.data.case_type || "-",
        },
        {
            title: "阶段",
            dataIndex: "status",
            width: 115,
            render: (v: string) => <Tag color={statusColors[v] || "blue"}>{v}</Tag>,
        },
        {
            title: "法院",
            key: "court",
            width: 190,
            ellipsis: true,
            render: (_: unknown, r: CaseRow) => r.data.court || "-",
        },
        {
            title: "开庭律师",
            key: "hearing_lawyer",
            width: 90,
            render: (_: unknown, r: CaseRow) => context.casePersonDisplayName(r.data.hearing_lawyer, r.data.hearing_lawyer_display_name),
        },
        {
            title: "经办律师",
            key: "handlers",
            width: 130,
            render: (_: unknown, r: CaseRow) => context.casePersonDisplayNames(r.data.handling_lawyers),
        },
        {
            title: "律师助理",
            key: "assistant",
            width: 90,
            render: (_: unknown, r: CaseRow) => context.caseAssistantDisplayNames(r.data),
        },
        {
            title: "操作",
            key: "actions",
            fixed: "right" as const,
            width: 400,
            render: (_: unknown, r: CaseRow) => {
                const capability = context.getCaseCapability(r);
                return (<Space size={0}>
            {capability.can_assign_team && <Button type="link" icon={<TeamOutlined />} disabled={ARCHIVE_LOCKED_STATUSES.includes(r.status)} onClick={() => context.openAssign(r)}>
              分配
            </Button>}
            {capability.can_update_progress && <Button type="link" icon={<EditOutlined />} disabled={[
                            "等待公证书",
                            "等待审核公证书",
                            "待归档审核",
                            "已归档",
                        ].includes(r.status)} onClick={() => context.openProgress(r)}>
              进展
            </Button>}
            <Button type="link" icon={<FileTextOutlined />} onClick={() => context.openCaseTasks(r)}>
              任务
            </Button>
            {capability.can_create_finance && <Button type="link" onClick={() => context.openCaseFee(r)}>费用</Button>}
            {capability.can_manage_hearing && <Button type="link" icon={<CalendarOutlined />} disabled={ARCHIVE_LOCKED_STATUSES.includes(r.status)} onClick={() => context.openHearing(r)}>
              排期
            </Button>}
            {capability.can_archive && <Button type="link" icon={<CheckSquareOutlined />} disabled={ARCHIVE_LOCKED_STATUSES.includes(r.status)} onClick={() => context.openArchive(r)}>
              归档
            </Button>}
          </Space>);
            },
        },
    ], [context.caseActionCapabilities, context.cases]);
}
