import { useCallback, useEffect, useState } from "react";
import { Button, Card, Input, Popconfirm, Space, Tag, Tooltip, message } from "antd";
import dayjs from "dayjs";
import Table from "../components/ResizableTable";
import { api } from "../api";

// 陶国南 11-07：钉钉收文群里没匹配上案件的短信进收文台，显示“待处理”。
// 收文人员填系统案号“入库”（与一键收文确认入库相同，按本人案件权限），或“不入库”标记处理完。没有待处理时不显示。
export type BotReceiptRow = {
  id: number;
  status: string;
  sent_at: string;
  sender: string;
  text: string;
  kind: string;
  reason: string;
  candidates: string[];
  documents: { name: string; kind: string }[];
};

export const botReceiptDocuments = (row: BotReceiptRow) =>
  [...new Set(row.documents.map((item) => item.kind || item.name).filter(Boolean))].join("、") || "—";

function ActionCell({ row, onDone }: { row: BotReceiptRow; onDone: () => void }) {
  const [caseNo, setCaseNo] = useState(row.candidates.length === 1 ? row.candidates[0] : "");
  const [busy, setBusy] = useState(false);
  const run = async (path: string, body: object, done: string) => {
    setBusy(true);
    try {
      await api.post(`/documents/court-service/bot-receipts/${row.id}/${path}`, body);
      message.success(done);
      onDone();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "操作失败");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Space size={4} wrap={false}>
      {row.kind === "zxfw" && (
        <>
          <Input size="small" style={{ width: 140 }} placeholder="系统案号" value={caseNo} onChange={(event) => setCaseNo(event.target.value)} />
          <Button size="small" type="primary" loading={busy} disabled={!caseNo.trim()}
            onClick={() => void run("assign", { case_no: caseNo.trim() }, "已存入案件")}>入库</Button>
        </>
      )}
      <Popconfirm title="确定不入库？记录会保留，标记为已处理。" onConfirm={() => void run("close", {}, "已标记不入库")}>
        <Button size="small" disabled={busy}>不入库</Button>
      </Popconfirm>
    </Space>
  );
}

export function BotReceiptPending() {
  const [rows, setRows] = useState<BotReceiptRow[]>([]);
  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/documents/court-service/bot-receipts");
      setRows(data.items || []);
    } catch {
      setRows([]); // 没有官文收文权限或接口不可用时不显示，不影响收文列表
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  if (!rows.length) return null;
  const columns = [
    { title: "发送时间", key: "sent_at", width: 120, render: (_: unknown, r: BotReceiptRow) => r.sent_at ? dayjs(r.sent_at).format("MM-DD HH:mm") : "—" },
    { title: "发送人", dataIndex: "sender", width: 90 },
    { title: "状态", dataIndex: "status", width: 90, render: (v: string) => <Tag color="orange">{v}</Tag> },
    { title: "短信", dataIndex: "text", width: 260, ellipsis: true, render: (v: string) => <Tooltip title={v}>{v || "—"}</Tooltip> },
    { title: "文书", key: "documents", width: 180, ellipsis: true, render: (_: unknown, r: BotReceiptRow) => <Tooltip title={botReceiptDocuments(r)}>{botReceiptDocuments(r)}</Tooltip> },
    { title: "原因", dataIndex: "reason", width: 180, ellipsis: true, render: (v: string) => <Tooltip title={v}>{v || "—"}</Tooltip> },
    { title: "处理", key: "action", width: 280, render: (_: unknown, r: BotReceiptRow) => <ActionCell row={r} onDone={() => void load()} /> },
  ];
  return (
    <Card className="panel bot-receipt-pending" size="small" title={`钉钉收文待处理（${rows.length}）`} style={{ marginBottom: 12 }}>
      <Table rowKey="id" size="small" pagination={false} scroll={{ x: 1200 }} dataSource={rows} columns={columns} />
    </Card>
  );
}
