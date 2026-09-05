import { Button, Tag } from "antd";
import type { MessageType } from "antd/es/message/interface";
import type { CaseRow, Hearing, Profile } from "../types";
export function createHearingColumns(context: {
    readonly openSpecialCaseDetail: (row: {
        case?: CaseRow | undefined;
        case_record_id?: number | undefined;
        serial_no?: string | undefined;
        case_no?: string | undefined;
    }) => Promise<void>;
    readonly openRelatedCustomer: (target: {
        id?: number | undefined;
        serial_no?: string | undefined;
        title?: string | undefined;
        customer?: string | undefined;
    }) => Promise<void>;
    readonly casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
    readonly profile: Profile;
    readonly deleteHearing: (row: Hearing) => MessageType | undefined;
}) {
    return [
        { title: "星期", dataIndex: "weekday", width: 75 },
        { title: "日期", dataIndex: "hearing_date", width: 105 },
        { title: "时间", dataIndex: "hearing_time", width: 75 },
        { title: "开庭法院", dataIndex: "court", width: 220 },
        { title: "法庭", dataIndex: "courtroom", width: 100 },
        {
            title: "案号",
            dataIndex: "case_no",
            width: 145,
            render: (value: string, row: Hearing) => {
                return value ? (<Button type="link" className="case-cell-link" onClick={() => void context.openSpecialCaseDetail({ case_record_id: row.case_record_id, case_no: value })}>
            {value}
          </Button>) : "—";
            },
        },
        { title: "客户", dataIndex: "customer", width: 190, render: (value: string) => value ? <Button type="link" className="case-cell-link" onClick={() => context.openRelatedCustomer({ title: value })}>{value}</Button> : "—" },
        { title: "开庭类型", dataIndex: "hearing_type", width: 100 },
        { title: "开庭律师", dataIndex: "hearing_lawyer", width: 90, render: (value: string) => context.casePersonDisplayName(value) },
        {
            title: "状态",
            dataIndex: "status",
            width: 90,
            render: (v: string) => <Tag color="green">{v}</Tag>,
        },
        {
            title: "操作",
            key: "actions",
            width: 80,
            render: (_: unknown, row: Hearing) => context.profile.role === "admin"
                ? <Button type="link" danger onClick={() => context.deleteHearing(row)}>删除</Button>
                : null,
        },
    ];
}
