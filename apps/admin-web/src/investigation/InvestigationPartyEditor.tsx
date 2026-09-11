import { Button, Cascader, Form, Input, Modal, Select, Space, Tag, Typography } from "antd";
import { DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import { useMemo, useState } from "react";
import { useCascaderAreaData } from "@vant/area-data";

export type InvestigationParty = {
  nature?: string;
  name: string;
  confirmation_method?: string;
  identity_no?: string;
  license_no?: string;
  legal_representative?: string;
  province?: string;
  city?: string;
  district?: string;
  region?: string | string[];
  business_address?: string;
  address?: string;
};
type Props = { value?: InvestigationParty[]; onChange?: (value: InvestigationParty[]) => void };

type RegionOption = { value: string; label: string; children?: RegionOption[] };
const NATURE_OPTIONS = ["企业", "个体工商户", "个人", "其他"].map((value) => ({ value, label: value }));
const CONFIRMATION_OPTIONS = ["经营主体", "发票主体", "收款主体", "名片", "店招", "印章", "地址倒查", "工商信息", "工商登记", "现场确认", "客户提供", "网络核验", "其他"].map((value) => ({ value, label: value }));

function regionParts(value: InvestigationParty["region"], party?: InvestigationParty) {
  const parts = Array.isArray(value) ? value : String(value || "").split(/[\s/,，、;；]+/).filter(Boolean);
  return {
    province: party?.province || parts[0] || "",
    city: party?.city || parts[1] || "",
    district: party?.district || parts[2] || "",
  };
}

function normalizeParty(party: InvestigationParty): InvestigationParty {
  const name = String(party.name || (party as any).indictee || "").trim();
  const identity = String(party.identity_no || party.license_no || "").trim();
  const { province, city, district } = regionParts(party.region, party);
  const region = [province, city, district].filter(Boolean);
  const address = String(party.business_address || party.address || "").trim();
  return {
    ...party,
    name,
    identity_no: identity,
    license_no: identity,
    province,
    city,
    district,
    region,
    business_address: address,
    address,
  };
}

export default function InvestigationPartyEditor({ value = [], onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [form] = Form.useForm<InvestigationParty>();
  const nature = Form.useWatch("nature", form) || "企业";
  const requiresRepresentative = nature === "企业" || nature === "个体工商户";
  const parties = useMemo(() => (Array.isArray(value) ? value : []).map(normalizeParty), [value]);
  const areaData = useCascaderAreaData() as Array<{ text: string; value?: string; children?: Array<{ text: string; value?: string; children?: Array<{ text: string; value?: string }> }> }>;
  const regionOptions = useMemo<RegionOption[]>(() => areaData.map((province) => ({
    value: province.text,
    label: province.text,
    children: (province.children || []).map((city) => ({
      value: city.text,
      label: city.text,
      children: (city.children || []).map((district) => ({ value: district.text, label: district.text })),
    })),
  })), [areaData]);

  const startCreate = () => {
    setEditingIndex(null);
    form.resetFields();
    form.setFieldsValue({ nature: "企业", confirmation_method: "工商信息", region: [] });
    setOpen(true);
  };
  const startEdit = (index: number) => {
    const party = parties[index] || { name: "" };
    setEditingIndex(index);
    form.setFieldsValue({ ...party, ...regionParts(party.region, party), region: Array.isArray(party.region) ? party.region : [party.province, party.city, party.district].filter((item): item is string => Boolean(item)) });
    setOpen(true);
  };
  const save = async () => {
    const next = await form.validateFields();
    const path = Array.isArray(next.region) ? next.region.filter(Boolean).map(String) : [];
    const [province = "", city = "", district = ""] = path;
    const address = String(next.business_address || next.address || "").trim();
    const identity = String(next.identity_no || next.license_no || "").trim();
    const normalized: InvestigationParty = {
      ...next,
      name: String(next.name || "").trim(),
      identity_no: identity,
      license_no: identity,
      legal_representative: String(next.legal_representative || "").trim(),
      province: province || String(next.province || "").trim(),
      city: city || String(next.city || "").trim(),
      district: district || String(next.district || "").trim(),
      region: path.length ? path : [next.province, next.city, next.district].filter((item): item is string => Boolean(item)),
      business_address: address,
      address,
    };
    const nextParties = [...parties];
    if (editingIndex === null) nextParties.push(normalized);
    else nextParties[editingIndex] = normalized;
    onChange?.(nextParties);
    setOpen(false);
  };
  const remove = (index: number) => onChange?.(parties.filter((_, itemIndex) => itemIndex !== index));

  return <Space direction="vertical" style={{ width: "100%" }} size={8}>
    <Space wrap>
      {parties.map((party, index) => <Tag key={`${party.name || "party"}-${index}`} closable closeIcon={<DeleteOutlined />} onClose={(event) => { event.preventDefault(); remove(index); }}>
        {party.name || `主体信息${index + 1}`}
        <Button type="link" size="small" icon={<EditOutlined />} aria-label={`编辑主体 ${party.name || index + 1}`} onClick={() => startEdit(index)} />
      </Tag>)}
      <Button type="dashed" icon={<PlusOutlined />} onClick={startCreate}>新增主体</Button>
    </Space>
    {parties.length > 0 && <div className="investigation-party-summary" style={{ display: "grid", gap: 6 }}>
      {parties.map((party, index) => <Typography.Text type="secondary" key={`summary-${index}`}>
        主体信息{index + 1}：{[party.nature, party.name, party.confirmation_method, party.identity_no, party.legal_representative, [party.province, party.city, party.district].filter(Boolean).join("/"), party.business_address].filter(Boolean).join(" / ")}
      </Typography.Text>)}
    </div>}
    <Modal open={open} width={700} title={editingIndex === null ? "新增经营主体" : `修改经营主体${editingIndex + 1}`} okText="确定" cancelText="取消" onOk={() => void save()} onCancel={() => setOpen(false)} destroyOnHidden>
      <Form form={form} layout="vertical">
        <div className="form-grid">
          <Form.Item label="经营性质" name="nature" rules={[{ required: true, message: "请选择经营性质" }]}><Select options={NATURE_OPTIONS} /></Form.Item>
          <Form.Item label="主体名称" name="name" rules={[{ required: true, message: "请输入主体名称" }]}><Input /></Form.Item>
          <Form.Item label="确认方式" name="confirmation_method" rules={[{ required: true, message: "请选择确认方式" }]}><Select options={CONFIRMATION_OPTIONS} /></Form.Item>
          <Form.Item label={nature === "个人" ? "身份证号" : "证照号码"} name="identity_no" rules={[{ required: true, message: nature === "个人" ? "请输入身份证号" : "请输入主体标识" }]}><Input /></Form.Item>
          {requiresRepresentative && <Form.Item label={nature === "个体工商户" ? "经营者" : "法定代表人"} name="legal_representative" rules={[{ required: true, message: nature === "个体工商户" ? "请输入经营者" : "请输入法定代表人" }]}><Input /></Form.Item>}
          <Form.Item className="span-2" label="省/市/区县" name="region" rules={[{ required: true, type: "array", min: 3, message: "请选择省、市、区/县" }]}><Cascader options={regionOptions} showSearch expandTrigger="hover" placeholder="请选择省、市、区/县" /></Form.Item>
          <Form.Item className="span-2" label="工商地址" name="business_address" rules={[{ required: true, message: "请输入工商地址" }]}><Input /></Form.Item>
        </div>
      </Form>
    </Modal>
  </Space>;
}
