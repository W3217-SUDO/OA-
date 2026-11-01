import { KeywordPersonSelect } from "./components/KeywordPersonSelect";
import { useEffect, useState } from "react";
import { DownloadOutlined } from "@ant-design/icons";
import { Alert, Button, DatePicker, Empty, Form, Input, Segmented, Select, Space, Spin, message } from "antd";
import Table from "./components/ResizableTable";import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "./api";
import { rememberCustomerDetailTarget, resolveCustomerDetailTarget } from "./customerDetailNavigation";
import { useMobileFilterToggle } from "./components/common/MobileFilterToggle";
import { usePeopleNames } from "./personNames";
import ProgressMatrixReport from "./ProgressMatrixReport";
import { useReportBigScreen } from "./reportBigScreen";
import "./report-center.css";

type ChartResult = { title: string; unit: ChartSpec["unit"]; items: { name: string; label?: string; value: number | null }[] };
type Analytics = { charts: ChartResult[]; warnings?: string[]; filter_options: { customers: string[]; lawyers: string[] }; source: "realtime" };
type ReportFilterValues = {
  customer?: string[];
  courtLawyer?: string[];
  handlingLawyer?: string;
  assistant?: string;
  investigator?: string;
  court?: string;
  groupMode?: string;
  sourceDate?: any;
  hearingDate?: any;
};

type ChartSpec = {
  title: string;
  unit: "天/案" | "元" | "百分比" | "个/案";
  metricKeys?: string[];
  limit?: number;
  /** 柱子变窄（每项约 64 像素、柱宽不超过 28 像素），品牌、律师资金统计用（tgn 11-01）。 */
  narrowBars?: boolean;
};

type PageSpec = {
  title: string;
  tab?: string;
  filter: "brand" | "lawyer" | "none" | "customer-roi";
  charts: ChartSpec[];
};

type CustomerRoiRow = {
  customer: string;
  customer_id?: number;
  customer_no?: string;
  department: string;
  employee: string;
  income: number;
  cost: number;
  profit: number;
  roi: number | null;
};

type CustomerRoiData = {
  view: "customer-roi";
  rows: CustomerRoiRow[];
  totals: Omit<CustomerRoiRow, "customer" | "department" | "employee">;
  filter_options: { departments: string[]; employees: string[] };
  source: "realtime";
  date_basis?: string;
  formula?: string;
};

type CustomerRoiFilterValues = {
  dateRange?: any;
  department?: string;
  employee?: string;
};

type StaffPerformanceRow = {
  person: string;
  agency_fee: number | null;
  new_cases: number;
  active_cases: number;
  hearings: number;
  archived_cases: number;
  loss_archived_cases: number;
};

type StaffPerformanceData = {
  year: number;
  role: string;
  role_label: string;
  amount_visible: boolean;
  totals: Omit<StaffPerformanceRow, "person">;
  rows: StaffPerformanceRow[];
  roles: { value: string; label: string }[];
  definition?: string;
};

const PAGE_SPECS: Record<string, PageSpec> = {
  "reports-brand": {
    title: "资金运营情况统计",
    tab: "按品牌统计",
    filter: "brand",
    charts: [
      { title: "资金回款周期统计", unit: "天/案", metricKeys: ["资金回款周期", "资金回款周期统计"], narrowBars: true },
      { title: "资金亏损金额统计", unit: "元", metricKeys: ["资金亏损金额", "资金亏损金额统计"], narrowBars: true },
      { title: "资金回报率统计", unit: "百分比", metricKeys: ["资金回报率", "资金回报率统计"], narrowBars: true },
      { title: "资金亏损率统计", unit: "百分比", metricKeys: ["资金亏损率", "资金亏损率统计"], narrowBars: true },
    ],
  },
  "reports-lawyer": {
    title: "资金运营情况统计",
    tab: "按开庭律师统计",
    filter: "lawyer",
    charts: [
      { title: "资金回款周期统计", unit: "天/案", metricKeys: ["资金回款周期", "资金回款周期统计"], narrowBars: true },
      { title: "资金亏损金额统计", unit: "元", metricKeys: ["资金亏损金额", "资金亏损金额统计"], narrowBars: true },
      { title: "资金回报率统计", unit: "百分比", metricKeys: ["资金回报率", "资金回报率统计"], narrowBars: true },
      { title: "资金亏损率统计", unit: "百分比", metricKeys: ["资金亏损率", "资金亏损率统计"], narrowBars: true },
    ],
  },
  "reports-refund": {
    title: "退费进度案件统计",
    filter: "none",
    charts: [
      { title: "准备资料进度案件数量", unit: "个/案" },
      { title: "客户盖章进度案件数量", unit: "个/案" },
      { title: "提交法院进度案件数量", unit: "个/案" },
      { title: "等待客户回款进度案件数量", unit: "个/案" },
    ],
  },
};

PAGE_SPECS["reports-staff-roi"] = {
  title: "员工业绩统计中心",
  filter: "none",
  charts: [],
};

PAGE_SPECS["reports-customer-roi"] = {
  title: "客户ROI统计",
  filter: "customer-roi",
  charts: [],
};

function Filters({ kind, options, onQuery }: { kind: "brand" | "lawyer"; options: Analytics["filter_options"]; onQuery: (values: ReportFilterValues) => void }) {
  const [form] = Form.useForm();
  const mobileFilter = useMobileFilterToggle();

  return (
    <>
    {mobileFilter.toggle}
    <Form
      form={form}
      className={`report-filter ${mobileFilter.className}`}
      initialValues={{ customer: [], courtLawyer: [], groupMode: "按律师分组统计" }}
      onFinish={onQuery}
    >
      <Form.Item className="report-filter-wide" label="客户名称" name="customer">
        <Select mode="multiple" showSearch optionFilterProp="label" maxTagCount="responsive" placeholder="请选择客户" options={options.customers.map(value => ({ value, label: value }))} />
      </Form.Item>
      <Form.Item className="report-filter-wide" label="开庭律师" name="courtLawyer">
        <KeywordPersonSelect mode="multiple" showSearch optionFilterProp="label" maxTagCount="responsive" placeholder="请选择" options={options.lawyers.map(value => ({ value, label: value }))} />
      </Form.Item>
      {kind === "brand" ? (
        <Form.Item label="经办律师" name="handlingLawyer">
          <Input placeholder="开庭律师" />
        </Form.Item>
      ) : (
        <Form.Item label="分组模式" name="groupMode">
          <Select
            options={[
              { value: "按律师分组统计", label: "按律师分组统计" },
              { value: "按文书分组统计", label: "按文书分组统计" },
            ]}
          />
        </Form.Item>
      )}
      <Form.Item label="律师助理" name="assistant">
        <Input />
      </Form.Item>
      <Form.Item label="案源时间" name="sourceDate">
        <DatePicker.RangePicker />
      </Form.Item>
      <Form.Item label="调查员" name="investigator">
        <Input />
      </Form.Item>
      <Form.Item label="法院名称" name="court">
        <Input />
      </Form.Item>
      <Form.Item label="开庭时间" name="hearingDate">
        <DatePicker.RangePicker />
      </Form.Item>
      <div className="report-filter-action">
        <Button type="primary" htmlType="submit">查询</Button>
        <Button onClick={()=>{form.resetFields(); onQuery({})}}>重置</Button>
      </div>
    </Form>
    </>
  );
}

