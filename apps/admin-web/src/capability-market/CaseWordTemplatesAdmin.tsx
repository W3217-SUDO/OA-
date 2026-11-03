import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button, Empty, Input, Modal, Space, Switch, Tag, message } from "antd";
import { DeleteOutlined, DownloadOutlined, EditOutlined, FileWordOutlined, ReloadOutlined, UploadOutlined } from "@ant-design/icons";
import { api } from "../api";
import type { WordTemplate } from "../legal/CaseWordTemplateModal";
import "./dsh-plugin-center.css";

// 陶国南 11-03：管理员上传 Word 模板（用 {字段} 标出要替换的地方），可以替换文件、停用、维护常用选项；删除只做逻辑删除。
type Listing = { items: WordTemplate[]; can_manage: boolean; auto_fields: string[] };

const errorText = (failure: unknown, fallback: string) => {
  const detail = (failure as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
};

export function CaseWordTemplatesAdmin({ active }: { active: boolean }) {
  const [state, setState] = useState<Listing | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [optionsFor, setOptionsFor] = useState<WordTemplate | null>(null);
  const [optionText, setOptionText] = useState<Record<string, string>>({});
  const replaceInput = useRef<HTMLInputElement>(null);
  const replaceTarget = useRef<WordTemplate | null>(null);

  const load = useCallback(async () => {
    setError("");
    try { setState((await api.get<Listing>("/case-word-templates")).data); }
    catch (failure) { setError(errorText(failure, "文书模板加载失败")); }
  }, []);
  useEffect(() => { if (active) void load(); }, [active, load]);

  const run = async (key: string, action: () => Promise<unknown>, done: string) => {
    setBusy(key); setError("");
    try { await action(); message.success(done); await load(); return true; }
    catch (failure) { setError(errorText(failure, "操作未完成")); return false; }
    finally { setBusy(""); }
  };
  const upload = async () => {
    if (!file || !name.trim()) return;
    const form = new FormData(); form.append("name", name.trim()); form.append("file", file);
    if (await run("create", () => api.post("/case-word-templates", form), "模板已上传")) { setCreating(false); setName(""); setFile(null); }
  };
  const replace = async (target: WordTemplate, next: File) => {
    const form = new FormData(); form.append("file", next);
    await run(target.id, () => api.put(`/case-word-templates/${target.id}/file`, form), "模板文件已替换，旧文件保留");
  };
  const download = async (item: WordTemplate) => {
    try {
      const response = await api.get(`/case-word-templates/${item.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data), link = document.createElement("a");
      link.href = url; link.download = `${item.name}-模板.docx`; link.click(); URL.revokeObjectURL(url);
    } catch { message.error("下载失败"); }
  };
  const openOptions = (item: WordTemplate) => {
    setOptionsFor(item);
    const manual = item.fields.filter(field => !state?.auto_fields.includes(field));
    setOptionText(Object.fromEntries(manual.map(field => [field, (item.options[field] || []).join("\n")])));
  };
  const saveOptions = async () => {
    if (!optionsFor) return;
    const options = Object.fromEntries(Object.entries(optionText).map(([key, text]) => [key, text.split("\n").map(line => line.trim()).filter(Boolean)]));
    if (await run(optionsFor.id, () => api.patch(`/case-word-templates/${optionsFor.id}`, { options }), "常用选项已保存")) setOptionsFor(null);
  };
  const remove = (item: WordTemplate) => Modal.confirm({
    title: `删除“${item.name}”？`, content: "删除后案件里不再能选这个模板；已生成的文书不受影响，模板文件保留。", okText: "删除", cancelText: "取消",
    okButtonProps: { danger: true }, onOk: () => run(item.id, () => api.delete(`/case-word-templates/${item.id}`), "模板已删除"),
  });
  const canManage = !!state?.can_manage;

  return <section className="dsh-plugin-center" aria-label="文书模板">
    <header className="dsh-plugin-heading">
      <div><span className="dsh-plugin-eyebrow">CASE DOCUMENTS</span><h2><FileWordOutlined />文书模板</h2>
        <p>上传固定格式的 Word 文书，在要替换的地方写 {"{字段}"}，例如 {"{法院}{原告}{被告}{案由}{法院案号}{开庭律师}{生成日期}"}。
          案件里点“按模板生成文书”或说“生成撤诉申请书”，系统按案件信息替换字段，正文和格式不变。</p>
        {state && <p>系统自动带出的字段：{state.auto_fields.join("、")}。其他字段（如撤诉理由）由人选常用项或手填。</p>}</div>
      <Space wrap>
        <Button icon={<ReloadOutlined />} disabled={!!busy} onClick={() => void load()}>刷新</Button>
        {canManage && <Button type="primary" icon={<UploadOutlined />} disabled={!!busy} onClick={() => setCreating(true)}>上传模板</Button>}
      </Space>
    </header>
    {state && !canManage && <Alert type="info" showIcon title="只有管理员可以上传和修改文书模板。" />}
    {error && <Alert type="error" showIcon title={error} />}
    {state && !state.items.length && <Empty description="还没有文书模板" />}
    <input ref={replaceInput} hidden type="file" accept=".docx" onChange={event => {
      const next = event.target.files?.[0]; event.target.value = "";
      if (next && replaceTarget.current) void replace(replaceTarget.current, next);
    }} />
    <div className="dsh-provider-list">{state?.items.map(item => <article key={item.id}>
      <div className="dsh-plugin-info">
        <div className="dsh-plugin-title"><strong>{item.name}</strong>{item.builtin && <Tag>内置</Tag>}
          <Tag color={item.is_active ? "success" : "default"}>{item.is_active ? "启用" : "已停用"}</Tag></div>
        <p>字段：{item.fields.map(field => <Tag key={field} color={state.auto_fields.includes(field) ? "blue" : "orange"}>{field}</Tag>)}</p>
      </div>
      {canManage && <Space wrap>
        <Switch aria-label={`${item.name}启用状态`} checked={item.is_active} loading={busy === item.id} disabled={!!busy}
          onChange={checked => void run(item.id, () => api.patch(`/case-word-templates/${item.id}`, { is_active: checked }), checked ? "已启用" : "已停用")} />
        <Button icon={<EditOutlined />} disabled={!!busy} onClick={() => openOptions(item)}>常用选项</Button>
        <Button icon={<UploadOutlined />} disabled={!!busy} onClick={() => { replaceTarget.current = item; replaceInput.current?.click(); }}>替换文件</Button>
        <Button icon={<DownloadOutlined />} onClick={() => void download(item)}>下载</Button>
        {!item.builtin && <Button danger icon={<DeleteOutlined />} disabled={!!busy} onClick={() => remove(item)}>删除</Button>}
      </Space>}
    </article>)}</div>
    <Modal title="上传文书模板" open={creating} okText="上传" cancelText="取消" confirmLoading={busy === "create"}
      okButtonProps={{ disabled: !file || !name.trim() }} onOk={() => void upload()} onCancel={() => setCreating(false)} destroyOnHidden>
      <Space direction="vertical" style={{ width: "100%" }}>
        <Input placeholder="模板名称，例如：民事起诉状" value={name} maxLength={60} onChange={event => setName(event.target.value)} />
        <input type="file" accept=".docx" onChange={event => setFile(event.target.files?.[0] || null)} />
        <small>只支持 .docx；.doc 请先在 Word 里另存为 .docx。</small>
      </Space>
    </Modal>
    <Modal title={`常用选项：${optionsFor?.name || ""}`} open={!!optionsFor} okText="保存" cancelText="取消" confirmLoading={!!optionsFor && busy === optionsFor.id}
      onOk={() => void saveOptions()} onCancel={() => setOptionsFor(null)} destroyOnHidden>
      {Object.keys(optionText).length ? Object.keys(optionText).map(field => <div key={field} style={{ marginBottom: 12 }}>
        <strong>{field}</strong><small>（每行一个，生成时可以直接选）</small>
        <Input.TextArea autoSize={{ minRows: 3, maxRows: 8 }} value={optionText[field]}
          onChange={event => setOptionText(current => ({ ...current, [field]: event.target.value }))} />
      </div>) : <Empty description="这个模板的字段都由系统从案件带出，不需要常用选项" />}
    </Modal>
  </section>;
}
