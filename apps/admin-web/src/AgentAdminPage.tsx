import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Drawer as AntDrawer, Empty, Modal as AntModal, Space, Tabs, Tag, message } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { api } from "./api";
import Table from "./components/ResizableTable";
import { SkillManager } from "./personal-agent/SkillManager";
import { errorText, type WorkspaceSkill } from "./personal-agent/types";
import { CapabilityMarket } from "./capability-market/CapabilityMarket";

// 允许结构测试使用最小 antd mock，同时生产环境仍使用真实抽屉和确认弹窗。
const Drawer = AntDrawer || ((props: any) => props.open ? <div>{props.children}</div> : null);
const Modal = AntModal || { confirm: () => undefined };

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
type SystemSkill = {
  id: string;
  name: string;
  category: string;
  description: string;
  source: string;
  available: boolean;
  unavailable_reason: string;
  quick_prompts: string[];
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
type Overview = { runtime: Runtime; system_skills: SystemSkill[]; user_libraries: UserLibrary[] };

const skillColumns = [
  { title: "名称", dataIndex: "name", width: 150 },
  { title: "分类", dataIndex: "category", width: 90 },
  { title: "说明", dataIndex: "description" },
  { title: "来源", dataIndex: "source", width: 260, ellipsis: true },
  {
    title: "状态",
    width: 200,
    render: (_: unknown, item: SystemSkill) => item.available
      ? <Tag color="success">可用</Tag>
      : <Tag color="warning">{item.unavailable_reason || "不可用"}</Tag>,
  },
];

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

// 管理员查看智能体运行状态、系统技能目录和各账号保存的个人技能。
export default function AgentAdminPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("capabilities");
  const [globalSkills, setGlobalSkills] = useState<WorkspaceSkill[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [skillsOpen, setSkillsOpen] = useState(false);
  const [capabilityBusy, setCapabilityBusy] = useState(false);
  const [error, setError] = useState("");
  const [skillOwner, setSkillOwner] = useState<UserLibrary | null>(null);
  const [skillDetails, setSkillDetails] = useState<UserSkill[]>([]);
  const [skillLoading, setSkillLoading] = useState(false);
  const refreshGlobals = useCallback(async () => {
    const { data } = await api.get<{ items: WorkspaceSkill[]; can_manage: boolean }>("/agent/global-skills");
    setGlobalSkills(data.items); setCanManage(data.can_manage);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(""); setCanManage(false);
    try {
      const { data } = await api.get<Overview>("/agent-admin/overview");
      setOverview(data);
      await refreshGlobals();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "智能体设置加载失败");
      setError(errorText(error, "智能体设置加载失败"));
    } finally {
      setLoading(false);
    }
  }, [refreshGlobals]);

  useEffect(() => { void load(); }, [load]);

  const runtime = overview?.runtime;
  const openUserSkills = async (owner: UserLibrary) => {
    setSkillOwner(owner); setSkillDetails([]); setSkillLoading(true);
    try { const { data } = await api.get<{ items: UserSkill[] }>(`/agent-admin/skills/users/${encodeURIComponent(owner.username)}`); setSkillDetails(data.items || []); }
    catch (failure) { message.error(errorText(failure, "个人技能详情加载失败")); }
    finally { setSkillLoading(false); }
  };
  const deleteUserSkill = (skill: UserSkill) => Modal.confirm({ title: `删除“${skill.name}”？`, content: `将从账号 ${skillOwner?.username || ""} 的个人技能库中删除，删除后不可恢复。`, okText: "确认删除", cancelText: "取消", okButtonProps: { danger: true }, onOk: async () => {
    if (!skillOwner) return;
    try { await api.delete(`/agent-admin/skills/users/${encodeURIComponent(skillOwner.username)}/${encodeURIComponent(skill.id)}`); message.success("个人技能已删除"); await openUserSkills(skillOwner); await load(); }
    catch (failure) { message.error(errorText(failure, "个人技能删除失败")); throw failure; }
  } });
  return (
    <div className="agent-scope-admin" data-testid="agent-admin-page">
      <Tabs activeKey={tab} onChange={key => { if (!capabilityBusy) setTab(key); }} items={[{ key: "capabilities", label: "专家、技能、连接器", disabled: capabilityBusy }, { key: "global", label: "全局技能", disabled: capabilityBusy }, { key: "overview", label: "运行状态与个人库", disabled: capabilityBusy }]} />
      <div hidden={tab !== "capabilities"}><CapabilityMarket active={tab === "capabilities"} scope="global" onInstalled={refreshGlobals} onBusy={setCapabilityBusy} /></div>
      {error && <Alert type="error" showIcon title="智能体设置加载未完成" description={error} action={<Button loading={loading} onClick={() => void load()}>重试</Button>} />}
      <div hidden={tab !== "global"}>
        <Card title="全局技能" loading={loading && !overview} extra={<Button loading={loading} icon={<ReloadOutlined />} onClick={() => void load()}>刷新</Button>}>
          <p>启用的全局技能可供全所账号选用；个人技能仍只属于原账号，不会迁移到全局。系统内置技能保持只读。</p>
          {overview && canManage && <Button type="primary" disabled={loading} onClick={() => setSkillsOpen(true)}>管理全局技能 · 从市场安装</Button>}
          {!canManage && !loading && !error && <Alert type="info" title="当前账号仅可查看和选用已启用的全局技能，不能修改。" />}
          {!loading && !error && !globalSkills.length && <Empty description="尚未安装全局技能" />}
          <div className="agent-global-skill-cards">{globalSkills.map(skill => <article key={skill.id}><div><strong>{skill.name}</strong><Tag color={skill.available ? "success" : "default"}>{skill.available ? "已启用" : "已停用"}</Tag></div><p>{skill.description}</p><small>全局 · {skill.category}</small></article>)}</div>
        </Card>
      </div>
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
        <Table
          rowKey="id"
          size="small"
          loading={loading}
          columns={skillColumns}
          dataSource={overview?.system_skills || []}
          pagination={false}
          scroll={{ x: 900 }}
        />
      </Card>
      <Card title="技能管理入口" className="agent-skill-management-entry">
        <Space wrap>
          <Button type="primary" onClick={() => setTab("global")}>管理全局技能</Button>
          {canManage && <Button onClick={() => setSkillsOpen(true)}>安装全局技能</Button>}
          <span>可按账号查看个人技能，并对全局技能执行安装、启用、停用和卸载。</span>
        </Space>
      </Card>
      <Card title="个人技能库（按账号）" extra={<span>共 {overview?.user_libraries.length || 0} 个有效账号</span>}>
        <Table
          rowKey="username"
          size="small"
          loading={loading}
          columns={libraryColumns(openUserSkills)}
          dataSource={overview?.user_libraries || []}
          pagination={false}
          locale={{ emptyText: "还没有账号创建个人技能" }}
        />
      </Card>
      </Space>
      <Drawer title={skillOwner ? `${skillOwner.display_name || skillOwner.username} 的个人技能详情` : "个人技能详情"} open={!!skillOwner} onClose={() => setSkillOwner(null)} width="min(760px, 100vw)">
        <Table rowKey="id" loading={skillLoading} dataSource={skillDetails} pagination={false} locale={{ emptyText: "该账号没有个人技能" }} expandable={{ expandedRowRender: (skill: UserSkill) => <Descriptions size="small" column={1} bordered><Descriptions.Item label="完整技能指令"><pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{skill.instruction || "—"}</pre></Descriptions.Item><Descriptions.Item label="快捷指令">{skill.quick_prompts?.join("、") || "—"}</Descriptions.Item></Descriptions> }} columns={[{ title: "名称", dataIndex: "name", width: 150 }, { title: "分类", dataIndex: "category", width: 90 }, { title: "说明", dataIndex: "description" }, { title: "状态", width: 80, render: (_: unknown, skill: UserSkill) => <Tag color={skill.enabled ? "success" : "default"}>{skill.enabled ? "启用" : "停用"}</Tag> }, { title: "操作", width: 80, render: (_: unknown, skill: UserSkill) => <Button danger type="link" onClick={() => deleteUserSkill(skill)}>删除</Button> }]} />
      </Drawer>
      {overview && canManage && <SkillManager open={skillsOpen} onClose={() => setSkillsOpen(false)} scope="global" skills={globalSkills} refresh={refreshGlobals} />}
    </div>
  );
}
