import { useCallback, useEffect, useState } from "react";
import { Button, Card, Input, message } from "antd";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import Table from "../components/ResizableTable";
import { api } from "../api";

interface PartyLibraryRow {
  id: number;
  case_id: number;
  case_no: string;
  case_category: string;
  party_no: string;
  subject_name: string;
  subject_position: string;
  our_parties: string[];
  our_position: string;
  opponent_parties: string[];
  opponent_position: string;
  managers: string[];
}

const PAGE_SIZE = 15;
const joinNames = (names: string[]) => (names || []).join("、") || "—";

const SCOPE_TITLES: Record<string, string> = { mine: "我的当事人", department: "部门当事人", company: "公司当事人", recycle: "当事人回收站" };

export default function PartyLibraryPage({ scope = "company", category = "", isAdmin = false, onOpenCase }: { scope?: string; category?: string; isAdmin?: boolean; onOpenCase?: (row: PartyLibraryRow) => void }) {
  const [rows, setRows] = useState<PartyLibraryRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [caseNo, setCaseNo] = useState("");
  const [name, setName] = useState("");
  const [peopleCount, setPeopleCount] = useState(0);

  const load = useCallback(async (nextPage = 1, filters = { caseNo, name, category }) => {
    setLoading(true);
    try {
      const { data } = await api.get("/party-library", {
        params: { scope, case_no: filters.caseNo, name: filters.name, case_category: filters.category, page: nextPage, page_size: PAGE_SIZE },
      });
      setRows(data.items || []);
      setTotal(Number(data.total || 0));
      setPeopleCount(Number(data.people_count || 0));
      setPage(nextPage);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "当事人库加载失败");
    } finally {
      setLoading(false);
    }
  }, [scope, category, caseNo, name]);

  useEffect(() => { void load(1); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const rebuild = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/party-library/rebuild");
      message.success(`已按案件重新生成，共 ${data.total} 条`);
      await load(1);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "重建失败");
      setLoading(false);
    }
  };

  const registerUnnumbered = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/party-library/register-unnumbered");
      message.success(`已补发 ${data.created} 个当事人编号`);
      await load(1);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "补发失败");
      setLoading(false);
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
        <span>
          <Button onClick={() => void registerUnnumbered()} style={{ marginRight: 8 }}>补发当事人编号</Button>
          <Button icon={<ReloadOutlined />} onClick={() => void rebuild()}>按案件重新生成</Button>
        </span>
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
          current: page, pageSize: PAGE_SIZE, total, showSizeChanger: false,
          showTotal: (count) => `共有${count}条，${peopleCount}人`, onChange: (next) => void load(next),
        }}
        columns={[
          {
            title: "案号", dataIndex: "case_no", width: 170,
            render: (value: string, row) => (onOpenCase && row.case_category !== "非诉讼" ? <a onClick={() => onOpenCase(row)}>{value}</a> : value),
          },
          { title: "我方当事人", dataIndex: "our_parties", render: joinNames },
          { title: "诉讼地位", dataIndex: "our_position", width: 90, render: (value: string) => value || "—" },
          { title: "当事人编号", dataIndex: "party_no", width: 130, render: (value: string) => value || "—" },
          {
            title: "姓名或名称", dataIndex: "subject_name",
            render: (value: string) => value,
          },
          { title: "对方当事人", dataIndex: "opponent_parties", render: joinNames },
          { title: "诉讼地位", dataIndex: "opponent_position", width: 90, render: (value: string) => value || "—" },
          { title: "管理人", dataIndex: "managers", width: 140, render: joinNames },
        ]}
      />
    </Card>
  );
}
