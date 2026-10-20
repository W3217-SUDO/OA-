import { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Button, Drawer, Empty, Input, Pagination, Segmented, Skeleton, Tabs, Tag, Tooltip, message } from "antd";
import { AppstoreOutlined, CheckOutlined, DownloadOutlined, LinkOutlined, ReloadOutlined, RobotOutlined, SearchOutlined, TeamOutlined, ToolOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText, type SkillRuntime, type WorkspaceSkill } from "../personal-agent/types";
import { SkillRuntimeStatus } from "../personal-agent/SkillRuntimeStatus";
import { refreshAgentSkillCatalogConsumers } from "../agentSkillCatalog";
import { skillScopeLabel, type SkillScope } from "../personal-agent/skillScope";
import "./capability-market.css";
import { CapabilityAvatar } from "./CapabilityAvatar";
import { ConnectorConfigPanel, connectionLabel } from "./ConnectorConfigPanel";

type Capability = {
  id: string; kind: "expert" | "team" | "skill" | "connector"; name: string; description: string; category: string;
  author: string; license: string; version: string; tags: string[]; avatar: string; avatar_fetch?: boolean; source: string;
  members: { id: string; name: string; profession: string }[]; unavailable_reason: string; sha256: string;
  installed: { id: string; scope: SkillScope; enabled?: boolean; available?: boolean; skill_runtime?: SkillRuntime; needs_resource_sync?: boolean }[];
  skill_runtime?: SkillRuntime;
  connection?: { status: string; saved: boolean } | null;
};
type Definition = Omit<Capability, "installed"> & {
  instruction: string; resources: string[]; license_documents: Record<string, string>;
  connection_configs: Record<string, unknown>; excluded_resources: string[];
};
type Tool = { name: string; title: string; description: string; is_write: boolean };
type Props = { active: boolean; scope?: SkillScope; onInstalled?: (skill: WorkspaceSkill) => Promise<void>; onSelect?: (id: string) => void; onBusy?: (value: boolean) => void; managementView?: boolean; canManage?: boolean; installedSkills?: WorkspaceSkill[]; onManageInstalled?: () => void };

