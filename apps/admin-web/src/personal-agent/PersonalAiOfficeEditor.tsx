import { useRef, useState } from "react";
import { isAxiosError } from "axios";
import { Alert, Button, Modal, message } from "antd";
import { ExportOutlined, FileWordOutlined, ReloadOutlined, SaveOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "./types";
import type { PersonalAiFile } from "./personalAiSpaceApi";
import "./personal-ai-office-editor.css";

type OfficeSession = { session_id: string; name: string; url: string };
type OfficeSavedVersion = { file: PersonalAiFile; unchanged: boolean };
type Props = {
  file: PersonalAiFile;
  onClose: () => void;
  onBusy: (busy: boolean) => void;
  onVersionCreated: (file: PersonalAiFile) => void;
  onSaved: (file: PersonalAiFile, blob: Blob) => void;
  disabled?: boolean;
};

function isDefiniteOfficeSaveRejection(failure: unknown): boolean {
  if (!isAxiosError(failure) || !failure.response) return false;
  const { status, data } = failure.response;
  // 仅回存前置拒绝可重新确认；写入器含文件计划的结构化错误不能重放。
  return status >= 400 && status < 500 && data !== null && typeof data === "object"
    && !Array.isArray(data) && typeof data.detail === "string" && Object.keys(data).length === 1;
}

export function PersonalAiOfficeEditor({ file, onClose, onBusy, onVersionCreated, onSaved, disabled = false }: Props) {
  const [session, setSession] = useState<OfficeSession | null>(null);
  const [busy, setBusy] = useState<"open" | "save" | "read" | null>(null);
  const [error, setError] = useState("");
  const [savedVersion, setSavedVersion] = useState<OfficeSavedVersion | null>(null);
  const [submissionUncertain, setSubmissionUncertain] = useState(false);
  const operationLock = useRef(false);
  const close = () => { if (!disabled && !operationLock.current) onClose(); };
  const prepare = async () => {
    if (disabled || operationLock.current || savedVersion || submissionUncertain) return;
    // Open a tab synchronously so browsers do not classify the later async
    // navigation as a popup. The URL is filled only after OA confirms the
    // upload and passes the DingTalk-host validation below.
    const editorWindow = typeof window !== "undefined" ? window.open("about:blank", "_blank") : null;
    if (typeof window !== "undefined" && !editorWindow) {
      setError("浏览器阻止了钉钉编辑页面，请允许本站打开新窗口后重试");
      return;
    }
    let opened = false;
    operationLock.current = true; setBusy("open"); onBusy(true); setError(""); setSession(null);
    try {
      const { data } = await api.post<OfficeSession>(`/personal-agent/ai-space/files/${encodeURIComponent(file.id)}/office/open`,
        { expected_sha256: file.sha256 }, { headers: { "x-oa-agent-confirmation": "frontend" } });
      const url = new URL(data.url);
      if (url.protocol !== "https:" || url.username || url.password || (url.port && url.port !== "443")
        || !(url.hostname === "dingtalk.com" || url.hostname.endsWith(".dingtalk.com"))) {
        throw new Error("钉钉编辑地址无效，未打开文件");
      }
      setSession(data);
      if (editorWindow) {
        editorWindow.location.replace(url.href);
        opened = true;
      }
    } catch (failure) { setSubmissionUncertain(true); setError(errorText(failure, "钉钉 Word 编辑请求未确认，请核对，勿重复上传")); }
    finally {
      if (!opened) {
        try { editorWindow?.close(); } catch { /* 浏览器可能已接管新窗口 */ }
      }
      operationLock.current = false; setBusy(null); onBusy(false);
    }
  };
  const readSavedVersion = async (version: OfficeSavedVersion) => {
    const saved = version.file;
    const { data: current } = await api.get<PersonalAiFile>(`/personal-agent/ai-space/files/${encodeURIComponent(saved.id)}`);
    if (current.id !== saved.id || current.status !== "available" || !current.download_url
      || current.owner_user_id !== file.owner_user_id || current.case_id !== null
      || current.supersedes !== file.id || current.name !== saved.name || !current.name.toLowerCase().endsWith(".docx")
      || current.sha256 !== saved.sha256 || current.size !== saved.size) {
      throw new Error("OA 新 Word 的归属、版本关系或持久信息不一致，未确认读取，请核对该新文件");
    }
    // 复杂 Word 按完整字节核验和预览，不经过受限正文提取或 Markdown 重建。
    const { data: blob } = await api.get<Blob>(`/personal-agent/ai-space/files/${encodeURIComponent(saved.id)}/download`, { responseType: "blob" });
    if (blob.size !== current.size) throw new Error("OA 新 Word 回读大小不一致，请核对，勿重复回存");
    if (!globalThis.crypto?.subtle) throw new Error("当前连接无法核验 Word 摘要，请使用 HTTPS 后重新读取已回存的新版本");
    const digest = await globalThis.crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
    const sha256 = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
    if (sha256 !== current.sha256) throw new Error("OA 新 Word 回读 SHA256 不一致，请核对，勿重复回存");
    onSaved(current, blob);
    message.success(version.unchanged ? "已读取此前回存的 OA Word 新版本，未重复生成" : "修改已回存并读取 OA Word 新版本，原文件保留");
  };
  const retryReadback = async () => {
    if (disabled || !savedVersion || operationLock.current) return;
    operationLock.current = true; setBusy("read"); onBusy(true); setError("");
    try { await readSavedVersion(savedVersion); }
    catch (failure) { setError(errorText(failure, "新 Word 回读未完成，勿重复回存")); }
    finally { operationLock.current = false; setBusy(null); onBusy(false); }
  };
  const save = async () => {
    if (disabled || !session || operationLock.current || savedVersion || submissionUncertain) return;
    operationLock.current = true; setBusy("save"); onBusy(true); setError("");
    let persisted: OfficeSavedVersion | null = null;
    try {
      const { data } = await api.post<OfficeSavedVersion & { supersedes: string }>(
        `/personal-agent/ai-space/files/${encodeURIComponent(file.id)}/office/save`,
        { session_id: session.session_id }, { headers: { "x-oa-agent-confirmation": "frontend" } });
      if (data.supersedes !== file.id || !data.file.id || data.file.id === file.id || data.file.status !== "available"
        || data.file.owner_user_id !== file.owner_user_id || data.file.case_id !== null) {
        throw new Error("Word 回存返回的文件归属、版本或状态异常，请核对，勿重复回存");
      }
      persisted = { file: data.file, unchanged: data.unchanged };
      setSavedVersion(persisted); onVersionCreated(data.file);
      await readSavedVersion(persisted);
    } catch (failure) {
      if (!persisted) setSubmissionUncertain(!isDefiniteOfficeSaveRejection(failure));
      setError(errorText(failure, "Word 回存或回读未完成，请核对钉钉及 OA 保存状态"));
    } finally { operationLock.current = false; setBusy(null); onBusy(false); }
  };
  return <Modal open title="钉钉 Word 在线编辑" width={640} rootClassName="personal-ai-office-editor"
    closable={!busy && !disabled} maskClosable={!busy && !disabled} keyboard={!busy && !disabled} onCancel={close} destroyOnHidden
    footer={<Button disabled={!!busy || disabled} onClick={close}>关闭</Button>}>
    <div className="personal-ai-office-content">
      <div className="personal-ai-office-file"><FileWordOutlined /><strong>{file.name}</strong></div>
      <Alert type="info" showIcon title="使用钉钉的 Word 编辑工具"
        description={`仅把你选定的这份文件副本上传至绑定钉钉账号的独立编辑空间。文件所属人：${file.owner_name}。原文件继续由 OA 保管，不覆盖。`} />
      {savedVersion && <Alert type="warning" showIcon title="OA 新版本已回存；正在核对完整 Word，不能重复回存。" description={`新文件：${savedVersion.file.id}`} />}
      {error && <Alert type="error" showIcon title={submissionUncertain ? "请求结果未确认，请核对，勿重复提交" : "操作未完成"} description={error} />}
      <ol className="personal-ai-office-steps">
        <li>准备文件副本，然后在新页面打开钉钉。请使用与当前 OA 账号绑定的钉钉账号登录。</li>
        <li>在钉钉完成排版、表格等编辑，等待钉钉保存完成。</li>
        <li>返回这里取回已保存的 Word，生成 OA 个人空间新版本。</li>
      </ol>
      <div className="personal-ai-office-actions">
        <Button icon={session ? <ReloadOutlined /> : <FileWordOutlined />} loading={busy === "open"} disabled={disabled || !!busy || !!savedVersion || submissionUncertain}
          onClick={() => void prepare()}>{session ? "刷新钉钉编辑链接" : "上传副本并打开钉钉编辑"}</Button>
        {session && <Button type="primary" icon={<ExportOutlined />} href={session.url} target="_blank" rel="noopener noreferrer" disabled={!!busy || disabled}>打开钉钉编辑</Button>}
        {session && <Button icon={<SaveOutlined />} loading={busy === "save"} disabled={disabled || !!busy || !!savedVersion || submissionUncertain} onClick={() => void save()}>已在钉钉保存，取回新版本</Button>}
        {savedVersion && <Button icon={<ReloadOutlined />} loading={busy === "read"} disabled={disabled || !!busy} onClick={() => void retryReadback()}>重新读取已回存的新版本</Button>}
      </div>
      <p className="personal-ai-office-hint">钉钉编辑需要对应文件权限和 Office 服务。关闭此窗口不会自动回存；重新从原文件进入可继续同一编辑副本。</p>
    </div>
  </Modal>;
}
