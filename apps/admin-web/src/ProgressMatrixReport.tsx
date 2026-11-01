import { useEffect, useState } from "react";
import { Alert, Button, Empty, Modal, Spin, message } from "antd";
import Table from "./components/ResizableTable";
import type { ColumnsType } from "antd/es/table";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { POPUP_WIDTH } from "./components/common/popupSize";

// 按人统计的进度表：每人一行、横向是进度，格子是案件数，点数字看案件清单（BUG 500789）。
export type ProgressMatrixRow = { person: string; counts: Record<string, number>; total: number };
export type ProgressMatrixData = {
  person_label: string;
  stages: string[];
  rows: ProgressMatrixRow[];
  totals: Record<string, number>;
  total: number;
  definition?: string;
};
// 清单列由接口给出：退费表多费用、金额，执行表多执行法院、执行案号（BUG 500788）。
type ProgressCase = { case_id: number; case_no: string; customer: string; people: string[]; fee_id?: number } & Record<string, unknown>;
type DetailColumn = { key: string; title: string; type?: "amount" };
type Drill = { person: string; stage: string };

const BIG_SCREEN_PAGE_SIZE = 12;
const BIG_SCREEN_REFRESH_MS = 5 * 60_000;
const BIG_SCREEN_PAGE_MS = 10_000;
const emptyData: ProgressMatrixData = { person_label: "", stages: [], rows: [], totals: {}, total: 0 };

export const progressMatrixPages = (rows: number, pageSize = BIG_SCREEN_PAGE_SIZE) => Math.max(1, Math.ceil(rows / pageSize));

