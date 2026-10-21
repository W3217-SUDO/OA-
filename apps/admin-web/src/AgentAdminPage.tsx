import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Drawer, Empty, Modal, Space, Switch, Tabs, Tag, message } from "antd";
import { AppstoreOutlined, DeleteOutlined, EyeOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { api } from "./api";
import Table from "./components/ResizableTable";
import { SkillManager } from "./personal-agent/SkillManager";
import { errorText, type WorkspaceSkill } from "./personal-agent/types";
import { CapabilityMarket } from "./capability-market/CapabilityMarket";
import { GlobalMcpWorkspace } from "./capability-market/GlobalMcpWorkspace";
import { DshPluginCenter } from "./capability-market/DshPluginCenter";
import { SystemSkillPanel } from "./SystemSkillPanel";
import { SkillRuntimeStatus } from "./personal-agent/SkillRuntimeStatus";
import type { AgentSkill } from "./agentSkillRouting";
import { refreshAgentSkillCatalogConsumers } from "./agentSkillCatalog";
import "./agent-admin-workspace.css";

type Runtime = {
  ready: boolean;
  model: string;
  model_provider: string;
  model_configured: boolean;
  checkpoint_backend: string;
  max_concurrency: number;
  write_requires_approval: boolean;
  error?: string;
};
type UserSkill = {
  id: string; name: string; category: string; description?: string; source?: string;
  instruction?: string; quick_prompts?: string[]; enabled: boolean;
};
type UserLibrary = {
  username: string;
  display_name: string;
  skills: UserSkill[];
};
type Overview = {
  runtime: Runtime;
  system_skills: AgentSkill[];
  user_libraries: UserLibrary[];
  can_manage_global: boolean;
  can_view_user_libraries: boolean;
};

const libraryColumns = (onView: (item: UserLibrary) => void) => [
  { title: "账号", dataIndex: "username", width: 160 },
  { title: "姓名", dataIndex: "display_name", width: 140 },
  { title: "技能数", width: 90, render: (_: unknown, item: UserLibrary) => item.skills.length },
  {
    title: "个人技能",
    render: (_: unknown, item: UserLibrary) => (
      <Space wrap size={[4, 4]}>
        {item.skills.map((skill) => <Tag key={skill.id} color={skill.enabled ? "blue" : undefined}>{skill.name}</Tag>)}
      </Space>
    ),
  },
  { title: "操作", width: 110, render: (_: unknown, item: UserLibrary) => <Button type="link" onClick={() => onView(item)}>查看详情</Button> },
];

type SkillDefinition = { name: string; content: string; definition_sha256: string; import_sha256?: string };

// 全局管理可单独委派，其他员工个人技能库仍仅向真实管理员开放。
export default function AgentAdminPage({ isSystemAdmin }: { isSystemAdmin: boolean }) {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("global");
  const [globalSkills, setGlobalSkills] = useState<WorkspaceSkill[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [skillsOpen, setSkillsOpen] = useState(false);
  const [capabilityBusy, setCapabilityBusy] = useState(false);
  const [error, setError] = useState("");
  const [skillOwner, setSkillOwner] = useState<UserLibrary | null>(null);
  const [skillDetails, setSkillDetails] = useState<UserSkill[]>([]);
  const [skillLoading, setSkillLoading] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<WorkspaceSkill | null>(null);
  const [skillDefinition, setSkillDefinition] = useState<SkillDefinition | null>(null);
  const [definitionLoading, setDefinitionLoading] = useState(false);
  const [definitionError, setDefinitionError] = useState("");
  const [updatingSkill, setUpdatingSkill] = useState("");
  const refreshGlobals = useCallback(async () => {
    const { data } = await api.get<{ items: WorkspaceSkill[]; can_manage: boolean }>("/agent/global-skills");
    setGlobalSkills(data.items); setCanManage(data.can_manage);
  }, []);
  const refreshGlobalConsumers = async () => {
    const results = await Promise.allSettled([refreshGlobals(), refreshAgentSkillCatalogConsumers()]);
    const failure = results.find(result => result.status === "rejected");
    if (failure?.status === "rejected") throw failure.reason;
  };

  const load = useCallback(async () => {
    setLoading(true);
    setSkillOwner(null); setSkillDetails([]);
    setError(""); setCanManage(false);
    try {
      const [summary, skills] = await Promise.allSettled([api.get<Overview>("/agent-admin/overview"), refreshGlobals()]);
      if (summary.status === "fulfilled") setOverview(summary.value.data);
      else if ((summary.reason as { response?: { status?: number } })?.response?.status === 403) setOverview(null);
      else throw summary.reason;
      if (skills.status === "rejected") throw skills.reason;
    } catch (failure) {
      setError(errorText(failure, "智能体设置加载失败"));
    } finally {
      setLoading(false);
    }
  }, [refreshGlobals]);

  useEffect(() => { void load(); }, [load]);

  const refreshSystemSkills = useCallback(async () => {
    const results = await Promise.allSettled([
      api.get<Overview>("/agent-admin/overview").then(({ data }) => { setOverview(data); }),
      refreshAgentSkillCatalogConsumers(),
    ]);
    const failure = results.find(result => result.status === "rejected");
    if (failure?.status === "rejected") throw failure.reason;
  }, []);

  const runtime = overview?.runtime;
  const canViewUserLibraries = isSystemAdmin && overview?.can_view_user_libraries === true;
  const openUserSkills = async (owner: UserLibrary) => {
    if (!canViewUserLibraries) return;
    setSkillOwner(owner); setSkillDetails([]); setSkillLoading(true);
    try { const { data } = await api.get<{ items: UserSkill[] }>(`/agent-admin/skills/users/${encodeURIComponent(owner.username)}`); setSkillDetails(data.items || []); }
    catch (failure) { message.error(errorText(failure, "个人技能详情加载失败")); }
    finally { setSkillLoading(false); }
  };
  const deleteUserSkill = (skill: UserSkill) => Modal.confirm({ title: `删除“${skill.name}”？`, content: `将从账号 ${skillOwner?.username || ""} 的个人技能库中删除，删除后不可恢复。`, okText: "确认删除", cancelText: "取消", okButtonProps: { danger: true }, onOk: async () => {
    if (!canViewUserLibraries || !skillOwner) return;
    try { await api.delete(`/agent-admin/skills/users/${encodeURIComponent(skillOwner.username)}/${encodeURIComponent(skill.id)}`); message.success("个人技能已删除"); await openUserSkills(skillOwner); await load(); }
    catch (failure) { message.error(errorText(failure, "个人技能删除失败")); throw failure; }
  } });
  const deleteGlobalSkill = (skill: WorkspaceSkill) => Modal.confirm({ title: `删除全局技能“${skill.name}”？`, content: "删除后所有账号都无法再选用该技能，已有对话记录保留。", okText: "确认删除", cancelText: "取消", okButtonProps: { danger: true }, onOk: async () => {
    if (!canManage) return;
    try { await api.delete(`/agent/global-skills/${encodeURIComponent(skill.id)}`); message.success("全局技能已删除"); await refreshGlobalConsumers(); }
    catch (failure) { message.error(errorText(failure, "全局技能删除失败")); throw failure; }
  } });
  const toggleGlobalSkill = async (skill: WorkspaceSkill, enabled: boolean) => {
    if (!canManage || updatingSkill) return;
    setUpdatingSkill(skill.id);
    try {
      await api.patch(`/agent/global-skills/${encodeURIComponent(skill.id)}`, { enabled });
      await refreshGlobalConsumers();
      message.success(enabled ? "全局技能已启用" : "全局技能已停用");
    } catch (failure) { message.error(errorText(failure, "全局技能更新失败，请刷新确认实际状态")); throw failure; }
    finally { setUpdatingSkill(""); }
  };
  const confirmToggleGlobalSkill = (skill: WorkspaceSkill, enabled: boolean) => {
    if (!canManage || updatingSkill) return;
    Modal.confirm({
      title: `${enabled ? "启用" : "停用"}全局技能“${skill.name}”？`,
      content: enabled ? "启用后，全所账号可在授权范围内使用该技能。" : "停用后，全所账号将无法选用该技能；已有对话记录保留。",
      okText: `确认${enabled ? "启用" : "停用"}`, cancelText: "取消",
      onOk: () => toggleGlobalSkill(skill, enabled),
    });
  };
  const openSkillDefinition = async (skill: WorkspaceSkill) => {
    setSelectedSkill(skill); setSkillDefinition(null); setDefinitionError(""); setDefinitionLoading(true);
    try {
      const { data } = await api.get<SkillDefinition>(`/agent/global-skills/${encodeURIComponent(skill.id)}/definition`);
      setSkillDefinition(data);
    } catch (failure) { setDefinitionError(errorText(failure, "技能详情加载失败")); }
    finally { setDefinitionLoading(false); }
  };
  return (
    <div className="agent-scope-admin" data-testid="agent-admin-page">
      <Tabs activeKey={tab} onChange={key => { if (!capabilityBusy) setTab(key); }} items={[
        { key: "plugins", label: "DSH 插件中心", disabled: capabilityBusy },
        { key: "global", label: "全局 Skill", disabled: capabilityBusy },
        { key: "mcp", label: "全局 MCP", disabled: capabilityBusy },
        { key: "market", label: "能力市场", disabled: capabilityBusy },
        ...(overview ? [{ key: "overview", label: canViewUserLibraries ? "运行状态与个人库" : "运行状态", disabled: capabilityBusy }] : []),
      ]} />
      {error && <Alert type="error" showIcon title="智能体设置加载未完成" description={error} action={<Button loading={loading} onClick={() => void load()}>重试</Button>} />}
      {tab === "plugins" && <DshPluginCenter active canManage={isSystemAdmin} onBusy={setCapabilityBusy} />}
      <div hidden={tab !== "global"}>
        <Card title="全局 Skill" loading={loading && !globalSkills.length} extra={<Space wrap>
          <Button loading={loading} icon={<ReloadOutlined />} onClick={() => void load()}>刷新</Button>
          {canManage && <Button icon={<PlusOutlined />} onClick={() => setSkillsOpen(true)}>新增或导入</Button>}
          {canManage && <Button type="primary" icon={<AppstoreOutlined />} onClick={() => setTab("market")}>去市场</Button>}
        </Space>}>
          <p className="agent-admin-note">这里仅列出已安装的全局技能。启用后，全所账号可在授权范围内使用；个人技能仍属于各自账号。</p>
          {!canManage && !loading && !error && <Alert type="info" title="当前账号仅可查看全局技能。" />}
          {!loading && !error && !globalSkills.length && <Empty description="尚未安装全局技能" />}
          <div className="agent-admin-skill-list">{globalSkills.map(skill => <article key={skill.id}>
            <div className="agent-admin-skill-main"><strong>{skill.name}</strong><Tag color={skill.enabled === true ? "success" : "default"}>{skill.enabled === true ? "已启用" : "已停用"}</Tag><span>{skill.category}</span>
              <p>{skill.description}</p><SkillRuntimeStatus runtime={skill.skill_runtime} enabled={skill.enabled} details /><small>来源：{skill.source || "系统创建"}</small></div>
            <div className="agent-admin-skill-actions">
              <Button icon={<EyeOutlined />} onClick={() => void openSkillDefinition(skill)}>详情</Button>
              {canManage && <><Switch aria-label={`${skill.name}启用状态`} checked={skill.enabled === true} loading={updatingSkill === skill.id} disabled={!!updatingSkill} onChange={enabled => confirmToggleGlobalSkill(skill, enabled)} />
                <Button danger icon={<DeleteOutlined />} onClick={() => deleteGlobalSkill(skill)}>删除</Button></>}
            </div>
          </article>)}</div>
        </Card>
      </div>
      <div hidden={tab !== "mcp"}><GlobalMcpWorkspace active={tab === "mcp"} canManage={canManage} /></div>
      <div hidden={tab !== "market"}><CapabilityMarket active={tab === "market"} scope="global" managementView canManage={canManage} installedSkills={globalSkills} onManageInstalled={() => setTab("global")} onInstalled={refreshGlobals} onBusy={setCapabilityBusy} /></div>
      <Space hidden={tab !== "overview"} orientation="vertical" size={12} style={{ width: "100%" }}>
      <Card
        title="运行状态"
        loading={loading && !overview}
        extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>刷新</Button>}
      >
        {runtime && (
          <>
            {runtime.error && <Alert type="error" showIcon title={runtime.error} style={{ marginBottom: 12 }} />}
            <Descriptions size="small" column={{ xs: 1, md: 3 }} bordered>
              <Descriptions.Item label="服务状态">
                <Tag color={runtime.ready ? "success" : "error"}>{runtime.ready ? "服务已连接" : "模型未就绪"}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="模型服务商">{runtime.model_provider || "未配置"}</Descriptions.Item>
              <Descriptions.Item label="模型">{runtime.model || "未配置"}</Descriptions.Item>
              <Descriptions.Item label="检查点存储">{runtime.checkpoint_backend}</Descriptions.Item>
              <Descriptions.Item label="最大并发">{runtime.max_concurrency}</Descriptions.Item>
              <Descriptions.Item label="写入系统前确认">{runtime.write_requires_approval ? "需要用户确认" : "无需确认"}</Descriptions.Item>
            </Descriptions>
          </>
        )}
      </Card>
      <Card title="系统技能">
        <SystemSkillPanel items={overview?.system_skills || []} loading={loading} canManage={overview?.can_manage_global === true} onChanged={refreshSystemSkills} />
      </Card>
      {canViewUserLibraries && <Card title="个人技能库（按账号）" extra={<span>共 {overview?.user_libraries.length || 0} 个有效账号</span>}>
        <Table
          rowKey="username"
          size="small"
          loading={loading}
          columns={libraryColumns(openUserSkills)}
          dataSource={overview?.user_libraries || []}
          pagination={false}
          locale={{ emptyText: "还没有账号创建个人技能" }}
        />
      </Card>}
      </Space>
      {canViewUserLibraries && <Drawer title={skillOwner ? `${skillOwner.display_name || skillOwner.username} 的个人技能详情` : "个人技能详情"} open={!!skillOwner} onClose={() => setSkillOwner(null)} width="min(760px, 100vw)">
        <Table rowKey="id" loading={skillLoading} dataSource={skillDetails} pagination={false} locale={{ emptyText: "该账号没有个人技能" }} expandable={{ expandedRowRender: (skill: UserSkill) => <Descriptions size="small" column={1} bordered><Descriptions.Item label="完整技能指令"><pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{skill.instruction || "—"}</pre></Descriptions.Item><Descriptions.Item label="快捷指令">{skill.quick_prompts?.join("、") || "—"}</Descriptions.Item></Descriptions> }} columns={[{ title: "名称", dataIndex: "name", width: 150 }, { title: "分类", dataIndex: "category", width: 90 }, { title: "说明", dataIndex: "description" }, { title: "状态", width: 80, render: (_: unknown, skill: UserSkill) => <Tag color={skill.enabled ? "success" : "default"}>{skill.enabled ? "启用" : "停用"}</Tag> }, { title: "操作", width: 80, render: (_: unknown, skill: UserSkill) => <Button danger type="link" onClick={() => deleteUserSkill(skill)}>删除</Button> }]} />
      </Drawer>}
      {canManage && <SkillManager open={skillsOpen} onClose={() => setSkillsOpen(false)} scope="global" skills={globalSkills} refresh={refreshGlobalConsumers} />}
      <Drawer title={selectedSkill?.name || "全局技能详情"} open={!!selectedSkill} onClose={() => setSelectedSkill(null)} width={680} rootClassName="agent-admin-definition">
        {definitionLoading && <p>正在加载技能原文…</p>}
        {definitionError && <Alert type="error" showIcon title={definitionError} action={<Button onClick={() => selectedSkill && void openSkillDefinition(selectedSkill)}>重试</Button>} />}
        {skillDefinition && <><p>当前保存的技能定义，摘要：{skillDefinition.definition_sha256}</p><pre tabIndex={0}>{skillDefinition.content}</pre></>}
      </Drawer>
    </div>
  );
}
