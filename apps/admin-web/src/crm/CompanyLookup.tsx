import { useState } from "react";
import { Alert, Button, Descriptions, List, Modal, Tag, message } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import type { FormInstance } from "antd";
import { api } from "../api";
import { POPUP_WIDTH } from "../components/common/popupSize";

type Candidate = { name: string; credit_code: string; legal_person: string; start_date: string; status: string; address: string; abnormal: boolean };
type Detail = {
  name: string; credit_code: string; legal_representative: string; registered_address: string; organization_type: string;
  phone: string; registered_capital: string; established_date: string; status: string; business_scope: string;
  registration_authority: string; abnormal: boolean; source: string; queried_at: string;
};
type Duplicate = { id: number; serial_no: string; title: string; deleted: boolean; matched_by: string };
export type BusinessRegistration = Pick<Detail, "registered_capital" | "established_date" | "status" | "business_scope" | "registration_authority" | "source" | "queried_at">;

const errorText = (failure: unknown, fallback: string) => {
  const detail = (failure as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" && detail ? detail : fallback;
};

/** 新建客户“查企业”（501106）：输入至少 2 个字查企查查（模糊搜索未开通时按全称直接查），选中后带出工商信息，所有字段仍可手改；先查重再带入。 */
export function CompanyLookup({ form, disabled }: { form: FormInstance; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<Candidate[]>([]);
  const [error, setError] = useState("");
  const [picking, setPicking] = useState("");
  const [hint, setHint] = useState("");
  const search = async () => {
    const keyword = String(form.getFieldValue("title") || "").trim();
    if (keyword.length < 2) { message.warning("请先在客户名称里输入至少 2 个字"); return; }
    setOpen(true); setLoading(true); setError(""); setHint(""); setItems([]);
    try {
      // 模糊搜索接口没开通时，后端改按全称或信用代码直接查工商信息（mode=exact），这里提示要输全称。
      const { data } = await api.get<{ items: Candidate[]; mode?: string; hint?: string }>("/company-lookup/search", { params: { keyword } });
      setItems(data.items); setHint(data.mode === "exact" ? data.hint || "" : "");
    }
    catch (failure) { setError(errorText(failure, "查询失败，请手工填写")); }
    finally { setLoading(false); }
  };
  const pick = async (item: Candidate) => {
    setPicking(item.credit_code || item.name);
    try {
      const { data } = await api.get<Detail>("/company-lookup/detail", { params: { keyword: item.credit_code || item.name } });
      const { data: duplicates } = await api.get<{ items: Duplicate[] }>("/company-lookup/duplicates", { params: { credit_code: data.credit_code, name: data.name } });
      const current = form.getFieldsValue();
      form.setFieldsValue({
        title: data.name || current.title, credit_code: data.credit_code || current.credit_code,
        legal_representative: data.legal_representative || current.legal_representative,
        registered_address: data.registered_address || current.registered_address,
        invoice_address: current.invoice_address || data.registered_address,
        organization_type: data.organization_type || current.organization_type,
        phone: data.phone || current.phone, registered_capital: data.registered_capital || current.registered_capital,
        business_registration: { registered_capital: data.registered_capital, established_date: data.established_date, status: data.status,
          business_scope: data.business_scope, registration_authority: data.registration_authority, source: data.source, queried_at: data.queried_at },
        company_duplicates: duplicates.items,
      });
      setOpen(false);
      if (duplicates.items.length) message.warning(`已有客户 ${duplicates.items[0].title}（${duplicates.items[0].serial_no}${duplicates.items[0].deleted ? "，在回收站" : ""}），请勿重复新建`);
      else message.success("已带出工商信息，可再修改");
    } catch (failure) { message.error(errorText(failure, "读取工商信息失败，请手工填写")); }
    finally { setPicking(""); }
  };
  return <>
    <Button icon={<SearchOutlined />} disabled={disabled} onClick={() => void search()}>查企业</Button>
    <Modal title="从企查查查企业" open={open} width={POPUP_WIDTH.md} footer={null} onCancel={() => setOpen(false)} destroyOnHidden>
      {error && <Alert type="warning" showIcon title={error} />}
      {hint && !error && <Alert type="info" showIcon title={hint} style={{ marginBottom: 8 }} />}
      <List loading={loading} dataSource={items} locale={{ emptyText: loading ? "查询中" : "没有找到匹配的企业，请换个关键词或手工填写" }}
        renderItem={(item) => <List.Item actions={[<Button key="pick" type="link" loading={picking === (item.credit_code || item.name)} disabled={!!picking} onClick={() => void pick(item)}>选择</Button>]}>
          <List.Item.Meta title={<span>{item.name} {item.status && <Tag color={item.abnormal ? "error" : "success"}>{item.status}</Tag>}</span>}
            description={`法人：${item.legal_person || "—"} · 成立：${item.start_date || "—"} · 信用代码：${item.credit_code || "—"}`} />
        </List.Item>} />
    </Modal>
  </>;
}

/** 客户资料里的工商信息（只读）。 */
export function BusinessRegistrationInfo({ value, duplicates }: { value?: BusinessRegistration; duplicates?: Duplicate[] }) {
  if (!value && !duplicates?.length) return null;
  return <div className="customer-business-registration">
    {!!duplicates?.length && <Alert type="error" showIcon title={`已有客户：${duplicates.map((item) => `${item.title}（${item.serial_no}${item.deleted ? "，在回收站" : ""}，按${item.matched_by}）`).join("；")}，不能重复新建`} />}
    {value && <Descriptions size="small" column={2} bordered title={`工商信息（来自${value.source || "企查查"}，查询时间 ${value.queried_at ? new Date(value.queried_at).toLocaleString("zh-CN") : "—"}）`}>
      <Descriptions.Item label="注册资本">{value.registered_capital || "—"}</Descriptions.Item>
      <Descriptions.Item label="成立日期">{value.established_date || "—"}</Descriptions.Item>
      <Descriptions.Item label="经营状态"><span style={{ color: /注销|吊销|撤销|停业|清算/.test(value.status || "") ? "#cf1322" : undefined }}>{value.status || "—"}</span></Descriptions.Item>
      <Descriptions.Item label="登记机关">{value.registration_authority || "—"}</Descriptions.Item>
      <Descriptions.Item label="经营范围" span={2}>{value.business_scope || "—"}</Descriptions.Item>
    </Descriptions>}
  </div>;
}
