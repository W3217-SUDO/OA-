import { Button, Form, Input, Modal, Select, Space, Tag } from "antd";
import { DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import { useState } from "react";

export type InvestigationParty = {
  nature?: string; name: string; confirmation_method?: string; identity_no?: string;
  legal_representative?: string; province?: string; city?: string; district?: string;
  region?: string | string[]; business_address?: string; address?: string;
};
type Props = { value?: InvestigationParty[]; onChange?: (value: InvestigationParty[]) => void };
const NATURE_OPTIONS = ["企业", "个体工商户", "个人", "其他"].map((value) => ({ value, label: value }));
const CONFIRMATION_OPTIONS = ["工商信息", "工商登记", "现场确认", "客户提供", "网络核验", "其他"].map((value) => ({ value, label: value }));
function regionParts(value: InvestigationParty["region"]) {
  const parts = Array.isArray(value) ? value : String(value || "").split(/[\s/]+/).filter(Boolean);
  return { province: parts[0] || "", city: parts[1] || "", district: parts[2] || "" };
}
export default function InvestigationPartyEditor({ value = [], onChange }: Props) {
  const [open, setOpen] = useState(false); const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [form] = Form.useForm<InvestigationParty>(); const nature = Form.useWatch("nature", form) || "企业";
  const parties = Array.isArray(value) ? value : [];
  const startCreate = () => { setEditingIndex(null); form.resetFields(); form.setFieldsValue({ nature: "企业", confirmation_method: "工商信息" }); setOpen(true); };
  const startEdit = (index: number) => { const party = parties[index] || {}; setEditingIndex(index); form.setFieldsValue({ ...party, ...regionParts(party.region), business_address: party.business_address || party.address || "" }); setOpen(true); };
  const save = async () => {
    const next = await form.validateFields();
    const region = [next.province, next.city, next.district].map((item) => item?.trim()).filter(Boolean).join(" ");
    const address = next.business_address?.trim() || next.address?.trim() || "";
    const normalized = { ...next, name: next.name.trim(), identity_no: next.identity_no?.trim() || "", legal_representative: next.legal_representative?.trim() || "", region: region || (Array.isArray(next.region) ? next.region.join(" ") : String(next.region || "").trim()), business_address: address, address };
    const nextParties = [...parties]; if (editingIndex === null) nextParties.push(normalized); else nextParties[editingIndex] = normalized; onChange?.(nextParties); setOpen(false);
  };
  return <>
    <Space wrap>{parties.map((party, index) => <Tag key={`${party.name || "party"}-${index}`} closable closeIcon={<DeleteOutlined />} onClose={(event) => { event.preventDefault(); onChange?.(parties.filter((_, itemIndex) => itemIndex !== index)); }}>{party.name || "未命名主体"}<Button type="link" size="small" icon={<EditOutlined />} aria-label={`编辑主体 ${party.name || index + 1}`} onClick={() => startEdit(index)} /></Tag>)}<Button type="dashed" icon={<PlusOutlined />} onClick={startCreate}>新增主体</Button></Space>
    <Modal open={open} width={660} title={editingIndex === null ? "新增经营主体" : "修改经营主体"} okText="确定" cancelText="取消" onOk={() => void save()} onCancel={() => setOpen(false)} destroyOnHidden>
      <Form form={form} layout="vertical"><div className="form-grid">
        <Form.Item label="经营性质" name="nature" rules={[{ required: true, message: "请选择经营性质" }]}><Select options={NATURE_OPTIONS} /></Form.Item>
        <Form.Item label="主体名称" name="name" rules={[{ required: true, message: "请输入主体名称" }]}><Input /></Form.Item>
        <Form.Item label="确认方式" name="confirmation_method" rules={[{ required: true, message: "请选择确认方式" }]}><Select options={CONFIRMATION_OPTIONS} /></Form.Item>
        <Form.Item label={nature === "个人" ? "身份证号" : "主体标识"} name="identity_no" rules={nature === "个人" ? [{ required: true, message: "请输入身份证号" }] : []}><Input /></Form.Item>
        {nature !== "个人" && <Form.Item label={nature === "个体工商户" ? "经营者" : "法定代表人"} name="legal_representative"><Input /></Form.Item>}
        <Form.Item label="省" name="province"><Input placeholder="省" /></Form.Item><Form.Item label="市" name="city"><Input placeholder="市" /></Form.Item><Form.Item label="区/县" name="district"><Input placeholder="区/县" /></Form.Item>
        <Form.Item className="span-2" label="经营地址" name="business_address" rules={[{ required: true, message: "请输入经营地址" }]}><Input /></Form.Item>
      </div></Form>
    </Modal>
  </>;
}
