import { Button, Tooltip } from "antd";
import { CopyOutlined, FileExcelOutlined, FileWordOutlined, FolderOpenOutlined, PaperClipOutlined, RobotOutlined } from "@ant-design/icons";
import { AgentMessageContent } from "../AgentMessageContent";
import { AgentToolResult } from "../AgentToolResult";
import { workspaceDocumentSaveTarget, type Material, type WorkspaceMessage } from "./types";

type Props = {
  item: WorkspaceMessage;
  generating: boolean;
  readingMaterials: boolean;
  progress: string;
  saved: boolean;
  savedSpreadsheet: boolean;
  busy: boolean;
  onCopy: (content: string) => void;
  onPreview: (material: Material) => void;
  onSave: () => void;
  onSaveSpreadsheet: () => void;
  onViewFiles: () => void;
};

export function ConversationMessage({ item, generating, readingMaterials, progress, saved, savedSpreadsheet, busy, onCopy, onPreview, onSave, onSaveSpreadsheet, onViewFiles }: Props) {
  const assistant = item.role === "assistant";
  const documentTarget = workspaceDocumentSaveTarget(item);
  return <article className={`personal-message ${item.role}${item.failed ? " failed" : ""}`}>
    {assistant && <div className="workspace-message-avatar" aria-hidden="true"><RobotOutlined /></div>}
    <div className="workspace-message-main">
      <div className="workspace-message-heading">
        <span>{assistant ? "办公助手" : "我"}</span>
        {item.created_at && <time dateTime={item.created_at}>{new Date(item.created_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</time>}
        {item.stopped && <span className="workspace-thinking">已停止</span>}
        {assistant && item.skill_name && <small title={item.skill_name}>{item.skill_name}</small>}
      </div>
      <div className="workspace-message-surface">
        <div className="workspace-message-body">
          {assistant ? item.content ? <AgentMessageContent content={item.content} /> : <span className="workspace-thinking" role="status">{generating ? progress || (readingMaterials ? "正在读取材料并处理问题…" : "正在处理…") : "未收到回答"}</span> : <div className="workspace-user-content">{item.content}</div>}
        </div>
        {assistant && <AgentToolResult result={item.tool_result} />}
        {!!item.attachments?.length && <div className="workspace-message-files">
          {item.attachments.map((file) => <span key={file.id} className={file.status === "failed" ? "workspace-message-file is-failed" : "workspace-message-file"}>
            <button onClick={() => onPreview(file)}><PaperClipOutlined />{file.name}</button>
            {file.status && <small title={file.error || undefined}>{file.status === "failed" ? "读取失败" : file.status === "readable" ? "可读取" : "已缓存"}</small>}
          </span>)}
        </div>}
        {assistant && !!item.content && !item.failed && !generating && <div className="workspace-message-actions">
          <Tooltip title="复制回答"><Button type="text" size="small" icon={<CopyOutlined />} aria-label="复制回答" onClick={() => onCopy(item.content)} /></Tooltip>
          {documentTarget && !item.stopped && (saved ? <>
            <span className="personal-ai-document-saved"><FileWordOutlined />{documentTarget === "case" ? "已存入案件 AI 空间" : "已存入个人 AI 空间"}</span>
            <Button type="link" icon={<FolderOpenOutlined />} onClick={onViewFiles}>{documentTarget === "case" ? "查看案件文件" : "查看文件"}</Button>
          </> : <>
            <Tooltip title={documentTarget === "case" ? `将回答保存为 Word 到 ${item.case_no} 的案件 AI 空间` : "将回答保存为 Word 到个人 AI 空间"}>
              <Button type="text" size="small" icon={<FileWordOutlined />} disabled={busy} onClick={onSave}>保存 Word</Button>
            </Tooltip>
            {documentTarget === "personal" && item.can_save_spreadsheet && (savedSpreadsheet ? <span className="personal-ai-document-saved"><FileExcelOutlined />已存入个人 AI 空间</span> : <Tooltip title="将回答中的 Markdown 表格保存为 Excel 到个人 AI 空间"><Button type="text" size="small" icon={<FileExcelOutlined />} disabled={busy} onClick={onSaveSpreadsheet}>保存 Excel</Button></Tooltip>)}
          </>)}
        </div>}
      </div>
    </div>
  </article>;
}
