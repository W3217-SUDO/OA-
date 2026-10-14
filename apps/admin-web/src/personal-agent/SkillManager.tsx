import { useRef, useState } from "react";
import { Alert, Button, Empty, Form, Input, Modal, Space, Switch, Tabs, Tooltip, message } from "antd";
import { DeleteOutlined, EditOutlined, GithubOutlined, PlusOutlined, UploadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText, type WorkspaceSkill } from "./types";
import { SkillCatalog } from "./SkillCatalog";
import { managedSkills, skillBase, skillScopeLabel, type SkillScope } from "./skillScope";
import "./workspace-context.css";
import { CapabilityMarket } from "../capability-market/CapabilityMarket";

type Props = { open: boolean; onClose: () => void; skills: WorkspaceSkill[]; refresh: () => Promise<void>; onSelect?: (id: string) => void; scope?: SkillScope };
type GithubPreview = { name: string; description: string; instruction: string; source: string; sha256: string; url: string };
function githubSourceUrl(source?: string) {
  if (!source) return null;
  try { const url = new URL(source); return url.protocol === "https:" && url.hostname === "github.com" && !url.username && !url.password && url.pathname.split("/").filter(Boolean).length >= 2 ? url.href : null; }
  catch { return null; }
}

export function SkillManager({ open, onClose, skills, refresh, onSelect, scope = "personal" }: Props) {
  const base = skillBase(scope);
  const scopeLabel = skillScopeLabel(scope);
  const ownedSkills = managedSkills(skills, scope);
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState("");
  const [tab, setTab] = useState("capabilities");
  const [busy, setBusy] = useState(false);
  const [githubUrl, setGithubUrl] = useState("");
  const [githubPreview, setGithubPreview] = useState<GithubPreview | null>(null);
  const [githubError, setGithubError] = useState("");
  const [githubRefreshPending, setGithubRefreshPending] = useState<WorkspaceSkill | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const reset = () => { setEditingId(""); form.resetFields(); };
  const previewGithub = async () => {
    setBusy(true); setGithubError(""); setGithubPreview(null);
    try { const { data } = await api.post<GithubPreview>(`${base}/github/preview`, { url: githubUrl.trim() }); setGithubPreview(data); }
    catch (error) { setGithubError(errorText(error, "GitHub 技能预览失败")); }
    finally { setBusy(false); }
  };
  const installGithub = async () => {
    if (!githubPreview) return;
    setBusy(true); setGithubError("");
    let saved: WorkspaceSkill | null = null;
    try {
      const { data } = await api.post<WorkspaceSkill>(`${base}/github/install`, { url: githubPreview.url, sha256: githubPreview.sha256 });
      saved = data; setGithubPreview(null); setGithubUrl(""); setGithubRefreshPending(null);
      await refresh(); setTab("mine");
      if (data.available) { onSelect?.(data.id); message.success(onSelect ? "技能已安装并选中" : `${scopeLabel}已安装`); }
      else { message.info("该技能已存在但已停用，请启用后使用；当前选择保持不变"); }
    } catch (error) {
      if (saved) { setGithubRefreshPending(saved); setGithubError(`技能已安装，但列表刷新失败，请刷新重试：${errorText(error, `${scopeLabel}加载失败`)}`); }
      else setGithubError(errorText(error, "GitHub 技能安装失败，请重新预览后再试"));
    }
    finally { setBusy(false); }
  };
  const refreshInstalledGithub = async () => {
    if (!githubRefreshPending || busy) return;
    setBusy(true);
    try {
      await refresh(); setTab("mine"); setGithubError("");
      if (githubRefreshPending.available) { onSelect?.(githubRefreshPending.id); message.success(onSelect ? "技能已刷新并选中" : `${scopeLabel}已刷新`); }
      else message.info("该技能已停用，请启用后使用；当前选择保持不变");
      setGithubRefreshPending(null);
    } catch (error) { setGithubError(`技能已安装，但列表刷新失败，请刷新重试：${errorText(error, `${scopeLabel}加载失败`)}`); }
    finally { setBusy(false); }
  };
  const save = async (values: Record<string, string>) => {
    setBusy(true);
    try {
      const payload = { ...values, quick_prompts: (values.quick_prompts || "").split(/\r?\n/).map((value) => value.trim()).filter(Boolean) };
      if (editingId) await api.patch(`${base}/${editingId}`, payload);
      else { const { data } = await api.post(base, payload); onSelect?.(data.id); }
      await refresh(); reset(); setTab("mine"); message.success("技能已保存");
    } catch (error) { message.error(errorText(error, "技能保存失败")); }
    finally { setBusy(false); }
  };
  const upload = async (file?: File) => {
    if (!file) return;
    setBusy(true);
    try {
      const body = new FormData(); body.append("file", file);
      const { data } = await api.post(`${base}/upload`, body);
      await refresh(); onSelect?.(data.id); message.success(onSelect ? "技能已上传并选中" : `${scopeLabel}已上传`);
    } catch (error) { message.error(errorText(error, "技能上传失败")); }
    finally { setBusy(false); if (fileRef.current) fileRef.current.value = ""; }
  };
  const toggle = async (skill: WorkspaceSkill, enabled: boolean) => {
    setBusy(true);
    try { await api.patch(`${base}/${skill.id}`, { enabled }); await refresh(); }
    catch (error) { message.error(errorText(error, "技能更新失败")); }
    finally { setBusy(false); }
  };
  const remove = (skill: WorkspaceSkill) => Modal.confirm({ title: `删除${scopeLabel}“${skill.name}”？`, content: scope === "global" ? "删除后所有账号都无法再选用该全局技能，已有对话记录保留。" : "仅删除你自己的个人技能，不影响全局技能和其他账号。", okText: "删除", cancelText: "取消", okButtonProps: { danger: true }, onOk: async () => {
    try { await api.delete(`${base}/${skill.id}`); await refresh(); if (editingId === skill.id) reset(); }
    catch (error) { message.error(errorText(error, "技能删除失败")); throw error; }
  } });
  return <Modal open={open} title={scopeLabel} width={1040} footer={null} className="workspace-skill-modal" maskClosable={!busy} closable={!busy} onCancel={() => { if (busy) return; onClose(); reset(); setTab("capabilities"); setGithubPreview(null); setGithubError(""); }}>
    <Alert type="info" showIcon title={scope === "global" ? "管理全局技能：启用后可供全所账号选用，只有管理员可以修改。" : "管理个人技能：仅本人可用，不会共享给其他账号。"} />
    <Tabs activeKey={tab} onChange={key => { if (!busy) setTab(key); }} items={[
      { key: "capabilities", label: "专家、技能、连接器", disabled: busy }, { key: "market", label: "更多技能", disabled: busy }, { key: "mine", label: scopeLabel, disabled: busy },
      { key: "github", label: "GitHub 链接", disabled: busy }, { key: "custom", label: editingId ? "编辑技能" : "手工新增", disabled: busy },
    ]} />
    <div className="workspace-skill-manager">
      <div hidden={tab !== "capabilities"}><CapabilityMarket active={open && tab === "capabilities"} scope={scope} onBusy={setBusy} onInstalled={async () => { await refresh(); }} onSelect={onSelect ? id => { onSelect(id); onClose(); } : undefined} /></div>
      <div hidden={tab !== "market"}><SkillCatalog scope={scope} active={open && tab === "market"} busy={busy} onBusy={setBusy} onInstalled={async skill => {
        await refresh(); setTab("mine");
        if (skill.available) { onSelect?.(skill.id); message.success(onSelect ? "技能已安装到个人库并选中" : `${scopeLabel}已安装`); }
        else message.info("该技能已存在但已停用，请启用后使用；当前选择保持不变");
      }} /></div>
      <section hidden={tab !== "github"} className="workspace-github-install" aria-label="从 GitHub 安装技能">
        <div className="workspace-section-heading"><b><GithubOutlined /> 从 GitHub 安装</b></div>
        <p>粘贴公开 GitHub 技能目录或 SKILL.md 链接，先查看指令，再确认安装到{scopeLabel}。仅导入 SKILL.md 作为 OA 技能指令，仓库中的脚本和 references 不会自动执行。</p>
        <div className="workspace-github-url">
          <Input aria-label="GitHub 技能链接" placeholder="https://github.com/owner/repo/tree/main/skills/example" value={githubUrl} disabled={busy} onChange={(event) => { setGithubUrl(event.target.value); setGithubPreview(null); setGithubError(""); }} onPressEnter={() => { if (!busy && githubUrl.trim()) void previewGithub(); }} />
          <Button icon={<GithubOutlined />} loading={busy} disabled={!githubUrl.trim() || busy} onClick={() => void previewGithub()}>预览技能</Button>
        </div>
        {(githubError || githubRefreshPending) && <Alert type={githubRefreshPending ? "warning" : "error"} showIcon message={githubError || `技能已安装，但${scopeLabel}库尚未刷新，请刷新重试`} action={githubRefreshPending ? <Button disabled={busy} onClick={() => void refreshInstalledGithub()}>刷新{scopeLabel}</Button> : undefined} />}
        {githubPreview && <div className="workspace-github-preview">
          <h3>{githubPreview.name}</h3><p>{githubPreview.description}</p>
          <a href={githubPreview.source} target="_blank" rel="noopener noreferrer">来源：{githubPreview.source}</a>
          <span className="workspace-skill-hash">SHA256：{githubPreview.sha256}</span>
          <b>完整技能指令</b><pre tabIndex={0}>{githubPreview.instruction}</pre>
          <p>{scope === "global" ? "确认后加入全局技能，启用后全所账号可选用。" : "确认后加入个人技能，仅本人可用。"}技能会参与 AI 回答，请先检查完整指令及来源。</p>
          <Button type="primary" loading={busy} disabled={busy || githubPreview.instruction.length > 64000} onClick={() => void installGithub()}>{scope === "global" ? "确认安装到全局技能" : "确认安装并选中"}</Button>
          {githubPreview.instruction.length > 64000 && <Alert type="error" showIcon title="指令超过 64000 字符，不支持安装；完整正文仍可阅读" />}
        </div>}
      </section>
      <section hidden={tab !== "mine"} className="workspace-skill-list">
        <div className="workspace-section-heading"><b>{scopeLabel}</b><Space size={4}>
          <input hidden ref={fileRef} type="file" accept=".json,.md,.markdown,.docx" onChange={(event) => void upload(event.target.files?.[0])} />
          <Tooltip title="上传 Markdown、JSON 或 Word 技能"><Button icon={<UploadOutlined />} disabled={busy} onClick={() => fileRef.current?.click()}>上传</Button></Tooltip>
          <Tooltip title="新增技能"><Button icon={<PlusOutlined />} disabled={busy} onClick={() => { reset(); setTab("custom"); }} aria-label="新增技能" /></Tooltip>
        </Space></div>
        {ownedSkills.map((skill) => <div className="workspace-skill-row" key={skill.id}>
          <div><b>{skill.name}</b><p>{skill.description}</p>{githubSourceUrl(skill.source) ? <a className="workspace-skill-source" href={githubSourceUrl(skill.source)!} target="_blank" rel="noopener noreferrer">GitHub 来源：{skill.source}</a> : skill.source && <span className="workspace-skill-source">来源：{skill.source.startsWith("user-upload") ? "本地上传" : skill.source === "user-custom" ? "手工创建" : skill.source}</span>}</div><Space size={2} wrap>
            {onSelect && <Button size="small" disabled={busy || !skill.available} onClick={() => { onSelect(skill.id); onClose(); }}>使用</Button>}
            <label className="workspace-skill-toggle"><Switch size="small" checked={skill.available} disabled={busy} onChange={(value) => void toggle(skill, value)} aria-label={`启用${skill.name}`} /></label>
            <Tooltip title="编辑技能"><Button type="text" icon={<EditOutlined />} disabled={busy} aria-label="编辑技能" onClick={() => { setEditingId(skill.id); setTab("custom"); form.setFieldsValue({ ...skill, quick_prompts: skill.quick_prompts.join("\n") }); }} /></Tooltip>
            <Tooltip title="删除技能"><Button type="text" danger icon={<DeleteOutlined />} disabled={busy} aria-label="删除技能" onClick={() => remove(skill)} /></Tooltip>
          </Space>
        </div>)}
        {!ownedSkills.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`暂无${scopeLabel}`} />}
      </section>
      <div hidden={tab !== "custom"}><Form layout="vertical" form={form} onFinish={(values) => void save(values)} disabled={busy}>
        <div className="workspace-section-heading"><b>{editingId ? "编辑技能" : "新增技能"}</b></div>
        <div className="workspace-skill-fields">
          <Form.Item name="name" label="名称" rules={[{ required: true, min: 2, max: 64 }]}><Input /></Form.Item>
          <Form.Item name="category" label="分类" initialValue="自定义" rules={[{ required: true, max: 32 }]}><Input /></Form.Item>
        </div>
        <Form.Item name="description" label="说明" rules={[{ required: true, min: 2, max: 8000 }]}><Input.TextArea autoSize={{ minRows: 2, maxRows: 6 }} /></Form.Item>
        <Form.Item name="instruction" label="技能指令" rules={[{ required: true, min: 10, max: 64000 }]}><Input.TextArea autoSize={{ minRows: 5, maxRows: 10 }} /></Form.Item>
        <Form.Item name="quick_prompts" label="快捷指令"><Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} /></Form.Item>
        <Button htmlType="submit" type="primary" loading={busy}>保存技能</Button>
      </Form></div>
    </div>
  </Modal>;
}
