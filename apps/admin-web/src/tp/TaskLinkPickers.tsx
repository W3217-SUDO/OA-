import { useEffect, useRef, useState } from "react";
import { AutoComplete, Button, Input, Modal, Select, Space, Tooltip } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import type { TableColumnsType } from "antd";
import Table from "../components/ResizableTable";
import { POPUP_WIDTH } from "../components/common/popupSize";
import { api } from "../api";

// 新建任务的“关联案件”“客户”：可以直接输入（边输边搜、下拉里选），也可以点右侧放大镜弹出搜索框选择后带入
// （问题处理中心 BUG20261026002）。只列当前账号看得到的案件和客户。
export type TaskCaseOption = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  court_case_no: string;
};
export type TaskCustomerOption = { id: number; serial_no: string; name: string; status: string };

const SUGGEST_LIMIT = 20;
const DIALOG_LIMIT = 50;

/** 按关键词查选项：输入停顿 300ms 再查，只采用最后一次请求的结果。 */
function useLookup<T>(path: string) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const timer = useRef(0);
  const latest = useRef(0);
  const run = (keyword: string, limit = SUGGEST_LIMIT) => {
    const request = ++latest.current;
    window.clearTimeout(timer.current);
    setLoading(true);
    return api.get<{ items: T[] }>(path, { params: { keyword: keyword.trim(), limit } })
      .then(({ data }) => { if (request === latest.current) setItems(data.items); })
      .catch(() => { if (request === latest.current) setItems([]); })
      .finally(() => { if (request === latest.current) setLoading(false); });
  };
  const search = (keyword: string) => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void run(keyword), 300);
  };
  useEffect(() => () => window.clearTimeout(timer.current), []);
  return { items, loading, run, search };
}

const caseColumns: TableColumnsType<TaskCaseOption> = [
  { title: "案号", dataIndex: "serial_no", width: 140 },
  { title: "案件名称", dataIndex: "title", width: 220, ellipsis: true },
  { title: "客户", dataIndex: "customer", width: 180, ellipsis: true },
  { title: "法院案号", dataIndex: "court_case_no", width: 180, ellipsis: true, render: (value: string) => value || "—" },
  { title: "阶段", dataIndex: "status", width: 110, ellipsis: true },
];

const customerColumns: TableColumnsType<TaskCustomerOption> = [
  { title: "客户名称", dataIndex: "name", width: 280, ellipsis: true },
  { title: "客户编号", dataIndex: "serial_no", width: 160 },
  { title: "状态", dataIndex: "status", width: 100 },
];

function CaseSearchDialog({ open, onCancel, onConfirm }: {
  open: boolean;
  onCancel: () => void;
  onConfirm: (items: TaskCaseOption[]) => void;
}) {
  const lookup = useLookup<TaskCaseOption>("/tasks/case-options");
  const [keyword, setKeyword] = useState("");
  const [selected, setSelected] = useState<TaskCaseOption[]>([]);
  useEffect(() => {
    if (!open) return;
    setSelected([]);
    void lookup.run(keyword, DIALOG_LIMIT);
  }, [open]);
  return <Modal open={open} title="搜索案件" width={POPUP_WIDTH.lg} okText="带入所选案件" cancelText="取消"
    okButtonProps={{ disabled: !selected.length }} onOk={() => onConfirm(selected)} onCancel={onCancel}>
    <Input.Search allowClear enterButton="搜索" value={keyword} placeholder="案号、案件名称、客户或法院案号"
      aria-label="搜索案件关键词" style={{ marginBottom: 12 }}
      onChange={(event) => setKeyword(event.target.value)}
      onSearch={(value) => void lookup.run(value, DIALOG_LIMIT)} />
    <Table<TaskCaseOption> rowKey="serial_no" size="small" columns={caseColumns} dataSource={lookup.items}
      loading={lookup.loading} pagination={false} scroll={{ y: 360 }}
      locale={{ emptyText: "没有找到案件，换个关键词试试" }}
      rowSelection={{ selectedRowKeys: selected.map((item) => item.serial_no), onChange: (_keys, rows) => setSelected(rows) }}
      onRow={(row) => ({ onDoubleClick: () => onConfirm([row]) })} />
    <div className="task-link-picker-hint">勾选后点“带入所选案件”，双击一行可直接带入；最多显示 {DIALOG_LIMIT} 条。</div>
  </Modal>;
}

