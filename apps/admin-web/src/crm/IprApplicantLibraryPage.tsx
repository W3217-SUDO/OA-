import { useCallback, useEffect, useState } from "react";
import { Button, Card, Input, Space, message } from "antd";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import Table from "../components/ResizableTable";
import { api } from "../api";
import { usePersonNames } from "../personNames";

interface ApplicantRow {
  id: number;
  applicant_no: string;
  name: string;
  created_by: string;
  created_at: string;
  cases: { case_id: number; case_no: string }[];
}

/** 501187：非诉申请人库。新建、修改非诉案件时手填的新申请人登记在这里，和诉讼的当事人库分开。 */
export default function IprApplicantLibraryPage() {
  const [rows, setRows] = useState<ApplicantRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [caseNo, setCaseNo] = useState("");
  const showPerson = usePersonNames();
  const load = useCallback(async (nextPage = 1, size = 15) => {
    setLoading(true);
    try {
      const { data } = await api.get("/party-library/ipr-applicants", { params: { keyword, case_no: caseNo, page: nextPage, page_size: size } });
      setRows(data.items || []);
      setTotal(Number(data.total || 0));
      setPage(nextPage);
      setPageSize(size);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "非诉申请人库加载失败");
    } finally {
      setLoading(false);
    }
  }, [keyword, caseNo]);
  useEffect(() => { void load(); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <Card size="small" title="非诉申请人库">
      <Space wrap style={{ marginBottom: 12 }}>
        <Input allowClear style={{ width: 220 }} placeholder="申请人名称或编号" value={keyword} onChange={(event) => setKeyword(event.target.value)} onPressEnter={() => void load()} />
        <Input allowClear style={{ width: 200 }} placeholder="案号" value={caseNo} onChange={(event) => setCaseNo(event.target.value)} onPressEnter={() => void load()} />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => void load()}>查询</Button>
        <Button icon={<ReloadOutlined />} onClick={() => void load(page, pageSize)}>刷新</Button>
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={rows}
        columns={[
          { title: "申请人编号", dataIndex: "applicant_no", width: 130 },
          { title: "申请人", dataIndex: "name", width: 280 },
          { title: "关联案件", dataIndex: "cases", render: (cases: ApplicantRow["cases"]) => (cases || []).map((item) => item.case_no).join("、") || "—" },
          { title: "登记人", dataIndex: "created_by", width: 110, render: (value: string) => showPerson(value) },
          { title: "登记时间", dataIndex: "created_at", width: 170, render: (value: string) => String(value || "").slice(0, 19).replace("T", " ") },
        ]}
        pagination={{ current: page, pageSize, total, showSizeChanger: true, onChange: (next, size) => void load(next, size) }}
      />
    </Card>
  );
}
