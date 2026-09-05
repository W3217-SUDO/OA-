import { Button } from "antd";
import type { CaseRow } from "../types";
export function createOriginalArchiveColumns(context: {
    readonly casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
    readonly archiveDone: boolean;
    readonly archiveRefused: boolean;
    readonly openCounselDetail: (row: CaseRow, preferredTab?: string | undefined) => Promise<void>;
    readonly casePersonDisplayNames: (sources: unknown) => string;
    readonly caseAssistantDisplayNames: (data: Record<string, unknown> | null | undefined) => string;
}): any[] {
    return [
        { title: "提交人", key: "submitter", width: 105, render: (_: unknown, row: CaseRow) => context.casePersonDisplayName(row.data.archive_submitter || row.owner, row.data.archive_submitter_display_name || row.owner_display_name) },
        { title: "提交日期", key: "submitted", width: 150, render: (_: unknown, row: CaseRow) => row.data.archive_submitted_at || "" },
        ...(context.archiveDone || context.archiveRefused ? [{ title: "审核人", key: "reviewer", width: 105, render: (_: unknown, row: CaseRow) => context.casePersonDisplayName(row.data.archive_reviewer, row.data.archive_reviewer_display_name) }, { title: "审核日期", key: "reviewed", width: 150, render: (_: unknown, row: CaseRow) => row.data.archive_reviewed_at || row.data.archived_at || "" }] : [{ title: "提交人备注", key: "comment", width: 160, render: (_: unknown, row: CaseRow) => row.data.archive_submit_comment || row.description || "" }]),
        { title: "案件编号", width: 145, render: (_: unknown, row: CaseRow) => <Button type="link" className="case-cell-link" onClick={() => void context.openCounselDetail(row)}>{row.serial_no}</Button> }, { title: "案件阶段", dataIndex: "status", width: 110 },
        { title: "法院名称", key: "court", width: 190, render: (_: unknown, row: CaseRow) => row.data.court || "" },
        { title: "原告", key: "plaintiff", width: 180, render: (_: unknown, row: CaseRow) => row.data.plaintiff || row.customer },
        { title: "被告", key: "defendant", width: 180, render: (_: unknown, row: CaseRow) => row.data.opponent || "" },
        { title: "开庭律师", key: "hearing", width: 105, render: (_: unknown, row: CaseRow) => context.casePersonDisplayName(row.data.hearing_lawyer, row.data.hearing_lawyer_display_name) },
        { title: "经办律师", key: "handlers", width: 130, render: (_: unknown, row: CaseRow) => context.casePersonDisplayNames(row.data.handling_lawyers) },
        { title: "律师助理", key: "assistant", width: 105, render: (_: unknown, row: CaseRow) => context.caseAssistantDisplayNames(row.data) },
    ];
}
