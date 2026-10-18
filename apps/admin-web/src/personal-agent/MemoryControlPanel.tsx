import { useEffect, useState } from "react";
import { Alert, Button, Drawer, Empty, List, Popconfirm, Segmented, Space, Spin, Switch, Tag, Tooltip, message } from "antd";
import { DeleteOutlined, HistoryOutlined, LockOutlined, ReloadOutlined, SettingOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "./types";
import "./memory-control-panel.css";

export type PersonalMemory = {
  id: string;
  memory_type: "short" | "long";
  content: string;
  source?: string | null;
  conversation_id?: string | null;
  created_at?: string | null;
  expires_at?: string | null;
  permission_scope?: string | null;
  memory_category?: "fact" | "preference" | "experience" | "temporary_state" | null;
  source_type?: string | null;
  source_label?: string | null;
  task_scope?: string | null;
  confidence?: number | null;
  recall_score?: number | null;
  compressed_at?: string | null;
  covered_message_start?: number | null;
  covered_message_end?: number | null;
  covered_messages?: number | null;
  covered_message_range?: string | null;
  covered_message_count?: number | null;
  message_range?: string | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  token_count?: number | null;
  summary_token_count?: number | null;
  token_budget?: number | null;
};

type MemoryAudit = { id: string; occurred_at: string; action: string; memory_id?: string | null; memory_category?: string | null; task_scope?: string | null; permission_scope?: string | null; content_snapshot?: string | null; detail?: Record<string, unknown> };
type MemoryResponse = { items: PersonalMemory[]; total?: number; long_term_enabled?: boolean; recall_limit?: number };

export function MemoryControlPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [scope, setScope] = useState<"short" | "long" | "audit">("short");
  const [items, setItems] = useState<PersonalMemory[]>([]);
  const [audit, setAudit] = useState<MemoryAudit[]>([]);
  const [enabled, setEnabled] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true); setError("");
    try {
      if (scope === "audit") {
        const { data } = await api.get<{ items: MemoryAudit[] }>("/personal-agent/memory/audit", { params: { limit: 100 } });
        setAudit(Array.isArray(data.items) ? data.items : []); setItems([]); return;
      }
      const { data } = await api.get<MemoryResponse>("/personal-agent/memory", { params: { scope, limit: 50 } });
      setItems(Array.isArray(data.items) ? data.items : []);
      if (typeof data.long_term_enabled === "boolean") setEnabled(data.long_term_enabled);
    } catch (failure) {
      setError(errorText(failure, "记忆服务暂不可用，请稍后重试"));
      setItems([]);
    } finally { setLoading(false); }
  };
  useEffect(() => { if (open) void load(); }, [open, scope]);

  const remove = async (id: string) => {
    try {
      await api.delete(`/personal-agent/memory/${encodeURIComponent(id)}`);
      setItems((current) => current.filter((item) => item.id !== id));
      message.success("记忆已删除");
    } catch (failure) { message.error(errorText(failure, "记忆删除失败")); }
  };
  const setMemoryEnabled = async (value: boolean) => {
    setSaving(true);
    try {
      await api.post("/personal-agent/memory/settings", { enabled: value });
      setEnabled(value);
      message.success(value ? "长期记忆已启用" : "长期记忆已停用");
    } catch (failure) { message.error(errorText(failure, "记忆设置保存失败")); }
    finally { setSaving(false); }
  };

  const auditAction: Record<string, string> = { created: "写入", deduplicated: "去重更新", conflict_resolved: "冲突替换", expired: "过期", revoked: "撤销" };
  return <Drawer
    open={open}
    onClose={onClose}
    title={<span><SettingOutlined /> 记忆管理</span>}
    width={560}
    rootClassName="memory-control-drawer"
    destroyOnHidden
    extra={<Tooltip title="刷新记忆"><Button type="text" icon={<ReloadOutlined />} aria-label="刷新记忆" loading={loading} onClick={() => void load()} /></Tooltip>}
  >
    <div className="memory-control">
      <Alert showIcon type="info" message="记忆只对当前登录账号可见，并在召回前按权限范围过滤。" description="短期记忆用于当前会话上下文；长期记忆可随时停用或删除。" />
      <div className="memory-control-toolbar">
        <Segmented value={scope} onChange={(value) => setScope(value as "short" | "long" | "audit")} options={[{ value: "short", label: "短期上下文" }, { value: "long", label: "长期记忆" }, { value: "audit", label: "记忆审计" }]} />
        {scope === "long" && <Space size={8}><span className="memory-control-setting-label">允许召回</span><Switch checked={enabled} loading={saving} onChange={(value) => void setMemoryEnabled(value)} /></Space>}
      </div>
      {error && <Alert type="warning" showIcon message="记忆服务未完成请求" description={error} />}
      {loading ? <Spin className="memory-control-loading" /> : scope === "audit" ? (audit.length ? <List className="memory-control-list" dataSource={audit} renderItem={(event) => <List.Item>
        <List.Item.Meta avatar={<HistoryOutlined />} title={`${auditAction[event.action] || event.action}｜${event.memory_category || "记忆"}`} description={<div className="memory-control-item-meta"><span>{event.content_snapshot || event.memory_id || ""}</span>{event.task_scope && <span>任务范围：{event.task_scope}</span>}{event.permission_scope && <span>权限：{event.permission_scope}</span>}<span>{event.occurred_at && new Date(event.occurred_at).toLocaleString("zh-CN")}</span></div>} />
      </List.Item>} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无记忆审计记录" />) : items.length ? <List
        className="memory-control-list"
        dataSource={items}
        renderItem={(item) => <List.Item actions={scope === "long" ? [<Popconfirm key="delete" title="删除这条长期记忆？" description="删除后不可用于后续召回。" okText="删除" cancelText="取消" onConfirm={() => void remove(item.id)}><Button danger type="text" icon={<DeleteOutlined />} aria-label="删除记忆">删除</Button></Popconfirm>] : undefined}>
          <List.Item.Meta avatar={item.memory_type === "long" ? <LockOutlined /> : <HistoryOutlined />} title={<div className="memory-control-item-title"><span>{item.content}</span>{item.memory_category && <Tag>{({ fact: "事实", preference: "偏好", experience: "经验", temporary_state: "临时状态" } as Record<string, string>)[item.memory_category] || item.memory_category}</Tag>}{item.permission_scope && <Tag>{item.permission_scope}</Tag>}</div>} description={<div className="memory-control-item-meta"><span>{item.source ? `来源：${item.source}` : "来源：当前会话"}</span>{item.task_scope && <span>任务范围：{item.task_scope}</span>}{item.confidence != null && <span>可信度：{Math.round(item.confidence * 100)}%</span>}{item.conversation_id && <span>会话：{item.conversation_id}</span>}{(item.compressed_at || item.created_at) && <span>压缩时间：{new Date(item.compressed_at || item.created_at || "").toLocaleString("zh-CN")}</span>}{item.covered_message_range || item.message_range ? <span>覆盖消息：{item.covered_message_range || item.message_range}</span> : item.covered_message_start != null || item.covered_message_end != null ? <span>覆盖消息：{item.covered_message_start ?? "?"}—{item.covered_message_end ?? "?"}</span> : item.covered_message_count != null || item.covered_messages != null ? <span>覆盖消息：{item.covered_message_count ?? item.covered_messages} 条</span> : null}{(item.summary_token_count != null || item.token_count != null) && <span>摘要 Token：{item.summary_token_count ?? item.token_count}{item.token_budget != null ? ` / ${item.token_budget}` : ""}</span>}{item.recall_score != null && <span>匹配度：{item.recall_score <= 1 ? `${Math.round(item.recall_score * 100)}%` : item.recall_score}</span>}</div>} />
        </List.Item>}
      /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={error ? "未能读取记忆" : scope === "short" ? "当前没有短期上下文" : "还没有长期记忆"} />}
    </div>
  </Drawer>;
}
