import { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  DatePicker,
  Descriptions,
  Divider,
  Form,
  Input,
  List,
  message,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
} from "antd";
import { DeleteOutlined, EditOutlined, MessageOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "./api";
import "./task-center.css";

type VipNode = {
  id: number;
  title: string;
  owner: string;
  priority: string;
  status: string;
  start_at?: string;
  deadline?: string;
  end_at?: string;
  description?: string;
  participants?: string[];
};
type VipMessage = {
  id: number;
  node_id?: number;
  sender: string;
  recipient: string;
  content: string;
  is_read: boolean;
  created_at: string;
  read_at?: string;
};
type VipTask = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  priority: string;
  owner: string;
  department: string;
  description: string;
  start_at?: string;
  end_at?: string;
  deadline?: string;
  collaborators: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
  node_count: number;
  unread_message_count: number;
  nodes?: VipNode[];
  messages?: VipMessage[];
};
type VipQuery = { keyword?: string; customer?: string; status_filter?: string; priority?: string };

const statusColor: Record<string, string> = {
  "待处理": "orange", "处理中": "blue", "进行中": "blue", "已完成": "green", "已验收": "green", "已暂停": "default", "已取消": "default", "已停止": "default", "已拒绝": "red",
};
const priorityOptions = ["紧急", "重要", "普通", "低"].map((value) => ({ value, label: value }));
const statusOptions = ["待处理", "处理中", "已完成", "已验收", "已拒绝", "已暂停", "已取消"].map((value) => ({ value, label: value }));
const formatDate = (value?: string) => value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—";
const dateValue = (value?: string) => value ? dayjs(value) : undefined;

