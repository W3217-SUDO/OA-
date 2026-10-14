import { useState } from "react";
import { Alert, Button, Modal, message } from "antd";
import { ExportOutlined, FileWordOutlined, ReloadOutlined, SaveOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "./types";
import type { PersonalAiFile } from "./personalAiSpaceApi";
import "./personal-ai-office-editor.css";

type OfficeSession = { session_id: string; name: string; url: string };
type Props = { file: PersonalAiFile; onClose: () => void; onSaved: () => void };

export function PersonalAiOfficeEditor({ file, onClose, onSaved }: Props) {
  const [session, setSession] = useState<OfficeSession | null>(null);
  const [busy, setBusy] = useState<"open" | "save" | null>(null);
  const [error, setError] = useState("");
  const prepare = async () => {
    if (busy) return;
    setBusy("open"); setError(""); setSession(null);
    try {
      const { data } = await api.post<OfficeSession>(`/personal-agent/ai-space/files/${encodeURIComponent(file.id)}/office/open`,
        { expected_sha256: file.sha256 }, { headers: { "x-oa-agent-confirmation": "frontend" } });
      const url = new URL(data.url);
      if (url.protocol !== "https:" || url.username || url.password || (url.port && url.port !== "443")
        || !(url.hostname === "dingtalk.com" || url.hostname.endsWith(".dingtalk.com"))) {
        throw new Error("钉钉编辑地址无效，未打开文件");
      }
      setSession(data);
    } catch (failure) { setError(errorText(failure, "钉钉 Word 编辑未打开")); }
    finally { setBusy(null); }
  };
  const save = async () => {
    if (!session || busy) return;
    setBusy("save"); setError("");
    try {
      const { data } = await api.post<{ file: PersonalAiFile; unchanged: boolean }>(
        `/personal-agent/ai-space/files/${encodeURIComponent(file.id)}/office/save`,
        { session_id: session.session_id }, { headers: { "x-oa-agent-confirmation": "frontend" } });
      message.success(data.unchanged ? "该钉钉版本已保存到 OA，未重复生成" : "修改已保存为 OA 新版本，原文件保留");
      onSaved(); onClose();
    } catch (failure) { setError(errorText(failure, "未保存回 OA，请核对钉钉保存状态")); }
    finally { setBusy(null); }
  };
  return <Modal open title="钉钉 Word 在线编辑" width={640} rootClassName="personal-ai-office-editor"
    closable={!busy} maskClosable={!busy} keyboard={!busy} onCancel={onClose} destroyOnHidden
    footer={<Button disabled={!!busy} onClick={onClose}>关闭</Button>}>
    <div className="personal-ai-office-content">
      <div className="personal-ai-office-file"><FileWordOutlined /><strong>{file.name}</strong></div>
      <Alert type="info" showIcon title="使用钉钉的 Word 编辑工具"
        description={`仅把你选定的这份文件副本上传至绑定钉钉账号的独立编辑空间。文件所属人：${file.owner_name}。原文件继续由 OA 保管，不覆盖。`} />
      {error && <Alert type="error" showIcon title="操作未完成" description={error} />}
      <ol className="personal-ai-office-steps">
        <li>准备文件副本，然后在新页面打开钉钉。请使用与当前 OA 账号绑定的钉钉账号登录。</li>
        <li>在钉钉完成排版、表格等编辑，等待钉钉保存完成。</li>
        <li>返回这里取回已保存的 Word，生成 OA 个人空间新版本。</li>
      </ol>
      <div className="personal-ai-office-actions">
        <Button icon={session ? <ReloadOutlined /> : <FileWordOutlined />} loading={busy === "open"} disabled={busy === "save"}
          onClick={() => void prepare()}>{session ? "刷新钉钉编辑链接" : "确认上传副本并准备编辑"}</Button>
        {session && <Button type="primary" icon={<ExportOutlined />} href={session.url} target="_blank" rel="noopener noreferrer" disabled={!!busy}>打开钉钉编辑</Button>}
        {session && <Button icon={<SaveOutlined />} loading={busy === "save"} disabled={busy === "open"} onClick={() => void save()}>已在钉钉保存，取回新版本</Button>}
      </div>
      <p className="personal-ai-office-hint">钉钉编辑需要对应文件权限和 Office 服务。关闭此窗口不会自动回存；重新从原文件进入可继续同一编辑副本。</p>
    </div>
  </Modal>;
}
