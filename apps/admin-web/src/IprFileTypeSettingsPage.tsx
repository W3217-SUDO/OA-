import { useEffect, useState } from "react";
import { Button, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Switch, Table, message } from "antd";
import { api } from "./api";

type FileType = { id: number; code: string; name: string; sort_order: number; is_active: boolean; extra: { case_kinds?: string[]; requires_transmission?: boolean; allow_repeat?: boolean; hedging_file_type_codes?: string[]; hedging_fee_type_codes?: string[] } };

const category = "ipr_case_file_type";

export default function IprFileTypeSettingsPage() {
  const [items, setItems] = useState<FileType[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<FileType | null>(null);
  const [form] = Form.useForm();
  const load = async () => {
    try { const { data } = await api.get("/system/parameters", { params: { category } }); setItems(data.items || []); }
    catch (error: any) { message.error(error?.response?.data?.detail || "文件类型加载失败"); }
  };
  useEffect(() => { void load(); }, []);
  const start = (row?: FileType) => {
    setEditing(row || null); form.resetFields();
    form.setFieldsValue(row ? { ...row, ...row.extra, hedging_file_type_codes: (row.extra.hedging_file_type_codes || []).join(","), hedging_fee_type_codes: (row.extra.hedging_fee_type_codes || []).join(",") } : { case_kinds: ["专利", "商标"], allow_repeat: true, is_active: true, sort_order: items.length + 1 });
    setOpen(true);
  };
  const save = async () => {
    try {
      const value = await form.validateFields();
      const extra = { case_kinds: value.case_kinds, is_official: false, requires_transmission: !!value.requires_transmission, allow_repeat: value.allow_repeat !== false, hedging_file_type_codes: (value.hedging_file_type_codes || "").split(",").map((x: string) => x.trim()).filter(Boolean), hedging_fee_type_codes: (value.hedging_fee_type_codes || "").split(",").map((x: string) => x.trim()).filter(Boolean) };
      const payload = { category, code: value.code, name: value.name, sort_order: value.sort_order, is_active: value.is_active, extra };
      if (editing) await api.patch(`/system/parameters/${editing.id}`, payload); else await api.post("/system/parameters", payload);
      message.success("文件类型已保存"); setOpen(false); await load();
    } catch (error: any) { if (!error?.errorFields) message.error(error?.response?.data?.detail || "文件类型保存失败"); }
  };
  const remove = async (row: FileType) => { try { await api.delete(`/system/parameters/${row.id}`); message.success("文件类型已删除"); await load(); } catch (error: any) { message.error(error?.response?.data?.detail || "文件类型删除失败"); } };
  return <><Table rowKey="id" dataSource={items} size="small" scroll={{ x: 900 }} title={() => <Space><span>知识产权案件文件类型</span><Button type="primary" onClick={() => start()}>新增类型</Button></Space>} columns={[
    { title: "类型代码", dataIndex: "code", width: 150 }, { title: "类型名称", dataIndex: "name", width: 220 },
    { title: "适用案件", width: 140, render: (_, row: FileType) => (row.extra.case_kinds || []).join("、") || "全部" },
    { title: "待转文", width: 100, render: (_, row: FileType) => row.extra.requires_transmission ? "是" : "否" },
    { title: "允许重复", width: 100, render: (_, row: FileType) => row.extra.allow_repeat === false ? "否" : "是" },
    { title: "状态", width: 90, render: (_, row: FileType) => row.is_active ? "启用" : "停用" },
    { title: "操作", fixed: "right", width: 130, render: (_, row: FileType) => <Space size={0}><Button type="link" onClick={() => start(row)}>修改</Button><Popconfirm title="确认删除此文件类型？" onConfirm={() => void remove(row)}><Button danger type="link">删除</Button></Popconfirm></Space> },
  ]} />
  <Modal open={open} title={editing ? "修改知识产权案件文件类型" : "新增知识产权案件文件类型"} onCancel={() => setOpen(false)} onOk={() => void save()} destroyOnHidden><Form form={form} layout="vertical">
    <Form.Item name="code" label="类型代码" rules={[{ required: true }]}><Input maxLength={64} /></Form.Item><Form.Item name="name" label="类型名称" rules={[{ required: true }]}><Input maxLength={255} /></Form.Item>
    <Form.Item name="case_kinds" label="适用案件类型" rules={[{ required: true }]}><Select mode="multiple" options={[{ value: "专利" }, { value: "商标" }]} /></Form.Item>
    <Form.Item name="requires_transmission" label="需要转文" valuePropName="checked"><Switch checkedChildren="是" unCheckedChildren="否" /></Form.Item><Form.Item name="allow_repeat" label="允许重复上传" valuePropName="checked"><Switch checkedChildren="是" unCheckedChildren="否" /></Form.Item>
    <Form.Item name="hedging_file_type_codes" label="旧文件对冲类型代码"><Input placeholder="多个代码用英文逗号分隔" /></Form.Item><Form.Item name="hedging_fee_type_codes" label="费用对冲类型代码"><Input placeholder="多个代码用英文逗号分隔" /></Form.Item>
    <Form.Item name="sort_order" label="排序号" rules={[{ required: true }]}><InputNumber min={0} style={{ width: "100%" }} /></Form.Item><Form.Item name="is_active" label="是否启用" valuePropName="checked"><Switch /></Form.Item>
  </Form></Modal></>;
}