export default function VipTaskCenterPage() {
  const [items, setItems] = useState<VipTask[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [loading, setLoading] = useState(false);
  const [queryForm] = Form.useForm<VipQuery>();
  const [taskForm] = Form.useForm();
  const [nodeForm] = Form.useForm();
  const [messageForm] = Form.useForm();
  const [query, setQuery] = useState<VipQuery>({});
  const [editing, setEditing] = useState<VipTask | null>(null);
  const [detail, setDetail] = useState<VipTask | null>(null);
  const [nodes, setNodes] = useState<VipNode[]>([]);
  const [messages, setMessages] = useState<VipMessage[]>([]);
  const [nodeEditing, setNodeEditing] = useState<VipNode | null>(null);
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [nodeModalOpen, setNodeModalOpen] = useState(false);

  const load = useCallback(async (nextQuery = query, nextPage = page, nextPageSize = pageSize) => {
    setLoading(true);
    try {
      const { data } = await api.get("/vip-tasks", { params: { ...nextQuery, page: nextPage, page_size: nextPageSize } });
      setItems(data.items || []);
      setTotal(Number(data.total || 0));
      setPage(Number(data.page || nextPage));
      setPageSize(Number(data.page_size || nextPageSize));
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "VIP任务加载失败");
    } finally { setLoading(false); }
  }, [page, pageSize, query]);

  const openDetail = async (task: VipTask) => {
    try {
      const [taskResult, messageResult] = await Promise.all([
        api.get(`/vip-tasks/${task.id}`), api.get(`/vip-tasks/${task.id}/messages`),
      ]);
      const loaded = taskResult.data as VipTask;
      setDetail(loaded);
      setNodes(loaded.nodes || []);
      setMessages(messageResult.data.items || loaded.messages || []);
      const unreadIds = (messageResult.data.items || []).filter((item: VipMessage) => !item.is_read).map((item: VipMessage) => item.id);
      if (unreadIds.length) await api.post(`/vip-tasks/${task.id}/messages/read`, { message_ids: unreadIds });
    } catch (error: any) { message.error(error?.response?.data?.detail || "VIP任务详情加载失败"); }
  };

  useEffect(() => { void load(); }, []); // Initial request only; submit handlers own subsequent query changes.

  const openTaskModal = (task?: VipTask) => {
    setEditing(task || null);
    taskForm.resetFields();
    taskForm.setFieldsValue(task ? {
      ...task, start_at: dateValue(task.start_at), end_at: dateValue(task.end_at), deadline: dateValue(task.deadline), collaborators: (task.collaborators || []).join("、"),
    } : { priority: "普通", status: "待处理" });
    setTaskModalOpen(true);
  };
  const saveTask = async () => {
    const values = await taskForm.validateFields();
    const payload = {
      ...values,
      start_at: values.start_at?.toISOString(), end_at: values.end_at?.toISOString(), deadline: values.deadline?.format("YYYY-MM-DD"),
      collaborators: String(values.collaborators || "").split(/[、,，;；\n]/).map((value) => value.trim()).filter(Boolean),
    };
    try {
      if (editing) await api.put(`/vip-tasks/${editing.id}`, payload); else await api.post("/vip-tasks", payload);
      message.success(editing ? "VIP任务已保存" : "VIP任务已创建"); setTaskModalOpen(false); await load(query, 1);
    } catch (error: any) { message.error(error?.response?.data?.detail || "保存VIP任务失败"); }
  };
  const removeTask = async (task: VipTask) => {
    try { await api.delete(`/vip-tasks/${task.id}`); message.success("VIP任务已删除"); if (detail?.id === task.id) setDetail(null); await load(query, 1); }
    catch (error: any) { message.error(error?.response?.data?.detail || "删除VIP任务失败"); }
  };
  const changeTaskStatus = async (status: string) => {
    if (!detail) return;
    try {
      await api.put(`/vip-tasks/${detail.id}`, { status });
      message.success(`VIP任务已更新为“${status}”`);
      await openDetail(detail);
      await load();
    } catch (error: any) { message.error(error?.response?.data?.detail || "VIP任务状态更新失败"); }
  };
  const changeNodeStatus = async (node: VipNode, status: string) => {
    if (!detail) return;
    try {
      await api.put(`/vip-tasks/${detail.id}/nodes/${node.id}`, { status });
      message.success(`VIP任务节点已更新为“${status}”`);
      await refreshNodes();
      await openDetail(detail);
      await load();
    } catch (error: any) { message.error(error?.response?.data?.detail || "VIP任务节点状态更新失败"); }
  };
  const nodeStatusAction = (node: VipNode) => {
    const actions: Array<{ label: string; status: string; danger?: boolean; primary?: boolean }> = [];
    if (node.status === "待处理") actions.push({ label: "开始", status: "处理中" }, { label: "拒绝", status: "已拒绝", danger: true }, { label: "暂停", status: "已暂停" });
    if (node.status === "处理中") actions.push({ label: "完成", status: "已完成", primary: true }, { label: "暂停", status: "已暂停" }, { label: "取消", status: "已取消", danger: true });
    if (node.status === "已暂停") actions.push({ label: "继续", status: "处理中" }, { label: "取消", status: "已取消", danger: true });
    if (node.status === "已完成") actions.push({ label: "验收", status: "已验收", primary: true }, { label: "拒绝", status: "已拒绝", danger: true });
    if (node.status === "已拒绝") actions.push({ label: "重开", status: "待处理" });
    return actions.map((action) => <Button key={action.status} type={action.primary ? "link" : "link"} danger={action.danger} onClick={() => void changeNodeStatus(node, action.status)}>{action.label}</Button>);
  };
  const refreshNodes = async () => {
    if (!detail) return;
    const { data } = await api.get(`/vip-tasks/${detail.id}/nodes`); setNodes(data.items || []);
  };
  const openNodeModal = (node?: VipNode) => {
    setNodeEditing(node || null); nodeForm.resetFields();
    nodeForm.setFieldsValue(node ? { ...node, start_at: dateValue(node.start_at), end_at: dateValue(node.end_at), deadline: dateValue(node.deadline), participants: (node.participants || []).join("、") } : { priority: "普通", status: "待处理" });
    setNodeModalOpen(true);
  };
  const saveNode = async () => {
    if (!detail) return;
    const values = await nodeForm.validateFields();
    const payload = { ...values, start_at: values.start_at?.toISOString(), end_at: values.end_at?.toISOString(), deadline: values.deadline?.format("YYYY-MM-DD"), participants: String(values.participants || "").split(/[、,，;；\n]/).map((value) => value.trim()).filter(Boolean) };
    try {
      if (nodeEditing) await api.put(`/vip-tasks/${detail.id}/nodes/${nodeEditing.id}`, payload); else await api.post(`/vip-tasks/${detail.id}/nodes`, payload);
      message.success(nodeEditing ? "任务节点已保存" : "任务节点已创建"); setNodeModalOpen(false); await refreshNodes(); await load();
    } catch (error: any) { message.error(error?.response?.data?.detail || "保存任务节点失败"); }
  };
  const removeNode = async (node: VipNode) => {
    if (!detail) return;
    try { await api.delete(`/vip-tasks/${detail.id}/nodes/${node.id}`); message.success("任务节点已删除"); await refreshNodes(); await load(); }
    catch (error: any) { message.error(error?.response?.data?.detail || "删除任务节点失败"); }
  };
  const sendMessage = async () => {
    if (!detail) return;
    const values = await messageForm.validateFields();
    try {
      await api.post(`/vip-tasks/${detail.id}/messages`, { node_id: values.node_id || undefined, content: values.content, recipients: String(values.recipients || "").split(/[、,，;；\n]/).map((value) => value.trim()).filter(Boolean) });
      messageForm.resetFields(); const { data } = await api.get(`/vip-tasks/${detail.id}/messages`); setMessages(data.items || []); await load();
    } catch (error: any) { message.error(error?.response?.data?.detail || "发送通知失败"); }
  };

  return <Card className="task-center-page" title="VIP任务" extra={<Button icon={<ReloadOutlined />} onClick={() => void load()}>刷新</Button>}>
    <Form form={queryForm} layout="inline" onFinish={(values) => { setQuery(values); void load(values, 1); }} style={{ marginBottom: 16 }}>
      <Form.Item name="keyword"><Input allowClear placeholder="任务编号、标题或内容" /></Form.Item>
      <Form.Item name="customer"><Input allowClear placeholder="客户" /></Form.Item>
      <Form.Item name="status_filter"><Select allowClear placeholder="状态" style={{ width: 120 }} options={statusOptions} /></Form.Item>
      <Form.Item name="priority"><Select allowClear placeholder="优先级" style={{ width: 110 }} options={priorityOptions} /></Form.Item>
      <Space><Button type="primary" htmlType="submit">查询</Button><Button onClick={() => { queryForm.resetFields(); setQuery({}); void load({}, 1); }}>重置</Button><Button type="primary" icon={<PlusOutlined />} onClick={() => openTaskModal()}>新建VIP任务</Button></Space>
    </Form>
    <Table<VipTask> rowKey="id" loading={loading} dataSource={items} scroll={{ x: 1180 }} pagination={{ current: page, pageSize, total, showSizeChanger: true, showTotal: (value) => `共 ${value} 条` }} onChange={(pagination) => void load(query, pagination.current || 1, pagination.pageSize || pageSize)} columns={[
      { title: "任务编号", dataIndex: "serial_no", width: 145 },
      { title: "任务标题", dataIndex: "title", width: 210, render: (value, row) => <Button type="link" onClick={() => void openDetail(row)}>{value}</Button> },
      { title: "客户", dataIndex: "customer", width: 150, ellipsis: true },
      { title: "负责人", dataIndex: "owner", width: 120 },
      { title: "状态", dataIndex: "status", width: 105, render: (value) => <Tag color={statusColor[value] || "default"}>{value || "—"}</Tag> },
      { title: "优先级", dataIndex: "priority", width: 100, render: (value) => <Tag color={value === "紧急" ? "red" : value === "重要" ? "orange" : "default"}>{value || "普通"}</Tag> },
      { title: "截止日期", dataIndex: "deadline", width: 145, render: formatDate },
      { title: "节点", dataIndex: "node_count", width: 80, align: "center" },
      { title: "未读通知", dataIndex: "unread_message_count", width: 100, align: "center", render: (value) => value ? <Tag color="red">{value}</Tag> : "0" },
      { title: "操作", key: "action", width: 160, fixed: "right", render: (_, row) => <Space size={0}><Button type="link" icon={<MessageOutlined />} onClick={() => void openDetail(row)}>详情</Button><Button type="link" icon={<EditOutlined />} onClick={() => openTaskModal(row)}>编辑</Button><Popconfirm title="确认删除该VIP任务？" onConfirm={() => void removeTask(row)}><Button danger type="link" icon={<DeleteOutlined />}>删除</Button></Popconfirm></Space> },
    ]} />
    <Modal open={taskModalOpen} title={editing ? "编辑VIP任务" : "新建VIP任务"} onCancel={() => setTaskModalOpen(false)} onOk={() => void saveTask()} destroyOnClose width={720}>
      <Form form={taskForm} layout="vertical"><div className="task-form-grid">
        <Form.Item label="任务标题" name="title" rules={[{ required: true, message: "请填写任务标题" }]}><Input /></Form.Item><Form.Item label="客户" name="customer"><Input /></Form.Item>
        <Form.Item label="负责人" name="owner" rules={[{ required: true, message: "请填写负责人" }]}><Input /></Form.Item><Form.Item label="优先级" name="priority"><Select options={priorityOptions} /></Form.Item>
        {editing && <Form.Item label="状态" name="status"><Select options={statusOptions} /></Form.Item>}<Form.Item label="协作人" name="collaborators"><Input placeholder="用顿号或逗号分隔" /></Form.Item>
        <Form.Item label="开始时间" name="start_at"><DatePicker showTime style={{ width: "100%" }} /></Form.Item><Form.Item label="截止日期" name="deadline"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item label="结束时间" name="end_at"><DatePicker showTime style={{ width: "100%" }} /></Form.Item>
      </div><Form.Item label="任务说明" name="description"><Input.TextArea rows={4} /></Form.Item></Form>
    </Modal>
    <Modal open={Boolean(detail)} title={detail ? `VIP任务详情：${detail.title}` : "VIP任务详情"} onCancel={() => setDetail(null)} footer={<Button onClick={() => setDetail(null)}>关闭</Button>} width={980}>
      {detail && <><Descriptions bordered size="small" column={3}><Descriptions.Item label="任务编号">{detail.serial_no}</Descriptions.Item><Descriptions.Item label="客户">{detail.customer || "—"}</Descriptions.Item><Descriptions.Item label="负责人">{detail.owner}</Descriptions.Item><Descriptions.Item label="状态"><Tag color={statusColor[detail.status] || "default"}>{detail.status}</Tag></Descriptions.Item><Descriptions.Item label="优先级">{detail.priority}</Descriptions.Item><Descriptions.Item label="截止日期">{formatDate(detail.deadline)}</Descriptions.Item><Descriptions.Item label="协作人" span={3}>{(detail.collaborators || []).join("、") || "—"}</Descriptions.Item><Descriptions.Item label="任务说明" span={3}>{detail.description || "—"}</Descriptions.Item></Descriptions>
      <Space wrap style={{ marginTop: 12 }} aria-label="VIP任务状态操作">
        {detail.status === "待处理" && <><Button onClick={() => void changeTaskStatus("处理中")}>开始处理</Button><Button danger onClick={() => void changeTaskStatus("已拒绝")}>拒绝任务</Button></>}
        {detail.status === "处理中" && <Button type="primary" onClick={() => void changeTaskStatus("已完成")}>完成任务</Button>}
        {["待处理", "处理中"].includes(detail.status) && <Button onClick={() => void changeTaskStatus("已暂停")}>暂停任务</Button>}
        {detail.status === "已暂停" && <Button onClick={() => void changeTaskStatus("处理中")}>继续任务</Button>}
        {["待处理", "处理中", "已暂停"].includes(detail.status) && <Button danger onClick={() => void changeTaskStatus("已取消")}>取消任务</Button>}
        {detail.status === "已完成" && <><Button type="primary" onClick={() => void changeTaskStatus("已验收")}>验收任务</Button><Button danger onClick={() => void changeTaskStatus("已拒绝")}>拒绝任务</Button><Button onClick={() => void changeTaskStatus("待处理")}>重新打开</Button></>}
        {detail.status === "已拒绝" && <Button onClick={() => void changeTaskStatus("待处理")}>重新打开</Button>}
      </Space>
      <Divider>VIP任务节点 <Button size="small" type="link" icon={<PlusOutlined />} onClick={() => openNodeModal()}>新增节点</Button></Divider>
      <Table<VipNode> size="small" rowKey="id" pagination={false} dataSource={nodes} scroll={{ x: 900 }} columns={[{ title: "节点", dataIndex: "title" }, { title: "负责人", dataIndex: "owner", width: 110 }, { title: "状态", dataIndex: "status", width: 100, render: (value) => <Tag color={statusColor[value] || "default"}>{value}</Tag> }, { title: "优先级", dataIndex: "priority", width: 90 }, { title: "截止日期", dataIndex: "deadline", width: 145, render: formatDate }, { title: "操作", width: 250, render: (_, node) => <Space size={0} wrap>{nodeStatusAction(node)}<Button type="link" onClick={() => openNodeModal(node)}>编辑</Button><Popconfirm title="确认删除该节点？" onConfirm={() => void removeNode(node)}><Button danger type="link">删除</Button></Popconfirm></Space> }]} />
      <Divider>VIP任务消息/通知</Divider>
      <List size="small" bordered dataSource={messages} locale={{ emptyText: "暂无消息" }} renderItem={(item) => <List.Item><List.Item.Meta title={<Space>{item.sender || "系统"}<span>{formatDate(item.created_at)}</span>{!item.is_read && <Tag color="red">未读</Tag>}</Space>} description={item.content} /><span>{item.node_id ? `节点 #${item.node_id}` : "任务消息"}</span></List.Item>} />
      <Form form={messageForm} layout="vertical" style={{ marginTop: 16 }}><Form.Item label="关联节点" name="node_id"><Select allowClear placeholder="可选，选择本条通知所属节点" options={nodes.map((node) => ({ value: node.id, label: node.title }))} /></Form.Item><Form.Item label="通知内容" name="content" rules={[{ required: true, message: "请填写通知内容" }]}><Input.TextArea rows={3} /></Form.Item><Form.Item label="接收人" name="recipients"><Input placeholder="可选，用顿号或逗号分隔；留空由后端按参与人通知" /></Form.Item><Button type="primary" onClick={() => void sendMessage()}>发送通知</Button></Form>
      <Modal open={nodeModalOpen} title={nodeEditing ? "编辑VIP任务节点" : "新增VIP任务节点"} onCancel={() => setNodeModalOpen(false)} onOk={() => void saveNode()} destroyOnClose>
        <Form form={nodeForm} layout="vertical"><Form.Item label="节点名称" name="title" rules={[{ required: true, message: "请填写节点名称" }]}><Input /></Form.Item><Form.Item label="负责人" name="owner" rules={[{ required: true, message: "请填写负责人" }]}><Input /></Form.Item><div className="task-form-grid">{nodeEditing && <Form.Item label="状态" name="status"><Select options={statusOptions} /></Form.Item>}<Form.Item label="优先级" name="priority"><Select options={priorityOptions} /></Form.Item><Form.Item label="开始时间" name="start_at"><DatePicker showTime style={{ width: "100%" }} /></Form.Item><Form.Item label="截止日期" name="deadline"><DatePicker style={{ width: "100%" }} /></Form.Item></div><Form.Item label="参与人" name="participants"><Input placeholder="用顿号或逗号分隔" /></Form.Item><Form.Item label="节点说明" name="description"><Input.TextArea rows={3} /></Form.Item></Form>
      </Modal>
      </>}
    </Modal>
  </Card>;
}
