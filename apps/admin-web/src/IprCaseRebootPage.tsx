import { useState } from "react";
import { Alert, Button, Card, Descriptions, Form, Input, Space, Steps, message } from "antd";
import { api } from "./api";

// BUG20261030004：知识产权中心“案件重提”单独菜单，照老系统 输入原案号 → 确认案件信息 → 重提。
type RebootLookup = {
  source_case_id: number;
  source_case_no: string;
  source_title: string;
  source_status: string;
  next_serial_no: string;
  case_kind: string;
  case_type: string;
  customer: string;
  application_no: string;
  application_date: string;
  procurator: string;
  can_reboot: boolean;
};

const errorDetail = (error: any, fallback: string) => error?.response?.data?.detail || fallback;

export default function IprCaseRebootPage() {
  const [caseNo, setCaseNo] = useState("");
  const [lookup, setLookup] = useState<RebootLookup | null>(null);
  const [created, setCreated] = useState<{ id: number; serial_no: string; case_kind: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const next = async () => {
    const value = caseNo.trim();
    if (!value) {
      message.warning("请输入原案号");
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.get<RebootLookup>("/ipr/case-reboot/lookup", { params: { case_no: value } });
      setLookup(data);
      form.resetFields();
    } catch (error) {
      message.error(errorDetail(error, "找不到该案件"));
    } finally {
      setLoading(false);
    }
  };

  const submit = async () => {
    if (!lookup) return;
    setLoading(true);
    try {
      const values = await form.validateFields();
      const { data } = await api.post(`/ipr/cases/${lookup.source_case_id}/reboot`, { reason: String(values.reason || "").trim() });
      setCreated({ id: data.id, serial_no: data.serial_no, case_kind: lookup.case_kind });
      message.success(`已重提为新案件 ${data.serial_no}`);
    } catch (error) {
      message.error(errorDetail(error, "案件重提失败"));
    } finally {
      setLoading(false);
    }
  };

  const restart = () => {
    setCaseNo("");
    setLookup(null);
    setCreated(null);
    form.resetFields();
  };

  const openCreated = () => {
    if (!created) return;
    const params = new URLSearchParams(window.location.search);
    params.set("page", created.case_kind === "商标" ? "ipr-trademark" : "ipr-patent");
    params.set("record_id", String(created.id));
    window.location.search = params.toString();
  };

  const step = created ? 2 : lookup ? 1 : 0;
  return (
    <div className="page-shell">
      <Card size="small" title="案件重提">
        <Steps size="small" current={step} style={{ marginBottom: 16 }} items={[{ title: "输入需要重新提交的案号" }, { title: "确认案件信息" }, { title: "完成" }]} />
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message={<>
            <div>1. 对于未产生费用的案件发生小的变动，请直接在原案件中修改。</div>
            <div>2. 案件重新提交后，产生新的案号为原案号+版本号（A、B、C）。</div>
            <div>3. 案件重新提交后，原案件信息复制到新案件中，原案件保留不变。</div>
          </>}
        />
        {step === 0 && (
          <Space>
            <span>原案号：</span>
            <Input value={caseNo} onChange={(event) => setCaseNo(event.target.value)} onPressEnter={() => void next()} style={{ width: 260 }} allowClear />
            <Button type="primary" loading={loading} onClick={() => void next()}>下一步</Button>
          </Space>
        )}
        {step === 1 && lookup && (
          <>
            <Descriptions bordered size="small" column={2} items={[
              { key: "no", label: "原案号", children: lookup.source_case_no },
              { key: "next", label: "新案号", children: lookup.next_serial_no },
              { key: "title", label: "案件名称", children: lookup.source_title },
              { key: "status", label: "原案件状态", children: lookup.source_status },
              { key: "kind", label: "案件类型", children: [lookup.case_kind, lookup.case_type].filter(Boolean).join(" / ") || "—" },
              { key: "customer", label: "客户", children: lookup.customer || "—" },
              { key: "appno", label: "申请号", children: lookup.application_no || "—" },
              { key: "appdate", label: "申请日", children: lookup.application_date || "—" },
              { key: "procurator", label: "代理人", children: lookup.procurator || "—" },
            ]} />
            {!lookup.can_reboot && <Alert type="warning" showIcon style={{ marginTop: 12 }} message={`原案件状态为“${lookup.source_status}”，不能重提`} />}
            <Form form={form} layout="vertical" style={{ marginTop: 16, maxWidth: 640 }}>
              <Form.Item name="reason" label="重提说明">
                <Input.TextArea rows={3} maxLength={1000} />
              </Form.Item>
            </Form>
            <Space>
              <Button onClick={() => setLookup(null)}>上一步</Button>
              <Button type="primary" loading={loading} disabled={!lookup.can_reboot} onClick={() => void submit()}>确认重提</Button>
            </Space>
          </>
        )}
        {step === 2 && created && (
          <Space direction="vertical">
            <Alert type="success" showIcon message={`已生成新案件 ${created.serial_no}`} />
            <Space>
              <Button type="primary" onClick={openCreated}>打开新案件</Button>
              <Button onClick={restart}>继续重提其他案件</Button>
            </Space>
          </Space>
        )}
      </Card>
    </div>
  );
}
