import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button, Empty, Input, Modal, Select, Space, Switch, Tag, message } from "antd";
import { DeleteOutlined, DownloadOutlined, EditOutlined, FileWordOutlined, ReloadOutlined, UploadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { POPUP_WIDTH } from "../components/common/popupSize";
import type { WordTemplate, WordTemplateSlot } from "../legal/caseWordTemplateMatch";
import "./dsh-plugin-center.css";

// 陶国南 11-03：管理员上传 Word 范本：带下划线的文字是要替换的地方，后面括号写说明；系统识别后列出“字段 → 案件里哪一项”，
// 对不上的可以改或设成生成时手填。可以替换文件、停用、维护常用选项；删除只做逻辑删除。
type Mapping = Record<string, { source: "case" | "manual"; field?: string; label?: string }>;
const MANUAL = "__manual__";
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
  const [mappingFor, setMappingFor] = useState<WordTemplate | null>(null);
  const [mapping, setMapping] = useState<Mapping>({});
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
    let created: WordTemplate | null = null;
    if (await run("create", async () => { created = (await api.post<WordTemplate>("/case-word-templates", form)).data; }, "模板已上传，请核对识别到的字段")) {
      setCreating(false); setName(""); setFile(null);
      if (created) openMapping(created);
    }
  };
  const replace = async (target: WordTemplate, next: File) => {
    const form = new FormData(); form.append("file", next);
    let replaced: WordTemplate | null = null;
    if (await run(target.id, async () => { replaced = (await api.put<WordTemplate>(`/case-word-templates/${target.id}/file`, form)).data; },
      "模板文件已替换，旧文件保留，请核对识别到的字段") && replaced) openMapping(replaced);
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
    const manual = (item.slots || []).filter(slot => slot.source === "manual").map(slot => slot.key).filter((key, index, all) => all.indexOf(key) === index);
    setOptionText(Object.fromEntries(manual.map(field => [field, (item.options[field] || []).join("\n")])));
  };
  const saveOptions = async () => {
    if (!optionsFor) return;
    const options = Object.fromEntries(Object.entries(optionText).map(([key, text]) => [key, text.split("\n").map(line => line.trim()).filter(Boolean)]));
    if (await run(optionsFor.id, () => api.patch(`/case-word-templates/${optionsFor.id}`, { options }), "常用选项已保存")) setOptionsFor(null);
  };
  const openMapping = (item: WordTemplate) => {
    setMappingFor(item);
    setMapping(Object.fromEntries((item.slots || []).filter(slot => slot.kind === "underline").map(slot => [String(slot.index),
      slot.source === "case" ? { source: "case" as const, field: slot.key } : { source: "manual" as const, label: slot.key }])));
  };
  const saveMapping = async () => {
    if (!mappingFor) return;
    if (await run(mappingFor.id, () => api.patch(`/case-word-templates/${mappingFor.id}`, { mapping }), "字段对应已保存")) setMappingFor(null);
  };
  const slotLabel = (slot: WordTemplateSlot) => slot.kind === "placeholder" ? slot.sample : `${slot.sample || "（空）"}${slot.note ? `（${slot.note}）` : ""}`;
  const remove = (item: WordTemplate) => Modal.confirm({
    title: `删除“${item.name}”？`, content: "删除后案件里不再能选这个模板；已生成的文书不受影响，模板文件保留。", okText: "删除", cancelText: "取消",
    okButtonProps: { danger: true }, onOk: () => run(item.id, () => api.delete(`/case-word-templates/${item.id}`), "模板已删除"),
  });
  const canManage = !!state?.can_manage;

  return <section className="dsh-plugin-center" aria-label="文书模板">
    <header className="dsh-plugin-heading">
      <div><span className="dsh-plugin-eyebrow">CASE DOCUMENTS</span><h2><FileWordOutlined />文书模板</h2>
        <p>上传固定格式的 Word 范本：要替换的文字加下划线，紧跟着用括号写说明，例如“<u>上海市浦东新区人民法院</u>（哪个法院）”。
          系统自动识别并对应到案件信息，对不上的可以改。案件里点“按模板生成文书”或说“生成撤诉申请书”时，下划线换成案件信息、去掉下划线，
          括号说明删掉，其他文字和格式不变。</p>
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
        <p>字段：{item.fields.map(field => <Tag key={field} color={(item.slots || []).some(slot => slot.key === field && slot.source === "manual") ? "orange" : "blue"}>{field}</Tag>)}</p>
      </div>
      {canManage && <Space wrap>
        <Switch aria-label={`${item.name}启用状态`} checked={item.is_active} loading={busy === item.id} disabled={!!busy}
          onChange={checked => void run(item.id, () => api.patch(`/case-word-templates/${item.id}`, { is_active: checked }), checked ? "已启用" : "已停用")} />
        <Button icon={<EditOutlined />} disabled={!!busy} onClick={() => openMapping(item)}>核对字段</Button>
        <Button disabled={!!busy} onClick={() => openOptions(item)}>常用选项</Button>
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
    <Modal title={`核对字段：${mappingFor?.name || ""}`} open={!!mappingFor} okText="保存" cancelText="取消" width={POPUP_WIDTH.md}
      confirmLoading={!!mappingFor && busy === mappingFor.id} onOk={() => void saveMapping()} onCancel={() => setMappingFor(null)} destroyOnHidden>
      <p>左边是模板里识别到的下划线文字和括号说明，右边选它对应案件里的哪一项；案件里没有的选“生成时手填”，并写一个名称（如撤诉理由）。</p>
      <div className="case-word-mapping">
        {(mappingFor?.slots || []).map((slot, position) => {
          if (slot.kind === "placeholder") return <div key={`p-${position}`} className="case-word-mapping-row"><span>{slotLabel(slot)}</span><Tag>{slot.key}</Tag></div>;
          const current = mapping[String(slot.index)] || { source: "manual" as const, label: slot.note };
          return <div key={String(slot.index)} className="case-word-mapping-row">
            <span title={slotLabel(slot)}>{slotLabel(slot)}</span>
            <Select value={current.source === "case" ? current.field : MANUAL} aria-label={`${slotLabel(slot)}对应`}
              options={[...(state?.auto_fields || []).map(field => ({ value: field, label: field })), { value: MANUAL, label: "生成时手填" }]}
              onChange={value => setMapping(all => ({ ...all, [String(slot.index)]: value === MANUAL ? { source: "manual", label: slot.note || slot.sample } : { source: "case", field: value } }))} />
            {current.source === "manual" && <Input value={current.label} placeholder="手填字段名称" maxLength={20}
              onChange={event => setMapping(all => ({ ...all, [String(slot.index)]: { source: "manual", label: event.target.value } }))} />}
          </div>;
        })}
      </div>
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
