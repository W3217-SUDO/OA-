import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Input, Modal, Popconfirm, Select, Tag, Typography, message } from "antd";
import { CopyOutlined, LaptopOutlined } from "@ant-design/icons";
import { api } from "../api";
import Table from "../components/ResizableTable";

type AccessToken = {
  id: number; name: string; token_prefix: string; status: "active" | "expired" | "revoked";
  created_at: string; expires_at: string; last_used_at: string | null; call_count: number;
};
type CallLog = { id: number; token_id: number; tool_name: string; ok: boolean; detail: string; created_at: string };
type Listing = { items: AccessToken[]; calls: CallLog[]; mcp_endpoint: string; max_days: number; rate_limit_per_minute: number };

const STATUS: Record<AccessToken["status"], { text: string; color: string }> = {
  active: { text: "有效", color: "success" }, expired: { text: "已过期", color: "default" }, revoked: { text: "已撤销", color: "error" },
};
const when = (value: string | null) => (value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "—");

/** 管理员专属：生成只读访问令牌，让自己电脑上的本地 agent 通过 MCP 读取 OA。非管理员看不到入口。 */
export function LocalAgentAccess() {
  const [listing, setListing] = useState<Listing | null>(null);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [days, setDays] = useState(30);
  const [busy, setBusy] = useState(false);
  const [fresh, setFresh] = useState("");

  const load = useCallback(async () => {
    try {
      const { data } = await api.get<Listing>("/agent-tools/access-tokens");
      setListing(Array.isArray(data?.items) ? data : null);
    } catch {
      setListing(null); // 403：不是系统管理员，不显示入口
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  if (!listing) return null;

  const endpoint = (typeof window === "undefined" ? "" : window.location.origin) + listing.mcp_endpoint;
  const command = `claude mcp add --transport http oa ${endpoint} --header "Authorization: Bearer ${fresh || "<令牌>"}"`;
  const json = JSON.stringify({ mcpServers: { oa: { type: "http", url: endpoint, headers: { Authorization: `Bearer ${fresh || "<令牌>"}` } } } }, null, 2);
  const copy = (text: string) => navigator.clipboard.writeText(text).then(() => message.success("已复制"), () => message.error("复制失败，请手动选择复制"));

  const create = async () => {
    setBusy(true);
    try {
      const { data } = await api.post<{ token: string }>("/agent-tools/access-tokens", { name, days });
      setFresh(data.token);
      setName("");
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "生成失败");
    } finally {
      setBusy(false);
    }
  };
  const revoke = async (id: number) => {
    try {
      await api.delete(`/agent-tools/access-tokens/${id}`);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "撤销失败");
    }
  };

  return <>
    <Button type="text" icon={<LaptopOutlined />} onClick={() => setOpen(true)}>电脑连接 OA</Button>
    <Modal title="让我电脑上的 agent 连接 OA（只读）" open={open} width={860} footer={null} onCancel={() => { setOpen(false); setFresh(""); }} destroyOnHidden>
      <Alert type="warning" showIcon style={{ marginBottom: 12 }}
        title="令牌只能读取、不能修改；权限和你的账号一致。OA 数据会进入你电脑上的 agent（及其所用的模型），请确认符合律所保密要求。令牌等同密码，不要发给他人或写进共享文件，不用时请撤销。" />
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <Input value={name} maxLength={100} placeholder="令牌名称，例如：我的笔记本" onChange={(event) => setName(event.target.value)} />
        <Select value={days} onChange={setDays} style={{ width: 140 }}
          options={[7, 30, 90].filter((value) => value <= listing.max_days).map((value) => ({ value, label: `有效 ${value} 天` }))} />
        <Button type="primary" loading={busy} disabled={!name.trim()} onClick={() => void create()}>生成令牌</Button>
      </div>
      {fresh && <Alert type="success" showIcon style={{ marginBottom: 12 }} title="令牌已生成，只显示这一次，关闭后无法再查看" description={<div>
        <Typography.Paragraph code copyable={{ text: fresh }} style={{ wordBreak: "break-all" }}>{fresh}</Typography.Paragraph>
        <div>Claude Code：<Button size="small" icon={<CopyOutlined />} onClick={() => void copy(command)}>复制命令</Button>　
          Claude Desktop / Cursor 等（写入 MCP 配置）：<Button size="small" icon={<CopyOutlined />} onClick={() => void copy(json)}>复制配置</Button></div>
      </div>} />}
      <Table<AccessToken>
        size="small" rowKey="id" pagination={false} dataSource={listing.items} locale={{ emptyText: "还没有令牌" }}
        columns={[
          { title: "名称", dataIndex: "name" },
          { title: "令牌前缀", dataIndex: "token_prefix" },
          { title: "状态", dataIndex: "status", render: (value: AccessToken["status"]) => <Tag color={STATUS[value].color}>{STATUS[value].text}</Tag> },
          { title: "到期时间", dataIndex: "expires_at", render: when },
          { title: "最近使用", dataIndex: "last_used_at", render: when },
          { title: "调用次数", dataIndex: "call_count" },
          { title: "操作", key: "action", render: (_: unknown, row: AccessToken) => row.status === "active"
            ? <Popconfirm title="撤销后该令牌立即失效，确定吗？" onConfirm={() => void revoke(row.id)}><Button size="small" danger>撤销</Button></Popconfirm> : "—" },
        ]}
      />
      <h4 style={{ margin: "16px 0 8px" }}>最近调用记录（每分钟最多 {listing.rate_limit_per_minute} 次）</h4>
      <Table<CallLog>
        size="small" rowKey="id" pagination={{ pageSize: 8 }} dataSource={listing.calls} locale={{ emptyText: "暂无调用" }}
        columns={[
          { title: "时间", dataIndex: "created_at", render: when },
          { title: "工具", dataIndex: "tool_name" },
          { title: "结果", dataIndex: "ok", render: (value: boolean) => <Tag color={value ? "success" : "error"}>{value ? "成功" : "失败"}</Tag> },
          { title: "参数", dataIndex: "detail", ellipsis: true },
        ]}
      />
    </Modal>
  </>;
}
