import { useRef, useState } from "react";
import { Alert, Button, Empty, Form, Input, Modal, Space, Switch, Tooltip, message } from "antd";
import { DeleteOutlined, EditOutlined, GithubOutlined, PlusOutlined, UploadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText, type WorkspaceSkill } from "./types";
import "./workspace-context.css";

type Props = { open: boolean; onClose: () => void; skills: WorkspaceSkill[]; refresh: () => Promise<void>; onSelect: (id: string) => void };
type GithubPreview = { name: string; description: string; instruction: string; source: string; sha256: string; url: string };
function githubSourceUrl(source?: string) {
  if (!source) return null;
  try { const url = new URL(source); return url.protocol === "https:" && url.hostname === "github.com" && !url.username && !url.password && url.pathname.split("/").filter(Boolean).length >= 2 ? url.href : null; }
  catch { return null; }
}

export function SkillManager({ open, onClose, skills, refresh, onSelect }: Props) {
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState("");
  const [busy, setBusy] = useState(false);
  const [githubUrl, setGithubUrl] = useState("");
  const [githubPreview, setGithubPreview] = useState<GithubPreview | null>(null);
  const [githubError, setGithubError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const reset = () => { setEditingId(""); form.resetFields(); };
  const previewGithub = async () => {
    setBusy(true); setGithubError(""); setGithubPreview(null);
    try { const { data } = await api.post<GithubPreview>("/agent/skills/github/preview", { url: githubUrl.trim() }); setGithubPreview(data); }
    catch (error) { setGithubError(errorText(error, "GitHub 技能预览失败")); }
    finally { setBusy(false); }
  };
  const installGithub = async () => {
    if (!githubPreview) return;
    setBusy(true); setGithubError("");
    try {
      const { data } = await api.post<WorkspaceSkill>("/agent/skills/github/install", { url: githubPreview.url, sha256: githubPreview.sha256 });
      await refresh(); setGithubPreview(null); setGithubUrl("");
      if (data.available) { onSelect(data.id); message.success("技能已安装并选中"); }
      else { message.info("该技能已存在但已停用，请启用后使用；当前选择保持不变"); }
    } catch (error) { setGithubError(errorText(error, "GitHub 技能安装失败，请重新预览后再试")); }
    finally { setBusy(false); }
  };
  const save = async (values: Record<string, string>) => {
    setBusy(true);
    try {
      const payload = { ...values, quick_prompts: (values.quick_prompts || "").split(/\r?\n/).map((value) => value.trim()).filter(Boolean) };
      if (editingId) await api.patch(`/agent/skills/${editingId}`, payload);
      else { const { data } = await api.post("/agent/skills", payload); onSelect(data.id); }
      await refresh(); reset(); message.success("技能已保存");
    } catch (error) { message.error(errorText(error, "技能保存失败")); }
    finally { setBusy(false); }
  };
  const upload = async (file?: File) => {
    if (!file) return;
    setBusy(true);
    try {
      const body = new FormData(); body.append("file", file);
      const { data } = await api.post("/agent/skills/upload", body);
      await refresh(); onSelect(data.id); message.success("技能已上传并选中");
    } catch (error) { message.error(errorText(error, "技能上传失败")); }
    finally { setBusy(false); if (fileRef.current) fileRef.current.value = ""; }
  };
  const toggle = async (skill: WorkspaceSkill, enabled: boolean) => {
    setBusy(true);
    try { await api.patch(`/agent/skills/${skill.id}`, { enabled }); await refresh(); }
    catch (error) { message.error(errorText(error, "技能更新失败")); }
    finally { setBusy(false); }
  };
  const remove = (skill: WorkspaceSkill) => Modal.confirm({ title: `删除“${skill.name}”？`, okText: "删除", cancelText: "取消", okButtonProps: { danger: true }, onOk: async () => {
    try { await api.delete(`/agent/skills/${skill.id}`); await refresh(); if (editingId === skill.id) reset(); }
    catch (error) { message.error(errorText(error, "技能删除失败")); throw error; }
  } });
  return <Modal open={open} title="技能" width={760} footer={null} className="workspace-skill-modal" maskClosable={!busy} closable={!busy} onCancel={() => { if (busy) return; onClose(); reset(); setGithubPreview(null); setGithubError(""); }}>
    <div className="workspace-skill-manager">
      <section className="workspace-github-install" aria-label="从 GitHub 安装技能">
        <div className="workspace-section-heading"><b><GithubOutlined /> 从 GitHub 安装</b></div>
        <p>粘贴公开 GitHub 技能目录或 SKILL.md 链接，先查看指令，再确认安装到你的个人技能。仅导入 SKILL.md 作为 OA 技能指令，仓库中的脚本和 references 不会自动执行。</p>
        <div className="workspace-github-url">
          <Input aria-label="GitHub 技能链接" placeholder="https://github.com/owner/repo/tree/main/skills/example" value={githubUrl} disabled={busy} onChange={(event) => { setGithubUrl(event.target.value); setGithubPreview(null); setGithubError(""); }} onPressEnter={() => { if (!busy && githubUrl.trim()) void previewGithub(); }} />
          <Button icon={<GithubOutlined />} loading={busy} disabled={!githubUrl.trim() || busy} onClick={() => void previewGithub()}>预览技能</Button>
        </div>
        {githubError && <Alert type="error" showIcon message={githubError} />}
        {githubPreview && <div className="workspace-github-preview">
          <h3>{githubPreview.name}</h3><p>{githubPreview.description}</p>
          <a href={githubPreview.source} target="_blank" rel="noopener noreferrer">来源：{githubPreview.source}</a>
          <span className="workspace-skill-hash">SHA256：{githubPreview.sha256}</span>
          <b>完整技能指令</b><pre tabIndex={0}>{githubPreview.instruction}</pre>
          <p>确认后加入个人技能。技能会参与 AI 回答，请先检查完整指令及来源。</p>
          <Button type="primary" loading={busy} disabled={busy} onClick={() => void installGithub()}>确认安装并选中</Button>
        </div>}
      </section>
      <section className="workspace-skill-list">
        <div className="workspace-section-heading"><b>自定义技能</b><Space size={4}>
          <input hidden ref={fileRef} type="file" accept=".json,.md,.markdown,.docx" onChange={(event) => void upload(event.target.files?.[0])} />
          <Tooltip title="上传 Markdown、JSON 或 Word 技能"><Button icon={<UploadOutlined />} disabled={busy} onClick={() => fileRef.current?.click()}>上传</Button></Tooltip>
          <Tooltip title="新增技能"><Button icon={<PlusOutlined />} disabled={busy} onClick={reset} aria-label="新增技能" /></Tooltip>
        </Space></div>
        {skills.filter((skill) => skill.custom).map((skill) => <div className="workspace-skill-row" key={skill.id}>
          <div><b>{skill.name}</b><p>{skill.description}</p>{githubSourceUrl(skill.source) ? <a className="workspace-skill-source" href={githubSourceUrl(skill.source)!} target="_blank" rel="noopener noreferrer">GitHub 来源：{skill.source}</a> : skill.source && <span className="workspace-skill-source">来源：{skill.source.startsWith("user-upload") ? "本地上传" : skill.source === "user-custom" ? "手工创建" : skill.source}</span>}</div><Space size={2} wrap>
            <Button size="small" disabled={busy || !skill.available} onClick={() => { onSelect(skill.id); onClose(); }}>使用</Button>
            <label className="workspace-skill-toggle"><Switch size="small" checked={skill.available} disabled={busy} onChange={(value) => void toggle(skill, value)} aria-label={`启用${skill.name}`} /></label>
            <Tooltip title="编辑技能"><Button type="text" icon={<EditOutlined />} disabled={busy} aria-label="编辑技能" onClick={() => { setEditingId(skill.id); form.setFieldsValue({ ...skill, quick_prompts: skill.quick_prompts.join("\n") }); }} /></Tooltip>
            <Tooltip title="删除技能"><Button type="text" danger icon={<DeleteOutlined />} disabled={busy} aria-label="删除技能" onClick={() => remove(skill)} /></Tooltip>
          </Space>
        </div>)}
        {!skills.some((skill) => skill.custom) && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无自定义技能" />}
      </section>
      <Form layout="vertical" form={form} onFinish={(values) => void save(values)} disabled={busy}>
        <div className="workspace-section-heading"><b>{editingId ? "编辑技能" : "新增技能"}</b></div>
        <div className="workspace-skill-fields">
          <Form.Item name="name" label="名称" rules={[{ required: true, min: 2, max: 64 }]}><Input /></Form.Item>
          <Form.Item name="category" label="分类" initialValue="自定义" rules={[{ required: true, max: 32 }]}><Input /></Form.Item>
        </div>
        <Form.Item name="description" label="说明" rules={[{ required: true, min: 2, max: 500 }]}><Input /></Form.Item>
        <Form.Item name="instruction" label="技能指令" rules={[{ required: true, min: 10, max: 6000 }]}><Input.TextArea autoSize={{ minRows: 5, maxRows: 10 }} /></Form.Item>
        <Form.Item name="quick_prompts" label="快捷指令"><Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} /></Form.Item>
        <Button htmlType="submit" type="primary" loading={busy}>保存技能</Button>
      </Form>
    </div>
  </Modal>;
}
