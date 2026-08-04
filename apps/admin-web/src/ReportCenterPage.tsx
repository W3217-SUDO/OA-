import { useEffect, useState } from "react";
import { Button, DatePicker, Empty, Form, Input, message, Select, Spin } from "antd";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "./api";
import "./report-center.css";

type ChartResult = { title: string; unit: ChartSpec["unit"]; items: { name: string; value: number }[] };
type Analytics = { charts: ChartResult[]; filter_options: { customers: string[]; lawyers: string[] }; source: "realtime" };
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
};

type PageSpec = {
  title: string;
  tab?: string;
  filter: "brand" | "lawyer" | "none";
  charts: ChartSpec[];
};

const PAGE_SPECS: Record<string, PageSpec> = {
  "reports-brand": {
    title: "资金运营情况统计",
    tab: "按品牌统计",
    filter: "brand",
    charts: [
      { title: "资金回款周期统计", unit: "天/案", metricKeys: ["资金回款周期", "资金回款周期统计"] },
      { title: "资金亏损金额统计", unit: "元", metricKeys: ["资金亏损金额", "资金亏损金额统计"] },
      { title: "资金回报率统计", unit: "百分比", metricKeys: ["资金回报率", "资金回报率统计"] },
      { title: "资金亏损率统计", unit: "百分比", metricKeys: ["资金亏损率", "资金亏损率统计"] },
    ],
  },
  "reports-lawyer": {
    title: "资金运营情况统计",
    tab: "按开庭律师统计",
    filter: "lawyer",
    charts: [
      { title: "资金回款周期统计", unit: "天/案", metricKeys: ["资金回款周期", "资金回款周期统计"] },
      { title: "资金亏损金额统计", unit: "元", metricKeys: ["资金亏损金额", "资金亏损金额统计"] },
      { title: "资金回报率统计", unit: "百分比", metricKeys: ["资金回报率", "资金回报率统计"] },
      { title: "资金亏损率统计", unit: "百分比", metricKeys: ["资金亏损率", "资金亏损率统计"] },
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
  "reports-execution-1": {
    title: "执行进度案件统计",
    filter: "none",
    charts: [
      { title: "一审待执行案件数量", unit: "个/案", limit: 20 },
      { title: "二审待执行案件数量", unit: "个/案", limit: 20 },
      { title: "准备材料案件数量", unit: "个/案", limit: 20 },
      { title: "提交法院案件数量", unit: "个/案", limit: 20 },
    ],
  },
};

PAGE_SPECS["reports-execution-2"] = {
  title: "执行进度案件统计",
  filter: "none",
  charts: [
    { title: "执行受理案件数量", unit: "个/案", limit: 20 },
    { title: "执行中止案件数量", unit: "个/案", limit: 20 },
    { title: "执行结案案件数量", unit: "个/案", limit: 20 },
    { title: "执行终本案件数量", unit: "个/案", limit: 20 },
  ],
};
PAGE_SPECS["reports-execution-3"] = {
  title: "执行进度案件统计",
  filter: "none",
  charts: [
    { title: "执行终结案件数量", unit: "个/案", limit: 20 },
    { title: "执行中止案件数量", unit: "个/案", limit: 20 },
  ],
};

function Filters({ kind, options, onQuery }: { kind: "brand" | "lawyer"; options: Analytics["filter_options"]; onQuery: (values: ReportFilterValues) => void }) {
  const [form] = Form.useForm();

  return (
    <Form
      form={form}
      className="report-filter"
      initialValues={{ customer: [], courtLawyer: [], groupMode: "按律师分组统计" }}
      onFinish={onQuery}
    >
      <Form.Item className="report-filter-wide" label="客户名称" name="customer">
        <Select mode="multiple" showSearch optionFilterProp="label" maxTagCount="responsive" placeholder="请选择客户" options={options.customers.map(value => ({ value, label: value }))} />
      </Form.Item>
      <Form.Item className="report-filter-wide" label="开庭律师" name="courtLawyer">
        <Select mode="multiple" showSearch optionFilterProp="label" maxTagCount="responsive" placeholder="请选择" options={options.lawyers.map(value => ({ value, label: value }))} />
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
  );
}

function MetricChart({ spec, items }: { spec: ChartSpec; items: { name: string; value: number }[] }) {
  const chartItems = spec.limit ? items.slice(0, spec.limit) : items;
  return (
    <section className="report-chart-panel">
      <div className="report-chart-title">
        <span>{spec.title}</span>
        <span className="report-chart-unit">单位： {spec.unit}</span>
      </div>
      <div className="report-chart-body">
        {chartItems.length ? <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartItems} margin={{ top: 20, right: 24, bottom: 16, left: 4 }}>
            <CartesianGrid stroke="#ececec" vertical={false} />
            <XAxis dataKey="name" axisLine={{ stroke: "#d8d8d8" }} tickLine={false} tick={{ fill: "#777", fontSize: 11 }} />
            <YAxis
              allowDecimals={spec.unit !== "个/案"}
              domain={[0, "auto"]}
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#777", fontSize: 11 }}
            />
            <Tooltip formatter={(item) => [`${Number(item).toLocaleString()} ${spec.unit}`, spec.title]} />
            <Bar dataKey="value" fill="#36b978" maxBarSize={72} />
          </BarChart>
        </ResponsiveContainer> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前条件下暂无真实业务数据" />}
      </div>
    </section>
  );
}

const largeScreenViews = ["reports-refund", "reports-execution-1", "reports-execution-2", "reports-execution-3"];

export function ReportLargeScreenPage({ initialView = "reports-refund" }: { initialView?: string }) {
  const [index, setIndex] = useState(() => Math.max(0, largeScreenViews.indexOf(initialView)));
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => setIndex(current => (current + 1) % largeScreenViews.length), 30_000);
    return () => clearInterval(timer);
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      const request = document.documentElement.requestFullscreen?.();
      if (request) void request.then(() => setFullscreen(true)).catch(() => setFullscreen(false));
    } else {
      const exit = document.exitFullscreen?.();
      if (exit) void exit.then(() => setFullscreen(false));
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 1000, overflow: "auto", background: "#0b2545", color: "#fff" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px" }}>
        <span>报表大屏</span>
        <Button onClick={toggleFullscreen}>{fullscreen ? "退出全屏" : "全屏"}</Button>
      </div>
      <ReportCenterPage key={largeScreenViews[index]} initialView={largeScreenViews[index]} />
    </div>
  );
}

