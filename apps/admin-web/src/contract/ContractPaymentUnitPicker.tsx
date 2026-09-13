import { Button, Checkbox, Input, Modal, Select, Space, Table, message } from "antd";
import { useEffect, useRef, useState } from "react";
import type { PaymentTypeOption } from "./types";

export function ContractPaymentUnitPicker({ open, options, selectedId, onCancel, onSelect, onCreate }: {
  open: boolean;
  options: PaymentTypeOption[];
  selectedId?: number;
  onCancel: () => void;
  onSelect: (row: PaymentTypeOption) => void;
  onCreate: () => void;
}) {
  const [keyword, setKeyword] = useState("");
  const [nature, setNature] = useState("官费");
  const [query, setQuery] = useState({ keyword: "", nature: "官费" });
  const [checkedId, setCheckedId] = useState<number>();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const previousIds = useRef(new Set<number>());
  useEffect(() => {
    if (!open) return;
    previousIds.current = new Set(options.map((item) => item.value));
    setKeyword(""); setNature("官费"); setQuery({ keyword: "", nature: "官费" });
    setCheckedId(selectedId); setPage(1); setPageSize(10);
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const added = options.find((item) => !previousIds.current.has(item.value));
    previousIds.current = new Set(options.map((item) => item.value));
    if (added) {
      setKeyword(added.payee); setNature(added.nature);
      setQuery({ keyword: added.payee, nature: added.nature }); setPage(1);
      setCheckedId(undefined);
    }
  }, [options, open]);
  const rows = options.filter((item) => (!query.nature || item.nature === query.nature)
    && item.payee.toLocaleLowerCase().includes(query.keyword.trim().toLocaleLowerCase()))
    .sort((a, b) => b.value - a.value);
  const select = () => {
    const row = rows.find((item) => item.value === checkedId);
    if (!row) { message.warning("请选择付款单位"); return; }
    onSelect(row);
  };
  return <Modal open={open} title="选择付款单位" width="min(1028px, 94vw)" className="contract-payment-unit-picker"
    onCancel={onCancel} footer={<Button onClick={onCancel}>取消</Button>}>
    <Space className="contract-payment-unit-query" wrap>
      <label>收款单位：<Input aria-label="收款单位查询" value={keyword} onChange={(event) => setKeyword(event.target.value)} onPressEnter={() => { setQuery({ keyword, nature }); setPage(1); setCheckedId(undefined); }} /></label>
      <label>类型：<Select aria-label="付款单位类型" value={nature} onChange={setNature}
        options={[{ value: "", label: "全部" }, ...Array.from(new Set(["官费", ...options.map((item) => item.nature)])).filter(Boolean).map((value) => ({ value, label: value }))]} /></label>
      <Button type="primary" onClick={() => { setQuery({ keyword, nature }); setPage(1); setCheckedId(undefined); }}>查询</Button>
      <Button type="primary" onClick={select}>选择</Button>
      <Button type="primary" onClick={onCreate}>新增</Button>
    </Space>
    <Table<PaymentTypeOption> bordered size="small" rowKey="value" dataSource={rows} scroll={{ x: 850 }}
      locale={{ emptyText: "没有查询到符合条件的记录" }}
      pagination={{ current: page, pageSize, total: rows.length, showSizeChanger: true, pageSizeOptions: [10, 20, 50, 100], showQuickJumper: { goButton: <Button size="small">GO</Button> }, showTotal: (total) => `共有${total}条`, onChange: (next, size) => { setPage(size !== pageSize ? 1 : next); setPageSize(size); setCheckedId(undefined); } }}
      columns={[
        { title: "选择", width: 58, render: (_, row) => <Checkbox aria-label={`选择${row.payee}`} checked={checkedId === row.value} onChange={(event) => setCheckedId(event.target.checked ? row.value : undefined)} /> },
        { title: "类型", dataIndex: "nature", width: 100 },
        { title: "收款单位", dataIndex: "payee", width: 220 },
        { title: "开户行", dataIndex: "account_bank", width: 230 },
        { title: "帐号信息", dataIndex: "account" },
      ]} />
  </Modal>;
}
