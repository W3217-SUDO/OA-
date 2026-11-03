import { useEffect, useRef, useState, type ReactNode } from "react";
import { POPUP_WIDTH } from "../components/common/popupSize";
import { Button, Drawer, Empty, Input, Modal, Tooltip, message } from "antd";
import { DeleteOutlined, EditOutlined, FolderOpenOutlined, HistoryOutlined, LoadingOutlined, MessageOutlined, PlusOutlined, UnorderedListOutlined } from "@ant-design/icons";
import { errorText, type WorkspaceConversation } from "./types";
import type { CaseAgentConversationSummary } from "./types";
import AgentMascot from "./AgentMascot";
import "./activeConversation.css";

type Props = {
  items: WorkspaceConversation[];
  activeId?: string | null;
  busy: boolean;
  loading?: boolean;
  runningIds: string[];
  // 调用方只等待这些操作完成，不消费返回值，因此对返回的会话状态保持宽松。
  onCreate: () => Promise<unknown>;
  onSelect: (id: string) => Promise<unknown>;
  onDelete: (id: string) => Promise<unknown>;
  /** 历史会话改名（501141）；不传则不显示改名按钮。 */
  onRename?: (id: string, title: string) => Promise<unknown>;
  // 抽屉样式类由调用方给出：智能体中心与工作台的样式作用域不同。
  drawerClassName?: string;
  listClassName?: string;
  rowClassName?: string;
  selectClassName?: string;
  showHistoryLabel?: boolean;
  presentation?: "drawer" | "sidebar";
  /** 传函数时，历史会话作为参数交给导航，放在所选空间下面（501147）。 */
  navigation?: ReactNode | ((history: ReactNode) => ReactNode);
  /** 历史会话放进空间时的标题，如“个人空间 · 最近会话”。 */
  historyTitle?: string;
  caseAgentConversations?: CaseAgentConversationSummary[];
  onSelectCaseAgentConversation?: (item: CaseAgentConversationSummary) => void;
};

