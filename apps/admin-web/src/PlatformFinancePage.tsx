import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  DatePicker,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  message,
  Select,
  Space,
  Table,
  Tag,
} from "antd";
import type { TableColumnsType } from "antd";
import { DownloadOutlined, EyeOutlined, ReloadOutlined, SearchOutlined, UndoOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberContractDetailTarget } from "./contractDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import { formatRequiredDate } from "./formSafety";
import "./platform-finance.css";

type FieldKind = "text" | "select" | "range" | "money-range";
type QueryField = {
  key: string;
  label: string;
  kind?: FieldKind;
  options?: string[];
  disabled?: boolean;
};
type PageKind =
  | "receipt"
  | "receipt-create"
  | "payment"
  | "payment-audit"
  | "invoice"
  | "settlement"
  | "archive"
  | "fee-query";
type PageConfig = {
  title: string;
  kind: PageKind;
  status?: string;
};
type EmptyRow = { key: string };

const paymentStatuses = [
  "创建待提交",
  "待审批",
  "待付款",
  "待核销",
  "已付款",
  "已驳回",
  "已作废",
];
const paymentTypes = ["官方费用", "内部费用", "结算费用", "归档费用", "其他费用"];
const invoiceStatuses = ["创建待提交", "待处理", "待开票", "已开票", "已驳回", "已作废"];
const paymentMethods = ["银行转账", "现金", "支票", "支付宝", "微信", "其他"];

const pages: Record<string, PageConfig> = {
  "platform-finance-overview": { title: "回款查询", kind: "receipt" },
  "platform-finance-overview-icbc": { title: "回款（工行）", kind: "receipt" },
  "platform-finance-overview-citic": { title: "回款（中信）", kind: "receipt" },
  "platform-finance-overview-boc": { title: "回款（中行）", kind: "receipt" },
  "platform-finance-overview-new": { title: "回款登记", kind: "receipt-create" },
  "platform-finance-overview-manage": { title: "回款管理", kind: "receipt" },
  "platform-finance-overview-claim": { title: "回款领取", kind: "receipt", status: "待认领" },
  "platform-finance-overview-pending": { title: "待分配回款", kind: "receipt", status: "待分配" },
  "platform-finance-overview-allocated": { title: "已分配回款", kind: "receipt", status: "已分配" },
  "platform-finance-overview-query": { title: "回款查询", kind: "receipt" },

  "platform-finance-payment": { title: "我的请款单", kind: "payment" },
  "platform-finance-payment-mine": { title: "我的请款单", kind: "payment" },
  "platform-finance-payment-audit": {
    title: "请款单审批",
    kind: "payment-audit",
    status: "待审批",
  },
  "platform-finance-payment-waiting": {
    title: "请款单列表",
    kind: "payment",
    status: "已审批",
  },
  "platform-finance-payment-print": {
    title: "付款单打印",
    kind: "payment",
    status: "已付款",
  },
  "platform-finance-payment-writeoff": {
    title: "待核销列表",
    kind: "payment",
    status: "待核销",
  },
  "platform-finance-payment-query": { title: "请款单列表", kind: "payment" },

  "platform-finance-invoice": { title: "公司开票", kind: "invoice" },
  "platform-finance-invoice-mine": { title: "我的开票", kind: "invoice" },
  "platform-finance-invoice-pending": {
    title: "待处理开票",
    kind: "invoice",
    status: "待处理",
  },
  "platform-finance-invoice-company": { title: "公司开票", kind: "invoice" },

  "platform-finance-settlement": { title: "待结算", kind: "settlement" },
  "platform-finance-settlement-pending": {
    title: "待结算",
    kind: "settlement",
    status: "待结算",
  },
  "platform-finance-settlement-audit": {
    title: "待审核",
    kind: "settlement",
    status: "待审核",
  },
  "platform-finance-settlement-payment": {
    title: "待付款",
    kind: "settlement",
    status: "待付款",
  },
  "platform-finance-settlement-paid": {
    title: "已付款",
    kind: "settlement",
    status: "已付款",
  },
  "platform-finance-settlement-refused": {
    title: "已拒绝",
    kind: "settlement",
    status: "已拒绝",
  },

  "platform-finance-archive-fee": { title: "待归档", kind: "archive" },
  "platform-finance-archive-fee-pending": {
    title: "待归档",
    kind: "archive",
    status: "待归档",
  },
  "platform-finance-archive-fee-payment": {
    title: "待支付",
    kind: "archive",
    status: "待支付",
  },
  "platform-finance-archive-fee-paid": {
    title: "已支付",
    kind: "archive",
    status: "已支付",
  },
  "platform-finance-archive-fee-refused": {
    title: "已拒绝",
    kind: "archive",
    status: "已拒绝",
  },
  "platform-finance-fee-query": { title: "费用查询", kind: "fee-query" },
};

