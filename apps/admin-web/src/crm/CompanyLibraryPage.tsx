import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Drawer, Empty, Input, List, Space, Tag, message } from "antd";
import { DownloadOutlined, FileWordOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import Table from "../components/ResizableTable";
import { api } from "../api";

// 501368（陶国南 11-04）：当事人中心 › 企业信息查询。按名称或信用代码查企业：先看本所存档（不扣次数），没有才查一次企查查，
// 结果存进企业信息库。库里的企业不是客户也不是当事人、不进利益冲突检索；在这里“新建客户”“新建当事人”后才进入角色。
import { COMPANY_PREFILL_KEY, type LibraryCompany, type LibraryRoles as Roles } from "./companyLibrary";

type LibraryDocument = { id: number; kind: "basic" | "due_diligence"; label: string; name: string; created_by: string; created_at: string; size: number };

const errorText = (failure: unknown, fallback: string) => {
  const detail = (failure as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" && detail ? detail : fallback;
};

export default function CompanyLibraryPage({ onCreateCustomer }: { onCreateCustomer?: () => void }) {
  const [keyword, setKeyword] = useState("");
  const [rows, setRows] = useState<LibraryCompany[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [looking, setLooking] = useState(false);
  const [error, setError] = useState("");
  const [viewing, setViewing] = useState<LibraryCompany | null>(null);
  const [creating, setCreating] = useState("");
  // 501368（陶国南 11-04 17:27）：企业基本信息表、尽职调查报告在这里生成/重新生成和查看历史版本，不关联案件。
  const [documents, setDocuments] = useState<LibraryDocument[]>([]);
  const [generating, setGenerating] = useState("");
  const companyKey = (company: LibraryCompany) => company.credit_code || company.name;
  const loadDocuments = async (company: LibraryCompany) => {
    try { setDocuments((await api.get("/company-library/documents", { params: { keyword: companyKey(company) } })).data.items); }
    catch { setDocuments([]); }
  };
  const openCompany = (company: LibraryCompany) => { setViewing(company); setDocuments([]); void loadDocuments(company); };
  const generate = async (company: LibraryCompany, kind: "basic" | "due_diligence") => {
    setGenerating(kind);
    try {
      const { data } = await api.post("/company-library/documents", { keyword: companyKey(company), kind });
      message.success(`已生成${data.label}${kind === "due_diligence" && !data.risk && data.risk_note ? `（${data.risk_note}）` : ""}`);
      await loadDocuments(company);
    } catch (failure) { message.error(errorText(failure, "生成失败")); }
    finally { setGenerating(""); }
  };
  const download = async (item: LibraryDocument) => {
    try {
      const response = await api.get(`/company-library/documents/${item.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data), link = document.createElement("a");
      link.href = url; link.download = item.name; link.click(); URL.revokeObjectURL(url);
    } catch { message.error("下载失败"); }
  };

  const load = useCallback(async (nextPage = 1, term = keyword) => {
    setLoading(true); setError("");
    try {
      const { data } = await api.get("/company-library", { params: { keyword: term.trim(), page: nextPage, page_size: 20 } });
      setRows(data.items); setTotal(data.total); setPage(nextPage);
    } catch (failure) { setError(errorText(failure, "企业信息库加载失败")); }
    finally { setLoading(false); }
  }, [keyword]);
  useEffect(() => { void load(1, ""); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const lookup = async (refresh = false, target = keyword) => {
    const term = target.trim();
    if (term.length < 2) { message.warning("请输入企业全称或统一社会信用代码"); return; }
    setLooking(true); setError("");
    try {
      const { data } = await api.post<LibraryCompany>("/company-library/lookup", { keyword: term, refresh });
      message.success(data.cached ? "已用本所存档，未扣企查查次数" : "已从企查查查到，存进企业信息库");
      openCompany(data);
      await load(1, "");
    } catch (failure) { setError(errorText(failure, "企业信息查询失败")); }
    finally { setLooking(false); }
  };
  const createParty = async (company: LibraryCompany) => {
    setCreating(company.name);
    try {
      const { data } = await api.post("/parties", { name: company.name, organization_type: company.organization_type, identity_no: company.credit_code,
        legal_representative: company.legal_representative, registered_address: company.registered_address });
      message.success(`已新建当事人 ${data.party_no}`);
      setViewing(null);
      await load(page);
    } catch (failure) { message.error(errorText(failure, "新建当事人失败")); }
    finally { setCreating(""); }
  };
  const createCustomer = (company: LibraryCompany) => {
    try { window.sessionStorage.setItem(COMPANY_PREFILL_KEY, JSON.stringify(company)); } catch { /* 存不了就只打开新建页 */ }
    onCreateCustomer?.();
  };
  const roleTags = (roles: Roles) => roles.customers.length || roles.parties.length ? <Space size={4} wrap>
    {roles.customers.map((item) => <Tag key={`c${item.id}`} color="blue">客户 {item.serial_no}</Tag>)}
    {roles.parties.map((item) => <Tag key={`p${item.id}`} color="purple">当事人 {item.party_no}</Tag>)}
  </Space> : <Tag>未建客户或当事人</Tag>;
  const actions = (company: LibraryCompany) => <Space size={4}>
    <Button size="small" onClick={() => openCompany(company)}>查看</Button>
    <Button size="small" icon={<FileWordOutlined />} onClick={() => openCompany(company)}>信息表/尽调报告</Button>
    {!company.roles.customers.length && <Button size="small" onClick={() => createCustomer(company)}>新建客户</Button>}
    {!company.roles.customers.length && !company.roles.parties.length && <Button size="small" loading={creating === company.name} onClick={() => void createParty(company)}>新建当事人</Button>}
  </Space>;

  return <Card title="企业信息查询">
    <Alert type="info" showIcon style={{ marginBottom: 12 }} title="先查本所存档，不扣次数；没有时点“查企查查”查一次并存进企业信息库。库里的企业不是客户也不是当事人，不参与利益冲突检索，新建客户或当事人后才进入角色。" />
    <Space wrap style={{ marginBottom: 12 }}>
      <Input allowClear style={{ width: 320 }} placeholder="企业全称或统一社会信用代码" value={keyword} maxLength={60}
        onChange={(event) => setKeyword(event.target.value)} onPressEnter={() => void load(1)} />
      <Button icon={<SearchOutlined />} onClick={() => void load(1)}>查本所存档</Button>
      <Button type="primary" loading={looking} onClick={() => void lookup(false)}>查企查查</Button>
      <Button icon={<ReloadOutlined />} onClick={() => { setKeyword(""); void load(1, ""); }}>刷新</Button>
    </Space>
    {error && <Alert type="error" showIcon style={{ marginBottom: 12 }} title={error} />}
    <Table rowKey={(row: LibraryCompany) => row.credit_code || row.name} loading={loading} dataSource={rows}
      pagination={{ current: page, pageSize: 20, total, showTotal: (count: number) => `共 ${count} 家`, onChange: (next: number) => void load(next) }}
      columns={[
        { title: "企业名称", dataIndex: "name", width: 240, render: (value: string, row: LibraryCompany) => <Button type="link" style={{ padding: 0 }} onClick={() => openCompany(row)}>{value}</Button> },
        { title: "统一社会信用代码", dataIndex: "credit_code", width: 190 },
        { title: "法定代表人", dataIndex: "legal_representative", width: 110 },
        { title: "经营状态", dataIndex: "status", width: 150, render: (value: string, row: LibraryCompany) => row.abnormal ? <Tag color="red">{value || "异常"}</Tag> : value || "—" },
        { title: "角色", key: "roles", width: 200, render: (_: unknown, row: LibraryCompany) => roleTags(row.roles) },
        { title: "查询时间", dataIndex: "queried_at", width: 160, render: (value: string) => String(value || "").replace("T", " ").slice(0, 16) || "—" },
        { title: "操作", key: "actions", width: 220, render: (_: unknown, row: LibraryCompany) => actions(row) },
      ]} />
    <Drawer open={!!viewing} title={viewing?.name} size="large" onClose={() => setViewing(null)}
      extra={viewing && <Space>{actions(viewing)}<Button loading={looking} onClick={() => void lookup(true, viewing.credit_code || viewing.name)}>重新查询（扣一次）</Button></Space>}>
      {viewing && <>
        <div style={{ marginBottom: 12 }}>{roleTags(viewing.roles)}</div>
        <Descriptions bordered size="small" column={1} items={[
          ["统一社会信用代码", viewing.credit_code], ["法定代表人", viewing.legal_representative], ["组织类型", viewing.organization_type],
          ["经营状态", viewing.status], ["成立日期", viewing.established_date], ["注册资本", viewing.registered_capital],
          ["注册地址", viewing.registered_address], ["电话", viewing.phone], ["登记机关", viewing.registration_authority], ["经营范围", viewing.business_scope],
          ["查询时间", String(viewing.queried_at || "").replace("T", " ").slice(0, 16)],
        ].filter(([, value]) => value).map(([label, value]) => ({ key: String(label), label, children: value }))} />
        {(["basic", "due_diligence"] as const).map((kind) => {
          const label = kind === "basic" ? "企业基本信息表" : "尽职调查报告";
          const versions = documents.filter((item) => item.kind === kind);
          return <section key={kind} style={{ marginTop: 16 }} aria-label={label}>
            <Space style={{ marginBottom: 8 }}>
              <strong>{label}</strong>
              <Button size="small" type="primary" ghost icon={<FileWordOutlined />} loading={generating === kind} disabled={!!generating}
                onClick={() => void generate(viewing, kind)}>{versions.length ? "重新生成" : "生成"}</Button>
            </Space>
            {kind === "due_diligence" && <div style={{ color: "#8c8c8c", fontSize: 12, marginBottom: 6 }}>不关联案件时“所属案件”写“未关联案件”；风险数据 30 天内查过的直接用。</div>}
            {versions.length ? <List size="small" bordered dataSource={versions} renderItem={(item) => <List.Item
              actions={[<Button key="download" type="link" size="small" icon={<DownloadOutlined />} onClick={() => void download(item)}>下载</Button>]}>
              <span>{item.name}</span><span style={{ color: "#8c8c8c", marginLeft: 8 }}>{String(item.created_at || "").replace("T", " ").slice(0, 16)}</span>
            </List.Item>} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`还没有生成过${label}`} />}
          </section>;
        })}
      </>}
    </Drawer>
  </Card>;
}