export default function ReportCenterPage({ initialView = "reports-brand" }: { initialView?: string }) {
  const page = PAGE_SPECS[initialView] ?? PAGE_SPECS["reports-brand"];
  const [loading, setLoading] = useState(false);
  const [analytics, setAnalytics] = useState<Analytics>({ charts: [], filter_options: { customers: [], lawyers: [] }, source: "realtime" });
  const [query, setQuery] = useState<ReportFilterValues>({});
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
    void load({});
  }, [initialView]);
  const queryReport = (values: ReportFilterValues) => { setQuery(values); void load(values); };
  const chartItems = (title: string) => analytics.charts.find(item => item.title === title)?.items ?? [];
  return (
    <div className={`report-page ${page.filter === "none" ? "report-page-no-filter" : ""}`}>
      <div className="report-page-heading">{page.title}</div>
      {page.filter !== "none" && <Filters key={initialView} kind={page.filter} options={analytics.filter_options} onQuery={queryReport} />}
      {page.tab && (
        <div className="report-tabs">
          <span className="report-tab-active">{page.tab}</span>
        </div>
      )}
      <Spin spinning={loading}>
        <div className={`report-chart-grid ${page.charts.length === 2 ? "report-chart-grid-two" : ""}`}>
          {page.charts.map((chart, index) => (
            <MetricChart key={`${chart.title}-${index}`} spec={chart} items={chartItems(chart.title)} />
          ))}
        </div>
      </Spin>
    </div>
  );
}