const receiptFields: QueryField[] = [
  { key: "receiptRange", label: "回款日期", kind: "range" },
  { key: "bankNo", label: "银行单号" },
  { key: "customer", label: "客户名称" },
  { key: "payer", label: "回款单位" },
  { key: "method", label: "回款方式", kind: "select", options: paymentMethods },
  { key: "contractNo", label: "合同编号" },
];
const paymentFields: QueryField[] = [
  { key: "applicationRange", label: "申请日期", kind: "range" },
  { key: "status", label: "付款状态", kind: "select", options: paymentStatuses },
  { key: "applicant", label: "申请人", disabled: true },
  { key: "paymentRange", label: "付款日期", kind: "range" },
  { key: "contractNo", label: "合同号" },
  { key: "caseNo", label: "案件编号" },
  { key: "payee", label: "收款单位" },
  { key: "paymentNo", label: "请款单号" },
  { key: "feeType", label: "费用类型", kind: "select", options: paymentTypes },
  { key: "customer", label: "客户名称" },
];
const paymentAuditFields: QueryField[] = [
  { key: "applicationRange", label: "申请日期", kind: "range" },
  {
    key: "status",
    label: "付款状态",
    kind: "select",
    options: paymentStatuses,
    disabled: true,
  },
  { key: "caseNo", label: "案件编号" },
  { key: "paymentNo", label: "请款单号" },
  { key: "customer", label: "客户名称" },
  { key: "contractNo", label: "合同号" },
  { key: "payee", label: "收款单位" },
  { key: "applicant", label: "申请人" },
  { key: "feeType", label: "费用类型", kind: "select", options: paymentTypes },
];
const invoiceFields: QueryField[] = [
  { key: "customer", label: "客户名称" },
  { key: "invoiceRequestNo", label: "请票单号" },
  {
    key: "invoiceType",
    label: "发票类别",
    kind: "select",
    options: ["增值税普通发票", "增值税专用发票", "电子发票"],
  },
  { key: "invoiceTitle", label: "开票抬头" },
  { key: "invoiceNo", label: "发票号码" },
  { key: "status", label: "发票状态", kind: "select", options: invoiceStatuses },
  { key: "invoiceRange", label: "开票日期", kind: "range" },
  { key: "applicant", label: "申请人" },
  { key: "caseNo", label: "案件编号" },
];
const settlementFields: QueryField[] = [
  { key: "customer", label: "客户名称" },
  { key: "caseNo", label: "案件编号" },
  { key: "receiptRange", label: "回款日期", kind: "range" },
  { key: "payer", label: "回款单位" },
  { key: "method", label: "回款方式", kind: "select", options: paymentMethods },
  { key: "customerSecond", label: "客户名称" },
  { key: "hearingLawyer", label: "开庭律师" },
  { key: "assistant", label: "律师助理" },
  { key: "customerManager", label: "客户管理人" },
  { key: "sourceOwner", label: "案源人" },
];
const archiveFields: QueryField[] = [
  { key: "caseType", label: "案件类型" },
  { key: "caseStage", label: "案件阶段" },
  { key: "payer", label: "回款单位" },
  { key: "receiptRange", label: "回款时间", kind: "range" },
  { key: "hearingLawyer", label: "开庭律师" },
  { key: "assistant", label: "律师助理" },
  { key: "submitter", label: "提交人" },
  { key: "settlementRange", label: "结算支付日期", kind: "range" },
  { key: "caseNo", label: "案件编号" },
  { key: "customer", label: "客户名称" },
  { key: "auditor", label: "审核人" },
];
const feeQueryFields: QueryField[] = [
  { key: "caseNo", label: "案件编号" },
  { key: "courtCaseNo", label: "法院案号" },
  { key: "notaryNo", label: "公证书号" },
  { key: "refundAmount", label: "退费金额", kind: "money-range" },
  { key: "customer", label: "客户名称" },
  { key: "payee", label: "收款单位" },
  { key: "status", label: "付款状态", kind: "select", options: paymentStatuses },
  { key: "paymentRange", label: "付款时间", kind: "range" },
  { key: "hearingLawyer", label: "开庭律师" },
  { key: "assistant", label: "律师助理" },
  { key: "caseStage", label: "案件阶段" },
  { key: "feeType", label: "费用类型", kind: "select", options: paymentTypes },
];

