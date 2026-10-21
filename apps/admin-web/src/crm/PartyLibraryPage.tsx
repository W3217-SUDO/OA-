import { useCallback, useEffect, useState } from "react";
import { Button, Card, Descriptions, Drawer, Input, Spin, message } from "antd";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import Table from "../components/ResizableTable";
import { api } from "../api";

interface PartyLibraryRow {
  id: number;
  case_id: number;
  case_no: string;
  case_category: string;
  party_id: number | null;
  case_phase: string;
  closed_at: string;
  party_no: string;
  subject_name: string;
  subject_position: string;
  our_parties: string[];
  our_position: string;
  opponent_parties: string[];
  opponent_position: string;
  managers: string[];
}

const PAGE_SIZE_OPTIONS = ["15", "30", "50", "100"];
const joinNames = (names: string[]) => (names || []).join("、") || "—";

interface PartyDetail {
  party_no: string; name: string; party_type: string; source_customer_id: number | null; owner: string; department: string;
  managers: string[]; status: string; description: string; organization_type: string; identity_no: string; created_by: string;
  cases: { case_id: number; case_no: string; case_category: string; case_phase: string; closed_at: string; closed: boolean; position: string; our_parties: string[]; our_position: string; opponent_parties: string[]; opponent_position: string }[];
}

const SCOPE_TITLES: Record<string, string> = { mine: "我的当事人", department: "部门当事人", company: "公司当事人", recycle: "当事人回收站" };

