import { Button, Tooltip } from "antd";
import { CopyOutlined, FileWordOutlined, PaperClipOutlined, RobotOutlined } from "@ant-design/icons";
import { AgentMessageContent } from "../AgentMessageContent";
import type { Material, WorkspaceMessage } from "./types";

type Props = {
  item: WorkspaceMessage;
  generating: boolean;
  readingMaterials: boolean;
  progress: string;
  saved: boolean;
  busy: boolean;
  onCopy: (content: string) => void;
  onPreview: (material: Material) => void;
  onSave: () => void;
};

export function ConversationMessage({ item, generating, readingMaterials, progress, saved, busy, onCopy, onPreview, onSave }: Props) {
  const assistant = item.role === "assistant";
  return <article className={`personal-message ${item.role}${item.failed ? " failed" : ""}`}>
    <div className="workspace-message-avatar" aria-hidden="true">{assistant ? <RobotOutlined /> : "我"}</div>
    <div className="workspace-message-main">
      <div className="workspace-message-heading">
        <span>{assistant ? "办公助手" : "我"}</span>
        {item.created_at && <time dateTime={item.created_at}>{new Date(item.created_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</time>}
        {assistant && item.skill_name && <small title={item.skill_name}>{item.skill_name}</small>}
      </div>
      <div className="workspace-message-surface">
        <div className="workspace-message-body">
          {assistant ? item.content ? <AgentMessageContent content={item.content} /> : <span className="workspace-thinking" role="status">{generating ? progress || (readingMaterials ? "正在读取材料并处理问题…" : "正在处理…") : "未收到回答"}</span> : <div className="workspace-user-content">{item.content}</div>}
        </div>
        {!!item.attachments?.length && <div className="workspace-message-files">
          {item.attachments.map((file) => <button key={file.id} onClick={() => onPreview(file)}><PaperClipOutlined />{file.name}</button>)}
        </div>}
        {assistant && !!item.content && !item.failed && !generating && <div className="workspace-message-actions">
          <Tooltip title="复制回答"><Button type="text" size="small" icon={<CopyOutlined />} aria-label="复制回答" onClick={() => onCopy(item.content)} /></Tooltip>
          {!!item.can_save_document && <Tooltip title={`将回答保存为 Word 到 ${item.case_no} 的 AI 空间`}>
            <Button type="text" size="small" icon={<FileWordOutlined />} disabled={saved || busy} onClick={onSave}>{saved ? "已存入 AI 空间" : "保存 Word"}</Button>
          </Tooltip>}
        </div>}
      </div>
    </div>
  </article>;
}
