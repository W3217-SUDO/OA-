import { useEffect,useState } from "react";
import { Alert,Button,Space,Typography } from "antd";
import Table from "../../components/ResizableTable";
import { api } from "../../api";
import { personDisplayName } from "../constants";
import type { Attachment,IprRecord } from "../types";
import { iprDateText,iprFlagChecked } from "./iprCaseInfo";

/** 原系统 IPR_Case_FeeItem 一行（后端 legacy-fee-items 原样转出）。 */
type LegacyFeeItem = {
  id: number;
  fee_type?: string | null;
  yearly?: string | number | null;
  fee_mitigation?: string | null;
  amount?: number | null;
  actual_amount?: number | null;
  inform_date?: string | null;
  gained_date?: string | null;
  payment_bank?: string | null;
  bill_no?: string | null;
  bill_date?: string | null;
  bill_amount?: number | null;
  bill_file_name?: string | null;
};

type CaseFeeRow = { id: number; status?: string; title?: string; created_at?: string; data?: Record<string, any> };

/** 费用明细一行：新系统费用和原系统费用明细合在一张表里。 */
type FeeLine = {
  key: string;
  source: "新系统" | "原系统";
  feeType: string;
  yearly: string;
  amount: number | null;
  paidAmount: number | null;
  mitigation: boolean;
  informDate: string;
  gainedDate: string;
  status: string;
};

const money = (value: number | null | undefined) => (value === null || value === undefined ? "—" : Number(value).toFixed(2));

function useLegacyFeeItems(caseId: number) {
  const [items, setItems] = useState<LegacyFeeItem[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    setLoading(true);
    api.get<{ items: LegacyFeeItem[] }>(`/ipr/cases/${caseId}/legacy-fee-items`)
      .then(({ data }) => { if (active) setItems(data.items || []); })
      .catch(() => { if (active) setItems([]); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [caseId]);
  return { items, loading };
}

/** 费用明细页签（原系统“费用明细”）。 */
export function IprCaseFeesPanel({ detail }: { detail: IprRecord }) {
  const legacy = useLegacyFeeItems(detail.id);
  const [fees, setFees] = useState<CaseFeeRow[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setError("");
    api.get<{ items: CaseFeeRow[] }>(`/ipr/cases/${detail.id}/fees`, { params: { page: 1, page_size: 200 } })
      .then(({ data }) => { if (active) setFees(data.items || []); })
      .catch(() => { if (active) { setFees([]); setError("新系统费用加载失败"); } });
    return () => { active = false; };
  }, [detail.id]);
  const lines: FeeLine[] = [
    ...fees.map((row) => ({
      key: `fee-${row.id}`,
      source: "新系统" as const,
      feeType: row.data?.fee_subtype || row.data?.fee_type || row.title || "—",
      yearly: "",
      amount: row.data?.amount ?? null,
      paidAmount: row.data?.paid_amount ?? null,
      mitigation: false,
      informDate: iprDateText(row.created_at),
      gainedDate: iprDateText(row.data?.paid_at || row.data?.arrived_at),
      status: row.status || "",
    })),
    ...legacy.items.map((row) => ({
      key: `legacy-${row.id}`,
      source: "原系统" as const,
      feeType: row.fee_type || "—",
      yearly: row.yearly ? String(row.yearly) : "",
      amount: row.amount ?? null,
      paidAmount: row.actual_amount ?? null,
      mitigation: iprFlagChecked(row.fee_mitigation),
      informDate: iprDateText(row.inform_date),
      gainedDate: iprDateText(row.gained_date),
      status: row.gained_date ? "已缴" : "未缴",
    })),
  ];
  return (
    <>
      {error ? <Alert type="warning" showIcon message={error} style={{ marginBottom: 12 }} /> : null}
      <Table
        rowKey="key"
        size="small"
        loading={legacy.loading}
        pagination={lines.length > 15 ? { pageSize: 15, showSizeChanger: false } : false}
        locale={{ emptyText: "暂无费用" }}
        dataSource={lines}
        columns={[
          { title: "费用类型", dataIndex: "feeType", ellipsis: true },
          { title: "年度", dataIndex: "yearly", width: 70, render: (value) => value || "—" },
          { title: "应缴金额", dataIndex: "amount", width: 110, align: "right", render: money },
          { title: "实缴金额", dataIndex: "paidAmount", width: 110, align: "right", render: money },
          { title: "费减", dataIndex: "mitigation", width: 60, render: (value) => (value ? "是" : "否") },
          { title: "通知日期", dataIndex: "informDate", width: 110, render: (value) => value || "—" },
          { title: "缴费日期", dataIndex: "gainedDate", width: 110, render: (value) => value || "—" },
          { title: "状态", dataIndex: "status", width: 90, render: (value) => value || "—" },
          { title: "来源", dataIndex: "source", width: 80 },
        ]}
      />
    </>
  );
}

/** 发票文件页签：案件文档里的发票/收据类文件，加上原系统费用明细里登记的票据。 */
export function IprInvoiceFilesPanel({ detail, onPreviewAttachment, onDownloadAttachment }: {
  detail: IprRecord;
  onPreviewAttachment: (item: Attachment) => void;
  onDownloadAttachment: (item: Attachment) => void;
}) {
  const legacy = useLegacyFeeItems(detail.id);
  const [files, setFiles] = useState<Attachment[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    setLoading(true);
    api.get<{ items: Attachment[] }>(`/ipr/cases/${detail.id}/files`, { params: { page: 1, page_size: 200, category_keywords: "发票,收据" } })
      .then(({ data }) => { if (active) setFiles(data.items || []); })
      .catch(() => { if (active) setFiles([]); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [detail.id]);
  const bills = legacy.items.filter((row) => row.bill_no || row.bill_file_name);
  return (
    <>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        pagination={files.length > 15 ? { pageSize: 15, showSizeChanger: false } : false}
        locale={{ emptyText: "暂无发票文件" }}
        dataSource={files}
        columns={[
          { title: "文档类型", dataIndex: "category", ellipsis: true, render: (value) => value || "—" },
          {
            title: "文件名称",
            dataIndex: "original_name",
            ellipsis: true,
            render: (value: string, row: Attachment) => <Button type="link" size="small" onClick={() => onPreviewAttachment(row)}>{value}</Button>,
          },
          { title: "文档日期", dataIndex: "document_date", width: 110, render: (value) => iprDateText(value) || "—" },
          { title: "上传人", dataIndex: "uploader_display_name", width: 100, render: personDisplayName },
          { title: "操作", width: 70, render: (_, row: Attachment) => <Button type="link" size="small" onClick={() => onDownloadAttachment(row)}>下载</Button> },
        ]}
      />
      {bills.length ? (
        <Space direction="vertical" size={8} style={{ width: "100%", marginTop: 16 }}>
          <Typography.Text strong>原系统登记的票据</Typography.Text>
          <Table
            rowKey="id"
            size="small"
            pagination={bills.length > 15 ? { pageSize: 15, showSizeChanger: false } : false}
            dataSource={bills}
            columns={[
              { title: "费用类型", dataIndex: "fee_type", ellipsis: true, render: (value) => value || "—" },
              { title: "票据号", dataIndex: "bill_no", width: 140, render: (value) => value || "—" },
              { title: "票据金额", dataIndex: "bill_amount", width: 110, align: "right", render: money },
              { title: "票据日期", dataIndex: "bill_date", width: 110, render: (value) => iprDateText(value) || "—" },
              { title: "票据文件", dataIndex: "bill_file_name", ellipsis: true, render: (value) => value || "—" },
            ]}
          />
        </Space>
      ) : null}
    </>
  );
}
