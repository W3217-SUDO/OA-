import { useEffect, useState } from "react";
import { Alert, Button, Drawer, Form, Input, Modal, Pagination, Spin, Tooltip, message } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "./types";
import { PersonalAiSpaceFiles } from "./PersonalAiSpaceFiles";
import { AttachmentPreviewContent, type PreviewAttachment } from "../components/common/AttachmentContent";
import { downloadPersonalAiFile, type PersonalAiFile, type PersonalAiFilePage, type PersonalAiSpaceInfo } from "./personalAiSpaceApi";
import "./personal-ai-space.css";

type Props = {
  open: boolean;
  onClose: () => void;
  revision: number;
  busy: boolean;
  onOpenConversation: (id: string) => Promise<unknown>;
  onSkillsChanged?: () => Promise<unknown>;
};

export function PersonalAiSpace({ open, onClose, revision, busy, onOpenConversation }: Props) {
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const [space, setSpace] = useState<PersonalAiSpaceInfo | null>(null);
  const [files, setFiles] = useState<PersonalAiFilePage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState("");
  const [preview, setPreview] = useState<PreviewAttachment | null>(null);
  const [editor, setEditor] = useState<{ id: string; name: string; content: string } | null>(null);
  const [editorSaving, setEditorSaving] = useState(false);
  const [editForm] = Form.useForm<{ name: string; content: string }>();
  const close = () => { setPage(1); setSpace(null); onClose(); };
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setLoading(true); setError(""); setFiles(null);
    void Promise.all([
      api.get<PersonalAiSpaceInfo>("/personal-agent/ai-space", { signal: controller.signal }).then((info) => { if (!controller.signal.aborted) setSpace(info.data); }),
      api.get<PersonalAiFilePage>("/personal-agent/ai-space/files", { params: { page, page_size: 20 }, signal: controller.signal }),
    ]).then(([, list]) => {
      if (!controller.signal.aborted) setFiles(list.data);
    }).catch((failure) => { if (!controller.signal.aborted) setError(errorText(failure, "个人 AI 空间加载失败")); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [open, page, refresh, revision]);
  const download = async (file: PersonalAiFile) => {
    if (downloadingId) return;
    setDownloadingId(file.id); setError("");
    try { await downloadPersonalAiFile(file); }
    catch (failure) { setError(errorText(failure, "文件下载失败")); }
    finally { setDownloadingId(""); }
  };
  const openPreview = async (file: PersonalAiFile) => {
    setError("");
    try {
      const suffix = file.name.toLowerCase().split(".").pop() || "";
      if (["md", "txt"].includes(suffix)) {
        const { data } = await api.get<{ content: string }>(`/personal-agent/ai-space/files/${encodeURIComponent(file.id)}/content`);
        setPreview({ name: file.name, kind: "text", text: data.content });
        return;
      }
      const { data } = await api.get<Blob>(`/personal-agent/ai-space/files/${encodeURIComponent(file.id)}/download`, { responseType: "blob" });
      const kind = suffix === "docx" ? "docx" : suffix === "pdf" ? "pdf" : suffix === "xlsx" || suffix === "xls" ? "xlsx" : ["png", "jpg", "jpeg", "gif", "webp"].includes(suffix) ? "image" : "unsupported";
      if (kind === "unsupported") { setPreview({ name: file.name, kind, text: "当前格式暂不支持在线查看，请下载后查看。" }); return; }
      setPreview({ name: file.name, kind, blob: data, url: URL.createObjectURL(data) });
    } catch (failure) { setError(errorText(failure, "文件在线查看失败")); }
  };
  const openEditor = async (file: PersonalAiFile) => {
    setError("");
    try {
      const { data } = await api.get<{ id: string; name: string; content: string }>(`/personal-agent/ai-space/files/${encodeURIComponent(file.id)}/content`);
      editForm.setFieldsValue({ name: data.name, content: data.content });
      setEditor(data);
    } catch (failure) { setError(errorText(failure, "文件在线编辑加载失败")); }
  };
  const saveEditor = async () => {
    if (!editor) return;
    const values = await editForm.validateFields();
    setEditorSaving(true);
    try {
      await api.post(`/personal-agent/ai-space/files/${encodeURIComponent(editor.id)}/edit`, values);
      message.success("已保存为个人 AI 空间新版本，原文件已保留");
      setEditor(null); editForm.resetFields(); setRefresh((value) => value + 1);
    } catch (failure) { message.error(errorText(failure, "文件保存失败")); }
    finally { setEditorSaving(false); }
  };
  const openConversation = async (id: string) => {
    setError("");
    try { await onOpenConversation(id); close(); }
    catch (failure) { setError(errorText(failure, "来源会话不可用")); }
  };
  return <Drawer
    open={open}
    onClose={close}
    width={760}
    destroyOnHidden
    rootClassName="personal-ai-space-drawer"
    title={<span className="personal-ai-space-title">{space ? `${space.owner_name}的个人 AI 空间` : "个人 AI 空间"}</span>}
  >
    <div className="personal-ai-space-content">
      <div className="personal-ai-space-toolbar"><Tooltip title="刷新个人 AI 空间"><Button icon={<ReloadOutlined />} aria-label="刷新个人 AI 空间" loading={loading} onClick={() => setRefresh((value) => value + 1)} /></Tooltip>{files && <span>共 {files.total} 个文件</span>}</div>
      {space && !space.configured && <Alert type="warning" showIcon title="OSS 尚未配置，不能保存新文件" />}
      {error && <Alert type="error" showIcon title="个人 AI 空间操作未完成" description={error} />}
      {loading ? <Spin /> : files && <PersonalAiSpaceFiles items={files.items} downloadingId={downloadingId} busy={busy} onDownload={(file) => void download(file)} onView={(file) => void openPreview(file)} onEdit={(file) => void openEditor(file)} onConversation={(id) => void openConversation(id)} />}
      {files && files.total > 0 && <Pagination simple current={files.page} pageSize={files.page_size} total={files.total} disabled={loading} showSizeChanger={false} onChange={setPage} />}
    </div>
    <Modal open={!!preview} title={`在线查看：${preview?.name || ""}`} width={preview?.kind === "pdf" ? 1000 : 860} footer={<Button onClick={() => { if (preview?.url) URL.revokeObjectURL(preview.url); setPreview(null); }}>关闭</Button>} onCancel={() => { if (preview?.url) URL.revokeObjectURL(preview.url); setPreview(null); }} destroyOnHidden>
      <AttachmentPreviewContent preview={preview} />
    </Modal>
    <Modal open={!!editor} title={`在线编辑：${editor?.name || ""}`} width={860} okText="保存为新版本" cancelText="取消" confirmLoading={editorSaving} onOk={() => void saveEditor()} onCancel={() => { setEditor(null); editForm.resetFields(); }} destroyOnHidden>
      <Alert type="info" showIcon title="保存会生成个人 AI 空间的新版本，原文件保留不覆盖。" style={{ marginBottom: 12 }} />
      <Form form={editForm} layout="vertical"><Form.Item name="name" label="文件名" rules={[{ required: true }, { pattern: /\.(docx|md|txt)$/i, message: "仅支持 .docx、.md、.txt" }]}><Input maxLength={255} /></Form.Item><Form.Item name="content" label="文档正文" rules={[{ required: true, message: "请输入文档正文" }]}><Input.TextArea autoSize={{ minRows: 18, maxRows: 30 }} /></Form.Item></Form>
    </Modal>
  </Drawer>;
}
