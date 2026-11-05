import { Alert, Button, Tag, Tooltip } from "antd";
import { CheckOutlined, CloseOutlined, LeftOutlined, MinusOutlined, RightOutlined } from "@ant-design/icons";
import { AgentChoice, agentConfirmHeadline, agentConfirmTable, hasAgentOperationPreview } from "../AgentOperationPreview";
import type { CaseAgentAction } from "./types";

// 501634（tgn 11-05）：案件智能体的写入确认卡片改成单独浮动弹出的确认窗口，直接在窗口上“驳回，不修改”或“批准并执行”。
// “缩小”只是收起，不算批准也不算驳回，卡片仍是待确认；智能体顶部和收起后的侧边按钮都显示“待确认 N”，随时再打开。
// tgn 11-05 07:22：标题去掉案号和操作名小字（保留“待确认”标签），只写“修改/编辑确认：修改××”（动了哪块写哪块），表格只列动了的字段。
// tgn 11-06 00:01：窗口只留一行操作对象 + 一张表（修改：字段 / 现状 / 改为，只列要改的；新增：字段 / 内容）+ 两个按钮，不再有摘要和重复说明。
// 窗口放在智能体窗口（CaseAgentDock）里面渲染、用 position:fixed 浮在页面上：智能体随页签缓存（is-cached）一起藏起来时它也一起藏，
// 层级在智能体窗口（1500）之上，压过案件详情抽屉。样式不用 :has、dvh、color-mix、@container（钉钉 Chrome 100）。
export function CaseAgentConfirmFloat({ actions, currentId, failures, decisionLoading, disabled, onSelect, onDecide, onMinimize }: {
  actions: CaseAgentAction[];
  currentId: string | null;
  target?: string;
  failures: Record<string, string>;
  decisionLoading: string;
  disabled: (action: CaseAgentAction) => boolean;
  onSelect: (id: string) => void;
  onDecide: (action: CaseAgentAction, decision: "approved" | "rejected") => void;
  onMinimize: () => void;
}) {
  if (!actions.length) return null;
  const index = Math.max(0, actions.findIndex((item) => item.id === currentId));
  const action = actions[index];
  const preparing = Boolean((action as { preparing?: boolean }).preparing);
  const blocked = disabled(action);
  const readable = hasAgentOperationPreview(action);
  const table = agentConfirmTable(action);
  const go = (step: number) => onSelect(actions[(index + step + actions.length) % actions.length].id);
  return <div className="case-agent-confirm-float agent-pending-card" role="dialog" aria-modal={false} aria-label="案件智能体操作确认" data-testid="case-agent-confirm-float">
    <header className="case-agent-confirm-float-header">
      <span className="agent-pending-title"><Tag className="agent-pending-tag">待确认</Tag><span className="case-agent-confirm-float-headline">{agentConfirmHeadline(action)}</span></span>
      <span className="case-agent-confirm-float-tools">
        {actions.length > 1 && <>
          <Button type="text" size="small" icon={<LeftOutlined />} aria-label="上一项" onClick={() => go(-1)} />
          <span className="case-agent-confirm-float-count">第 {index + 1}/{actions.length} 项</span>
          <Button type="text" size="small" icon={<RightOutlined />} aria-label="下一项" onClick={() => go(1)} />
        </>}
        <Tooltip title="缩小，稍后处理（不算批准或驳回）"><Button type="text" size="small" icon={<MinusOutlined />} aria-label="缩小确认窗口" onClick={onMinimize} /></Tooltip>
      </span>
    </header>
    <div className="case-agent-confirm-float-body">
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
      {failures[action.id] && <div className="agent-action-failure" role="alert">未执行：{failures[action.id]}</div>}
    </div>
    <footer className="case-agent-confirm-float-footer">
      {action.status === "executing" ? <span className="case-agent-confirm-float-status">正在执行…</span>
        : preparing ? <span className="case-agent-confirm-float-status">回复写完即可确认</span> : null}
      <Button className="agent-btn-cancel" icon={<CloseOutlined />} disabled={blocked} onClick={() => onDecide(action, "rejected")}>驳回，不修改</Button>
      <Button className="agent-btn-confirm" icon={<CheckOutlined />} disabled={blocked || !readable} loading={decisionLoading === action.id} onClick={() => onDecide(action, "approved")}>批准并执行</Button>
    </footer>
  </div>;
}
