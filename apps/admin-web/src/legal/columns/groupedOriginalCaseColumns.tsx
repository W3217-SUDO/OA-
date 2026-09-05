import { Button } from "antd";
import { getLegacyGroupedCaseColumnSchema } from "../constants";
import type { CaseRow } from "../types";
export function createGroupedOriginalCaseColumns(context: {
    readonly openCounselDetail: (row: CaseRow, preferredTab?: string | undefined) => Promise<void>;
    readonly casePersonDisplayNames: (sources: unknown) => string;
    readonly caseAssistantDisplayNames: (data: Record<string, unknown> | null | undefined) => string;
    readonly legacyCaseParticipantDisplayNames: (data: Record<string, any>) => string;
    readonly openCaseLogViewer: (row: CaseRow) => void;
    readonly openCaseTasks: (row: CaseRow) => Promise<void>;
    readonly casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
}) {
    return getLegacyGroupedCaseColumnSchema().map(({ key, title, width }) => ({
        key,
        title,
        width,
        sorter: key === "base" || key === "phase" || key === "task",
        render: (_: unknown, row: CaseRow) => {
            switch (key) {
                case "base":
                    return <><p><Button type="link" className="case-cell-link" onClick={() => void context.openCounselDetail(row)}>案号:{row.serial_no}</Button></p><p>阶段:{row.status || ""}</p></>;
                case "parties":
                    return <><p>原告:{row.data.plaintiff || row.customer}</p><p>被告:{row.data.opponent || row.data.defendant || ""}</p></>;
                case "court":
                    return <><p>法院:<Button type="link" className="case-cell-link case-inline-cell-link" onClick={() => void context.openCounselDetail(row)}>{row.data.court || ""}</Button></p><p>案号:{row.data.court_case_no || ""}</p></>;
                case "lawyer":
                    return <>
            <p>律师:{context.casePersonDisplayNames(row.data.handling_lawyers)}</p>
            <p>助理:{context.caseAssistantDisplayNames(row.data)}</p>
            {Array.isArray(row.data.legacy_participants) && row.data.legacy_participants.length > 0 && <p>案件参与人:{context.legacyCaseParticipantDisplayNames(row.data)}</p>}
          </>;
                case "phase":
                    return <><p>变更时间:{row.data.phase_changed_at || ""}</p><p>变更时长:{row.data.phase_duration || row.data.phase_changed_days || ""} <Button type="link" size="small" onClick={() => context.openCaseLogViewer(row)}>查看日志</Button></p></>;
                case "task":
                    return <><p>名称:<Button type="link" className="case-cell-link case-task-cell-link" onClick={() => context.openCaseTasks(row)}>{row.data.task_name || ""}</Button>　处理人:{context.casePersonDisplayName(row.data.task_handler || row.data.task_owner, row.data.task_handler_display_name || row.data.task_owner_display_name)}</p><p>内容:{row.data.task_content || ""}　到期日期:{row.data.task_due_date || row.data.task_deadline || ""}</p></>;
                default:
                    return null;
            }
        },
    }));
}
