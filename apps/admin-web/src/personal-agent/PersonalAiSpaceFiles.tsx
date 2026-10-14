import { Button, Empty, Tag, Tooltip } from "antd";
import { DeleteOutlined, DownloadOutlined, EditOutlined, EyeOutlined, MessageOutlined } from "@ant-design/icons";
import type { PersonalAiFile } from "./personalAiSpaceApi";

const STATUS_LABELS: Record<PersonalAiFile["status"], string> = { uploading: "保存中", available: "可下载", failed: "保存失败", uncertain: "保存结果待核对", deleting: "删除中", delete_failed: "删除失败", delete_uncertain: "删除结果待核对" };
const STATUS_COLORS: Record<PersonalAiFile["status"], string> = { uploading: "processing", available: "success", failed: "error", uncertain: "warning", deleting: "processing", delete_failed: "error", delete_uncertain: "warning" };
const SOURCE_LABELS: Record<string, string> = {
  mcp_export: "案件导出",
  mcp_generated: "智能体生成文件",
  case_draft: "案件AI草稿",
  case_upload: "案件AI上传",
  case_migration: "案件AI迁移",
  assistant_message: "助手回答",
  personal_identity: "个人身份文件",
  personal_edit: "在线编辑新版本",
};

export function PersonalAiSpaceFiles({ items, downloadingId, deletingId, latestSavedId, busy, onDownload, onView, onEdit, onDelete, onConversation }: {
  items: PersonalAiFile[];
  downloadingId: string;
  deletingId?: string;
  latestSavedId?: string;
  busy: boolean;
  onDownload: (item: PersonalAiFile) => void;
  onView: (item: PersonalAiFile) => void;
  onEdit: (item: PersonalAiFile) => void;
  onDelete: (item: PersonalAiFile) => void;
  onConversation: (id: string) => void;
}) {
  if (!items.length) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="个人 AI 空间暂无文件" />;
  return <ol className="personal-ai-space-files">
    {items.map((item) => <li key={item.id}>
      <div className="personal-ai-space-file-heading"><strong>{item.name}</strong><Tag color={STATUS_COLORS[item.status]}>{STATUS_LABELS[item.status]}</Tag>{item.id === latestSavedId && <Tag color="processing">本次保存的新版本</Tag>}</div>
      <dl className="personal-ai-space-file-metadata">
        <dt>格式</dt><dd>{item.name.includes(".") ? item.name.slice(item.name.lastIndexOf(".") + 1).toUpperCase() : item.content_type}</dd>
        <dt>大小</dt><dd>{new Intl.NumberFormat("zh-CN").format(item.size)} 字节</dd>
        <dt>保存时间</dt><dd><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString("zh-CN", { hour12: false })}</time></dd>
        <dt>来源</dt><dd>{Object.hasOwn(SOURCE_LABELS, item.source_kind) ? SOURCE_LABELS[item.source_kind] : item.source_kind}</dd>
        {item.supersedes && <><dt>上一版本</dt><dd>{item.supersedes}</dd></>}
        {item.source_request_id && <><dt>请求编号</dt><dd>{item.source_request_id}</dd></>}
      </dl>
      {item.error && <p className="personal-ai-space-file-error" role="alert">{item.error}</p>}
      <div className="personal-ai-space-file-actions">
        {item.conversation_id && <Tooltip title={item.conversation_id}><Button icon={<MessageOutlined />} disabled={busy} onClick={() => onConversation(item.conversation_id!)}>查看来源会话</Button></Tooltip>}
        {item.status === "available" && item.download_url && <>
          <Button icon={<EyeOutlined />} disabled={busy || !!downloadingId} onClick={() => onView(item)}>在线查看</Button>
          {/\.(docx|md|txt)$/i.test(item.name) && <Button icon={<EditOutlined />} disabled={busy || !!downloadingId} onClick={() => onEdit(item)}>在线编辑</Button>}
          <Button icon={<DownloadOutlined />} loading={downloadingId === item.id} disabled={busy || (!!downloadingId && downloadingId !== item.id)} onClick={() => onDownload(item)}>下载 {item.name.includes(".") ? item.name.slice(item.name.lastIndexOf(".") + 1).toUpperCase() : "文件"}</Button>
        </>}
        {item.can_delete && <Tooltip title="删除生成文件"><Button danger icon={<DeleteOutlined />} aria-label={`删除生成文件：${item.name}`} loading={deletingId === item.id} disabled={busy || !!downloadingId} onClick={() => onDelete(item)}>删除文件</Button></Tooltip>}
      </div>
    </li>)}
  </ol>;
}
