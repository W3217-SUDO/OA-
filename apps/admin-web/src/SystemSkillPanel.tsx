import { POPUP_WIDTH } from "./components/common/popupSize";
import { useEffect, useRef, useState } from "react";
import { Alert, Button, Descriptions, Drawer, Modal, Space, Spin, Tag, Tooltip, message } from "antd";
import { DeleteOutlined, EyeOutlined, ReloadOutlined } from "@ant-design/icons";
import { api } from "./api";
import type { AgentSkill } from "./agentSkillRouting";
import Table from "./components/ResizableTable";
import { errorText } from "./personal-agent/types";
import { SystemSkillResources, type SystemSkillResource } from "./SystemSkillResources";
import "./system-skill-panel.css";

type Definition = AgentSkill & {
  id: string; name: string; scope: "system"; filename: string; content: string;
  instruction: string; quick_prompts: string[]; definition_sha256: string;
  revision: number; can_delete: boolean; content_origin: "runtime_declaration" | "upstream_package";
  upstream?: { source: string; commit: string; content: string; sha256: string; excluded_resources: string[] } | null;
  resources: SystemSkillResource[];
};

export function SystemSkillPanel({ items, loading, canManage, onChanged }: {
  items: AgentSkill[]; loading: boolean; canManage: boolean; onChanged: () => Promise<void>;
}) {
  const [selected, setSelected] = useState<AgentSkill | null>(null);
  const [detail, setDetail] = useState<Definition | null>(null);
  const [confirmation, setConfirmation] = useState<Definition | null>(null);
  const [reading, setReading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");
  const [refreshNeeded, setRefreshNeeded] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const request = useRef<AbortController | null>(null);
  const mutation = useRef(false);
  const permission = useRef(canManage);
  permission.current = canManage;

  useEffect(() => () => { request.current?.abort(); }, []);
  useEffect(() => { if (!canManage) setConfirmation(null); }, [canManage]);

  const close = () => {
    if (mutation.current) return;
    request.current?.abort();
    setSelected(null); setDetail(null); setConfirmation(null); setReading(false);
  };
  const readDefinition = async (item: AgentSkill, forDeletion = false) => {
    if (mutation.current || (forDeletion && !permission.current)) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setSelected(item); setDetail(null); setConfirmation(null); setReading(true); setError("");
    try {
      const { data } = await api.get<Definition>(`/agent/system-skills/${encodeURIComponent(item.id)}/definition`, { signal: controller.signal });
      if (controller.signal.aborted) return;
      if (data.id !== item.id || data.scope !== "system" || !["runtime_declaration", "upstream_package"].includes(data.content_origin)
        || !Number.isInteger(data.revision) || data.revision < 0 || !/^[a-f0-9]{64}$/.test(data.definition_sha256)
        || typeof data.content !== "string" || typeof data.instruction !== "string" || !Array.isArray(data.quick_prompts)
        || !Array.isArray(data.resources) || (data.content_origin === "upstream_package" && (!data.upstream
          || typeof data.upstream.content !== "string" || !/^[a-f0-9]{40}$/.test(data.upstream.commit)))) {
        throw new Error("系统技能详情响应无效，请刷新后重试");
      }
      setDetail(data);
      if (forDeletion) {
        if (!permission.current || data.can_delete !== true) throw new Error("当前账号无权删除该系统技能");
        setConfirmation(data);
      }
    } catch (failure) {
      if (!controller.signal.aborted) setError(errorText(failure, "系统技能详情加载失败"));
    } finally {
      if (!controller.signal.aborted) setReading(false);
    }
  };
  const refresh = async () => {
    setRefreshing(true);
    try { await onChanged(); setRefreshNeeded(false); setError(""); }
    catch (failure) { setRefreshNeeded(true); setError(`系统技能已删除，但目录刷新失败：${errorText(failure, "请重试刷新")}`); }
    finally { setRefreshing(false); }
  };
  const remove = async () => {
    if (!confirmation || !permission.current || mutation.current) return;
    const snapshot = confirmation;
    mutation.current = true; setDeleting(true); setError("");
    try {
      const { data } = await api.delete<{ id: string; scope: string; deleted: boolean; deletion_mode: string; revision: number }>(
        `/agent/system-skills/${encodeURIComponent(snapshot.id)}`,
        { data: { confirm: true, revision: snapshot.revision, definition_sha256: snapshot.definition_sha256 } },
      );
      if (data.id !== snapshot.id || data.scope !== "system" || data.deleted !== true
        || data.deletion_mode !== "registry_deactivation" || !Number.isInteger(data.revision) || data.revision <= snapshot.revision) {
        throw new Error("删除结果无法确认，请刷新目录核对，勿重复删除");
      }
      setConfirmation(null); setSelected(null); setDetail(null);
      message.success("系统技能已删除（注销注册），历史对话保留");
      await refresh();
    } catch (failure) {
      setConfirmation(null); setDetail(null);
      setError(errorText(failure, "系统技能删除失败，请重新查看详情后确认"));
    } finally { mutation.current = false; setDeleting(false); }
  };

  const columns = [
    { title: "名称", dataIndex: "name", width: 150 },
    { title: "分类", dataIndex: "category", width: 90 },
    { title: "说明", dataIndex: "description" },
    { title: "来源", dataIndex: "source", width: 260, ellipsis: true },
    { title: "状态", width: 200, render: (_: unknown, item: AgentSkill) => item.available
      ? <Tag color="success">可用</Tag> : <Tag color="warning">{item.unavailable_reason || "不可用"}</Tag> },
    { title: "操作", width: 112, render: (_: unknown, item: AgentSkill) => <Space size={4}>
      <Tooltip title="查看系统技能详情"><Button aria-label={`查看${item.name}`} icon={<EyeOutlined />} disabled={deleting} onClick={() => void readDefinition(item)} /></Tooltip>
      {canManage && <Tooltip title="删除系统技能"><Button danger aria-label={`删除${item.name}`} icon={<DeleteOutlined />} disabled={deleting || refreshNeeded} onClick={() => void readDefinition(item, true)} /></Tooltip>}
    </Space> },
  ];
  return <div className="system-skill-panel">
    {error && <Alert type="error" showIcon title={error} action={refreshNeeded
      ? <Button icon={<ReloadOutlined />} loading={refreshing} onClick={() => void refresh()}>刷新目录</Button> : undefined} />}
    <Table rowKey="id" size="small" loading={loading} columns={columns} dataSource={items} pagination={false} scroll={{ x: 1012 }} />
    <Drawer title={selected ? `${selected.name} · 系统技能详情` : "系统技能详情"} open={!!selected} onClose={close} size={POPUP_WIDTH.lg} closable={!deleting} maskClosable={!deleting} keyboard={!deleting}>
      <div className="system-skill-detail">
        {reading && <Spin />}
        {error && <Alert type="error" showIcon title={error} />}
        {!reading && !detail && selected && <Button icon={<ReloadOutlined />} onClick={() => void readDefinition(selected)}>重新读取详情</Button>}
        {detail && <>
          <Descriptions size="small" bordered column={1}>
            <Descriptions.Item label="名称">{detail.name}</Descriptions.Item>
            <Descriptions.Item label="分类">{detail.category}</Descriptions.Item>
            <Descriptions.Item label="说明">{detail.description}</Descriptions.Item>
            <Descriptions.Item label="来源">{detail.source}</Descriptions.Item>
            <Descriptions.Item label="状态">{detail.available ? "可用" : detail.unavailable_reason || "不可用"}</Descriptions.Item>
            <Descriptions.Item label="内容范围">{detail.upstream ? "上游 SKILL.md 全文及配套文本，选中后加载原文" : "OA 内置指令"}</Descriptions.Item>
            {detail.upstream && <Descriptions.Item label="原文来源"><a href={detail.upstream.source} target="_blank" rel="noopener noreferrer">{detail.upstream.source}</a></Descriptions.Item>}
            {detail.upstream && <Descriptions.Item label="上游提交">{detail.upstream.commit}</Descriptions.Item>}
            <Descriptions.Item label="版本">{detail.revision}</Descriptions.Item>
            <Descriptions.Item label="内容摘要">{detail.definition_sha256}</Descriptions.Item>
          </Descriptions>
          {detail.upstream ? <>
            <h3>SKILL.md 原文全文</h3><pre>{detail.upstream.content}</pre>
            <SystemSkillResources key={detail.id} skillId={detail.id} items={detail.resources} />
            {!!detail.upstream.excluded_resources.length && <details><summary>未接入执行的脚本及其他资源（{detail.upstream.excluded_resources.length}）</summary><ul>{detail.upstream.excluded_resources.map(path => <li key={path}>{path}</li>)}</ul></details>}
            <details><summary>实际发送给 AI 的完整技能指令（含 OA 权限边界）</summary><pre>{detail.instruction}</pre></details>
          </> : <><h3>完整技能指令</h3><pre>{detail.instruction}</pre></>}
          <h3>快捷提示</h3>{detail.quick_prompts.length ? <ul>{detail.quick_prompts.map((prompt, index) => <li key={index}>{prompt}</li>)}</ul> : <p>无快捷提示</p>}
          <details><summary>{detail.filename}</summary><pre>{detail.content}</pre></details>
        </>}
      </div>
    </Drawer>
    <Modal title={`删除系统技能“${confirmation?.name || ""}”？`} open={!!confirmation} onOk={() => void remove()} onCancel={() => { if (!mutation.current) setConfirmation(null); }}
      okText="确认删除" cancelText="取消" okButtonProps={{ danger: true, disabled: !canManage }} confirmLoading={deleting} cancelButtonProps={{ disabled: deleting }} closable={!deleting} maskClosable={!deleting} keyboard={!deleting}>
      <div className="system-skill-detail">
        <p>将注销该系统技能，所有账号都无法再选用。不会删除源码或历史对话；清空技能后仍可进行普通对话。</p>
        <p>注册版本：{confirmation?.revision}</p><p>内容摘要：{confirmation?.definition_sha256}</p>
      </div>
    </Modal>
  </div>;
}
