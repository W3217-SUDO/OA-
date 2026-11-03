import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Alert, AutoComplete, Button, Empty, Input, Modal, Select, Space, Tag, message } from "antd";
import { DownloadOutlined, ReloadOutlined, SaveOutlined } from "@ant-design/icons";
import { api } from "../api";
import { POPUP_WIDTH } from "../components/common/popupSize";

// 陶国南 11-03：按固定模板生成文书。字段由系统从案件取，缺的让人补；正文只替换字段，不经智能体改写。
import { matchWordTemplate, type WordTemplate } from "./caseWordTemplateMatch";

export { matchWordTemplate, type WordTemplate };
type Field = { key: string; value: string; source: "case" | "manual"; missing: boolean; options: string[] };
type Preview = { fields: Field[]; missing: string[]; paragraphs: string[]; filename: string };

const errorText = (failure: unknown, fallback: string) => {
  const detail = (failure as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
};

export function CaseWordTemplateModal({ caseId, open, templateId, canSave, onClose, onSaved }: {
  caseId: number | null; open: boolean; templateId?: string; canSave: boolean; onClose: () => void; onSaved?: () => void;
}) {
  const [templates, setTemplates] = useState<WordTemplate[]>([]);
  const [selected, setSelected] = useState<string | undefined>(templateId);
  const [values, setValues] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const request = useRef(0);

  useEffect(() => {
    if (!open) return;
    setSelected(templateId); setValues({}); setPreview(null); setError("");
    api.get<{ items: WordTemplate[] }>("/case-word-templates")
      .then(({ data }) => setTemplates(data.items.filter(item => item.is_active)))
      .catch(failure => setError(errorText(failure, "文书模板加载失败")));
  }, [open, templateId]);

  const base = caseId ? `/cases/${caseId}/documents/word-templates/${selected}` : "";
  const refresh = useCallback(async (next: Record<string, string>) => {
    if (!caseId || !selected) return;
    const current = ++request.current;
    setBusy("preview"); setError("");
    try {
      const { data } = await api.post<Preview>(`${base}/preview`, { values: next });
      if (current === request.current) setPreview(data);
    } catch (failure) { if (current === request.current) setError(errorText(failure, "预览失败")); }
    finally { if (current === request.current) setBusy(""); }
  }, [base, caseId, selected]);
  useEffect(() => { if (open && selected) void refresh({}); }, [open, selected, refresh]);

  const edited = useMemo(() => Object.fromEntries((preview?.fields || []).map(field => [field.key, values[field.key] ?? field.value])), [preview, values]);
  const missing = (preview?.fields || []).filter(field => !String(edited[field.key] || "").trim()).map(field => field.key);

  const download = async () => {
    setBusy("download");
    try {
      const response = await api.post(`${base}/download`, { values: edited }, { responseType: "blob" });
      const url = URL.createObjectURL(response.data), link = document.createElement("a");
      link.href = url; link.download = preview?.filename || "文书.docx"; link.click(); URL.revokeObjectURL(url);
    } catch { message.error("下载失败，请先补齐字段"); }
    finally { setBusy(""); }
  };
  const save = async () => {
    setBusy("save");
    try {
      await api.post(`${base}/generate`, { values: edited });
      message.success("已保存到案件空间文档");
      onSaved?.();
      onClose();
    } catch (failure) { setError(errorText(failure, "保存失败")); }
    finally { setBusy(""); }
  };

  return <Modal title="按模板生成文书" open={open} onCancel={onClose} width={POPUP_WIDTH.lg} destroyOnHidden footer={<Space wrap>
    <Button onClick={onClose}>取消</Button>
    <Button icon={<DownloadOutlined />} loading={busy === "download"} disabled={!preview || !!missing.length || !!busy} onClick={() => void download()}>下载 Word</Button>
    {canSave && <Button type="primary" icon={<SaveOutlined />} loading={busy === "save"} disabled={!preview || !!missing.length || !!busy}
      onClick={() => void save()}>确认并保存到案件空间</Button>}
  </Space>}>
    <div className="case-word-template">
      <Select className="case-word-template-select" placeholder="选择文书模板" value={selected} onChange={value => { setSelected(value); setValues({}); }}
        options={templates.map(item => ({ value: item.id, label: item.name }))} notFoundContent="还没有可用的文书模板" />
      {error && <Alert type="error" showIcon title={error} />}
      {!selected && !error && <Empty description="选择一个模板后，系统会从案件信息带出字段" />}
      {preview && <>
        <p className="case-word-template-note">字段由系统从案件信息带出，可以修改；正文不会被改写，只替换这些字段。</p>
        <div className="case-word-template-fields">
          {preview.fields.map(field => <label key={field.key} className={missing.includes(field.key) ? "is-missing" : undefined}>
            <span>{field.key} <Tag color={field.source === "case" ? "blue" : "orange"}>{field.source === "case" ? "案件信息" : "需填写"}</Tag></span>
            {field.options.length
              ? <AutoComplete value={edited[field.key]} options={field.options.map(value => ({ value }))} placeholder={`选常用项或直接填写${field.key}`}
                  onChange={value => setValues(current => ({ ...current, [field.key]: value }))} />
              : <Input value={edited[field.key]} placeholder={field.source === "case" ? "案件里没有填写，请补充" : `请填写${field.key}`}
                  onChange={event => setValues(current => ({ ...current, [field.key]: event.target.value }))} />}
          </label>)}
        </div>
        {!!missing.length && <Alert type="warning" showIcon title={`还缺：${missing.join("、")}`} />}
        <div className="case-word-template-preview-head"><strong>预览</strong>
          <Button size="small" icon={<ReloadOutlined />} loading={busy === "preview"} onClick={() => void refresh(edited)}>按上面的字段刷新预览</Button></div>
        <div className="case-word-template-preview" aria-label="文书预览">
          {preview.paragraphs.map((text, index) => <p key={index}>{text || " "}</p>)}
        </div>
      </>}
    </div>
  </Modal>;
}