export function CapabilityMarket({ active, scope = "personal", onInstalled, onSelect, onBusy, managementView = false, canManage = true, installedSkills = [], onManageInstalled }: Props) {
  const [items, setItems] = useState<Capability[]>([]);
  const [tab, setTab] = useState(managementView ? "skills" : "experts");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("全部");
  const [expertType, setExpertType] = useState("expert");
  const [mine, setMine] = useState(false);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<Capability | null>(null);
  const [detail, setDetail] = useState<Definition | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refreshPending, setRefreshPending] = useState<WorkspaceSkill | null>(null);
  const operation = useRef(false);
  const [tools, setTools] = useState<Tool[] | null>(null);
  const [toolsError, setToolsError] = useState("");
  const [toolsOpen, setToolsOpen] = useState(false);
  useEffect(() => { onBusy?.(busy); }, [busy, onBusy]);
  useEffect(() => { setPage(1); }, [tab, query, category, expertType, mine]);

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    setLoading(true); setError("");
    void api.get<{ items: Capability[] }>("/capability-market", { signal: controller.signal, params: { scope } })
      .then(({ data }) => { if (!controller.signal.aborted) setItems(data.items); })
      .catch(failure => { if (!controller.signal.aborted) setError(errorText(failure, "能力目录加载失败")); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [active, revision, scope]);

  useEffect(() => {
    setDetail(null); setDetailError(""); setRefreshPending(null);
    if (!active || !selected) return;
    const controller = new AbortController();
    setDetailLoading(true);
    void api.get<Definition>(`/capability-market/items/${selected.id}`, { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setDetail(data); })
      .catch(failure => { if (!controller.signal.aborted) setDetailError(errorText(failure, "能力详情加载失败")); })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false); });
    return () => controller.abort();
  }, [active, selected]);

  useEffect(() => {
    if (!active || tab !== "connectors") return;
    const controller = new AbortController();
    setTools(null); setToolsError("");
    void api.get<{ tools: Tool[] }>("/agent-tools/catalog", { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setTools(data.tools); })
      .catch(failure => { if (!controller.signal.aborted) setToolsError(errorText(failure, "业务工具目录加载失败")); });
    return () => controller.abort();
  }, [active, tab, revision]);

  const scoped = useMemo(() => items.filter(item => tab === "skills" ? item.kind === "skill" : item.kind === expertType), [items, tab, expertType]);
  const categories = ["全部", ...new Set(scoped.map(item => item.category))];
  const matching = scoped.filter(item => (category === "全部" || item.category === category)
    && (!mine || item.installed.some(record => record.scope === scope))
    && `${item.name} ${item.description} ${item.author} ${item.tags.join(" ")}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  const connectors = items.filter(item => item.kind === "connector" && (!mine || item.connection?.saved) && `${item.name} ${item.description}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  const featured = categories.filter(value => value !== "全部").slice(0, 6).map(value => ({ category: value, items: scoped.filter(item => item.category === value).slice(0, 3) }));
  const current = selected && items.find(item => item.id === selected.id);
  const installed = current?.installed.find(record => record.scope === scope);
  const savedSkill = managementView && current?.kind === "skill" ? installedSkills.find(skill => skill.source === current.source) : undefined;
  const selectedInstalled = installed || savedSkill;
  const installedEnabled = savedSkill?.enabled ?? installed?.enabled;
  const selectedRuntime = savedSkill?.skill_runtime || installed?.skill_runtime || detail?.skill_runtime;
  const needsResourceSync = installed?.needs_resource_sync === true;
  const canSelectInstalled = !!installed && installedEnabled !== false && (savedSkill?.available ?? installed.available) !== false && selectedRuntime?.ready !== false;
  const refreshSkillConsumers = async (skill: WorkspaceSkill) => {
    const results = await Promise.allSettled([Promise.resolve().then(() => onInstalled?.(skill)), refreshAgentSkillCatalogConsumers()]);
    const failure = results.find(result => result.status === "rejected");
    if (failure?.status === "rejected") throw failure.reason;
  };
  const install = async () => {
    if (!detail || !selected || operation.current || detail.unavailable_reason || (selectedInstalled && !needsResourceSync) || (managementView && (!canManage || selected.kind !== "skill"))) return;
    operation.current = true; setBusy(true); setDetailError("");
    let saved: WorkspaceSkill | null = null;
    try {
      const { data } = await api.post<WorkspaceSkill>(`/capability-market/items/${selected.id}/install`, { scope, sha256: detail.sha256 });
      saved = data;
      setItems(previous => previous.map(item => item.id === selected.id ? { ...item, installed: [...item.installed.filter(record => record.scope !== scope), { id: data.id, scope, enabled: data.enabled, available: data.available, skill_runtime: data.skill_runtime, needs_resource_sync: false }] } : item));
      await refreshSkillConsumers(data);
      message.success(data.enabled === false ? "技能资源已保存；技能仍处于停用状态，请在技能库启用" : data.skill_runtime?.ready === false ? "技能已安装；运行依赖尚未就绪，请查看技能状态" : data.available ? `已安装到${skillScopeLabel(scope)}` : "已安装的技能处于停用状态，请在技能库启用");
    } catch (failure) {
      if (saved) setRefreshPending(saved);
      setDetailError(saved ? `能力已安装，但技能库刷新失败：${errorText(failure, "请刷新技能库")}` : errorText(failure, "安装失败"));
    } finally { operation.current = false; setBusy(false); }
  };
  const refreshInstalled = async () => {
    if (!refreshPending || operation.current) return;
    operation.current = true; setBusy(true);
    try { await refreshSkillConsumers(refreshPending); setRefreshPending(null); setDetailError(""); }
    catch (failure) { setDetailError(`能力已安装，但技能库刷新失败：${errorText(failure, "请刷新技能库")}`); }
    finally { operation.current = false; setBusy(false); }
  };
  const installAction = refreshPending ? <Button type="primary" icon={<ReloadOutlined />} loading={busy} onClick={() => void refreshInstalled()}>刷新技能库</Button>
    : needsResourceSync ? <Button type="primary" icon={<DownloadOutlined />} loading={busy} disabled={!detail || !!detail.unavailable_reason || (managementView && !canManage)} onClick={() => void install()}>补齐技能资源</Button>
    : installedEnabled === false && onManageInstalled ? <Button type="primary" onClick={() => { setSelected(null); onManageInstalled(); }}>已安装 · 已停用，去启用</Button>
    : canSelectInstalled && onSelect ? <Button type="primary" icon={<CheckOutlined />} disabled={busy} onClick={() => { onSelect(installed!.id); setSelected(null); }}>使用</Button>
    : <Button type="primary" icon={selectedInstalled ? <CheckOutlined /> : <DownloadOutlined />} loading={busy} disabled={!detail || !!detail.unavailable_reason || !!selectedInstalled || (managementView && !canManage)} onClick={() => void install()}>{selectedInstalled ? installedEnabled === false ? "已安装 · 已停用" : selectedRuntime?.ready === false ? "已安装 · 依赖未就绪" : "已安装" : managementView && !canManage ? "只读" : `安装到${skillScopeLabel(scope)}`}</Button>;

  return <section className="capability-market" aria-label={managementView ? "全局技能与连接器市场" : "专家、技能与连接器"}>
    <header className="capability-market-header">
      <Tabs activeKey={tab} onChange={key => { if (!busy) { setTab(key); setCategory("全部"); setSelected(null); } }} items={[
        ...(!managementView ? [{ key: "experts", disabled: busy, label: <span><RobotOutlined /> 专家（{items.filter(item => item.kind === "expert" || item.kind === "team").length}）</span> }] : []),
        { key: "skills", disabled: busy, label: <span><ToolOutlined /> 技能（{items.filter(item => item.kind === "skill").length}）</span> },
        { key: "connectors", disabled: busy, label: <span><LinkOutlined /> 连接器（{items.filter(item => item.kind === "connector").length}）</span> },
      ]} />
      <div className="capability-market-search">
        <Input prefix={<SearchOutlined />} aria-label="搜索能力" placeholder="搜索名称、职责或描述" value={query} onChange={event => setQuery(event.target.value)} allowClear />
        <Button icon={<AppstoreOutlined />} onClick={() => setMine(value => !value)} type={mine ? "primary" : "default"}>{mine ? "全部能力" : "我的能力"}</Button>
        <Tooltip title="刷新目录"><Button icon={<ReloadOutlined />} aria-label="刷新目录" loading={loading} onClick={() => setRevision(value => value + 1)} /></Tooltip>
      </div>
    </header>
    {error && <Alert type="error" showIcon title={error} action={<Button onClick={() => setRevision(value => value + 1)}>重试</Button>} />}
    {tab !== "connectors" && <>
      {tab === "experts" && !mine && !query && !loading && !!featured.length && <section className="capability-market-scenarios" aria-label="精选场景">
        <h2>精选场景</h2><div className="capability-market-scenario-rail">{featured.map(scene => <article key={scene.category}>
          <h3>{scene.category}</h3>{scene.items.map(item => <Button key={item.id} type="text" onClick={() => setSelected(item)}>{item.name}</Button>)}
        </article>)}</div>
      </section>}
      <div className="capability-market-section-heading"><h2>{tab === "skills" ? "技能" : "专家"}</h2>
        {tab === "experts" && <Segmented value={expertType} onChange={value => { setExpertType(value); setCategory("全部"); }} options={[{ value: "expert", label: "专家" }, { value: "team", label: "专家团" }]} />}
        <span>{matching.length} 项</span>
      </div>
      <Tabs className="capability-market-categories" activeKey={category} onChange={setCategory} items={categories.map(value => ({ key: value, label: value }))} />
      {loading && !items.length ? <Skeleton active paragraph={{ rows: 5 }} /> : !matching.length ? <Empty description={mine ? "尚未安装此类能力" : "没有匹配的能力"} /> : <div className="capability-market-grid">
        {matching.slice((page - 1) * 24, page * 24).map(item => {
          const record = item.installed.find(entry => entry.scope === scope);
          const saved = managementView ? installedSkills.find(skill => skill.source === item.source) : undefined;
          const hasInstalled = !!record || !!saved;
          const enabled = saved?.enabled ?? record?.enabled;
          const runtime = saved?.skill_runtime || record?.skill_runtime || item.skill_runtime;
          return <article className="capability-market-card" key={item.id}>
          <div className="capability-market-card-heading">
            <CapabilityAvatar source={item.avatar} authenticated={item.avatar_fetch} />
            <div><h3>{item.name}</h3><small>{item.author || item.license}</small></div>
          </div>
          <p>{item.description}</p>
          <div className="capability-market-tags">{item.tags.map(tag => <Tag key={tag}>{tag}</Tag>)}{!item.tags.length && <Tag>{item.category}</Tag>}</div>
          <SkillRuntimeStatus runtime={runtime} enabled={hasInstalled ? enabled : undefined} />
          <footer><span>{hasInstalled ? record?.needs_resource_sync ? "已安装 · 待补齐资源" : enabled === false ? "已安装 · 已停用" : "已安装" : item.unavailable_reason ? "待适配" : managementView && !canManage ? "只读" : managementView || tab === "skills" ? "可安装" : "可导入指令"}</span><Button size="small" onClick={() => setSelected(item)}>查看详情</Button></footer>
        </article>; })}
      </div>}
      {matching.length > 24 && <Pagination className="capability-market-pagination" current={page} pageSize={24} total={matching.length} onChange={setPage} showSizeChanger={false} responsive />}
    </>}
    {tab === "connectors" && <>
      <div className="capability-market-section-heading"><h2>连接器</h2></div>
      {toolsError ? <Alert type="error" showIcon title={toolsError} action={<Button onClick={() => setRevision(value => value + 1)}>重试</Button>} /> : tools === null ? <Skeleton active /> : <div className="capability-market-grid">
        <article className="capability-market-card">
          <div className="capability-market-card-heading"><span className="capability-market-icon"><LinkOutlined /></span><div><h3>沪知 OA</h3><small>MCP · 系统内置</small></div></div>
          <p>案件、合同、任务、费用与文书业务接口。</p>
          <div className="capability-market-tags"><Tag>{tools.length} 个已注册工具</Tag><Tag>写入需确认</Tag></div>
          <footer><span>已接入</span><Button size="small" onClick={() => setToolsOpen(true)}>查看工具</Button></footer>
        </article>
      </div>}
      <div className="capability-market-grid">{connectors.slice((page - 1) * 24, page * 24).map(item => <article className="capability-market-card" key={item.id}>
        <div className="capability-market-card-heading"><span className="capability-market-icon"><LinkOutlined /></span><div><h3>{item.name}</h3><small>{item.tags.join(" · ")}</small></div></div>
        <p>{item.description}</p><footer><span>{connectionLabel(item.connection?.status)}</span><Button size="small" icon={<LinkOutlined />} onClick={() => setSelected(item)}>{managementView && !canManage ? "查看连接" : "配置连接"}</Button></footer>
      </article>)}</div>
      {connectors.length > 24 && <Pagination className="capability-market-pagination" current={page} pageSize={24} total={connectors.length} onChange={setPage} showSizeChanger={false} responsive />}
    </>}
    <Drawer open={active && !!selected} onClose={() => { if (!busy) setSelected(null); }} title={selected?.name} width={680} zIndex={1500} rootClassName="capability-market-detail" maskClosable={!busy} closable={!busy}
      footer={<div className="capability-market-detail-actions"><Button disabled={busy} onClick={() => setSelected(null)}>关闭</Button>{selected?.kind !== "connector" && (!managementView || selected?.kind === "skill") && installAction}</div>}>
      {detailLoading ? <Skeleton active /> : detail && <>
        <p>{detail.description}</p><div className="capability-market-tags"><Tag>{detail.category}</Tag><Tag>{detail.license}</Tag>{detail.version && <Tag>v{detail.version}</Tag>}</div>
        <a href={detail.source} target="_blank" rel="noopener noreferrer">原始来源</a>
        {managementView && detail.kind === "skill" && <p>安装范围：全局。启用后全所账号可选用；OA 工具仍按登录账号权限执行，写入操作须在前端确认。</p>}
        {managementView && detail.kind === "skill" && <p>技能原文 SHA256：{detail.sha256}</p>}
        {detail.kind === "skill" && <SkillRuntimeStatus runtime={selectedRuntime} enabled={installedEnabled} details />}
        {needsResourceSync && <Alert type="info" showIcon title="已安装的版本缺少完整资源包" description="补齐后 DSH 才能读取技能脚本和参考资料；原启用状态保持不变。" />}
        {detail.kind === "connector" && (!managementView || canManage ? <ConnectorConfigPanel key={detail.id} itemId={detail.id} name={detail.name} scope={scope} onBusy={setBusy} onChanged={state => setItems(previous => previous.map(item => item.id === detail.id ? { ...item, connection: { status: state.status, saved: state.saved } } : item))} /> : <Alert type="info" showIcon title={`当前账号只读；${connectionLabel(current?.connection?.status)}`} />)}
        {detail.kind !== "connector" && detail.unavailable_reason && <Alert type="warning" showIcon title={detail.unavailable_reason} />}
        {detail.members.length > 1 && <section><h3><TeamOutlined /> 成员</h3>{detail.members.map(member => <p key={member.id}>{member.name} · {member.profession}</p>)}</section>}
        {detail.kind === "connector" && <details><summary>原始连接配置</summary>{Object.entries(detail.connection_configs).map(([path, config]) => <section key={path}><h4>{path}</h4><pre>{JSON.stringify(config, null, 2)}</pre></section>)}</details>}
        <details open={detail.kind !== "connector"}><summary>{detail.kind === "connector" ? "接入要求" : "完整指令"}</summary><pre>{detail.instruction}</pre></details>
        <details><summary>参考资料（{detail.resources.length}）</summary><ul>{detail.resources.map(path => <li key={path}>{path}</li>)}</ul></details>
        {!!detail.excluded_resources.length && <details><summary>未加载的脚本与验证资料（{detail.excluded_resources.length}）</summary><ul>{detail.excluded_resources.map(path => <li key={path}>{path}</li>)}</ul></details>}
        <details><summary>许可证与版权声明</summary>{Object.entries(detail.license_documents).map(([path, text]) => <section key={path}><h4>{path}</h4><pre>{text}</pre></section>)}</details>
      </>}
      {detailError && <Alert type="error" showIcon title={detailError} />}
    </Drawer>
    <Drawer open={active && toolsOpen} onClose={() => setToolsOpen(false)} title="沪知 OA · 业务工具" width={680} zIndex={1500} rootClassName="capability-market-detail">
      <div className="capability-market-tool-list">{tools?.map(tool => <article key={tool.name}><h3>{tool.title || tool.name}</h3><p>{tool.description}</p><Tag>{tool.is_write ? "写入需确认" : "只读查询"}</Tag></article>)}</div>
    </Drawer>
  </section>;
}