export default function ProgressMatrixReport({ title, endpoint, bigScreen = false, onNavigate }: {
  title: string;
  endpoint: string;
  bigScreen?: boolean;
  onNavigate?: (route: string) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ProgressMatrixData>(emptyData);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [drill, setDrill] = useState<Drill | null>(null);
  const [drillLoading, setDrillLoading] = useState(false);
  const [drillItems, setDrillItems] = useState<ProgressCase[]>([]);
  const [drillColumns, setDrillColumns] = useState<DetailColumn[]>([]);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const { data: result } = await api.get<ProgressMatrixData>(endpoint);
      setData({ ...emptyData, ...result });
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || `${title}加载失败`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    if (!bigScreen) return;
    const timer = window.setInterval(() => void load(), BIG_SCREEN_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [endpoint, bigScreen]);

  // 大屏上人多时自动翻页。
  useEffect(() => {
    if (!bigScreen) return;
    const pages = progressMatrixPages(data.rows.length);
    if (pages <= 1) return;
    const timer = window.setInterval(() => setPage(current => current % pages + 1), BIG_SCREEN_PAGE_MS);
    return () => window.clearInterval(timer);
  }, [bigScreen, data.rows.length]);

  const openDrill = async (person: string, stage: string) => {
    if (bigScreen) return;
    setDrill({ person, stage });
    setDrillItems([]);
    setDrillLoading(true);
    try {
      const { data: result } = await api.get<{ items: ProgressCase[]; columns?: DetailColumn[] }>(`${endpoint}/cases`, { params: { person, stage } });
      setDrillItems(result.items || []);
      setDrillColumns(result.columns || []);
    } catch (requestError: any) {
      message.error(requestError?.response?.data?.detail || "案件清单加载失败");
    } finally {
      setDrillLoading(false);
    }
  };
  const openCase = (item: ProgressCase) => {
    if (!onNavigate || !rememberCaseDetailTarget({ id: item.case_id, serial_no: item.case_no })) return;
    setDrill(null);
    onNavigate(`case-detail-${item.case_id}-${encodeURIComponent(item.case_no)}`);
  };
  const countCell = (value: number, person: string, stage: string) => value
    ? <Button type="link" size="small" className="progress-matrix-count" disabled={bigScreen} onClick={() => void openDrill(person, stage)}>{value}</Button>
    : <span className="progress-matrix-zero">0</span>;

  const columns: ColumnsType<ProgressMatrixRow> = [
    { title: data.person_label || "人员", dataIndex: "person", fixed: "left", width: 130 },
    ...data.stages.map(stage => ({
      title: stage, key: stage, align: "center" as const, width: 110,
      render: (_: unknown, row: ProgressMatrixRow) => countCell(row.counts[stage] || 0, row.person, stage),
    })),
    { title: "合计", key: "total", align: "center", width: 90, fixed: "right", render: (_, row) => countCell(row.total, row.person, "") },
  ];
  const drillTitle = drill ? `${drill.person || "全部"} · ${drill.stage || "全部进度"}` : "";
  return (
    <div className={`report-page progress-matrix-page${bigScreen ? " is-big-screen" : ""}`}>
      <div className="report-page-heading">
        <span>{title}</span>
        {!bigScreen && onNavigate && <Button size="small" type="primary" onClick={() => onNavigate("reports-large-screen")}>大屏展示</Button>}
      </div>
      {data.definition && <div className="report-roi-description">{data.definition}</div>}
      {error && <Alert type="error" showIcon message={error} action={<Button size="small" onClick={() => void load()}>重试</Button>} />}
      <Spin spinning={loading}>
        <Table<ProgressMatrixRow>
          className="progress-matrix-table"
          rowKey="person"
          size={bigScreen ? "large" : "middle"}
          dataSource={data.rows}
          columns={columns}
          scroll={{ x: 130 + data.stages.length * 110 + 90 }}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有处在这些进度的案件" /> }}
          pagination={bigScreen
            ? { current: page, pageSize: BIG_SCREEN_PAGE_SIZE, onChange: setPage, showTotal: total => `共 ${total} 人` }
            : { pageSize: 50, showSizeChanger: true, showTotal: total => `共 ${total} 人` }}
          summary={() => data.rows.length ? (
            <Table.Summary fixed>
              <Table.Summary.Row className="progress-matrix-total-row">
                <Table.Summary.Cell index={0}>合计</Table.Summary.Cell>
                {data.stages.map((stage, index) => (
                  <Table.Summary.Cell key={stage} index={index + 1} align="center">{countCell(data.totals[stage] || 0, "", stage)}</Table.Summary.Cell>
                ))}
                <Table.Summary.Cell index={data.stages.length + 1} align="center">{countCell(data.total, "", "")}</Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          ) : null}
        />
      </Spin>
      <Modal open={Boolean(drill)} title={drillTitle} width={POPUP_WIDTH.lg} footer={<Button onClick={() => setDrill(null)}>关闭</Button>} onCancel={() => setDrill(null)} destroyOnHidden>
        <Table<ProgressCase>
          rowKey={item => `${item.case_id}-${item.fee_id ?? ""}`}
          size="small"
          loading={drillLoading}
          dataSource={drillItems}
          scroll={{ x: 980 }}
          pagination={{ pageSize: 20, showTotal: total => {
            const cases = new Set(drillItems.map(item => item.case_id)).size;
            return cases === total ? `共 ${cases} 件案件` : `共 ${cases} 件案件、${total} 笔费用`;
          } }}
          columns={[
            { title: "案号", dataIndex: "case_no", width: 140, render: (value, item) => onNavigate ? <Button type="link" size="small" onClick={() => openCase(item)}>{value}</Button> : value },
            { title: "客户", dataIndex: "customer", width: 200, ellipsis: true },
            ...drillColumns.map(column => ({
              title: column.title, dataIndex: column.key, width: column.type === "amount" ? 120 : 140, ellipsis: true,
              align: column.type === "amount" ? "right" as const : undefined,
              render: (value: unknown) => column.type === "amount"
                ? Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                : String(value ?? "") || "—",
            })),
            { title: data.person_label || "人员", dataIndex: "people", width: 150, render: (value: string[]) => (value || []).join("、") },
          ]}
        />
      </Modal>
    </div>
  );
}