function MetricChart({ spec, items }: { spec: ChartSpec; items: { name: string; label?: string; value: number | null }[] }) {
  // 横轴显示简称（有的话），鼠标停留显示全称（tgn 11-01，BUG20261101002）。
  const chartItems = (spec.limit ? items.slice(0, spec.limit) : items).map((item) => ({ ...item, axis: item.label || item.name }));
  const slot = spec.narrowBars ? 64 : 88;
  return (
    <section className="report-chart-panel">
      <div className="report-chart-title">
        <span>{spec.title}</span>
        <span className="report-chart-unit">单位： {spec.unit}</span>
      </div>
      <div className="report-chart-body report-chart-scroll">
        {/* 客户多时每个柱子固定宽度，超出部分左右拖动查看（tgn 11-01，BUG20261101001）。 */}
        {chartItems.length ? <div className="report-chart-track" style={{ minWidth: chartItems.length > 8 ? chartItems.length * slot : undefined }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartItems} margin={{ top: 20, right: 24, bottom: 16, left: 4 }}>
            <CartesianGrid stroke="#ececec" vertical={false} />
            <XAxis dataKey="axis" interval={0} axisLine={{ stroke: "#d8d8d8" }} tickLine={false} tick={{ fill: "#777", fontSize: 11 }} />
            <YAxis
              allowDecimals={spec.unit !== "个/案"}
              domain={[0, "auto"]}
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#777", fontSize: 11 }}
            />
            <Tooltip
              labelFormatter={(_label, payload) => payload?.[0]?.payload?.name ?? _label}
              formatter={(item) => [item == null ? "不可计算" : `${Number(item).toLocaleString()} ${spec.unit}`, spec.title]}
            />
            <Bar dataKey="value" fill="#36b978" maxBarSize={spec.narrowBars ? 28 : 72} />
          </BarChart>
        </ResponsiveContainer>
        </div> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前条件下暂无真实业务数据" />}
      </div>
    </section>
  );
}

const currency = (value: number) => Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const percentage = (value: number) => `${Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
const roiDisplay = (roi: number | null, cost: number) => Number(cost || 0) === 0 || roi === null ? "—" : percentage(roi);

// 客户ROI 图（BUG 500793，思法汇成 11-01 17:19）：收入和成本对比柱（收入前 15 名），ROI 排行横条（正绿负红）。
// 17:36 起左图不再叠 ROI 折线：折线按右侧 ROI 刻度画，容易被看成金额（如万盛联 109 万的点画到 700% 的高度）。
const ROI_TOP_INCOME = 15;
const ROI_BIG_SCREEN_EDGE = 10;
const ROI_REGION_PREFIXES = [
  "北京市", "上海市", "天津市", "重庆市", "北京", "上海", "天津", "重庆", "黑龙江", "内蒙古",
  "河北", "山西", "辽宁", "吉林", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
  "广东", "广西", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "宁夏", "新疆", "西藏",
  "杭州", "广州", "深圳", "青岛", "苏州", "南京", "宁波", "厦门", "武汉", "成都", "西安", "无锡", "佛山", "东莞",
];
const ROI_COMPANY_SUFFIXES = ["股份有限公司", "有限责任公司", "有限公司", "集团", "公司"];

// 与品牌资金统计横轴简称同一规则：去掉省市名、括号内容和公司字样，最多 8 个字。
export function customerShortName(name: string, limit = 8) {
  let text = String(name || "").replace(/[（(][^）)]*[）)]/g, "").trim();
  const prefix = ROI_REGION_PREFIXES.find(item => text.startsWith(item) && text.length > item.length + 1);
  if (prefix) text = text.slice(prefix.length).replace(/^[省市]+/, "");
  let changed = true;
  while (changed) {
    changed = false;
    for (const suffix of ROI_COMPANY_SUFFIXES) {
      if (text.endsWith(suffix) && text.length > suffix.length + 1) {
        text = text.slice(0, -suffix.length);
        changed = true;
      }
    }
  }
  return (text || String(name || "")).slice(0, limit);
}

type RoiChartItem = CustomerRoiRow & { label: string };

export function customerRoiChartItems(rows: CustomerRoiRow[], bigScreen: boolean) {
  const withLabel = rows.map(row => ({ ...row, label: customerShortName(row.customer) }));
  const incomeTop = [...withLabel]
    .filter(row => row.income || row.cost)
    .sort((left, right) => right.income - left.income || right.cost - left.cost)
    .slice(0, ROI_TOP_INCOME);
  const ranked = withLabel
    .filter(row => row.roi !== null && row.roi !== undefined && Number(row.cost || 0) !== 0)
    .sort((left, right) => Number(right.roi) - Number(left.roi));
  // 大屏一屏放下：只显示最高 10 家和最低 10 家。
  const roiRanking = bigScreen && ranked.length > ROI_BIG_SCREEN_EDGE * 2
    ? [...ranked.slice(0, ROI_BIG_SCREEN_EDGE), ...ranked.slice(-ROI_BIG_SCREEN_EDGE)]
    : ranked;
  // 个别客户 ROI 特别高（如成本很小）时，横轴按第二名放大，最高那条画到边上、数字照实显示，其他客户的条不至于看不见。
  const values = roiRanking.map(row => Number(row.roi));
  const [first = 0, second = 0] = [...values].sort((left, right) => right - left);
  const roiAxisMax = first > 0 && second > 0 && first > second * 3 ? Math.ceil(second * 1.3) : undefined;
  const roiBars = roiRanking.map(row => ({ ...row, roiBar: roiAxisMax ? Math.min(Number(row.roi), roiAxisMax) : Number(row.roi), roiText: `${Number(row.roi).toFixed(2)}%` }));
  return { incomeTop, roiRanking: roiBars, roiAxisMax };
}

const wan = (value: number) => Math.abs(value) >= 10000 ? `${(value / 10000).toLocaleString("zh-CN", { maximumFractionDigits: 1 })}万` : Number(value || 0).toLocaleString("zh-CN");

function RoiTooltip({ active, payload }: { active?: boolean; payload?: { payload: RoiChartItem }[] }) {
  const row = active ? payload?.[0]?.payload : undefined;
  if (!row) return null;
  return (
    <div className="report-roi-tooltip">
      <div className="report-roi-tooltip-title">{row.customer}</div>
      <div>收入：{currency(row.income)} 元</div>
      <div>成本：{currency(row.cost)} 元</div>
      <div>利润：{currency(row.profit)} 元</div>
      <div>ROI：{roiDisplay(row.roi, row.cost)}</div>
    </div>
  );
}

function CustomerRoiCharts({ rows, bigScreen }: { rows: CustomerRoiRow[]; bigScreen: boolean }) {
  const { incomeTop, roiRanking, roiAxisMax } = customerRoiChartItems(rows, bigScreen);
  const fontSize = bigScreen ? 14 : 11;
  const rankingHeight = Math.max(240, roiRanking.length * (bigScreen ? 30 : 26) + 40);
  const empty = <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前条件下暂无真实业务数据" />;
  return (
    <div className="report-chart-grid report-roi-charts">
      <section className="report-chart-panel report-roi-chart">
        <div className="report-chart-title">
          <span>收入、成本对比（收入前 {ROI_TOP_INCOME} 名）</span>
          <span className="report-chart-unit">单位：元</span>
        </div>
        <div className="report-chart-body report-chart-scroll report-roi-chart-body">
          {incomeTop.length ? <div className="report-chart-track" style={{ minWidth: !bigScreen && incomeTop.length > 8 ? incomeTop.length * 76 : undefined }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={incomeTop} margin={{ top: 22, right: 8, bottom: 8, left: 8 }}>
                <CartesianGrid stroke="#ececec" vertical={false} />
                <XAxis dataKey="label" interval={0} axisLine={{ stroke: "#d8d8d8" }} tickLine={false} tick={{ fill: "#666", fontSize }} angle={-30} textAnchor="end" height={bigScreen ? 70 : 58} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: "#777", fontSize }} tickFormatter={wan} width={bigScreen ? 70 : 56} />
                <Tooltip content={<RoiTooltip />} />
                <Legend wrapperStyle={{ fontSize }} />
                <Bar dataKey="income" name="收入" fill="#4e8cff" maxBarSize={28} isAnimationActive={false} />
                <Bar dataKey="cost" name="成本" fill="#ffb95c" maxBarSize={28} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div> : empty}
        </div>
      </section>
      <section className="report-chart-panel report-roi-chart">
        <div className="report-chart-title">
          <span>ROI 排行{bigScreen && roiRanking.length >= ROI_BIG_SCREEN_EDGE * 2 ? `（最高、最低各 ${ROI_BIG_SCREEN_EDGE} 家）` : ""}</span>
          <span className="report-chart-unit">单位：%（成本为 0 的不计算）</span>
        </div>
        <div className="report-chart-body report-roi-ranking-body">
          {roiRanking.length ? <div style={{ height: rankingHeight }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={roiRanking} layout="vertical" margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                <CartesianGrid stroke="#ececec" horizontal={false} />
                <XAxis type="number" axisLine={false} tickLine={false} tick={{ fill: "#777", fontSize }} tickFormatter={value => `${value}%`}
                  {...(roiAxisMax ? { domain: [(dataMin: number) => Math.min(0, dataMin), roiAxisMax] } : {})} />
                <YAxis type="category" dataKey="label" interval={0} axisLine={{ stroke: "#d8d8d8" }} tickLine={false} tick={{ fill: "#666", fontSize }} width={bigScreen ? 130 : 110} />
                <Tooltip content={<RoiTooltip />} />
                <YAxis yAxisId="value" orientation="right" type="category" dataKey="roiText" interval={0} axisLine={false} tickLine={false} tick={{ fill: "#333", fontSize }} width={bigScreen ? 96 : 80} />
                {/* ROI 数字放在右侧一列；两张图都不用动画，手机钉钉和大屏上打开就能看到完整的图。 */}
                <Bar dataKey="roiBar" name="ROI" maxBarSize={18} isAnimationActive={false}>
                  {roiRanking.map(row => <Cell key={row.customer_id ?? row.customer} fill={Number(row.roi) < 0 ? "#ef6d85" : "#2cc47c"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div> : empty}
        </div>
      </section>
    </div>
  );
}

function CustomerRoiReport({ onNavigate }: { onNavigate?: (route: string) => void }) {
  const showPeople = usePeopleNames();
  const [form] = Form.useForm<CustomerRoiFilterValues>();
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  // 默认显示图，右上角“图 / 表格”切换；“大屏展示”只放图（BUG 500793，与 500789/500792 同一做法）。
  const [display, setDisplay] = useState<"chart" | "table">("chart");
  const pageBigScreen = useReportBigScreen();
  const bigScreen = pageBigScreen.active;
  const [data, setData] = useState<CustomerRoiData>({
    view: "customer-roi",
    rows: [],
    totals: { income: 0, cost: 0, profit: 0, roi: 0 },
    filter_options: { departments: [], employees: [] },
    source: "realtime",
  });

  const paramsFor = (values: CustomerRoiFilterValues) => ({
    date_from: values.dateRange?.[0]?.format("YYYY-MM-DD"),
    date_to: values.dateRange?.[1]?.format("YYYY-MM-DD"),
    department: values.department || undefined,
    employee: values.employee || undefined,
  });
  const load = async (values: CustomerRoiFilterValues = form.getFieldsValue()) => {
    setLoading(true);
    try {
      const { data: result } = await api.get<CustomerRoiData>("/reports/customer-roi", { params: paramsFor(values) });
      setData(result);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户ROI统计加载失败");
    } finally {
      setLoading(false);
    }
  };
  const exportReport = async () => {
    setExporting(true);
    try {
      const response = await api.get("/reports/customer-roi/export", { params: paramsFor(form.getFieldsValue()), responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "客户ROI统计.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户ROI统计导出失败");
    } finally {
      setExporting(false);
    }
  };
  const openCustomer = async (row: CustomerRoiRow) => {
    const target = await resolveCustomerDetailTarget({ id: row.customer_id, serial_no: row.customer_no, title: row.customer });
    if (!target || !rememberCustomerDetailTarget(target)) {
      message.warning("未找到关联客户或当前账号无权查看");
      return;
    }
    onNavigate?.("customer-company");
  };

  useEffect(() => { void load({}); }, []);
  return (
    <div ref={pageBigScreen.ref} className={`report-page report-customer-roi-page${bigScreen ? " report-page-big-screen" : ""}`}>
      <div className="report-page-heading">
        <span>客户ROI统计</span>
        {bigScreen
          ? <Button size="small" onClick={pageBigScreen.exit}>退出大屏</Button>
          : <Space size={8}>
            <Segmented size="small" value={display} onChange={value => setDisplay(value as "chart" | "table")} options={[{ label: "图", value: "chart" }, { label: "表格", value: "table" }]} />
            <Button size="small" type="primary" onClick={pageBigScreen.enter}>大屏展示</Button>
          </Space>}
      </div>
      {!bigScreen && <Form form={form} className="report-filter report-customer-roi-filter" onFinish={values => void load(values)}>
        <Form.Item label="日期" name="dateRange"><DatePicker.RangePicker /></Form.Item>
        <Form.Item label="归属部门" name="department"><Select allowClear showSearch optionFilterProp="label" placeholder="全部部门" options={data.filter_options.departments.map(value => ({ value, label: value }))} /></Form.Item>
        <Form.Item label="负责人" name="employee"><KeywordPersonSelect allowClear showSearch optionFilterProp="label" placeholder="全部负责人" options={data.filter_options.employees.map(value => ({ value, label: showPeople(value) }))} /></Form.Item>
        <div className="report-filter-action">
          <Button type="primary" htmlType="submit">查询</Button>
          <Button onClick={() => { form.resetFields(); void load({}); }}>重置</Button>
          <Button icon={<DownloadOutlined />} loading={exporting} onClick={() => void exportReport()}>导出CSV</Button>
        </div>
      </Form>}
      {!bigScreen && <div className="report-roi-description">按{data.date_basis || "开票日期、到账日期、付款日期"}筛选；{data.formula || "ROI＝（收入－成本）÷ 成本 × 100%"}。成本为 0 时显示“—”。部门和负责人按关联案件筛选。</div>}
      {(display === "chart" || bigScreen) && <Spin spinning={loading}><CustomerRoiCharts rows={data.rows} bigScreen={bigScreen} /></Spin>}
      {display === "table" && !bigScreen && <div className="report-roi-table-panel">
        <Table<CustomerRoiRow>
          rowKey={(row) => `${row.customer}-${row.department}-${row.employee}`}
          loading={loading}
          dataSource={data.rows}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前条件下暂无真实业务数据" /> }}
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: total => `共 ${total} 条` }}
          scroll={{ x: 1050 }}
          summary={() => (
            <Table.Summary.Row>
              <Table.Summary.Cell index={0} colSpan={3}>合计</Table.Summary.Cell>
              <Table.Summary.Cell index={3}>{currency(data.totals.income)}</Table.Summary.Cell>
              <Table.Summary.Cell index={4}>{currency(data.totals.cost)}</Table.Summary.Cell>
              <Table.Summary.Cell index={5}>{currency(data.totals.profit)}</Table.Summary.Cell>
              <Table.Summary.Cell index={6}>{roiDisplay(data.totals.roi, data.totals.cost)}</Table.Summary.Cell>
            </Table.Summary.Row>
          )}
          columns={[
            { title: "客户", dataIndex: "customer", width: 240, ellipsis: true, render: (value, row) => <Button type="link" className="report-roi-customer-link" onClick={() => void openCustomer(row)}>{value || "—"}</Button> },
            { title: "部门", dataIndex: "department", width: 170, ellipsis: true, render: value => value || "—" },
            { title: "员工", dataIndex: "employee", width: 160, ellipsis: true, render: value => showPeople(value) },
            { title: "收入（元）", dataIndex: "income", width: 150, align: "right", render: currency },
            { title: "成本（元）", dataIndex: "cost", width: 150, align: "right", render: currency },
            { title: "利润（元）", dataIndex: "profit", width: 150, align: "right", render: currency },
            { title: "ROI", dataIndex: "roi", width: 130, align: "right", render: (value, row) => roiDisplay(value, row.cost) },
          ]}
        />
      </div>}
    </div>
  );
}


// 员工业绩统计中心（BUG 500799，思法汇成 11-01 18:35）：当年代理费到账、在办、开庭、结案归档四类数，
// 按案源人 / 调查员 / 开庭律师 / 律师助理按人划分；默认显示图，右上角“图 / 表格”切换，“大屏展示”只放图。
const STAFF_CHART_LIMIT = 15;
const STAFF_ROLE_OPTIONS = [
  { value: "source", label: "案源人" },
  { value: "investigator", label: "调查员" },
  { value: "hearing", label: "开庭律师" },
  { value: "assistant", label: "律师助理" },
];

export function staffChartRows(rows: StaffPerformanceRow[]) {
  const byFee = rows.filter(row => Number(row.agency_fee || 0) > 0)
    .sort((left, right) => Number(right.agency_fee) - Number(left.agency_fee)).slice(0, STAFF_CHART_LIMIT);
  const byCases = rows.filter(row => row.new_cases || row.active_cases || row.hearings || row.archived_cases)
    .sort((left, right) => right.active_cases + right.hearings + right.archived_cases - (left.active_cases + left.hearings + left.archived_cases))
    .slice(0, STAFF_CHART_LIMIT);
  return { byFee, byCases };
}

function StaffPerformanceCharts({ data, bigScreen }: { data: StaffPerformanceData; bigScreen: boolean }) {
  const { byFee, byCases } = staffChartRows(data.rows);
  const fontSize = bigScreen ? 14 : 11;
  const empty = <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前条件下暂无真实业务数据" />;
  const axis = { dataKey: "person", interval: 0, axisLine: { stroke: "#d8d8d8" }, tickLine: false, tick: { fill: "#666", fontSize }, angle: -30, textAnchor: "end", height: bigScreen ? 70 : 58 } as const;
  return (
    <div className="report-chart-grid report-roi-charts">
      {data.amount_visible && <section className="report-chart-panel report-roi-chart">
        <div className="report-chart-title">
          <span>代理费到账（按{data.role_label}，前 {STAFF_CHART_LIMIT} 名）</span>
          <span className="report-chart-unit">单位：元</span>
        </div>
        <div className="report-chart-body report-chart-scroll">
          {byFee.length ? <div className="report-chart-track" style={{ minWidth: !bigScreen && byFee.length > 8 ? byFee.length * 64 : undefined }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byFee} margin={{ top: 22, right: 8, bottom: 8, left: 8 }}>
                <CartesianGrid stroke="#ececec" vertical={false} />
                <XAxis {...axis} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: "#777", fontSize }} tickFormatter={wan} width={bigScreen ? 70 : 56} />
                <Tooltip formatter={(value) => [`${currency(Number(value))} 元`, "代理费到账"]} />
                <Bar dataKey="agency_fee" name="代理费到账" fill="#4e8cff" maxBarSize={32} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div> : empty}
        </div>
      </section>}
      <section className="report-chart-panel report-roi-chart">
        <div className="report-chart-title">
          <span>新建、在办、开庭、结案归档（按{data.role_label}，前 {STAFF_CHART_LIMIT} 名）</span>
          <span className="report-chart-unit">单位：件 / 次</span>
        </div>
        <div className="report-chart-body report-chart-scroll">
          {byCases.length ? <div className="report-chart-track" style={{ minWidth: !bigScreen && byCases.length > 6 ? byCases.length * 90 : undefined }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byCases} margin={{ top: 22, right: 8, bottom: 8, left: 0 }}>
                <CartesianGrid stroke="#ececec" vertical={false} />
                <XAxis {...axis} />
                <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#777", fontSize }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize }} />
                <Bar dataKey="new_cases" name="新建案件" fill="#4e8cff" maxBarSize={22} isAnimationActive={false} />
                <Bar dataKey="active_cases" name="在办案件" fill="#18c7bb" maxBarSize={22} isAnimationActive={false} />
                <Bar dataKey="hearings" name="开庭" fill="#ffb95c" maxBarSize={22} isAnimationActive={false} />
                <Bar dataKey="archived_cases" name="结案归档" fill="#8a74e8" maxBarSize={22} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div> : empty}
        </div>
      </section>
    </div>
  );
}

function StaffRoiReport() {
  const thisYear = new Date().getFullYear();
  const [year, setYear] = useState(thisYear);
  const [role, setRole] = useState("source");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [display, setDisplay] = useState<"chart" | "table">("chart");
  const pageBigScreen = useReportBigScreen();
  const bigScreen = pageBigScreen.active;
  const [data, setData] = useState<StaffPerformanceData>({
    year: thisYear, role: "source", role_label: "案源人", amount_visible: false,
    totals: { agency_fee: null, new_cases: 0, active_cases: 0, hearings: 0, archived_cases: 0, loss_archived_cases: 0 },
    rows: [], roles: STAFF_ROLE_OPTIONS,
  });

  const load = async (next: { year?: number; role?: string; name?: string } = {}) => {
    setLoading(true);
    try {
      const { data: result } = await api.get<StaffPerformanceData>("/reports/staff-performance", {
        params: { year: next.year ?? year, role: next.role ?? role, name: (next.name ?? name).trim() || undefined },
      });
      setData(result);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "员工业绩统计中心加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { void load(); }, []);

  const totals = data.totals;
  const cards = [
    ...(data.amount_visible ? [{ label: "代理费到账（元）", value: currency(Number(totals.agency_fee || 0)) }] : []),
    { label: `${data.year} 年新建案件（件）`, value: totals.new_cases.toLocaleString("zh-CN") },
    { label: "当前在办案件（件）", value: totals.active_cases.toLocaleString("zh-CN") },
    { label: `${data.year} 年开庭（次）`, value: totals.hearings.toLocaleString("zh-CN") },
    { label: `${data.year} 年结案归档（件）`, value: totals.archived_cases.toLocaleString("zh-CN"), note: `其中亏损归档 ${totals.loss_archived_cases.toLocaleString("zh-CN")} 件` },
  ];
  return (
    <div ref={pageBigScreen.ref} className={`report-page report-staff-performance-page${bigScreen ? " report-page-big-screen" : ""}`}>
      <div className="report-page-heading">
        <span>员工业绩统计中心{bigScreen ? `（${data.year} 年 · 按${data.role_label}）` : ""}</span>
        {bigScreen
          ? <Button size="small" onClick={pageBigScreen.exit}>退出大屏</Button>
          : <Space size={8}>
            <Segmented size="small" value={display} onChange={value => setDisplay(value as "chart" | "table")} options={[{ label: "图", value: "chart" }, { label: "表格", value: "table" }]} />
            <Button size="small" type="primary" onClick={pageBigScreen.enter}>大屏展示</Button>
          </Space>}
      </div>
      {!bigScreen && <div className="report-filter report-staff-filter">
        <Select value={year} style={{ width: 110 }} onChange={value => { setYear(value); void load({ year: value }); }}
          options={Array.from({ length: 5 }, (_, index) => ({ value: thisYear - index, label: `${thisYear - index} 年` }))} />
        <Segmented value={role} onChange={value => { setRole(String(value)); void load({ role: String(value) }); }} options={STAFF_ROLE_OPTIONS} />
        <Input allowClear placeholder={`输入${STAFF_ROLE_OPTIONS.find(item => item.value === role)?.label || ""}姓名查个人`} style={{ width: 220 }}
          value={name} onChange={event => setName(event.target.value)} onPressEnter={() => void load()} />
        <Button type="primary" onClick={() => void load()}>查询</Button>
        <Button onClick={() => { setName(""); setYear(thisYear); setRole("source"); void load({ year: thisYear, role: "source", name: "" }); }}>重置</Button>
      </div>}
      {!bigScreen && data.definition && <div className="report-roi-description">{data.definition}</div>}
      <Spin spinning={loading}>
        <div className="report-staff-cards">
          {cards.map(card => (
            <div key={card.label} className="report-staff-card">
              <div className="report-staff-card-label">{card.label}</div>
              <div className="report-staff-card-value">{card.value}</div>
              {card.note && <div className="report-staff-card-note">{card.note}</div>}
            </div>
          ))}
        </div>
        {(display === "chart" || bigScreen) && <StaffPerformanceCharts data={data} bigScreen={bigScreen} />}
        {display === "table" && !bigScreen && <div className="report-roi-table-panel">
          <Table<StaffPerformanceRow>
            rowKey="person"
            dataSource={data.rows}
            pagination={{ pageSize: 20, showSizeChanger: true, showTotal: total => `共 ${total} 人` }}
            locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前条件下暂无真实业务数据" /> }}
            scroll={{ x: 820 }}
            columns={[
              { title: data.role_label, dataIndex: "person", width: 160, fixed: "left" },
              ...(data.amount_visible ? [{ title: "代理费到账（元）", dataIndex: "agency_fee", width: 150, align: "right" as const,
                sorter: (left: StaffPerformanceRow, right: StaffPerformanceRow) => Number(left.agency_fee || 0) - Number(right.agency_fee || 0),
                render: (value: number | null) => currency(Number(value || 0)) }] : []),
              { title: "新建案件", dataIndex: "new_cases", width: 110, align: "right", sorter: (left, right) => left.new_cases - right.new_cases },
              { title: "在办案件", dataIndex: "active_cases", width: 110, align: "right", sorter: (left, right) => left.active_cases - right.active_cases },
              { title: "开庭", dataIndex: "hearings", width: 100, align: "right", sorter: (left, right) => left.hearings - right.hearings },
              { title: "结案归档", dataIndex: "archived_cases", width: 110, align: "right", sorter: (left, right) => left.archived_cases - right.archived_cases },
              { title: "其中亏损归档", dataIndex: "loss_archived_cases", width: 130, align: "right" },
            ]}
          />
        </div>}
      </Spin>
    </div>
  );
}

const largeScreenViews = ["reports-refund", "reports-execution-1"];

// 报表大屏经营总数据（BUG 500801）。
type MonthValue = { month: number; value: number };
type ClueRow = { name: string; submitted: number; approved: number };
type LargeScreenOverview = {
  year: number;
  case_trend: MonthValue[];
  hearing_trend: MonthValue[];
  clues: { by_investigator: ClueRow[]; by_brand: ClueRow[]; submitted: number; approved: number };
  task_trend: { month: number; issued: number; done: number }[];
};

type LargeScreenData = {
  case_summary: { total: number; in_progress: number; closed: number };
  finance: { amount_visible: boolean; income: number | null; expense: number | null; income_label?: string; expense_label?: string };
  customer_summary: { total: number };
  employee_ranking: { username?: string; name: string; value: number }[];
  overview?: LargeScreenOverview;
  case_type_distribution: { name: string; value: number }[];
  monthly_trend: { month: string; cases: number; income: number | null; expense: number | null }[];
  definitions?: Record<string, string>;
  generated_at?: string;
};

const emptyLargeScreenData: LargeScreenData = {
  case_summary: { total: 0, in_progress: 0, closed: 0 },
  finance: { amount_visible: false, income: null, expense: null },
  customer_summary: { total: 0 },
  employee_ranking: [],
  case_type_distribution: [],
  monthly_trend: [],
};

const formatNumber = (value: number) => Number(value || 0).toLocaleString("zh-CN");
const formatCurrency = (value: number | null) => value == null ? "—" : `¥${Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const monthLabel = (month: number) => `${month}月`;
const shortName = (name: string) => name.length > 8 ? `${name.slice(0, 8)}…` : name;
// 当年还没到的月份不画点，免得折线在月底“掉到 0”（开庭按排期另算，保留后面的月份）。
const pastMonths = <T extends { month: number }>(rows: T[], year: number | undefined, keys: (keyof T)[]) => {
  const now = new Date();
  if (year !== now.getFullYear()) return rows;
  return rows.map(row => row.month > now.getMonth() + 1 ? { ...row, ...Object.fromEntries(keys.map(key => [key, null])) } : row);
};

// 经营总数据的图：按月柱状/折线、按人或品牌的两条线（BUG 500801）。
function MonthBarChart({ rows, name, color }: { rows: MonthValue[]; name: string; color: string }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={rows} margin={{ top: 20, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="#e8f0f2" vertical={false} />
        <XAxis dataKey="month" tickFormatter={monthLabel} tick={{ fontSize: 12 }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
        <Tooltip labelFormatter={(month) => monthLabel(Number(month))} formatter={(value) => [formatNumber(Number(value)), name]} />
        <Bar dataKey="value" name={name} fill={color} maxBarSize={28}>
          <LabelList dataKey="value" position="top" fontSize={11} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// 线索按调查员/品牌：每个人或品牌两根柱子——提交数和审核通过数（思法汇成 11-01 19:12，不要折线）。
function GroupedBarChart({ rows, bars }: { rows: Record<string, string | number>[]; bars: { key: string; name: string; color: string }[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={rows} margin={{ top: 20, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="#e8f0f2" vertical={false} />
        <XAxis dataKey="name" interval={0} tick={{ fontSize: 12 }} tickFormatter={(value) => shortName(String(value))} angle={-30} textAnchor="end" height={72} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(value, barName) => [formatNumber(Number(value)), barName]} />
        <Legend />
        {bars.map(bar => (
          <Bar key={bar.key} dataKey={bar.key} name={bar.name} fill={bar.color} maxBarSize={24}>
            <LabelList dataKey={bar.key} position="top" fontSize={10} />
          </Bar>
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

function TwoLineChart({ rows, xKey, lines, xFormatter, tilted }: {
  rows: Record<string, string | number | null>[];
  xKey: string;
  lines: { key: string; name: string; color: string }[];
  xFormatter?: (value: number) => string;
  tilted?: boolean;
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={rows} margin={{ top: 20, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="#e8f0f2" vertical={false} />
        <XAxis dataKey={xKey} interval={0} tick={{ fontSize: 12 }} tickFormatter={xFormatter ? (value) => xFormatter(Number(value)) : (value) => shortName(String(value))}
          {...(tilted ? { angle: -30, textAnchor: "end", height: 72 } : {})} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
        <Tooltip labelFormatter={xFormatter ? (value) => xFormatter(Number(value)) : undefined} formatter={(value, lineName) => [formatNumber(Number(value)), lineName]} />
        <Legend />
        {lines.map(line => (
          <Line key={line.key} type="monotone" dataKey={line.key} name={line.name} stroke={line.color} strokeWidth={2.5} dot={{ r: 3 }}>
            <LabelList dataKey={line.key} position="top" fontSize={10} />
          </Line>
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

function LargeScreenEmpty({ description = "暂无可展示的真实业务数据" }: { description?: string }) {
  return <Empty className="large-screen-empty" image={Empty.PRESENTED_IMAGE_SIMPLE} description={description} />;
}

export function ReportLargeScreenPage({ onExit }: { onExit?: () => void }) {
  const [screenMode, setScreenMode] = useState<"overview" | "legacy">("overview");
  const [legacyIndex, setLegacyIndex] = useState(0);
  const [fullscreen, setFullscreen] = useState(Boolean(document.fullscreenElement));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState<LargeScreenData>(emptyLargeScreenData);
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get<LargeScreenData>("/reports/large-screen");
      setData({ ...emptyLargeScreenData, ...response.data, case_summary: { ...emptyLargeScreenData.case_summary, ...response.data.case_summary }, finance: { ...emptyLargeScreenData.finance, ...response.data.finance }, customer_summary: { ...emptyLargeScreenData.customer_summary, ...response.data.customer_summary } });
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || "大屏实时数据加载失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // 大屏常开不关：发布新版本后旧页面还在定时取数，会和新接口对不上（BUG 500800，旧页面把缺字段显示成“无财务金额查看权限”）。
    // 每次定时刷新顺带看一下线上版本，变了就整页重新加载。
    let loadedVersion = "";
    const checkVersion = async () => {
      try {
        const response = await fetch(`/build-info.json?_=${Date.now()}`, { cache: "no-store" });
        const version = String((await response.json())?.version || "");
        if (!version) return;
        if (!loadedVersion) loadedVersion = version;
        else if (version !== loadedVersion) window.location.reload();
      } catch {
        // 取不到版本信息不影响大屏数据刷新。
      }
    };
    void checkVersion();
    const refreshTimer = window.setInterval(() => { void checkVersion(); void load(); }, 60_000);
    const syncFullscreen = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", syncFullscreen);
    return () => {
      window.clearInterval(refreshTimer);
      document.removeEventListener("fullscreenchange", syncFullscreen);
    };
  }, []);

  useEffect(() => {
    if (screenMode !== "legacy") return;
    const timer = window.setInterval(() => setLegacyIndex(current => (current + 1) % largeScreenViews.length), 30_000);
    return () => window.clearInterval(timer);
  }, [screenMode]);

  const toggleFullscreen = () => {
    if (document.fullscreenElement) {
      void document.exitFullscreen?.();
      return;
    }
    void document.documentElement.requestFullscreen?.().catch(() => message.warning("当前浏览器不支持进入全屏模式"));
  };

  const overview = data.overview;
  const clueLines = [{ key: "submitted", name: "提交线索数", color: "#3e8ef7" }, { key: "approved", name: "审核通过数", color: "#00a65a" }];
  return (
    <div className="report-large-screen">
      <header className="large-screen-header">
        <div>
          <p>REPORTING CENTER · REALTIME</p>
          <h1>经营数据大屏</h1>
        </div>
        <div className="large-screen-actions">
          <Button type={screenMode === "overview" ? "primary" : "default"} onClick={() => setScreenMode("overview")}>综合概览</Button>
          <Button type={screenMode === "legacy" ? "primary" : "default"} onClick={() => setScreenMode("legacy")}>旧报表轮播</Button>
          <Button onClick={() => void load()} loading={loading}>刷新数据</Button>
          <Button onClick={toggleFullscreen}>{fullscreen ? "退出全屏" : "全屏展示"}</Button>
          {onExit && <Button onClick={onExit}>返回报表中心</Button>}
        </div>
      </header>
      {screenMode === "legacy" ? (
        <section className="large-screen-legacy">
          <div className="large-screen-legacy-note">旧版专题报表每 30 秒自动切换，可保留用于会议轮播展示。</div>
          <ReportCenterPage key={largeScreenViews[legacyIndex]} initialView={largeScreenViews[legacyIndex]} bigScreen />
        </section>
      ) : (
        <Spin spinning={loading} tip="正在汇总实时数据">
          {error ? <Alert className="large-screen-alert" type="error" showIcon message="大屏数据未加载" description={error} action={<Button size="small" onClick={() => void load()}>重试</Button>} /> : (
            <main className="large-screen-content">
              <section className="large-screen-kpis" aria-label="业务概览">
                <article><span>案件总数</span><strong>{formatNumber(data.case_summary.total)}</strong><em>{data.definitions?.case_total || "符合统计条件的可见案件"}</em></article>
                <article><span>在办案件</span><strong>{formatNumber(data.case_summary.in_progress)}</strong><em>{data.definitions?.case_in_progress || "当前办理中"}</em></article>
                <article><span>已结案件</span><strong>{formatNumber(data.case_summary.closed)}</strong><em>{data.definitions?.case_closed || "已完成或归档"}</em></article>
                <article><span>财务收入</span><strong>{formatCurrency(data.finance.income)}</strong><em>{data.finance.amount_visible ? (data.definitions?.income || data.finance.income_label || "当前数据范围") : "无财务数据查看权限"}</em></article>
                <article><span>财务支出</span><strong>{formatCurrency(data.finance.expense)}</strong><em>{data.finance.amount_visible ? (data.definitions?.expense || data.finance.expense_label || "当前数据范围") : "无财务数据查看权限"}</em></article>
                <article><span>客户总数</span><strong>{formatNumber(data.customer_summary.total)}</strong><em>全部可见客户</em></article>
              </section>
              {/* 经营总数据 4 块（BUG 500801）；员工业绩排行已移到员工业绩统计中心（500799）。 */}
              <section className="large-screen-grid large-screen-overview" aria-label="经营总数据">
                <article className="large-screen-card">
                  <h2>{overview?.year ?? ""}年新增案件数 <small>{data.definitions?.case_trend || "按月"}</small></h2>
                  <div className="large-screen-chart">{overview ? <TwoLineChart rows={pastMonths(overview.case_trend, overview.year, ["value"])} xKey="month" xFormatter={monthLabel} lines={[{ key: "value", name: "新增案件数", color: "#00a65a" }]} /> : <LargeScreenEmpty />}</div>
                </article>
                <article className="large-screen-card">
                  <h2>{overview?.year ?? ""}年开庭数量 <small>{data.definitions?.hearing_trend || "按月"}</small></h2>
                  <div className="large-screen-chart">{overview ? <MonthBarChart rows={overview.hearing_trend} name="开庭数量" color="#8a74e8" /> : <LargeScreenEmpty />}</div>
                </article>
                {([["by_investigator", "按调查员"], ["by_brand", "按品牌"]] as const).map(([key, group]) => (
                  <article key={key} className="large-screen-card">
                    <h2>新增调查线索·{group} <small>{overview ? `提交 ${formatNumber(overview.clues.submitted)} 条，审核通过 ${formatNumber(overview.clues.approved)} 条` : ""}</small></h2>
                    <div className="large-screen-chart">{overview?.clues[key].length ? <GroupedBarChart rows={overview.clues[key]} bars={clueLines} /> : <LargeScreenEmpty />}</div>
                  </article>
                ))}
                <article className="large-screen-card trend-card">
                  <h2>{overview?.year ?? ""}年任务数量 <small>{data.definitions?.task_trend || "按月发出和完成的任务数"}</small></h2>
                  <div className="large-screen-chart">{overview ? <TwoLineChart rows={pastMonths(overview.task_trend, overview.year, ["issued", "done"])} xKey="month" xFormatter={monthLabel} lines={[{ key: "issued", name: "发出任务数", color: "#3e8ef7" }, { key: "done", name: "完成任务数", color: "#00a65a" }]} /> : <LargeScreenEmpty />}</div>
                </article>
              </section>
              {data.definitions?.clues && <p className="large-screen-ranking-note">线索：{data.definitions.clues}</p>}
              {data.generated_at && <p className="large-screen-updated">数据更新时间：{data.generated_at}</p>}
            </main>
          )}
        </Spin>
      )}
    </div>
  );
}

// 这些报表自己取数，不走 /reports/analytics。
const PAGE_OWN_LOADERS = new Set(["reports-customer-roi", "reports-staff-roi", "reports-refund", "reports-execution-1", "reports-execution-2", "reports-execution-3"]);

function StandardReportCenterPage({ initialView = "reports-brand", onNavigate, bigScreen = false }: { initialView?: string; onNavigate?: (route: string) => void; bigScreen?: boolean }) {  const page = PAGE_SPECS[initialView] ?? PAGE_SPECS["reports-brand"];
  const [loading, setLoading] = useState(false);
  const [analytics, setAnalytics] = useState<Analytics>({ charts: [], filter_options: { customers: [], lawyers: [] }, source: "realtime" });
  const [query, setQuery] = useState<ReportFilterValues>({});
  const pageBigScreen = useReportBigScreen();
  const view = initialView.replace("reports-", "");

  const paramsFor = (values: ReportFilterValues) => ({
    view,
    customer: values.customer?.join(",") || "",
    court_lawyer: values.courtLawyer?.join(",") || "",
    handling_lawyer: values.handlingLawyer || "",
    assistant: values.assistant || "",
    investigator: values.investigator || "",
    court: values.court || "",
    group_mode: values.groupMode || "",
    source_from: values.sourceDate?.[0]?.format("YYYY-MM-DD"),
    source_to: values.sourceDate?.[1]?.format("YYYY-MM-DD"),
    hearing_from: values.hearingDate?.[0]?.format("YYYY-MM-DD"),
    hearing_to: values.hearingDate?.[1]?.format("YYYY-MM-DD"),
  });
  const load = async (values: ReportFilterValues = query) => {
    setLoading(true);
    try {
      const { data } = await api.get("/reports/analytics", { params: paramsFor(values) });
      setAnalytics(data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "报表实时数据加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setQuery({});
    if (!PAGE_OWN_LOADERS.has(initialView)) void load({});
  }, [initialView]);
  const queryReport = (values: ReportFilterValues) => { setQuery(values); void load(values); };
  const chartItems = (title: string) => analytics.charts.find(item => item.title === title)?.items ?? [];
  if (initialView === "reports-customer-roi") return <CustomerRoiReport onNavigate={onNavigate} />;
  if (initialView === "reports-staff-roi") return <StaffRoiReport />;
  if (initialView === "reports-refund") return <ProgressMatrixReport title="退费进度案件统计" endpoint="/reports/refund-progress" bigScreen={bigScreen} onNavigate={onNavigate} />;
  // 三张执行进度表合并成一张（BUG 500788）；旧的（二）（三）入口也打开这张。
  if (initialView.startsWith("reports-execution-")) return <ProgressMatrixReport title="执行进度案件统计" endpoint="/reports/execution-progress" bigScreen={bigScreen} onNavigate={onNavigate} />;
  return (
    <div ref={pageBigScreen.ref} className={`report-page ${page.filter === "none" ? "report-page-no-filter" : ""}${pageBigScreen.active ? " report-page-big-screen" : ""}`}>
      <div className="report-page-heading">
        <span>{page.title}</span>
        {!bigScreen && (pageBigScreen.active
          ? <Button size="small" onClick={pageBigScreen.exit}>退出大屏</Button>
          : <Button size="small" type="primary" onClick={pageBigScreen.enter}>大屏展示</Button>)}
      </div>
      {page.filter !== "none" && <Filters key={initialView} kind={page.filter as "brand" | "lawyer"} options={analytics.filter_options} onQuery={queryReport} />}      {page.tab && (
        <div className="report-tabs">
          <span className="report-tab-active">{page.tab}</span>
        </div>
      )}
      <Spin spinning={loading}>
        {/* 算不出来的项留空，不再单独提醒（tgn 11-01，BUG20261101006）。 */}
        <div className={`report-chart-grid ${page.charts.length === 2 ? "report-chart-grid-two" : ""}`}>
          {page.charts.map((chart, index) => (
            <MetricChart key={`${chart.title}-${index}`} spec={chart} items={chartItems(chart.title)} />
          ))}
        </div>
      </Spin>
    </div>
  );
}

export default function ReportCenterPage({ initialView = "reports-brand", onNavigate, bigScreen = false }: { initialView?: string; onNavigate?: (route: string) => void; bigScreen?: boolean }) {
  return initialView === "reports-large-screen"
    ? <ReportLargeScreenPage onExit={() => onNavigate?.("reports-brand")} />
    : <StandardReportCenterPage initialView={initialView} onNavigate={onNavigate} bigScreen={bigScreen} />;
}