export function ConversationManager({ items, activeId, busy, loading = false, runningIds, onCreate, onSelect, onDelete, onRename,
  drawerClassName = "workspace-conversation-drawer",
  listClassName = "workspace-conversation-list",
  rowClassName = "workspace-conversation-row",
  selectClassName = "workspace-conversation-select",
  showHistoryLabel = false,
  presentation = "drawer",
  navigation,
  historyTitle,
  caseAgentConversations = [],
  onSelectCaseAgentConversation,
}: Props) {
  const [open, setOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyKeyword, setHistoryKeyword] = useState("");
  const [renaming, setRenaming] = useState<WorkspaceConversation | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [savingTitle, setSavingTitle] = useState(false);
  const startRename = (item: WorkspaceConversation) => { setRenaming(item); setNewTitle(item.title); };
  const saveRename = async () => {
    const title = newTitle.trim();
    if (!renaming || !onRename) return;
    if (!title) { message.warning("请输入对话名称"); return; }
    setSavingTitle(true);
    try { await onRename(renaming.id, title); message.success("对话已改名"); setRenaming(null); }
    catch (error) { message.error(errorText(error, "对话改名失败")); }
    finally { setSavingTitle(false); }
  };
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
  // 陶威 11-03：当前正在看的会话整行高亮；切换或新建后滚到它，看得出自己在哪个会话。
  const sidebarRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!activeId) return;
    const row = sidebarRef.current?.querySelector<HTMLElement>(".is-current-conversation");
    try { row?.scrollIntoView({ block: "nearest" }); } catch { /* 老内核不支持参数时不滚 */ }
  }, [activeId, items.length]);
  const rowsOf = (rows: WorkspaceConversation[], afterSelect?: () => void, ref?: typeof sidebarRef) => <div className={listClassName} ref={ref}>{rows.map((item) => <div className={`${rowClassName}${item.id === activeId ? " active is-current-conversation" : ""}`} key={item.id}>
        <button type="button" className={selectClassName} aria-current={item.id === activeId ? "true" : undefined} disabled={busy} onClick={() => void run(async () => { await onSelect(item.id); afterSelect?.(); }, presentation === "drawer")}>
          {runningIds.includes(item.id) ? <LoadingOutlined /> : <MessageOutlined />}<span><b title={item.title}>{item.title}</b><small>{runningIds.includes(item.id) ? "正在回答" : `${item.updated_at ? new Date(item.updated_at).toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }) + " · " : ""}${item.message_count} 条消息`}</small></span>
        </button>
        {onRename && <Tooltip title="重命名"><Button type="text" icon={<EditOutlined />} aria-label={`重命名对话：${item.title}`} disabled={busy} onClick={() => startRename(item)} /></Tooltip>}
        <Tooltip title={runningIds.includes(item.id) ? "请先停止该对话的回答" : "删除对话"}><Button type="text" danger icon={<DeleteOutlined />} aria-label={`删除对话：${item.title}`} disabled={busy || runningIds.includes(item.id)} onClick={() => remove(item)} /></Tooltip>
      </div>)}</div>;
  const list = <>
      {!items.length && (loading ? <div className="assistant-conversation-loading" role="status" aria-live="polite" aria-label="正在加载对话"><AgentMascot pose="laptop" height={40} bob /><span>正在加载对话</span></div> : <Empty image={<AgentMascot pose="sleep" height={72} />} description="暂无对话" />)}
      {rowsOf(items)}
  </>;
  // 陶威 11-03：侧栏最近会话撑满左侧栏，能放几条放几条（超出滚动）；“全部历史会话”里可搜索、重命名、删除。
  const recentLimit = 50;
  const keyword = historyKeyword.trim().toLowerCase();
  const filtered = keyword ? items.filter((item) => item.title.toLowerCase().includes(keyword)) : items;
  const sidebarList = <>
      {!items.length && (loading ? <div className="assistant-conversation-loading" role="status" aria-live="polite" aria-label="正在加载对话"><AgentMascot pose="laptop" height={40} bob /><span>正在加载对话</span></div> : <Empty image={<AgentMascot pose="sleep" height={72} />} description="暂无对话" />)}
      {/* 当前会话不在前 50 条里：放到最上面并标“当前会话”。 */}
      {activeId && items.findIndex((item) => item.id === activeId) >= recentLimit && <div className="assistant-current-outside">当前会话（较早）</div>}
      {rowsOf(items.findIndex((item) => item.id === activeId) >= recentLimit
        ? [items.find((item) => item.id === activeId)!, ...items.slice(0, recentLimit)] : items.slice(0, recentLimit), undefined, sidebarRef)}
      {items.length > 0 && <Button type="link" icon={<UnorderedListOutlined />} className="assistant-history-all" onClick={() => { setHistoryKeyword(""); setHistoryOpen(true); }}>全部历史会话（{items.length}）</Button>}
  </>;
  const historyModal = () => <Modal title="全部历史会话" width={POPUP_WIDTH.md} open={historyOpen} footer={null} onCancel={() => setHistoryOpen(false)} destroyOnHidden>
    <Input.Search allowClear placeholder="按名称搜索" aria-label="搜索历史会话" value={historyKeyword} onChange={(event) => setHistoryKeyword(event.target.value)} />
    <div className="assistant-history-all-list">
      {!filtered.length ? <Empty image={<AgentMascot pose={keyword ? "sorry" : "sleep"} height={72} />} description={keyword ? "没有找到匹配的会话" : "暂无对话"} /> : rowsOf(filtered, () => setHistoryOpen(false))}
    </div>
  </Modal>;
  const renameModal = <Modal title="重命名对话" width={POPUP_WIDTH.sm} open={!!renaming} okText="保存" cancelText="取消" confirmLoading={savingTitle}
    onOk={() => void saveRename()} onCancel={() => { if (!savingTitle) setRenaming(null); }} destroyOnHidden>
    <Input value={newTitle} maxLength={40} showCount autoFocus placeholder="输入新的对话名称" aria-label="对话名称"
      onChange={(event) => setNewTitle(event.target.value)} onPressEnter={() => void saveRename()} />
  </Modal>;
  const caseAgentList = caseAgentConversations.length ? <section className="assistant-case-agent-history" aria-label="案件智能体历史会话">
    <div className="assistant-workspace-history-heading"><FolderOpenOutlined /><h2>案件智能体会话</h2></div>
    <div className="assistant-conversation-list">
      {caseAgentConversations.map((item) => <div className="assistant-conversation-row assistant-case-agent-conversation-row" key={`${item.agent_id}-${item.id}`}>
        <button type="button" className="assistant-conversation-select" disabled={busy || !onSelectCaseAgentConversation} onClick={() => onSelectCaseAgentConversation?.(item)}>
          <MessageOutlined /><span><b title={item.title}>{item.title}</b><small>{item.agent_name} · {item.updated_at ? new Date(item.updated_at).toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }) : ""}</small></span>
        </button>
      </div>)}
    </div>
  </section> : null;
  if (presentation === "sidebar" && typeof navigation === "function") {
    const history = <section className="assistant-workspace-history is-in-space" aria-label={historyTitle || "最近会话"} aria-busy={loading}>
      <div className="assistant-workspace-history-heading"><HistoryOutlined /><h2>{historyTitle || "最近会话"}</h2></div>
      {caseAgentList}
      {sidebarList}
    </section>;
    return <>
      {contextHolder}
      {onRename && renameModal}
      <div className="assistant-workspace-navigation">
        <div className="workspace-conversation-controls">
          <Button icon={<PlusOutlined />} aria-label="新建对话" disabled={busy} onClick={() => create()}><span className="workspace-conversation-label">新建对话</span></Button>
        </div>
        {navigation(history)}
      </div>
      {historyOpen && historyModal()}
    </>;
  }
  if (presentation === "sidebar") return <>
    {contextHolder}
    {onRename && renameModal}
    <div className="assistant-workspace-navigation">
      <div className="workspace-conversation-controls">
        <Button icon={<PlusOutlined />} aria-label="新建对话" disabled={busy} onClick={() => create()}><span className="workspace-conversation-label">新建对话</span></Button>
      </div>
      {navigation as ReactNode}
    </div>
    <section className="assistant-workspace-history" aria-label="历史会话" aria-busy={loading}>
      <div className="assistant-workspace-history-heading"><HistoryOutlined /><h2>历史会话</h2></div>
      {caseAgentList}
      {sidebarList}
    </section>
    {historyOpen && historyModal()}
  </>;
  return <>
    {contextHolder}
    {onRename && renameModal}
    <div className="workspace-conversation-controls">
      <Tooltip title="新建对话"><Button size="small" icon={<PlusOutlined />} aria-label="新建对话" disabled={busy} onClick={() => create()}><span className="workspace-conversation-label">新建对话</span></Button></Tooltip>
      <Tooltip title="对话列表"><Button size="small" type="text" icon={<HistoryOutlined />} aria-label="对话列表" onClick={() => setOpen(true)}>{showHistoryLabel && <span className="workspace-conversation-label">对话列表</span>}</Button></Tooltip>
    </div>
    <Drawer title="我的对话" placement="right" size="min(360px, 100vw)" open={open} onClose={() => setOpen(false)} className={drawerClassName} extra={<Button icon={<PlusOutlined />} disabled={busy} onClick={() => create(true)}>新建对话</Button>}>
      {list}
    </Drawer>
  </>;
}
