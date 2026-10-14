import { useEffect, useRef, useState } from "react";
import { isAxiosError } from "axios";
import { Alert, Button, Form, Input, Modal, message } from "antd";
import { BoldOutlined, ItalicOutlined, OrderedListOutlined, RedoOutlined, ReloadOutlined, UndoOutlined, UnorderedListOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "./types";
import type { PersonalAiDocument, PersonalAiFile, PersonalAiFileEditResult } from "./personalAiSpaceApi";
import { personalHtmlToMarkdown, personalMarkdownToHtml, sanitizePersonalEditorHtml } from "./personalAiDocumentCodec";

function isDefiniteSaveRejection(failure: unknown): boolean {
  if (!isAxiosError(failure) || !failure.response) return false;
  const { status, data } = failure.response;
  // 后端前置拒绝只有字符串 detail；写入计划失败的结构化响应不能允许重写。
  return status >= 400 && status < 500 && data !== null && typeof data === "object"
    && !Array.isArray(data) && typeof data.detail === "string"
    && Object.keys(data).length === 1;
}

function RichTextEditor({ value, onChange, onError, disabled }: { value: string; onChange: (value: string) => void; onError: (value: string) => void; disabled: boolean }) {
  const editorRef = useRef<HTMLDivElement>(null);
  const lastValue = useRef<string | null>(null);
  useEffect(() => {
    if (editorRef.current && value !== lastValue.current) {
      try {
        editorRef.current.innerHTML = personalMarkdownToHtml(value);
        lastValue.current = value;
        onError("");
      } catch (failure) { onError(errorText(failure, "文档格式无法在线编辑，原文件未修改")); }
    }
  }, [value, onError]);
  const update = () => {
    if (disabled) return;
    try {
      const content = personalHtmlToMarkdown(editorRef.current?.innerHTML || "");
      personalMarkdownToHtml(content);
      lastValue.current = content;
      onChange(content); onError("");
    } catch (failure) { onError(errorText(failure, "文档格式转换失败，原文件未修改")); }
  };
  const command = (name: string, argument?: string) => {
    if (disabled) return;
    editorRef.current?.focus();
    document.execCommand(name, false, argument);
    update();
  };
  return <div className="personal-ai-rich-editor">
    <div className="personal-ai-rich-toolbar" role="toolbar" aria-label="文档格式工具栏">
      <Button size="small" icon={<UndoOutlined />} aria-label="撤销" onMouseDown={(event) => event.preventDefault()} onClick={() => command("undo")} />
      <Button size="small" icon={<RedoOutlined />} aria-label="重做" onMouseDown={(event) => event.preventDefault()} onClick={() => command("redo")} />
      <span className="personal-ai-rich-divider" />
      <Button size="small" icon={<BoldOutlined />} aria-label="加粗" onMouseDown={(event) => event.preventDefault()} onClick={() => command("bold")} />
      <Button size="small" icon={<ItalicOutlined />} aria-label="斜体" onMouseDown={(event) => event.preventDefault()} onClick={() => command("italic")} />
      <Button size="small" icon={<UnorderedListOutlined />} aria-label="项目符号" onMouseDown={(event) => event.preventDefault()} onClick={() => command("insertUnorderedList")} />
      <Button size="small" icon={<OrderedListOutlined />} aria-label="编号列表" onMouseDown={(event) => event.preventDefault()} onClick={() => command("insertOrderedList")} />
      <Button size="small" onMouseDown={(event) => event.preventDefault()} onClick={() => command("formatBlock", "h2")}>标题</Button>
    </div>
    <div ref={editorRef} className="personal-ai-rich-content" contentEditable={!disabled} aria-disabled={disabled} role="textbox" aria-label="文档正文编辑区" suppressContentEditableWarning onInput={update} onPaste={event => {
      event.preventDefault();
      if (disabled) return;
      try {
        const html = event.clipboardData.getData("text/html");
        const safe = html ? sanitizePersonalEditorHtml(html) : personalMarkdownToHtml(event.clipboardData.getData("text/plain"));
        document.execCommand("insertHTML", false, safe); update();
      } catch (failure) { onError(errorText(failure, "粘贴内容格式不受支持，原文件未修改")); }
    }} onDrop={event => { event.preventDefault(); onError("不支持拖入富文本或文件，原文件未修改"); }} />
    <div className="personal-ai-rich-hint">支持直接排版、撤销重做、加粗、斜体和列表；保存会生成个人 AI 空间的新版本。</div>
  </div>;
}

type Props = {
  document: PersonalAiDocument;
  onClose: () => void;
  onBusy: (busy: boolean) => void;
  onVersionCreated: (file: PersonalAiFile) => void;
  onSaved: (file: PersonalAiFile, document: PersonalAiDocument) => void;
};

export function PersonalAiDocumentEditor({ document, onClose, onBusy, onVersionCreated, onSaved }: Props) {
  const [form] = Form.useForm<{ name: string; content: string }>();
  const [formatError, setFormatError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedFile, setSavedFile] = useState<PersonalAiFile | null>(null);
  const [readbackPending, setReadbackPending] = useState(false);
  const [submissionUncertain, setSubmissionUncertain] = useState(false);
  const operationLock = useRef(false);
  useEffect(() => {
    form.setFieldsValue({ name: document.name, content: document.content });
    setFormatError("");
  }, [document, form]);

  const readSavedVersion = async (file: PersonalAiFile) => {
    const { data } = await api.get<PersonalAiDocument>(`/personal-agent/ai-space/files/${encodeURIComponent(file.id)}/content`);
    if (data.id !== file.id || data.name !== file.name) throw new Error("新版本回读的文件标识不一致，请核对文件夹，未重复提交保存");
    // 编辑目标只在真实回读成功后切换，不能把原文件内容冒充新版本。
    onSaved(file, data);
    setReadbackPending(false); setSaveError("");
    message.success(`已保存并读取新版本：${file.name}，原文件保留`);
  };
  const retryReadback = async () => {
    if (!savedFile || operationLock.current) return;
    operationLock.current = true; setSaving(true); onBusy(true);
    try { await readSavedVersion(savedFile); }
    catch (failure) { setSaveError(errorText(failure, "新版本读取失败，当前草稿保留")); }
    finally { operationLock.current = false; setSaving(false); onBusy(false); }
  };
  const save = async () => {
    if (operationLock.current || readbackPending || submissionUncertain || formatError) return;
    operationLock.current = true;
    let submitted = false;
    let persisted: PersonalAiFile | null = null;
    try {
      const values = await form.validateFields();
      setSaving(true); onBusy(true); setSaveError("");
      submitted = true;
      const { data } = await api.post<PersonalAiFileEditResult>(`/personal-agent/ai-space/files/${encodeURIComponent(document.id)}/edit`, values);
      if (data.supersedes !== document.id || data.file.id === document.id || data.file.status !== "available") {
        throw new Error("保存返回的版本关系或文件状态异常，请核对文件夹，未重复提交保存");
      }
      persisted = data.file;
      setSavedFile(persisted); setReadbackPending(true);
      onVersionCreated(persisted);
      await readSavedVersion(persisted);
    } catch (failure) {
      if (submitted) {
        if (!persisted) setSubmissionUncertain(!isDefiniteSaveRejection(failure));
        setSaveError(errorText(failure, "文件保存请求未完成，请核对文件夹，当前草稿保留"));
      } else if (!(failure && typeof failure === "object" && "errorFields" in failure)) setSaveError(errorText(failure, "文档校验未完成"));
    } finally { operationLock.current = false; setSaving(false); onBusy(false); }
  };
  return <Modal open title={`在线编辑：${document.name}`} width={860} rootClassName="personal-ai-document-confirmation"
    okText="保存为新版本" cancelText="关闭" confirmLoading={saving}
    okButtonProps={{ disabled: !!formatError || readbackPending || submissionUncertain }} cancelButtonProps={{ disabled: saving }}
    closable={!saving} keyboard={!saving} maskClosable={!saving} onOk={() => void save()} onCancel={onClose} destroyOnHidden>
    <Alert type="info" showIcon title={savedFile && !readbackPending ? "正在编辑已保存的新版本，原文件未覆盖。" : "当前文件的修改将保存为新版本，原文件保留不覆盖。"}
      description={`当前编辑文件：${document.id}`} style={{ marginBottom: 12 }} />
    {readbackPending && <Alert type="warning" showIcon title="新版本已保存，尚未读取；当前草稿保留，请勿重复保存。" description={saveError}
      action={<Button icon={<ReloadOutlined />} loading={saving} onClick={() => void retryReadback()}>重新读取新版本</Button>} />}
    {saveError && !readbackPending && <Alert type="error" showIcon title="保存请求未完成，当前草稿保留" description={saveError} />}
    {formatError && <Alert type="error" showIcon title={formatError} />}
    <Form form={form} layout="vertical" disabled={saving || readbackPending || submissionUncertain}>
      <Form.Item name="name" label="文件名" rules={[{ required: true }, { pattern: /\.(docx|md|txt)$/i, message: "仅支持 .docx、.md、.txt" }]}><Input maxLength={255} /></Form.Item>
      <Form.Item name="content" label="文档正文" rules={[{ required: true, message: "请输入文档正文" }]}>
        {document.name.toLowerCase().endsWith(".txt") ? <Input.TextArea autoSize={{ minRows: 18, maxRows: 30 }} /> : <RichTextEditor value={form.getFieldValue("content") || ""} onChange={(content) => form.setFieldValue("content", content)} onError={setFormatError} disabled={saving || readbackPending || submissionUncertain} />}
      </Form.Item>
    </Form>
  </Modal>;
}
