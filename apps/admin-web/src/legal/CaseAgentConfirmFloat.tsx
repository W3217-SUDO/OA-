import { useState } from "react";
import { Alert, Button, Tag, Tooltip } from "antd";
import { CheckOutlined, CloseOutlined, MinusOutlined } from "@ant-design/icons";
import { AgentChoice, agentConfirmHeadline, agentConfirmTable, hasAgentOperationPreview } from "../AgentOperationPreview";
import type { CaseAgentAction } from "./types";

// 501634（tgn 11-05）：案件智能体的写入确认卡片改成单独浮动弹出的确认窗口，直接在窗口上“驳回，不修改”或“批准并执行”。
// “缩小”只是收起，不算批准也不算驳回，卡片仍是待确认；智能体顶部和收起后的侧边按钮都显示“待确认 N”，随时再打开。
// tgn 11-05 07:22：标题去掉案号和操作名小字（保留“待确认”标签），只写“修改/编辑确认：修改××”（动了哪块写哪块），表格只列动了的字段。
// tgn 11-05 07:47：一句话拆成几项（如开庭律师一项、经办律师一项）时不再翻页，一个窗口从上到下全部列出；
// 底部两个按钮对窗口里的全部项一起生效，每项右边另有“驳回此项”。
// 窗口放在智能体窗口（CaseAgentDock）里面渲染、用 position:fixed 浮在页面上：智能体随页签缓存（is-cached）一起藏起来时它也一起藏，
// 层级在智能体窗口（1500）之上，压过案件详情抽屉。样式不用 :has、dvh、color-mix、@container（钉钉 Chrome 100）。
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
    {action.status === "executing" && <div className="case-agent-confirm-float-status">正在执行…</div>}
    {failure && <div className="agent-action-failure" role="alert">未执行：{failure}</div>}
  </section>;
}

export function CaseAgentConfirmFloat({ actions, failures, decisionLoading, disabled, onDecide, onMinimize }: {
  actions: CaseAgentAction[];
  currentId?: string | null;
  target?: string;
  failures: Record<string, string>;
  decisionLoading: string;
  disabled: (action: CaseAgentAction) => boolean;
  onSelect?: (id: string) => void;
  onDecide: Decide;
  onMinimize: () => void;
}) {
  const [running, setRunning] = useState(false);
  if (!actions.length) return null;
  const single = actions.length === 1;
  const open = actions.filter((action) => !disabled(action));
  const approvable = open.filter((action) => hasAgentOperationPreview(action));
  const preparing = actions.some((action) => Boolean((action as { preparing?: boolean }).preparing));
  // 全部批准/全部驳回按窗口里从上到下的顺序逐项办；有一项没执行成功就停下，后面的仍待确认。
  const decideAll = async (decision: "approved" | "rejected") => {
    setRunning(true);
    try {
      for (const action of decision === "approved" ? approvable : open) {
        const failure = await onDecide(action, decision);
        if (failure) break;
      }
    } finally {
      setRunning(false);
    }
  };
  const busy = running || Boolean(decisionLoading);
  return <div className="case-agent-confirm-float agent-pending-card" role="dialog" aria-modal={false} aria-label="案件智能体操作确认" data-testid="case-agent-confirm-float">
    <header className="case-agent-confirm-float-header">
      <span className="agent-pending-title"><Tag className="agent-pending-tag">待确认</Tag><span className="case-agent-confirm-float-headline">
        {single ? agentConfirmHeadline(actions[0]) : `共 ${actions.length} 项修改，请一起确认`}
      </span></span>
      <span className="case-agent-confirm-float-tools">
        <Tooltip title="缩小，稍后处理（不算批准或驳回）"><Button type="text" size="small" icon={<MinusOutlined />} aria-label="缩小确认窗口" onClick={onMinimize} /></Tooltip>
      </span>
    </header>
    <div className="case-agent-confirm-float-body">
      {actions.map((action) => <ConfirmItem key={action.id} action={action} single={single} failure={failures[action.id]}
        blocked={busy || disabled(action)} onReject={() => void onDecide(action, "rejected")} />)}
    </div>
    <footer className="case-agent-confirm-float-footer">
      {preparing ? <span className="case-agent-confirm-float-status">回复写完即可确认</span> : null}
      <Button className="agent-btn-cancel" icon={<CloseOutlined />} disabled={busy || !open.length} onClick={() => void decideAll("rejected")}>{single ? "驳回，不修改" : "全部驳回"}</Button>
      <Button className="agent-btn-confirm" icon={<CheckOutlined />} disabled={busy || !approvable.length} loading={busy} onClick={() => void decideAll("approved")}>{single ? "批准并执行" : "全部批准并执行"}</Button>
    </footer>
  </div>;
}
