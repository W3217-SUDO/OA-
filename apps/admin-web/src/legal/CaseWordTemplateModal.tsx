import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Alert, AutoComplete, Button, Empty, Input, Modal, Select, Space, Tag, message } from "antd";
import { DownloadOutlined, ReloadOutlined, SaveOutlined } from "@ant-design/icons";
import { api } from "../api";
import { POPUP_WIDTH } from "../components/common/popupSize";

// 陶国南 11-03：按固定模板生成文书。字段由系统从案件取，缺的让人补；正文只替换字段，不经智能体改写。
import { matchWordTemplate, type WordTemplate } from "./caseWordTemplateMatch";

export { matchWordTemplate, type WordTemplate };
// optional：可以留空（如调解协议书的调解员、付款期限，打印后手写）；derived：由别的字段算出（赔偿金额大写），不单独填；multiline：多个当事人逐行列出。
type Field = { key: string; value: string; source: "case" | "manual"; missing: boolean; options: string[]; optional?: boolean; derived?: boolean; multiline?: boolean };
// 陶国南 11-05 10:34：单位当事人缺法定代表人等信息时，企业信息库没有的会在下载或生成时查企查查（每家扣一次），预览里先提示。
type EnterpriseLookup = { message?: string; pending?: string[]; charged?: string[]; failed?: string[] };
type Preview = { fields: Field[]; missing: string[]; paragraphs: string[]; filename: string; enterprise_lookup?: EnterpriseLookup };

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

  const edited = useMemo(() => Object.fromEntries((preview?.fields || []).filter(field => !field.derived).map(field => [field.key, values[field.key] ?? field.value])), [preview, values]);
  const missing = (preview?.fields || []).filter(field => !field.optional && !field.derived && !String(edited[field.key] || "").trim()).map(field => field.key);

  const download = async () => {
    setBusy("download");
    try {
      const response = await api.post(`${base}/download`, { values: edited }, { responseType: "blob" });
      const url = URL.createObjectURL(response.data), link = document.createElement("a");
      link.href = url; link.download = preview?.filename || "文书.docx"; link.click(); URL.revokeObjectURL(url);
      // 下载时查过企查查的单位已存进企业信息库，刷新预览让页面也显示查到的信息。
      if (preview?.enterprise_lookup?.pending?.length) void refresh(edited);
    } catch { message.error("下载失败，请先补齐字段"); }
    finally { setBusy(""); }
  };
  const save = async () => {
    setBusy("save");
    try {
      const { data } = await api.post<{ enterprise_lookup?: EnterpriseLookup }>(`${base}/generate`, { values: edited });
      message.success("已保存到案件空间文档");
      if (data?.enterprise_lookup?.message) message.info(data.enterprise_lookup.message);
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
            <span>{field.key} {field.derived ? <Tag>自动生成</Tag> : field.optional ? <Tag>可留空</Tag>
              : <Tag color={field.source === "case" ? "blue" : "orange"}>{field.source === "case" ? "案件信息" : "需填写"}</Tag>}</span>
            {field.derived
              ? <Input value={field.value} disabled placeholder="随上面的金额自动生成，刷新预览后更新" />
              : field.multiline
              ? <Input.TextArea value={edited[field.key]} autoSize={{ minRows: 2, maxRows: 6 }} placeholder="每位当事人一行"
                  onChange={event => setValues(current => ({ ...current, [field.key]: event.target.value }))} />
              : field.options.length
              ? <AutoComplete value={edited[field.key]} options={field.options.map(value => ({ value }))} placeholder={`选常用项或直接填写${field.key}`}
                  onChange={value => setValues(current => ({ ...current, [field.key]: value }))} />
              : <Input value={edited[field.key]} placeholder={field.optional ? "可以留空，打印后手写" : field.source === "case" ? "案件里没有填写，请补充" : `请填写${field.key}`}
                  onChange={event => setValues(current => ({ ...current, [field.key]: event.target.value }))} />}
          </label>)}
        </div>
        {!!missing.length && <Alert type="warning" showIcon title={`还缺：${missing.join("、")}`} />}
        {preview.enterprise_lookup?.message && <Alert type="info" showIcon title={preview.enterprise_lookup.message} />}
        <div className="case-word-template-preview-head"><strong>预览</strong>
          <Button size="small" icon={<ReloadOutlined />} loading={busy === "preview"} onClick={() => void refresh(edited)}>按上面的字段刷新预览</Button></div>
        <div className="case-word-template-preview" aria-label="文书预览">
          {preview.paragraphs.map((text, index) => <p key={index}>{text || " "}</p>)}
        </div>
      </>}
    </div>
  </Modal>;
}