const column = (title: string, width = 120) => ({ title, dataIndex: title, width });
const operationColumn = column("操作", 90);
const receiptColumns: TableColumnsType<EmptyRow> = [
  column("客户名称", 190),
  column("客户管理人", 100),
  column("回款单位", 190),
  column("回款日期", 110),
  column("回款金额", 115),
  column("已分金额", 110),
  column("未分金额", 110),
  column("已分官费", 110),
  column("已分代理费", 115),
  column("已分其他费用", 125),
  column("回款方式", 100),
  column("备注", 180),
];
const paymentColumns: TableColumnsType<EmptyRow> = [
  operationColumn,
  column("请款单号", 150),
  column("状态", 90),
  column("申请日期", 105),
  column("申请金额", 110),
  column("截止日期", 105),
  column("案件编号", 145),
  column("案件阶段", 100),
  column("合同编号", 145),
  column("付款日期", 105),
  column("申请人", 90),
  column("客户管理人", 105),
  column("交款人", 90),
];
const paymentAuditColumns: TableColumnsType<EmptyRow> = [
  column("请款单号", 150),
  column("类型", 95),
  column("收款单位", 190),
  column("申请人", 90),
  column("申请付款金额", 120),
  column("交款截止日期", 120),
  column("案件编号", 145),
  column("案件阶段", 100),
  column("合同编号", 145),
  column("合同名称", 190),
  column("申请日期", 105),
  column("状态", 90),
];
const invoiceColumns: TableColumnsType<EmptyRow> = [
  operationColumn,
  column("请票单号", 145),
  column("客户名称", 190),
  column("开票金额", 110),
  column("高开金额", 110),
  column("开票抬头", 190),
  column("发票号码", 140),
  column("申请人", 90),
  column("领票人", 90),
  column("开票日期", 105),
  column("状态", 90),
];
const settlementColumns: TableColumnsType<EmptyRow> = [
  operationColumn,
  column("客户名称", 190),
  column("客户管理人", 105),
  column("回款单位", 190),
  column("回款日期", 105),
  column("回款金额", 110),
  column("已分金额", 110),
  column("未分金额", 110),
  column("已分官费", 110),
  column("已分代理费", 115),
  column("已分其他费用", 125),
  column("代理费结算金额", 135),
  column("扣归档费", 105),
  column("实际结算金额", 125),
];
const archiveColumns: TableColumnsType<EmptyRow> = [
  operationColumn,
  column("案号", 145),
  column("客户", 190),
  column("案件阶段", 100),
  column("律师助理", 95),
  column("开庭律师", 95),
  column("客户管理人", 105),
  column("费用类型", 100),
  column("回款方式", 100),
  column("回款时间", 110),
  column("回款金额", 110),
  column("归档费金额", 115),
  column("结算时间", 110),
];
const feeQueryColumns: TableColumnsType<EmptyRow> = [
  column("案号", 145),
  column("客户", 190),
  column("案件阶段", 100),
  column("助理", 90),
  column("开庭律师", 95),
  column("法院案号", 145),
  column("费用类型", 100),
  column("金额", 105),
  column("退费金额", 110),
  column("已退金额", 110),
  column("到账时间", 110),
  column("到账金额", 110),
  column("付款时间", 110),
  column("付款金额", 110),
  column("法院名称", 180),
  column("付款状态", 100),
];

const fieldsByKind: Record<PageKind, QueryField[]> = {
  receipt: receiptFields,
  "receipt-create": [],
  payment: paymentFields,
  "payment-audit": paymentAuditFields,
  invoice: invoiceFields,
  settlement: settlementFields,
  archive: archiveFields,
  "fee-query": feeQueryFields,
};
const columnsByKind: Record<PageKind, TableColumnsType<EmptyRow>> = {
  receipt: receiptColumns,
  "receipt-create": [],
  payment: paymentColumns,
  "payment-audit": paymentAuditColumns,
  invoice: invoiceColumns,
  settlement: settlementColumns,
  archive: archiveColumns,
  "fee-query": feeQueryColumns,
};