function CustomerSearchDialog({ open, onCancel, onConfirm }: {
  open: boolean;
  onCancel: () => void;
  onConfirm: (item: TaskCustomerOption) => void;
}) {
  const lookup = useLookup<TaskCustomerOption>("/tasks/customer-options");
  const [keyword, setKeyword] = useState("");
  useEffect(() => {
    if (open) void lookup.run(keyword, DIALOG_LIMIT);
  }, [open]);
  return <Modal open={open} title="搜索客户" width={POPUP_WIDTH.md} footer={null} onCancel={onCancel}>
    <Input.Search allowClear enterButton="搜索" value={keyword} placeholder="客户名称或客户编号"
      aria-label="搜索客户关键词" style={{ marginBottom: 12 }}
      onChange={(event) => setKeyword(event.target.value)}
      onSearch={(value) => void lookup.run(value, DIALOG_LIMIT)} />
    <Table<TaskCustomerOption> rowKey="id" size="small" dataSource={lookup.items} loading={lookup.loading}
      pagination={false} scroll={{ y: 360 }} locale={{ emptyText: "没有找到客户，换个关键词试试" }}
      columns={[...customerColumns, { title: "操作", key: "actions", width: 80,
        render: (_: unknown, row: TaskCustomerOption) => <Button type="link" size="small" onClick={() => onConfirm(row)}>选择</Button> }]}
      onRow={(row) => ({ onDoubleClick: () => onConfirm(row) })} />
    <div className="task-link-picker-hint">点“选择”或双击一行带入客户名称；最多显示 {DIALOG_LIMIT} 条。</div>
  </Modal>;
}

/** 关联案件（可多个）：值是案号数组，与 Form.Item name="case_nos" 配合使用。 */
export function TaskCasePicker({ value = [], onChange, onPick }: {
  value?: string[];
  onChange?: (value: string[]) => void;
  /** 选中某个案件时回调（用于带出该案件的客户）。 */
  onPick?: (item: TaskCaseOption) => void;
}) {
  const lookup = useLookup<TaskCaseOption>("/tasks/case-options");
  const [dialogOpen, setDialogOpen] = useState(false);
  const add = (items: TaskCaseOption[]) => {
    const next = [...value];
    for (const item of items) if (!next.includes(item.serial_no)) next.push(item.serial_no);
    onChange?.(next);
    items.forEach((item) => onPick?.(item));
  };
  return <>
    <Space.Compact block>
      <Select mode="multiple" showSearch allowClear filterOption={false} value={value}
        aria-label="关联案件" placeholder="输入案号、案件名称或客户搜索后选择，可选多个"
        loading={lookup.loading} notFoundContent={lookup.loading ? "正在搜索…" : "没有找到案件"}
        options={lookup.items.map((item) => ({ value: item.serial_no, label: item.serial_no }))}
        optionRender={(option) => {
          const item = lookup.items.find((row) => row.serial_no === option.value);
          return <div className="task-link-picker-option">
            <b>{String(option.value)}</b>
            {item && <span>{[item.title, item.customer].filter(Boolean).join(" · ")}</span>}
          </div>;
        }}
        onFocus={() => { if (!lookup.items.length) void lookup.run(""); }}
        onSearch={lookup.search}
        onChange={(next: string[]) => onChange?.(next)}
        onSelect={(serial: string) => {
          const item = lookup.items.find((row) => row.serial_no === serial);
          if (item) onPick?.(item);
        }} />
      <Tooltip title="搜索案件">
        <Button aria-label="搜索案件" icon={<SearchOutlined />} onClick={() => setDialogOpen(true)} />
      </Tooltip>
    </Space.Compact>
    <CaseSearchDialog open={dialogOpen} onCancel={() => setDialogOpen(false)}
      onConfirm={(items) => { add(items); setDialogOpen(false); }} />
  </>;
}

/** 客户：可以直接输入任意名称，也可以从提示或搜索框里选；值是客户名称。 */
export function TaskCustomerPicker({ value = "", onChange }: {
  value?: string;
  onChange?: (value: string) => void;
}) {
  const lookup = useLookup<TaskCustomerOption>("/tasks/customer-options");
  const [dialogOpen, setDialogOpen] = useState(false);
  return <>
    <Space.Compact block>
      <AutoComplete value={value} allowClear aria-label="客户" placeholder="输入客户名称，或点右侧放大镜搜索"
        style={{ width: "100%" }}
        options={lookup.items.map((item) => ({ value: item.name, label: <div className="task-link-picker-option">
          <b>{item.name}</b><span>{item.serial_no}</span></div> }))}
        onSearch={lookup.search}
        onFocus={() => { if (!lookup.items.length) void lookup.run(value); }}
        onChange={(next) => onChange?.(String(next ?? ""))} />
      <Tooltip title="搜索客户">
        <Button aria-label="搜索客户" icon={<SearchOutlined />} onClick={() => setDialogOpen(true)} />
      </Tooltip>
    </Space.Compact>
    <CustomerSearchDialog open={dialogOpen} onCancel={() => setDialogOpen(false)}
      onConfirm={(item) => { onChange?.(item.name); setDialogOpen(false); }} />
  </>;
}
