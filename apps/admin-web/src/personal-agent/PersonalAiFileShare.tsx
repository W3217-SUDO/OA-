import { useEffect, useRef, useState } from "react";
import { Alert, Button, Modal, Spin } from "antd";
import { ShareAltOutlined } from "@ant-design/icons";
import { api } from "../api";
import { type PersonalAiFile } from "./personalAiSpaceApi";
import { errorText } from "./types";

export function PersonalAiFileShare({ file, disabled }: { file: PersonalAiFile; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  const [prepared, setPrepared] = useState<File>();
  const [loading, setLoading] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [error, setError] = useState("");
  const controller = useRef<AbortController | null>(null);
  const shareLock = useRef(false);
  useEffect(() => () => controller.current?.abort(), []);

  function close() {
    if (shareLock.current) return;
    controller.current?.abort();
    setOpen(false); setPrepared(undefined); setError("");
  }

  async function prepare() {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setOpen(true); setPrepared(undefined); setError(""); setLoading(true);
    try {
      if (!navigator.share || !navigator.canShare) throw new Error("当前浏览器不支持文件分享。请使用下载按钮保存文件，再在钉钉或微信中选择文件发送。");
      const { data: current } = await api.get<PersonalAiFile>(`/personal-agent/ai-space/files/${encodeURIComponent(file.id)}`, { signal: request.signal });
      if (current.id !== file.id || current.status !== "available" || !current.download_url) throw new Error("文件尚未可用，请刷新核对保存状态");
      const { data } = await api.get<Blob>(`/personal-agent/ai-space/files/${encodeURIComponent(file.id)}/download`, { responseType: "blob", signal: request.signal });
      const content = new File([data], current.name.replace(/[\\/:*?"<>|\u0000-\u001f]/g, "_"), { type: data.type || current.content_type });
      if (!navigator.canShare({ files: [content] })) throw new Error("当前设备无法分享此文件格式或大小。请下载后在钉钉或微信中选择文件发送。");
      if (!request.signal.aborted) setPrepared(content);
    } catch (failure) {
      if (!request.signal.aborted) setError(errorText(failure, "分享文件准备失败"));
    } finally { if (!request.signal.aborted) setLoading(false); }
  }

  async function share() {
    if (!prepared || shareLock.current) return;
    shareLock.current = true; setSharing(true); setError("");
    try {
      // 从本次点击直接打开系统面板，文件下载已在前一步完成。
      await navigator.share({ files: [prepared] });
      setOpen(false); setPrepared(undefined);
    } catch (failure) {
      if (!(failure instanceof DOMException && failure.name === "AbortError")) setError(errorText(failure, "无法打开系统分享面板，请下载文件后发送"));
    } finally { shareLock.current = false; setSharing(false); }
  }

  return <>
    <Button icon={<ShareAltOutlined />} disabled={disabled} onClick={() => void prepare()}>分享文件</Button>
    <Modal open={open} title="分享文件" rootClassName="personal-ai-file-share" onCancel={close} closable={!sharing} maskClosable={!sharing} destroyOnHidden
      footer={<><Button disabled={sharing} onClick={close}>关闭</Button><Button type="primary" disabled={!prepared} loading={sharing} onClick={() => void share()}>打开系统分享面板</Button></>}>
      <p className="personal-ai-file-share-name">{file.name}</p>
      <p>由你在系统面板中选择钉钉、微信或其他应用及接收对象。可选应用由设备决定，发送结果请在目标应用中核对。</p>
      {file.source_kind === "personal_identity" && <Alert type="warning" showIcon title="这是个人身份文件，请确认内容适合分享后再继续。" />}
      {loading && <Spin description="正在准备文件" />}
      {error && <Alert type="error" showIcon title="文件分享未完成" description={error} />}
    </Modal>
  </>;
}