function QueryControl({
  field,
  value,
  onChange,
}: {
  field: QueryField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  if (field.kind === "range") {
    return (
      <DatePicker.RangePicker
        value={value as never}
        onChange={onChange}
        disabled={field.disabled}
        placeholder={["开始日期", "结束日期"]}
      />
    );
  }
  if (field.kind === "money-range") {
    const pair = (value as [number | null, number | null]) || [null, null];
    return (
      <Space.Compact className="platform-finance-money-range">
        <InputNumber
          value={pair[0]}
          min={0}
          precision={2}
          placeholder="最小金额"
          onChange={(next) => onChange([next, pair[1]])}
        />
        <Input className="range-split" value="-" readOnly tabIndex={-1} />
        <InputNumber
          value={pair[1]}
          min={0}
          precision={2}
          placeholder="最大金额"
          onChange={(next) => onChange([pair[0], next])}
        />
      </Space.Compact>
    );
  }
  if (field.kind === "select") {
    return (
      <Select
        allowClear={!field.disabled}
        value={value as string | undefined}
        disabled={field.disabled}
        placeholder="请选择"
        options={(field.options || []).map((option) => ({
          value: option,
          label: option,
        }))}
        onChange={onChange}
      />
    );
  }
  return (
    <Input
      allowClear
      value={value as string | undefined}
      disabled={field.disabled}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

type ReceiptCreateValues = {
  payerName: string;
  customer?: string;
  receivedDate: dayjs.Dayjs;
  amount: number;
  method: string;
  bankReference?: string;
  contractNo?: string;
  remark?: string;
};

function makeReceiptNo() {
  const suffix = String(Math.floor(Math.random() * 100000000)).padStart(8, "0");
  return `R${dayjs().format("YYMMDD")}-${suffix}`;
}

export function ReceiptCreatePage() {
  const [form] = Form.useForm<ReceiptCreateValues>();
  const [receiptNo, setReceiptNo] = useState(makeReceiptNo);
  const [customers, setCustomers] = useState<string[]>([]);
  const [contracts, setContracts] = useState<{ serial_no: string; customer: string; title: string }[]>([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api
      .get("/records?module=customer&page_size=100")
      .then(({ data }) =>
        setCustomers(
          Array.from(
            new Set<string>(
              (data.items || []).map((item: { title: string }) => item.title).filter(Boolean),
            ),
          ),
        ),
      )
      .catch(() => setCustomers([]));
  }, []);
  useEffect(() => {
    api.get("/records?module=contract&page_size=100").then(({ data }) => setContracts(data.items || [])).catch(() => setContracts([]));
  }, []);

  const submit = async (continueAdding: boolean) => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      const extra = [
        values.customer && `客户：${values.customer}`,
        values.method && `回款方式：${values.method}`,
        values.remark,
      ].filter(Boolean);
      const { data: payment } = await api.post("/finance/incoming-payments", {
        received_date: formatRequiredDate(values.receivedDate, "回款时间"),
        amount: values.amount,
        payer_name: values.payerName,
        bank_reference: values.bankReference?.trim() || receiptNo,
        customer: values.customer || "",
        contract_no: values.contractNo || "",
        remark: extra.join("；"),
      });
      if (values.customer) {
        await api.post(`/finance/incoming-payments/${payment.id}/claim`, {
          customer: values.customer,
          comment: "平台财务回款登记时匹配客户",
        });
      }
      message.success(values.customer ? "回款登记并认领客户成功" : "回款登记成功");
      if (continueAdding) {
        form.resetFields();
        form.setFieldValue("receivedDate", dayjs());
        setReceiptNo(makeReceiptNo());
      }
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || "回款登记失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="platform-finance-original platform-receipt-create" variant="borderless">
      <div className="platform-finance-title">回款登记</div>
      <div className="platform-receipt-hint">
        <b>温馨提示：</b>
        <p>1. 请完善以下信息，方便我们更好地为您服务。</p>
        <p>2. 如未匹配到客户，这笔回款将放入公海，由案源人自行领取。</p>
      </div>
      <Form<ReceiptCreateValues>
        form={form}
        className="platform-receipt-form"
        labelCol={{ span: 7 }}
        wrapperCol={{ span: 17 }}
        initialValues={{ receivedDate: dayjs() }}
      >
        <Form.Item label="回款流水号">
          <Input value={receiptNo} disabled />
        </Form.Item>
        <Form.Item label="回款单位" name="payerName" rules={[{ required: true, message: "请输入回款单位" }, { min: 2 }]}>
          <Input />
        </Form.Item>
        <Form.Item label="客户名称" name="customer">
          <Select
            allowClear
            showSearch
            placeholder="请选择客户"
            options={customers.map((value) => ({ value, label: value }))}
          />
        </Form.Item>
        <Form.Item label="回款时间" name="receivedDate" rules={[{ required: true, message: "请选择回款时间" }]}>
          <DatePicker />
        </Form.Item>
        <Form.Item label="回款金额" name="amount" rules={[{ required: true, message: "请输入回款金额" }]}>
          <InputNumber min={0.01} precision={2} controls={false} />
        </Form.Item>
        <Form.Item label="回款方式" name="method" rules={[{ required: true, message: "请选择回款方式" }]}>
          <Select options={paymentMethods.map((value) => ({ value, label: value }))} />
        </Form.Item>
        <Form.Item label="银行单号" name="bankReference" rules={[{ min: 2 }]}>
          <Input />
        </Form.Item>
        <Form.Item label="合同编号" name="contractNo">
          <Select allowClear showSearch placeholder="请选择已签约合同" options={contracts.filter((item) => !form.getFieldValue("customer") || item.customer === form.getFieldValue("customer")).map((item) => ({ value: item.serial_no, label: `${item.serial_no}｜${item.customer}｜${item.title}` }))} />
        </Form.Item>
        <Form.Item label="备注" name="remark">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item wrapperCol={{ offset: 7, span: 17 }}>
          <Space>
            <Button type="primary" loading={submitting} onClick={() => void submit(false)}>提交</Button>
            <Button type="primary" loading={submitting} onClick={() => void submit(true)}>提交并新增</Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
}

export default function PlatformFinancePage({
  initialView = "platform-finance-overview-query",
  onNavigate,
}: {
  initialView?: string;
  onNavigate?: (route: string) => void;
}) {
  const config = pages[initialView] || pages["platform-finance-overview-query"];
  const fields = fieldsByKind[config.kind];
  const columns = columnsByKind[config.kind];
  const initialQuery = useMemo(
    () => (config.status ? { status: config.status } : {}),
    [initialView, config.status],
  );
  const [query, setQuery] = useState<Record<string, unknown>>(initialQuery);
  const [submittedQuery, setSubmittedQuery] = useState<Record<string, unknown>>(initialQuery);
  const [selectedKeys, setSelectedKeys] = useState<React.Key[]>([]);
  const [sourceRows, setSourceRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<any | null>(null);

  const loadRows = async () => {
    if (config.kind === "receipt-create") return;
    setLoading(true);
    try {
      if (config.kind === "receipt") {
        const { data } = await api.get("/finance/incoming-payments");
        setSourceRows(data.items || []);
      } else {
        const module = config.kind === "invoice" ? "invoice" : "finance";
        const { data } = await api.get("/records", { params: { module, page_size: 100 } });
        setSourceRows(data.items || []);
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "平台财务数据加载失败");
      setSourceRows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setQuery(initialQuery);
    setSubmittedQuery(initialQuery);
    setSelectedKeys([]);
    void loadRows();
  }, [initialView, initialQuery]);

  const clear = () => {
    setQuery(initialQuery);
    setSubmittedQuery(initialQuery);
    setSelectedKeys([]);
  };
  const showSelection = ["receipt", "payment", "payment-audit", "fee-query"].includes(
    config.kind,
  );

  if (config.kind === "receipt-create") return <ReceiptCreatePage />;

  const money = (value: unknown) => value == null ? "—" : `¥ ${Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2 })}`;
  const openCaseDetail = (caseNo: unknown) => {
    const serialNo = String(caseNo || "").trim();
    if (!serialNo || serialNo === "—") {
      message.warning("当前财务记录未关联案件");
      return;
    }
    rememberCaseDetailTarget({ serial_no: serialNo });
    onNavigate?.("case-company");
  };
  const openContractDetail = (contractNo: unknown) => {
    const serialNo = String(contractNo || "").trim();
    if (!serialNo || serialNo === "—") {
      message.warning("当前财务记录未关联合同");
      return;
    }
    rememberContractDetailTarget({ serial_no: serialNo });
    onNavigate?.("contract-company");
  };
  const openCustomerDetail = (customer: unknown, customerNo?: unknown) => {
    const title = String(customer || "").trim();
    const serialNo = String(customerNo || "").trim();
    if (!title && !serialNo) return message.warning("当前财务记录未关联客户");
    rememberCustomerDetailTarget({ title, serial_no: serialNo });
    onNavigate?.("customer-company");
  };
  const tableRows = sourceRows
    .filter((item) => {
      if (config.kind === "settlement" && item.data?.fee_type !== "结算费用") return false;
      if (config.kind === "archive" && item.data?.fee_type !== "归档费用") return false;
      if (config.status === "已审批" && !["已审批", "部分付款"].includes(item.status)) return false;
      if (config.status && config.status !== "已审批" && item.status !== config.status) return false;
      if (initialView === "platform-finance-payment-writeoff" && (item.status !== "已付款" || item.data?.writeoff_status === "已核销")) return false;
      return true;
    })
    .map((item) => {
      const data = item.data || {};
      const amount = item.amount ?? data.amount;
      const row: any = {
        key: item.id,
        _source: item,
        操作: "",
        客户名称: item.claimed_customer || item.customer || "—",
        客户: item.customer || "—",
        客户管理人: item.claimant || data.customer_manager || item.owner || "—",
        回款单位: item.payer_name || data.payer || "—",
        回款日期: item.received_date || data.received_at || "—",
        回款时间: item.received_date || data.received_at || "—",
        回款金额: money(item.amount ?? data.received_amount ?? amount),
        已分金额: money(item.allocated_amount),
        未分金额: money(item.remaining_amount),
        回款方式: data.payment_method || "银行转账",
        备注: item.remark || item.description || "—",
        请款单号: item.serial_no || "—",
        请票单号: item.serial_no || "—",
        状态: item.status,
        付款状态: item.status,
        申请日期: item.created_at ? dayjs(item.created_at).format("YYYY-MM-DD") : "—",
        申请金额: money(amount),
        开票金额: money(amount),
        付款日期: data.payment_date || "—",
        申请人: data.applicant || item.owner || "—",
        案件编号: data.case_no || "—",
        案号: data.case_no || "—",
        合同编号: data.contract_no || "—",
        收款单位: data.payee || "—",
        费用类型: data.fee_type || "—",
        金额: money(amount),
        退费金额: money(data.refund_amount),
        开票抬头: data.invoice_title || item.customer || "—",
        发票号码: data.invoice_no || "—",
        案件阶段: data.case_stage || "—",
        开庭律师: data.hearing_lawyer || "—",
        律师助理: data.assistant || "—",
      };
      return row;
    });
  const filteredRows = tableRows.filter((row) => fields.every((field) => {
    const value = submittedQuery[field.key];
    if (value == null || value === "" || (Array.isArray(value) && !value.some(Boolean))) return true;
    if (field.kind === "money-range") {
      const raw = Number(row.金额?.replace?.(/[^0-9.-]/g, "") || 0);
      const [min, max] = value as [number | null, number | null];
      return (min == null || raw >= min) && (max == null || raw <= max);
    }
    if (field.kind === "range") {
      const raw = row[field.label] || row.申请日期 || row.回款日期 || row.付款日期;
      const date = dayjs(raw);
      const pair = value as dayjs.Dayjs[];
      return date.isValid() && (!pair[0] || !date.isBefore(pair[0], "day")) && (!pair[1] || !date.isAfter(pair[1], "day"));
    }
    if (field.key === "status") return String(row.状态 || row.付款状态) === String(value);
    return JSON.stringify(row).toLowerCase().includes(String(value).toLowerCase());
  }));
  const renderedColumns = columns.map((item: any) => item.title === "操作" ? {
    ...item,
    fixed: "left" as const,
    render: (_: unknown, row: any) => <Button type="link" icon={<EyeOutlined />} onClick={() => setDetail(row._source)}>详情</Button>,
  } : ["案件编号", "案号"].includes(String(item.title)) ? {
    ...item,
    render: (_: unknown, row: any) => {
      const value = row[item.title] || row._source?.data?.case_no;
      return value && value !== "—" ? <Button type="link" onClick={() => openCaseDetail(value)}>{value}</Button> : "—";
    },
  } : ["合同编号", "合同号"].includes(String(item.title)) ? {
    ...item,
    render: (_: unknown, row: any) => {
      const value = row[item.title] || row._source?.data?.contract_no;
      return value && value !== "—" ? <Button type="link" onClick={() => openContractDetail(value)}>{value}</Button> : "—";
    },
  } : ["客户名称", "客户"].includes(String(item.title)) ? {
    ...item,
    render: (_: unknown, row: any) => {
      const value = row[item.title] || row._source?.claimed_customer || row._source?.customer;
      return value && value !== "—" ? <Button type="link" onClick={() => openCustomerDetail(value, row._source?.data?.customer_no)}>{value}</Button> : "—";
    },
  } : item);
  const exportCsv = () => {
    const titles = renderedColumns.map((item: any) => String(item.title)).filter((title) => title !== "操作");
    const escape = (value: unknown) => `"${String(value ?? "").replaceAll('"', '""')}"`;
    const csv = "\ufeff" + [titles.map(escape).join(","), ...filteredRows.map(row => titles.map(title => escape(row[title])).join(","))].join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = `${config.title}-${dayjs().format("YYYYMMDD")}.csv`; link.click(); URL.revokeObjectURL(url);
  };

  return (
    <Card className="platform-finance-original" variant="borderless">
      <div className="platform-finance-title">{config.title}</div>
      <div className="platform-finance-query-panel">
        <div className="platform-finance-query-grid">
          {fields.map((field) => (
            <label className="platform-finance-field" key={field.key}>
              <span>{field.label}</span>
              <QueryControl
                field={field}
                value={query[field.key]}
                onChange={(value) =>
                  setQuery((current) => ({ ...current, [field.key]: value }))
                }
              />
            </label>
          ))}
        </div>
        <div className="platform-finance-actions">
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={() => setSubmittedQuery({ ...query })}
          >
            查询
          </Button>
          {config.kind === "fee-query" && (
            <Button icon={<UndoOutlined />} onClick={clear}>
              清空
            </Button>
          )}
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void loadRows()}>刷新</Button>
          <Button icon={<DownloadOutlined />} disabled={!filteredRows.length} onClick={exportCsv}>导出CSV</Button>
        </div>
      </div>
      <Table<any>
        className="platform-finance-table"
        rowKey="key"
        size="small"
        bordered
        loading={loading}
        columns={renderedColumns}
        dataSource={filteredRows}
        rowSelection={
          showSelection
            ? { selectedRowKeys: selectedKeys, onChange: setSelectedKeys }
            : undefined
        }
        scroll={{ x: "max-content" }}
        locale={{ emptyText: "暂无数据" }}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
        data-query-count={Object.keys(submittedQuery).length}
      />
      <Drawer open={Boolean(detail)} width={620} title={`财务详情：${detail?.serial_no || detail?.receipt_no || ""}`} onClose={() => setDetail(null)}>
        {detail && <Descriptions bordered size="small" column={1} items={[
          { key: "status", label: "状态", children: <Tag>{detail.status}</Tag> },
          { key: "customer", label: "客户", children: (detail.claimed_customer || detail.customer) ? <Button type="link" onClick={() => openCustomerDetail(detail.claimed_customer || detail.customer, detail.data?.customer_no)}>{detail.claimed_customer || detail.customer}</Button> : "—" },
          { key: "amount", label: "金额", children: money(detail.amount ?? detail.data?.amount) },
          { key: "case_no", label: "案件编号", children: detail.data?.case_no ? <Button type="link" onClick={() => openCaseDetail(detail.data.case_no)}>{detail.data.case_no}</Button> : "—" },
          { key: "contract_no", label: "合同编号", children: detail.data?.contract_no ? <Button type="link" onClick={() => openContractDetail(detail.data.contract_no)}>{detail.data.contract_no}</Button> : "—" },
          { key: "owner", label: "负责人", children: detail.claimant || detail.owner || detail.operator || "—" },
          { key: "date", label: "日期", children: detail.received_date || detail.created_at || "—" },
          { key: "remark", label: "说明", children: detail.remark || detail.description || "—" },
          { key: "data", label: "扩展信息", children: <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(detail.data || detail.allocations || {}, null, 2)}</pre> },
        ]} />}
      </Drawer>
    </Card>
  );
}
