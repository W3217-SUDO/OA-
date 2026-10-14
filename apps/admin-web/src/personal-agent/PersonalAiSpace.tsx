import { useEffect, useRef, useState } from "react";
import { Alert, Button, Drawer, Modal, Pagination, Spin, Tooltip, message } from "antd";
import { DeleteOutlined, ReloadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "./types";
import { PersonalAiSpaceFiles } from "./PersonalAiSpaceFiles";
import { PersonalAiOfficeEditor } from "./PersonalAiOfficeEditor";
import { PersonalAiDocumentEditor } from "./PersonalAiDocumentEditor";
import { AttachmentPreviewContent, type PreviewAttachment } from "../components/common/AttachmentContent";
import { downloadPersonalAiFile, type PersonalAiDocument, type PersonalAiFile, type PersonalAiFileDeleteResult, type PersonalAiFilePage, type PersonalAiSpaceInfo } from "./personalAiSpaceApi";
import "./personal-ai-space.css";

type Props = {
  open: boolean;
  onClose: () => void;
  revision: number;
  busy: boolean;
  onOpenConversation: (id: string) => Promise<unknown>;
  onSkillsChanged?: () => Promise<unknown>;
  label?: string;
};

export function PersonalAiSpace({ open, onClose, revision, busy, onOpenConversation, label = "个人空间" }: Props) {
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const [space, setSpace] = useState<PersonalAiSpaceInfo | null>(null);
  const [files, setFiles] = useState<PersonalAiFilePage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState("");
  const [preview, setPreview] = useState<PreviewAttachment | null>(null);
  const [officeFile, setOfficeFile] = useState<PersonalAiFile | null>(null);
  const [officeBusy, setOfficeBusy] = useState(false);
  const officeOperation = useRef(false);
  const [previewFileId, setPreviewFileId] = useState("");
  const [editor, setEditor] = useState<PersonalAiDocument | null>(null);
  const [editorBusy, setEditorBusy] = useState(false);
  const [latestSavedId, setLatestSavedId] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<PersonalAiFile | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const deleteLock = useRef(false);
  const fileRead = useRef<AbortController | null>(null);
  useEffect(() => () => fileRead.current?.abort(), []);
  const closePreview = () => { if (preview?.url) URL.revokeObjectURL(preview.url); setPreview(null); setPreviewFileId(""); };
  const close = () => {
    if (editorBusy || officeOperation.current || deleteLock.current) return;
    fileRead.current?.abort();
    closePreview(); setEditor(null); setOfficeFile(null); setDeleteTarget(null); setPage(1); setSpace(null); onClose();
  };
  const versionCreated = (file: PersonalAiFile) => { setLatestSavedId(file.id); setPage(1); setRefresh((value) => value + 1); };
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setLoading(true); setError(""); setFiles(null);
    void Promise.all([
      api.get<PersonalAiSpaceInfo>("/personal-agent/ai-space", { signal: controller.signal }).then((info) => { if (!controller.signal.aborted) setSpace(info.data); }),
      api.get<PersonalAiFilePage>("/personal-agent/ai-space/files", { params: { page, page_size: 20 }, signal: controller.signal }),
    ]).then(([, list]) => {
      if (!controller.signal.aborted) setFiles(list.data);
    }).catch((failure) => { if (!controller.signal.aborted) setError(errorText(failure, "个人空间加载失败")); })
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
  const openEditor = async (file: PersonalAiFile) => {
    if (editorBusy || officeOperation.current || deleteLock.current) return;
    fileRead.current?.abort();
    const controller = new AbortController(); fileRead.current = controller;
    setError("");
    if (file.case_id === null && file.name.toLowerCase().endsWith(".docx")) { setEditor(null); setOfficeFile(file); return; }
    try {
      const { data } = await api.get<PersonalAiDocument>(`/personal-agent/ai-space/files/${encodeURIComponent(file.id)}/content`, { signal: controller.signal });
      if (controller.signal.aborted) return;
      if (data.id !== file.id) throw new Error("编辑文件标识与所选文件不一致");
      setOfficeFile(null);
      setEditor(data);
    } catch (failure) { if (!controller.signal.aborted) setError(errorText(failure, "文件在线编辑加载失败")); }
  };
  const deleteFile = async () => {
    if (!deleteTarget || !deleteTarget.can_delete || deleteLock.current || editorBusy || officeOperation.current) return;
    fileRead.current?.abort();
    deleteLock.current = true; setDeleting(true); setDeleteError("");
    try {
      const { data } = await api.delete<PersonalAiFileDeleteResult>(`/personal-agent/ai-space/files/${encodeURIComponent(deleteTarget.id)}`, {
        data: { expected_sha256: deleteTarget.sha256 }, headers: { "X-OA-Agent-Confirmation": "frontend" },
      });
      if (data.id !== deleteTarget.id || data.status !== "deleted" || data.blob_status !== "retained") throw new Error("删除结果尚未确认，请刷新文件夹核对，未隐藏该文件");
      if (editor?.id === data.id) setEditor(null);
      if (officeFile?.id === data.id) setOfficeFile(null);
      if (previewFileId === data.id) closePreview();
      if (latestSavedId === data.id) setLatestSavedId("");
      setDeleteTarget(null);
      if (files) setPage(Math.min(page, Math.max(1, Math.ceil((files.total - 1) / files.page_size))));
      setRefresh((value) => value + 1);
      message.success(`文件已移入待清理：${deleteTarget.name}`);
    } catch (failure) { setDeleteError(errorText(failure, "文件删除未完成，请核对文件状态")); setRefresh((value) => value + 1); }
    finally { deleteLock.current = false; setDeleting(false); }
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
    title={<span className="personal-ai-space-title">{space ? `${space.owner_name}的${label}` : label}</span>}
  >
    <div className="personal-ai-space-content">
      <div className="personal-ai-space-toolbar"><Tooltip title={`刷新${label}`}><Button icon={<ReloadOutlined />} aria-label={`刷新${label}`} loading={loading} onClick={() => setRefresh((value) => value + 1)} /></Tooltip>{files && <span>共 {files.total} 个文件</span>}</div>
      {space && !space.configured && <Alert type="warning" showIcon title="OSS 尚未配置，不能保存新文件" />}
      {error && <Alert type="error" showIcon title="个人空间操作未完成" description={error} />}
      {loading ? <Spin /> : files && <PersonalAiSpaceFiles items={files.items} downloadingId={downloadingId} deletingId={deleting ? deleteTarget?.id : undefined} latestSavedId={latestSavedId} busy={busy || editorBusy || officeBusy || deleting} onDownload={(file) => void download(file)} onEdit={(file) => void openEditor(file)} onDelete={(file) => { if (!officeOperation.current && !editorBusy && !deleteLock.current) { setDeleteError(""); setDeleteTarget(file); } }} onConversation={(id) => void openConversation(id)} />}
      {files && files.total > 0 && <Pagination simple current={files.page} pageSize={files.page_size} total={files.total} disabled={loading} showSizeChanger={false} onChange={setPage} />}
    </div>
    <Modal open={!!preview} title={`在线查看：${preview?.name || ""}`} width={preview?.kind === "pdf" ? 1000 : 860} footer={<Button onClick={closePreview}>关闭</Button>} onCancel={closePreview} destroyOnHidden>
      <AttachmentPreviewContent preview={preview} />
    </Modal>
    {editor && <PersonalAiDocumentEditor document={editor} onBusy={setEditorBusy} onClose={() => { if (!editorBusy) setEditor(null); }} onVersionCreated={versionCreated} onSaved={(file, document) => {
      if (file.case_id === null && file.name.toLowerCase().endsWith(".docx")) { setEditor(null); setOfficeFile(file); }
      else setEditor(document);
    }} />}
    <Modal open={!!deleteTarget} title="确认删除生成文件？" rootClassName="personal-ai-document-confirmation" okText="确认删除" cancelText="取消"
      confirmLoading={deleting} okButtonProps={{ danger: true, icon: <DeleteOutlined /> }} cancelButtonProps={{ disabled: deleting }}
      closable={!deleting} keyboard={!deleting} maskClosable={!deleting} onOk={() => void deleteFile()} onCancel={() => { if (!deleteLock.current) { setDeleteTarget(null); setDeleteError(""); } }} destroyOnHidden>
      <p>{deleteTarget?.name}</p>
      <p>将从前端隐藏此生成文件，原文件、附件及钉钉编辑副本暂时保留，后续由统一清理任务处理。其他版本、来源会话和案件原附件不受影响。</p>
      {deleteTarget?.name.toLowerCase().endsWith(".docx") && <p>钉钉编辑副本不在本次删除范围。</p>}
      {deleteError && <Alert type="error" showIcon title="删除未完成" description={deleteError} />}
    </Modal>
    {officeFile && <PersonalAiOfficeEditor key={officeFile.id} file={officeFile} disabled={deleting || editorBusy} onBusy={(value) => { officeOperation.current = value; setOfficeBusy(value); }}
      onClose={() => { if (!officeOperation.current) setOfficeFile(null); }} onVersionCreated={versionCreated} onSaved={(file, blob) => {
        closePreview(); setOfficeFile(null); setPreviewFileId(file.id); setPreview({ name: file.name, kind: "docx", blob });
      }} />}
  </Drawer>;
}
