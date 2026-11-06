import { Alert, Button, Tag } from "antd";
import { AgentChoice, agentConfirmHeadline, agentConfirmTable, hasAgentOperationPreview } from "../AgentOperationPreview";
import type { CaseAgentAction } from "./types";

// 501634（tgn 11-06 15:31 确认 A）：写入确认不再弹浮动窗口。修改内容卡片直接显示在对话里（只列改动的字段，现状 → 改为），
// 批准/驳回在输入框上方的问题条里点（CaseAgentQuestionBar）；一句话拆成几项时卡片里从上到下全部列出，每项保留“驳回此项”。
// 陶国南 11-05“写入第一轮出卡片”不变：智能体第一轮就生成这张卡片。
type Decide = (action: CaseAgentAction, decision: "approved" | "rejected") => Promise<string | void> | string | void;

function ConfirmItem({ action, single, failure, blocked, onReject }: {
  action: CaseAgentAction; single: boolean; failure?: string; blocked: boolean; onReject: () => void;
}) {
  const readable = hasAgentOperationPreview(action);
  const table = agentConfirmTable(action);
  return <section className="case-agent-confirm-item" data-testid="case-agent-confirm-item">
    {!single && <div className="case-agent-confirm-item-head">
      <strong className="case-agent-confirm-item-title">{agentConfirmHeadline(action)}</strong>
      <Button type="link" size="small" disabled={blocked} onClick={onReject}>驳回此项</Button>
    </div>}
    {!readable && <Alert type="error" showIcon title="操作内容未读取，不能确认执行" />}
    <AgentChoice action={action} />
    {table.rows.length ? <table className="case-agent-confirm-table">
      <thead><tr><th>字段</th>{table.mode === "change" ? <><th>现状</th><th>改为</th></> : <th>内容</th>}</tr></thead>
      <tbody>{table.rows.map((row) => <tr key={row.field}>
        <th scope="row">{row.label}</th>
        {table.mode === "change" && <td className="is-before">{row.before}</td>}
        <td className="is-after">{row.after}</td>
      </tr>)}</tbody>
    </table> : <div className="case-agent-confirm-empty">没有字段发生变化</div>}
    {action.status === "executing" && <div className="case-agent-confirm-status">正在执行…</div>}
    {failure && <div className="agent-action-failure" role="alert">未执行：{failure}</div>}
  </section>;
}

export const confirmTitle = (actions: CaseAgentAction[]) =>
  actions.length === 1 ? agentConfirmHeadline(actions[0]) : `共 ${actions.length} 项修改，请一起确认`;

export function CaseAgentConfirmCard({ actions, failures, decisionLoading, disabled, onDecide }: {
  actions: CaseAgentAction[];
  failures: Record<string, string>;
  decisionLoading: string;
  disabled: (action: CaseAgentAction) => boolean;
  onDecide: Decide;
}) {
  if (!actions.length) return null;
  const single = actions.length === 1;
  return <div className="case-agent-confirm-card agent-pending-card" data-testid="case-agent-confirm-card" aria-label="案件智能体操作确认">
    <div className="case-agent-confirm-card-head">
      <span className="agent-pending-title"><Tag className="agent-pending-tag">待确认</Tag><span className="case-agent-confirm-card-headline">{confirmTitle(actions)}</span></span>
    </div>
    <div className="case-agent-confirm-card-body">
      {actions.map((action) => <ConfirmItem key={action.id} action={action} single={single} failure={failures[action.id]}
        blocked={Boolean(decisionLoading) || disabled(action)} onReject={() => void onDecide(action, "rejected")} />)}
    </div>
    <div className="case-agent-confirm-card-foot">请在下方选择“批准并执行”或“驳回，不修改”，也可以在“其他补充…”里说要怎么改。</div>
  </div>;
}
