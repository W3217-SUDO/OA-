import { useEffect, useState } from "react";
import { Alert, Button, Drawer, Pagination, Spin, Tooltip } from "antd";
import { FolderOpenOutlined, ReloadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "./types";
import { PersonalAiSpaceFiles } from "./PersonalAiSpaceFiles";
import { downloadPersonalAiFile, type PersonalAiFile, type PersonalAiFilePage, type PersonalAiSpaceInfo } from "./personalAiSpaceApi";
import "./personal-ai-space.css";

type Props = {
  revision: number;
  busy: boolean;
  onOpenConversation: (id: string) => Promise<unknown>;
};

export function PersonalAiSpace({ revision, busy, onOpenConversation }: Props) {
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const [space, setSpace] = useState<PersonalAiSpaceInfo | null>(null);
  const [files, setFiles] = useState<PersonalAiFilePage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState("");
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
  const openConversation = async (id: string) => {
    setError("");
    try { await onOpenConversation(id); setOpen(false); }
    catch (failure) { setError(errorText(failure, "来源会话不可用")); }
  };
  return <>
    <Tooltip title="个人 AI 空间"><Button className="personal-ai-space-trigger" type="text" icon={<FolderOpenOutlined />} aria-label="个人 AI 空间" onClick={() => { setPage(1); setSpace(null); setOpen(true); }}><span className="personal-ai-space-label">个人 AI 空间</span></Button></Tooltip>
    <Drawer
    open={open}
    onClose={() => setOpen(false)}
    width={760}
    destroyOnHidden
    rootClassName="personal-ai-space-drawer"
    title={<span className="personal-ai-space-title">{space ? `${space.owner_name}的个人 AI 空间` : "个人 AI 空间"}</span>}
  >
    <div className="personal-ai-space-content">
      <div className="personal-ai-space-toolbar"><Tooltip title="刷新个人 AI 空间"><Button icon={<ReloadOutlined />} aria-label="刷新个人 AI 空间" loading={loading} onClick={() => setRefresh((value) => value + 1)} /></Tooltip>{files && <span>共 {files.total} 个文件</span>}</div>
      {space && !space.configured && <Alert type="warning" showIcon title="OSS 尚未配置，不能保存新文件" />}
      {error && <Alert type="error" showIcon title="个人 AI 空间操作未完成" description={error} />}
      {loading ? <Spin /> : files && <PersonalAiSpaceFiles items={files.items} downloadingId={downloadingId} busy={busy} onDownload={(file) => void download(file)} onConversation={(id) => void openConversation(id)} />}
      {files && files.total > 0 && <Pagination simple current={files.page} pageSize={files.page_size} total={files.total} disabled={loading} showSizeChanger={false} onChange={setPage} />}
    </div>
  </Drawer>
  </>;
}
