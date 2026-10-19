import { useState } from "react";
import { Button, Input } from "antd";
import AgentAvatar from "./AgentAvatar";
import { errorText, type PendingAction } from "./types";
import "./mcp-connection-turn.css";

type Props = {
  action: PendingAction;
  busy: boolean;
  blocked: boolean;
  onDecide: (action: PendingAction, decision: "approved" | "rejected", credential?: string) => Promise<boolean>;
};

export function McpConnectionTurn({ action, busy, blocked, onDecide }: Props) {
  const [credential, setCredential] = useState("");
  const [error, setError] = useState("");
  const raw = action.payload?.plan;
  const plan = raw && typeof raw === "object" ? raw as Record<string, unknown> : null;
  if (!plan || typeof plan.name !== "string" || typeof plan.server_url !== "string"
      || !["none", "bearer", "api_key"].includes(String(plan.authentication))
      || !["personal", "global"].includes(String(action.payload?.scope))) {
    return <p role="alert">连接计划不完整，请在对话中重新准备连接。</p>;
  }
  const needsKey = plan.authentication !== "none";
  const decide = async (decision: "approved" | "rejected") => {
    if (busy || blocked) return;
    setError("");
    try {
      await onDecide(action, decision, decision === "approved" && needsKey ? credential : undefined);
    } catch (failure) { setError(errorText(failure, "连接未完成，请核对操作状态")); }
    finally { setCredential(""); }
  };
  return <div className="assistant-message is-assistant mcp-connection-turn">
    <div className="assistant-message-avatar" role="img" aria-label="AI助手"><AgentAvatar size={32} /></div>
    <div className="assistant-bubble">
      <p>我将连接 <strong>{plan.name}</strong>。请确认以下信息：</p>
      <dl><dt>服务地址</dt><dd>{plan.server_url}</dd><dt>使用范围</dt><dd>{action.payload?.scope === "global" ? "全局共享，所有用户可以使用" : "个人专用，仅你可以使用"}</dd><dt>认证方式</dt><dd>{plan.authentication === "none" ? "无需 Token" : plan.authentication === "bearer" ? "Bearer Token" : `API Key（${String(plan.header_name)}）`}</dd></dl>
      {needsKey && <div className="mcp-connection-secure-input">
        <label htmlFor={`mcp-connect-${action.id}`}>在这里安全填写 Key / Token</label>
        <Input.Password id={`mcp-connect-${action.id}`} value={credential} disabled={busy || blocked} maxLength={8192} autoComplete="new-password" visibilityToggle={false} onChange={event => setCredential(event.target.value)} onPressEnter={() => { if (credential.trim()) void decide("approved"); }} />
        <small>只填写密钥本体；密钥加密保存，不发送给模型、不进入聊天记录。</small>
      </div>}
      {error && <p role="alert" className="mcp-connection-error">{error}</p>}
      {blocked && <p role="alert">上次确认结果尚待核对，请从历史确认记录读取实际状态，不要重复连接。</p>}
      <div className="mcp-connection-turn-actions"><Button type="primary" disabled={blocked || (needsKey && !credential.trim())} loading={busy} onClick={() => void decide("approved")}>确认连接</Button><Button disabled={busy || blocked} onClick={() => void decide("rejected")}>取消</Button><span>想修改信息，直接继续告诉我。</span></div>
    </div>
  </div>;
}
