import { useState } from "react";
import { Button, Drawer, Empty, Modal, Tooltip, message } from "antd";
import { DeleteOutlined, HistoryOutlined, MessageOutlined, PlusOutlined } from "@ant-design/icons";
import { errorText, type WorkspaceConversation } from "./types";

type Props = {
  items: WorkspaceConversation[];
  activeId?: string | null;
  busy: boolean;
  onCreate: () => Promise<void>;
  onSelect: (id: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
};

export function ConversationManager({ items, activeId, busy, onCreate, onSelect, onDelete }: Props) {
  const [open, setOpen] = useState(false);
  const [modal, contextHolder] = Modal.useModal();
  const run = async (operation: () => Promise<void>, close = false) => {
    try { await operation(); if (close) setOpen(false); }
    catch (error) { message.error(errorText(error, "对话操作失败")); }
  };
  const remove = (item: WorkspaceConversation) => modal.confirm({
    title: "删除对话？",
    content: `“${item.title}”的聊天记录将被删除，已完成的 OA 操作和业务材料不受影响。`,
    okText: "删除", cancelText: "取消", okButtonProps: { danger: true },
    onOk: async () => {
      try { await onDelete(item.id); message.success("对话已删除"); }
      catch (error) { message.error(errorText(error, "删除对话失败")); throw error; }
    },
  });
  return <>
    {contextHolder}
    <div className="workspace-conversation-controls">
      <Button size="small" icon={<PlusOutlined />} disabled={busy} onClick={() => void run(onCreate)}>新建对话</Button>
      <Tooltip title="对话列表"><Button size="small" type="text" icon={<HistoryOutlined />} aria-label="对话列表" onClick={() => setOpen(true)} /></Tooltip>
    </div>
    <Drawer title="我的对话" placement="right" width={360} open={open} onClose={() => setOpen(false)} className="workspace-conversation-drawer" extra={<Button icon={<PlusOutlined />} disabled={busy} onClick={() => void run(onCreate, true)}>新建对话</Button>}>
      {!items.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无对话" />}
      <div className="workspace-conversation-list">{items.map((item) => <div className={`workspace-conversation-row${item.id === activeId ? " active" : ""}`} key={item.id}>
        <button className="workspace-conversation-select" aria-current={item.id === activeId ? "true" : undefined} disabled={busy} onClick={() => void run(() => onSelect(item.id), true)}>
          <MessageOutlined /><span><b title={item.title}>{item.title}</b><small>{item.updated_at && `${new Date(item.updated_at).toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })} · `}{item.message_count} 条消息</small></span>
        </button>
        <Tooltip title="删除对话"><Button type="text" danger icon={<DeleteOutlined />} aria-label={`删除对话：${item.title}`} disabled={busy} onClick={() => remove(item)} /></Tooltip>
      </div>)}</div>
    </Drawer>
  </>;
}
