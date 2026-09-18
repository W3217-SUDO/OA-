import { useEffect, useState } from "react";
import { Alert, Button, Modal, Table } from "antd";
import { api } from "./api";

interface QueueItem { id: number; serial_no: string; title: string; status: string; amount: number }
export function DashboardPersonalQueue({ selection, onClose, onNavigate }: {
  selection: { key: string; label: string } | null; onClose: () => void; onNavigate: (route: string) => void;
}) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    if (!selection) return;
    setLoading(true); setError(""); setItems([]);
    api.get(`/dashboard/personal-queues/${selection.key}`).then(({ data }) => {
      if (active) setItems(data.items);
    }).catch(error => {
      if (active) setError(error?.response?.data?.detail || "个人提醒加载失败");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [selection]);
  return <Modal open={!!selection} title={selection?.label} width={900} onCancel={onClose} footer={null}>
    {error && <Alert type="error" title={error} />}
    <Table<QueueItem> rowKey="id" loading={loading} dataSource={items} pagination={{ pageSize: 15 }} columns={[
      { title: "案号", dataIndex: "serial_no", render: (value, row) => <Button type="link" onClick={() => { onClose(); onNavigate(`case-detail-${row.id}-${encodeURIComponent(row.serial_no)}`); }}>{value}</Button> },
      { title: "案件名称", dataIndex: "title" }, { title: "阶段", dataIndex: "status" },
      ...(selection?.key.startsWith("official-fee") || selection?.key === "refund-pending" ? [{ title: "金额", dataIndex: "amount", render: (value: number) => value.toFixed(2) }] : []),
    ]} />
  </Modal>;
}
