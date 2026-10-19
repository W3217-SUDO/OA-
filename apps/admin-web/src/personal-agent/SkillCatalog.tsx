import { useEffect, useRef, useState } from "react";
import { Alert, Button, Empty, Input, Select, Spin } from "antd";
import { DownloadOutlined, ReloadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText, type WorkspaceSkill } from "./types";
import { skillBase, skillScopeLabel, type SkillScope } from "./skillScope";

type Source = "skills-sh" | "openai" | "anthropic";
type CatalogItem = { id: string; name: string; description: string; source: Source; market_url: string; repo: string; skill_slug: string; installs?: number };
type CatalogPage = { items: CatalogItem[]; source: Source; query: string; note?: string };
type Preview = { name: string; description: string; instruction: string; source: string; url: string; sha256: string };
const SOURCES: { value: Source; label: string; website: string }[] = [
  { value: "skills-sh", label: "Skills.sh 技能目录", website: "https://skills.sh/" },
  { value: "openai", label: "OpenAI 官方技能", website: "https://github.com/openai/skills" },
  { value: "anthropic", label: "Anthropic 官方技能", website: "https://github.com/anthropics/skills" },
];

export function SkillCatalog({ active, busy, onBusy, onInstalled, scope = "personal" }: {
  active: boolean; busy: boolean; onBusy: (value: boolean) => void; onInstalled: (skill: WorkspaceSkill) => Promise<void>; scope?: SkillScope;
}) {
  const scopeLabel = skillScopeLabel(scope);
  const [source, setSource] = useState<Source>("skills-sh");
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [revision, setRevision] = useState(0);
  const [page, setPage] = useState<CatalogPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewError, setPreviewError] = useState("");
  const [previewingId, setPreviewingId] = useState("");
  const [refreshPending, setRefreshPending] = useState<WorkspaceSkill | null>(null);
  const operationLock = useRef(false);
  const previewRef = useRef<HTMLDivElement>(null);
  const sourceInfo = SOURCES.find(item => item.value === source)!;
  useEffect(() => { if (preview) previewRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" }); }, [preview]);
  useEffect(() => {
    if (!active) { setPreview(null); setPreviewError(""); return; }
    const controller = new AbortController();
    setLoading(true); setError(""); setPage(null); setPreview(null); setPreviewError("");
    void api.get<CatalogPage>("/agent/skills/catalog", { params: { source, q: query }, signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setPage(data); })
      .catch(failure => { if (!controller.signal.aborted) setError(errorText(failure, "技能目录加载失败，请重试或访问来源网站")); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [active, source, query, revision]);
  const choose = async (item: CatalogItem) => {
    if (busy || operationLock.current || !page) return;
    operationLock.current = true; onBusy(true); setPreview(null); setPreviewError(""); setPreviewingId(item.id);
    try {
      const { data } = await api.post<Preview>("/agent/skills/catalog/preview", { source: item.source, id: item.id, q: page.query });
      setPreview(data);
    } catch (failure) { setPreviewError(errorText(failure, "此技能暂不支持导入或预览失败，请查看来源网站后重试")); }
    finally { operationLock.current = false; onBusy(false); setPreviewingId(""); }
  };
  const install = async () => {
    if (!preview || busy || operationLock.current) return;
    operationLock.current = true; onBusy(true); setPreviewError("");
    let saved: WorkspaceSkill | null = null;
    try {
      const { data } = await api.post<WorkspaceSkill>(`${skillBase(scope)}/github/install`, { url: preview.url, sha256: preview.sha256 });
      saved = data; setPreview(null); setRefreshPending(null);
      await onInstalled(data);
    } catch (failure) {
      if (saved) { setRefreshPending(saved); setPreviewError(`技能已安装，但列表刷新失败，请刷新重试：${errorText(failure, `${scopeLabel}加载失败`)}`); }
      else setPreviewError(errorText(failure, "安装未完成；若来源已变化，请重新选择并预览"));
    }
    finally { operationLock.current = false; onBusy(false); }
  };
  const retryRefresh = async () => {
    if (!refreshPending || busy || operationLock.current) return;
    operationLock.current = true; onBusy(true);
    try { await onInstalled(refreshPending); setRefreshPending(null); setPreviewError(""); }
    catch (failure) { setPreviewError(`技能已安装，但列表刷新失败，请刷新重试：${errorText(failure, `${scopeLabel}加载失败`)}`); }
    finally { operationLock.current = false; onBusy(false); }
  };
  return <section className="workspace-skill-catalog" aria-label="技能市场">
    <div className="workspace-catalog-toolbar">
      <Select aria-label="技能来源" value={source} options={SOURCES.map(({ value, label }) => ({ value, label }))} disabled={busy} onChange={value => { setSource(value); setInput(""); setQuery(""); }} />
      <a href={sourceInfo.website} target="_blank" rel="noopener noreferrer">访问来源网站 ↗</a>
    </div>
    <div className="workspace-catalog-search">
      <Input aria-label="搜索网站技能" value={input} maxLength={100} placeholder="PDF、文档、合同（或英文技能名）" disabled={busy} onChange={event => setInput(event.target.value)} onPressEnter={() => { if (!busy) { setQuery(input.trim()); setRevision(value => value + 1); } }} />
      <Button disabled={busy} onClick={() => { setQuery(input.trim()); setRevision(value => value + 1); }}>搜索技能</Button>
      <Button icon={<ReloadOutlined />} aria-label="刷新技能目录" disabled={busy || loading} onClick={() => setRevision(value => value + 1)} />
    </div>
    <p className="workspace-catalog-note">从来源网站读取真实技能目录。选择技能后查看完整指令，再确认安装到{scopeLabel}；保留技能目录与参考资料，不自动执行仓库脚本或安装依赖。</p>
    {page?.note && <Alert type="info" showIcon title={page.note} />}
    {error && <Alert type="error" showIcon title="技能目录暂不可用" description={error} action={<Button disabled={busy} onClick={() => setRevision(value => value + 1)}>重试</Button>} />}
    {(previewError || refreshPending) && <Alert type={refreshPending ? "warning" : "error"} showIcon title={refreshPending ? scope === "global" ? "技能已安装，待刷新全局库" : "技能已安装，待刷新个人库" : "技能操作未完成"} description={previewError || "技能已安装，但技能库尚未刷新，请刷新重试"} action={refreshPending ? <Button disabled={busy} onClick={() => void retryRefresh()}>刷新{scopeLabel}</Button> : undefined} />}
    {loading ? <div className="workspace-catalog-loading" role="status"><Spin /><span>正在读取技能网站</span></div> : page && !page.items.length ? <Empty description="没有找到技能，请尝试英文技能名或切换来源" /> : <div className="workspace-catalog-grid">{page?.items.map(item => <article className="workspace-catalog-card" key={`${item.source}:${item.id}`}>
      <h3>{item.name}</h3><p>{item.description || "来源未提供说明，选择后查看完整 SKILL.md。"}</p>
      <small>{item.repo} · {item.skill_slug}</small>
      {typeof item.installs === "number" && <small>来源网站安装数：{new Intl.NumberFormat("zh-CN").format(item.installs)}</small>}
      <div className="workspace-catalog-card-actions"><a href={item.market_url} target="_blank" rel="noopener noreferrer">来源详情 ↗</a><Button icon={<DownloadOutlined />} loading={previewingId === item.id} disabled={busy} onClick={() => void choose(item)}>选择并预览</Button></div>
    </article>)}</div>}
    {preview && <div ref={previewRef} className="workspace-github-preview workspace-catalog-preview" role="region" aria-label={`技能预览：${preview.name}`}>
      <h3>{preview.name}</h3><p>{preview.description}</p>
      <a href={preview.source} target="_blank" rel="noopener noreferrer">来源：{preview.source}</a>
      <span className="workspace-skill-hash">SHA256：{preview.sha256}</span>
      <b>完整技能指令（{preview.instruction.length} 字符）</b><pre tabIndex={0}>{preview.instruction}</pre>
      <p>请阅读完整指令。{scope === "global" ? "确认后加入全局技能库，启用后全所账号可选用。" : "确认后仅加入你自己的个人技能库，可在 AI 对话中选用。"}</p>
      <div className="workspace-catalog-preview-actions"><Button disabled={busy} onClick={() => { setPreview(null); setPreviewError(""); }}>取消选择</Button><Button type="primary" loading={busy} disabled={busy || preview.instruction.length > 64000} onClick={() => void install()}>{`确认安装到${scopeLabel}`}</Button></div>
      {preview.instruction.length > 64000 && <Alert type="error" showIcon title="指令超过 64000 字符，不支持安装；完整正文仍可阅读" />}
    </div>}
  </section>;
}