export default function PartyLibraryPage({ scope = "company", category = "", isAdmin = false, onOpenCase }: { scope?: string; category?: string; isAdmin?: boolean; onOpenCase?: (row: PartyLibraryRow) => void }) {
  const [rows, setRows] = useState<PartyLibraryRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [loading, setLoading] = useState(false);
  const [caseNo, setCaseNo] = useState("");
  const [name, setName] = useState("");
  const [peopleCount, setPeopleCount] = useState(0);
  const [detail, setDetail] = useState<PartyDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);

  const load = useCallback(async (nextPage = 1, filters = { caseNo, name, category }, size = pageSize) => {
    setLoading(true);
    try {
      const { data } = await api.get("/party-library", {
        params: { scope, case_no: filters.caseNo, name: filters.name, case_category: filters.category, page: nextPage, page_size: size },
      });
      setRows(data.items || []);
      setTotal(Number(data.total || 0));
      setPeopleCount(Number(data.people_count || 0));
      setPage(nextPage);
      setPageSize(size);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "当事人库加载失败");
    } finally {
      setLoading(false);
    }
  }, [scope, category, caseNo, name, pageSize]);

  useEffect(() => { void load(1); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const rebuild = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/party-library/rebuild");
      message.success(`已按案件重新生成，共 ${data.total} 条，新编号已自动发放`);
      await load(1);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "重建失败");
      setLoading(false);
    }
  };

  const openDetail = async (partyId: number | null) => {
    if (!partyId) return;
    setDetail(null);
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const { data } = await api.get<PartyDetail>(`/parties/${partyId}`);
      setDetail(data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "当事人信息加载失败");
      setDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const reset = () => {
    setCaseNo(""); setName("");
    void load(1, { caseNo: "", name: "", category });
  };

  return (
    <Card
      className="panel customer-list-panel"
      title={`${SCOPE_TITLES[scope] || "当事人中心"}${category ? ` · ${category === "法律顾问" ? category : `${category}案件`}` : ""}`}
      extra={isAdmin ? (
        <Button icon={<ReloadOutlined />} onClick={() => void rebuild()}>按案件重新生成</Button>
      ) : null}
    >
      <div className="customer-query">
        <label>案号</label>
        <Input value={caseNo} onChange={(e) => setCaseNo(e.target.value)} onPressEnter={() => void load(1)} allowClear />
        <label>姓名/名称/编号</label>
        <Input value={name} onChange={(e) => setName(e.target.value)} onPressEnter={() => void load(1)} allowClear />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => void load(1)}>查询</Button>
        <Button onClick={reset}>重置</Button>
      </div>
      <Table<PartyLibraryRow>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{
          current: page, pageSize, total, showSizeChanger: true, pageSizeOptions: PAGE_SIZE_OPTIONS, showQuickJumper: true,
          showTotal: (count) => `共有${count}条，${peopleCount}人`,
          onChange: (next, size) => void load(size !== pageSize ? 1 : next, undefined, size),
          locale: {
            items_per_page: "条/页", jump_to: "跳至", jump_to_confirm: "确定", page: "页",
            prev_page: "上一页", next_page: "下一页", prev_5: "向前 5 页", next_5: "向后 5 页", prev_3: "向前 3 页", next_3: "向后 3 页",
          },
        }}
        columns={[
          {
            title: "案号", dataIndex: "case_no", width: 170,
            render: (value: string, row) => (onOpenCase && row.case_category !== "非诉讼" ? <a onClick={() => onOpenCase(row)}>{value}</a> : value),
          },
          { title: "我方当事人", dataIndex: "our_parties", render: joinNames },
          { title: "诉讼地位", dataIndex: "our_position", width: 90, render: (value: string) => value || "—" },
          { title: "案件阶段", dataIndex: "case_phase", width: 110, render: (value: string) => value || "—" },
          { title: "归档日期", dataIndex: "closed_at", width: 110, render: (value: string) => value || "—" },
          {
            title: "对方当事人", dataIndex: "subject_name",
            render: (value: string, row) => (row.party_id ? <a onClick={() => void openDetail(row.party_id)}>{value}</a> : value),
          },
          { title: "诉讼地位", dataIndex: "subject_position", width: 90, render: (value: string) => value || "—" },
          { title: "管理人", dataIndex: "managers", width: 140, render: joinNames },
        ]}
      />
      <Drawer title="当事人信息" open={detailOpen} onClose={() => setDetailOpen(false)} size="large" destroyOnClose>
        {detailLoading || !detail ? <Spin /> : (
          <>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="当事人编号">{detail.party_no}</Descriptions.Item>
              <Descriptions.Item label="姓名或名称">{detail.name}</Descriptions.Item>
              <Descriptions.Item label="类型">{detail.party_type || "—"}</Descriptions.Item>
              <Descriptions.Item label="状态">{detail.status || "—"}</Descriptions.Item>
              <Descriptions.Item label="组织类型">{detail.organization_type || "—"}</Descriptions.Item>
              <Descriptions.Item label="证件号">{detail.identity_no || "—"}</Descriptions.Item>
              <Descriptions.Item label="负责人">{detail.owner || "—"}</Descriptions.Item>
              <Descriptions.Item label="部门">{detail.department || "—"}</Descriptions.Item>
              <Descriptions.Item label="管理人" span={2}>{(detail.managers || []).join("、") || "—"}</Descriptions.Item>
              <Descriptions.Item label="来源">{detail.source_customer_id ? "由客户挪入，沿用原客户编号" : `新建（${detail.created_by || "系统"}）`}</Descriptions.Item>
              <Descriptions.Item label="备注">{detail.description || "—"}</Descriptions.Item>
            </Descriptions>
            <h4 style={{ margin: "16px 0 8px" }}>所在案件（{detail.cases.length}）</h4>
            <Table<PartyDetail["cases"][number]>
              size="small" rowKey={(row) => `${row.case_id}`} pagination={false} dataSource={detail.cases}
              columns={[
                { title: "案号", dataIndex: "case_no" },
                { title: "案件类型", dataIndex: "case_category", render: (value: string) => (value === "法律顾问" ? value : `${value}案件`) },
                { title: "诉讼地位", dataIndex: "position", render: (value: string) => value || "—" },
                { title: "案件阶段", dataIndex: "case_phase", render: (value: string) => value || "—" },
                { title: "结案时间", dataIndex: "closed_at", render: (value: string) => value || "未结案" },
                { title: "我方当事人", dataIndex: "our_parties", render: (value: string[]) => (value || []).join("、") || "—" },
                { title: "对方当事人", dataIndex: "opponent_parties", render: (value: string[]) => (value || []).join("、") || "—" },
              ]}
            />
          </>
        )}
      </Drawer>
    </Card>
  );
}
