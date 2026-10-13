import { useRef, useState } from "react";
import { Button, Drawer, Empty, Modal, Tooltip, message } from "antd";
import { DeleteOutlined, HistoryOutlined, LoadingOutlined, MessageOutlined, PlusOutlined } from "@ant-design/icons";
import { errorText, type WorkspaceConversation } from "./types";

type Props = {
  items: WorkspaceConversation[];
  activeId?: string | null;
  busy: boolean;
  runningIds: string[];
  // 调用方只等待这些操作完成，不消费返回值，因此对返回的会话状态保持宽松。
  onCreate: () => Promise<unknown>;
  onSelect: (id: string) => Promise<unknown>;
  onDelete: (id: string) => Promise<unknown>;
  // 抽屉样式类由调用方给出：智能体中心与工作台的样式作用域不同。
  drawerClassName?: string;
  listClassName?: string;
  rowClassName?: string;
  selectClassName?: string;
  showHistoryLabel?: boolean;
};

export function ConversationManager({ items, activeId, busy, runningIds, onCreate, onSelect, onDelete,
  drawerClassName = "workspace-conversation-drawer",
  listClassName = "workspace-conversation-list",
  rowClassName = "workspace-conversation-row",
  selectClassName = "workspace-conversation-select",
  showHistoryLabel = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [modal, contextHolder] = Modal.useModal();
  const createConfirmationOpen = useRef(false);
  const run = async (operation: () => Promise<unknown>, close = false) => {
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
  const create = (close = false) => {
    if (createConfirmationOpen.current || busy) return;
    createConfirmationOpen.current = true;
    modal.confirm({
    title: "新建对话？",
    content: activeId ? "将打开一条新对话，当前对话和未发送的内容会保留，可在对话列表中返回。" : "确认打开一条新对话？",
    okText: "新建对话", cancelText: "取消",
    className: "workspace-new-conversation-confirmation",
    afterClose: () => { createConfirmationOpen.current = false; },
    onOk: async () => {
      try { await onCreate(); if (close) setOpen(false); }
      catch (error) { message.error(errorText(error, "新建对话失败")); throw error; }
    },
    });
  };
  return <>
    {contextHolder}
    <div className="workspace-conversation-controls">
      <Tooltip title="新建对话"><Button size="small" icon={<PlusOutlined />} aria-label="新建对话" disabled={busy} onClick={() => create()}><span className="workspace-conversation-label">新建对话</span></Button></Tooltip>
      <Tooltip title="对话列表"><Button size="small" type="text" icon={<HistoryOutlined />} aria-label="对话列表" onClick={() => setOpen(true)}>{showHistoryLabel && <span className="workspace-conversation-label">对话列表</span>}</Button></Tooltip>
    </div>
    <Drawer title="我的对话" placement="right" width="min(360px, 100vw)" open={open} onClose={() => setOpen(false)} className={drawerClassName} extra={<Button icon={<PlusOutlined />} disabled={busy} onClick={() => create(true)}>新建对话</Button>}>
      {!items.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无对话" />}
      <div className={listClassName}>{items.map((item) => <div className={`${rowClassName}${item.id === activeId ? " active" : ""}`} key={item.id}>
        <button className={selectClassName} aria-current={item.id === activeId ? "true" : undefined} disabled={busy} onClick={() => void run(() => onSelect(item.id), true)}>
          {runningIds.includes(item.id) ? <LoadingOutlined /> : <MessageOutlined />}<span><b title={item.title}>{item.title}</b><small>{runningIds.includes(item.id) ? "正在回答" : `${item.updated_at ? new Date(item.updated_at).toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }) + " · " : ""}${item.message_count} 条消息`}</small></span>
        </button>
        <Tooltip title={runningIds.includes(item.id) ? "请先停止该对话的回答" : "删除对话"}><Button type="text" danger icon={<DeleteOutlined />} aria-label={`删除对话：${item.title}`} disabled={busy || runningIds.includes(item.id)} onClick={() => remove(item)} /></Tooltip>
      </div>)}</div>
    </Drawer>
  </>;
}
