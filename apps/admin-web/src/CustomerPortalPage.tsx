import { useState } from "react";
import { Alert, Button, Card, Form, Input, message, Select, Space, Table, Tabs, Tag, Typography } from "antd";
import { api } from "./api";

type Credentials = { account: string; activation_code: string };
type PortalData = {
  customer: { serial_no: string; name: string; level: string };
  contracts: Array<{ id: number; serial_no: string; title: string; status: string; data: Record<string, any> }>;
  cases: Array<{ id: number; serial_no: string; title: string; status: string; data: Record<string, any> }>;
  documents: Array<{ id: number; original_name: string; category: string; size: number; created_at: string }>;
};

export default function CustomerPortalPage() {
  const [credentials, setCredentials] = useState<Credentials | null>(null);
  const [data, setData] = useState<PortalData | null>(null);
  const [loading, setLoading] = useState(false);
  const login = async (values: Credentials) => {
    setLoading(true);
    try {
      const response = await api.post("/customer-portal/overview", values);
      setCredentials(values);
      setData(response.data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户服务账号登录失败");
    } finally {
      setLoading(false);
    }
  };
  const download = async (file: PortalData["documents"][number]) => {
    if (!credentials) return;
    try {
      const response = await api.post(`/customer-portal/files/${file.id}/download`, credentials, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = file.original_name; anchor.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "文档下载失败");
    }
  };
  const submitDemand = async (values: { title: string; case_no?: string; content: string }) => {
    if (!credentials) return;
    try {
      const response = await api.post("/customer-portal/demands", { ...credentials, ...values });
      message.success(`需求已提交，任务编号：${response.data.serial_no}`);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "需求提交失败");
    }
  };
  if (!data) return (
    <div style={{ minHeight: "100vh", background: "#f3f5f7", padding: "10vh 16px" }}>
      <Card title="申浩客户服务端" style={{ maxWidth: 460, margin: "0 auto" }}>
        <Alert type="info" showIcon message="签约客户可查看合同、案件进展并下载已共享文档" style={{ marginBottom: 20 }} />
        <Form layout="vertical" onFinish={login}>
          <Form.Item name="account" label="客户服务账号" rules={[{ required: true }]}><Input autoComplete="username" /></Form.Item>
          <Form.Item name="activation_code" label="激活码" rules={[{ required: true }]}><Input.Password autoComplete="current-password" /></Form.Item>
          <Button loading={loading} type="primary" htmlType="submit" block>登录客户服务端</Button>
        </Form>
      </Card>
    </div>
  );
  return (
    <div style={{ minHeight: "100vh", background: "#f3f5f7", padding: 24 }}>
      <Card style={{ maxWidth: 1200, margin: "0 auto" }}>
        <Space style={{ width: "100%", justifyContent: "space-between" }}>
          <div><Typography.Title level={3}>{data.customer.name}</Typography.Title><Tag color="green">{data.customer.level || "签约客户"}</Tag> 客户编号：{data.customer.serial_no}</div>
          <Button onClick={() => { setCredentials(null); setData(null); }}>退出</Button>
        </Space>
        <Tabs style={{ marginTop: 20 }} items={[
          { key: "cases", label: `案件进展（${data.cases.length}）`, children: <Table rowKey="id" dataSource={data.cases} columns={[{ title: "案件编号", dataIndex: "serial_no" }, { title: "案件名称", dataIndex: "title" }, { title: "当前阶段", dataIndex: "status", render: (value) => <Tag color="blue">{value}</Tag> }, { title: "法院", render: (_, row) => row.data.court || row.data.first_court_name || "—" }]} /> },
          { key: "contracts", label: `合同（${data.contracts.length}）`, children: <Table rowKey="id" dataSource={data.contracts} columns={[{ title: "合同编号", dataIndex: "serial_no" }, { title: "合同名称", dataIndex: "title" }, { title: "状态", dataIndex: "status" }, { title: "外部合同号", render: (_, row) => (row.data.external_contract_numbers || [row.data.external_contract_no]).filter(Boolean).join("、") || "—" }]} /> },
          { key: "documents", label: `文档下载（${data.documents.length}）`, children: <Table rowKey="id" dataSource={data.documents} columns={[{ title: "文件名", dataIndex: "original_name" }, { title: "类别", dataIndex: "category" }, { title: "大小", dataIndex: "size", render: (value) => `${Math.ceil(Number(value || 0) / 1024)} KB` }, { title: "操作", render: (_, row) => <Button type="link" onClick={() => download(row)}>下载</Button> }]} /> },
          { key: "requests", label: "提交需求", children: <div style={{ maxWidth: 680 }}><Alert type="info" showIcon message="需求提交后会生成真实客户任务并分派给客户负责人。" style={{ marginBottom: 16 }} /><Form layout="vertical" onFinish={submitDemand}><Form.Item label="需求标题" name="title" rules={[{ required: true, min: 2 }]}><Input /></Form.Item><Form.Item label="关联案件" name="case_no"><Select allowClear options={data.cases.map((item) => ({ value: item.serial_no, label: `${item.serial_no}｜${item.title}` }))} /></Form.Item><Form.Item label="具体需求" name="content" rules={[{ required: true, min: 2 }]}><Input.TextArea rows={5} /></Form.Item><Button type="primary" htmlType="submit">提交服务需求</Button></Form></div> },
        ]} />
      </Card>
    </div>
  );
}
