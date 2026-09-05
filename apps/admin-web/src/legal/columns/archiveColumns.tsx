import { Button, Tag } from "antd";
import { ARCHIVE_FINAL_STATUSES, ARCHIVE_REVIEW_STATUSES, statusColors } from "../constants";
import type { CaseDetailCapabilities, CaseRow } from "../types";
export function createArchiveColumns(context: {
    readonly caseColumns: ({
        title: string;
        dataIndex: string;
        width: number;
        render: (value: string, row: CaseRow) => React.JSX.Element;
        ellipsis?: undefined;
        key?: undefined;
        fixed?: undefined;
    } | {
        title: string;
        dataIndex: string;
        width: number;
        ellipsis: boolean;
        render?: undefined;
        key?: undefined;
        fixed?: undefined;
    } | {
        title: string;
        dataIndex: string;
        width: number;
        ellipsis: boolean;
        render: (value: string, r: CaseRow) => "—" | React.JSX.Element;
        key?: undefined;
        fixed?: undefined;
    } | {
        title: string;
        key: string;
        width: number;
        render: (_: unknown, r: CaseRow) => any;
        dataIndex?: undefined;
        ellipsis?: undefined;
        fixed?: undefined;
    } | {
        title: string;
        key: string;
        width: number;
        ellipsis: boolean;
        render: (_: unknown, r: CaseRow) => any;
        dataIndex?: undefined;
        fixed?: undefined;
    } | {
        title: string;
        key: string;
        fixed: "right";
        width: number;
        render: (_: unknown, r: CaseRow) => React.JSX.Element;
        dataIndex?: undefined;
        ellipsis?: undefined;
    })[];
    readonly canReview: boolean;
    readonly openArchiveReview: (row: CaseRow) => void;
    readonly getCaseCapability: (row?: CaseRow | null | undefined) => CaseDetailCapabilities;
    readonly openArchive: (row: CaseRow, type?: "normal" | "deficit") => Promise<boolean | undefined>;
}) {
    return [
        ...context.caseColumns.slice(0, 5),
        {
            title: "归档状态",
            dataIndex: "status",
            width: 105,
            render: (v: string) => <Tag color={statusColors[v] || "blue"}>{v}</Tag>,
        },
        {
            title: "归档号",
            key: "archive_no",
            width: 135,
            render: (_: unknown, r: CaseRow) => r.data.archive_no || "—",
        },
        {
            title: "纸质卷宗",
            key: "paper",
            width: 170,
            render: (_: unknown, r: CaseRow) => r.data.paper_archive_location
                ? `${r.data.paper_archive_location}（${r.data.paper_volume_count || 1}卷）`
                : "—",
        },
        {
            title: "四项检查",
            key: "checks",
            width: 95,
            render: (_: unknown, r: CaseRow) => [
                "case_closed",
                "fees_settled",
                "documents_complete",
                "finance_complete",
            ].every((k) => r.data[k]) ? (<Tag color="green">已通过</Tag>) : (<Tag color="orange">待完善</Tag>),
        },
        {
            title: "驳回原因",
            key: "reject",
            width: 160,
            ellipsis: true,
            render: (_: unknown, r: CaseRow) => r.data.archive_reject_reason || "—",
        },
        {
            title: "操作",
            key: "archive",
            fixed: "right" as const,
            width: 190,
            render: (_: unknown, r: CaseRow) => ARCHIVE_REVIEW_STATUSES.includes(r.status) && context.canReview ? (<Button type="link" onClick={() => context.openArchiveReview(r)}>归档审核</Button>) : ARCHIVE_FINAL_STATUSES.includes(r.status) ? (<Tag color="green">已归档</Tag>) : context.getCaseCapability(r).can_archive ? (<Button type="link" onClick={() => context.openArchive(r)}>
            归档检查
          </Button>) : null,
        },
    ];
}
