import { useEffect, useRef, useState } from "react";
import { Alert, Button, Drawer, Empty, Input, Pagination, Select, Spin, Tag } from "antd";
import { api } from "../api";
import "../legal/case-party-classification.css";

interface Item { id: string; name: string; subject_kind: string; credit_code: string | null; classifications: string[]; cases: { id: number; number: string }[] }

export function CasePartyDirectory() {
  const [open, setOpen] = useState(false);
  const [scope, setScope] = useState("opponents");
  const [keyword, setKeyword] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<Item[]>([]);
  const [total, setTotal] = useState(0);
  const [pending, setPending] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const request = useRef(0);
  useEffect(() => {
    if (!open) return;
    const id = ++request.current;
    setLoading(true); setError("");
    void api.get("/customers/party-directory", { params: { scope, keyword: query, page, page_size: 15 } }).then(({ data }) => {
      if (id !== request.current) return;
      if (!Array.isArray(data.items) || !Number.isInteger(data.total)) throw new Error("案件主体名录响应无效");
      setItems(data.items); setTotal(data.total); setPending(data.unclassified_case_count);
    }).catch(cause => { if (id === request.current) { setItems([]); setError(cause.response?.data?.detail || cause.message || "名录加载失败"); } })
      .finally(() => { if (id === request.current) setLoading(false); });
    return () => { ++request.current; };
  }, [open, scope, query, page]);
  return <>
    <Button onClick={() => setOpen(true)}>案件当事人及对手方名录</Button>
    <Drawer className="case-party-directory-drawer" title="案件当事人及对手方名录" size={720} open={open} onClose={() => setOpen(false)}>
      <div className="case-party-directory">
        <Alert type="info" showIcon title="名录不创建 CRM 客户，按当前账号可见案件汇总。无证件的同名主体分别保留，利益冲突审查仍执行全所核查。" />
        <Alert type="warning" showIcon title={`有 ${pending} 个可见案件尚未分类，需逐案人工复核；当前名录不能代表全部历史主体已完成迁移。`} />
        <Select aria-label="主体名录范围" value={scope} options={[{ value: "opponents", label: "对手方名录" }, { value: "all", label: "全部已分类案件主体" }, { value: "review", label: "历史案件待复核" }]} onChange={next => { setScope(next); setPage(1); }} />
        <Input.Search aria-label="主体名录查询" value={keyword} placeholder="主体名称或案件编号" onChange={event => setKeyword(event.target.value)} onSearch={() => { setQuery(keyword); setPage(1); }} enterButton="查询" />
        {error && <Alert type="error" showIcon title={error} />}
        <Spin spinning={loading}><div className="case-party-directory">{items.map(item => <section className="case-party-directory-item" key={item.id}>
          <strong>{item.name}</strong><p>{item.subject_kind} {item.classifications.map(label => <Tag key={label}>{label}</Tag>)}</p>
          <p>证件号码/统一社会信用代码：{item.credit_code === null ? "受字段权限限制" : item.credit_code || "未登记"}</p>
          <div>{item.cases.map(caseRecord => <a key={caseRecord.id} href={`?page=case-detail-${caseRecord.id}-${encodeURIComponent(caseRecord.number)}`}>{caseRecord.number}</a>)}</div>
        </section>)}{!loading && !error && !items.length && <Empty description="当前查询无记录" />}</div></Spin>
        <Pagination current={page} pageSize={15} total={total} showSizeChanger={false} onChange={setPage} />
      </div>
    </Drawer>
  </>;
}
