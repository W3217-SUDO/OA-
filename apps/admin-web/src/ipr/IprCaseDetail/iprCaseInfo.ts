// 知识产权案件详情页的“案件信息”区，字段和顺序按原沪知系统案件页（BUG20261028001）。
// 迁移数据字段名沿用旧库（case_name、case_request_no……），新建案件用新字段名，按顺序取第一个有值的。
// 商标案件按原系统商标页：不显示证件号码、发明人、首年年费年度、费用减缓比例，另有商标类别等（BUG20261030005）。

type IprCaseLike = { serial_no?: string; customer?: string; status?: string; data?: Record<string, any> | null };

export type IprCaseInfoItem = { key: string; label: string; value: string };
export type IprCaseFlag = { key: string; label: string; checked: boolean };

const pick = (data: Record<string, any>, ...keys: string[]) => {
  for (const key of keys) {
    const value = data[key];
    if (Array.isArray(value) ? value.length : value !== null && value !== undefined && String(value).trim() !== "") return value;
  }
  return "";
};

const text = (value: unknown) => (Array.isArray(value) ? value.join("；") : String(value ?? "").trim());

/** 旧库日期带时间（2018-08-01T00:00:00），页面只显示日期。 */
export const iprDateText = (value: unknown) => {
  const raw = text(value);
  return /^\d{4}-\d{2}-\d{2}/.test(raw) ? raw.slice(0, 10) : raw;
};

// 费用减缓比例：旧库 1.00 表示不减缓，0.85、0.70 表示减缓 85%、70%（同原系统“85%减缓”“无减缓”）。
export const RELIEF_RATE_OPTIONS = [
  { value: "1.00", label: "无减缓" },
  { value: "0.85", label: "85%减缓" },
  { value: "0.70", label: "70%减缓" },
];
export const reliefRateText = (value: unknown) => {
  const raw = text(value);
  if (!raw) return "";
  const number = Number(raw);
  if (!Number.isFinite(number)) return raw;
  if (number >= 1 || number <= 0) return "无减缓";
  return `${Math.round(number * 100)}%减缓`;
};

const CHINESE_DIGITS = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九"];
const chineseNumber = (value: number) => value <= 10
  ? (value === 10 ? "十" : CHINESE_DIGITS[value])
  : value < 20 ? `十${CHINESE_DIGITS[value - 10]}` : `${CHINESE_DIGITS[Math.floor(value / 10)]}十${CHINESE_DIGITS[value % 10]}`;
// 首年年费年度：旧库存数字 1、2…，原系统显示“第一年”“第二年”。
export const annualYearText = (value: unknown) => {
  const raw = text(value);
  const number = Number(raw);
  return Number.isInteger(number) && number >= 1 && number <= 30 ? `第${chineseNumber(number)}年` : raw;
};
// 商标类型：旧库 TradeTypeId 只有 1（一般商标）。
export const TRADE_TYPE_OPTIONS = ["一般商标", "集体商标", "证明商标"].map((value) => ({ value, label: value }));
const tradeTypeText = (data: Record<string, any>) => text(data.trade_type_name) || (String(data.trade_type_id ?? "") === "1" ? "一般商标" : text(data.trade_type_id));

export const isTrademarkCase = (record: IprCaseLike) => record.data?.case_kind === "商标";

export const ANNUAL_YEAR_OPTIONS = Array.from({ length: 20 }, (_, index) => ({ value: String(index + 1), label: annualYearText(index + 1) }));

/** 旧库是 T/F，新建案件是布尔值。 */
export const iprFlagChecked = (value: unknown) => value === true || ["T", "t", "true", "1", "是"].includes(String(value ?? ""));

export function iprCaseInfoItems(record: IprCaseLike): IprCaseInfoItem[] {
  const data = record.data || {};
  const item = (key: string, label: string, value: unknown): IprCaseInfoItem => ({ key, label, value: text(value) || "—" });
  if (isTrademarkCase(record)) {
    return [
      item("serial", "案件编号", record.serial_no || data.case_no),
      item("type", "案件类型", pick(data, "case_type_name", "case_type", "application_type")),
      item("phase", "案件阶段", pick(data, "case_phase") || record.status),
      item("register-date", "立案日", iprDateText(pick(data, "case_register_date", "accepted_at"))),
      item("request-no", "申请号", pick(data, "case_request_no", "application_no")),
      item("name", "商标名称", pick(data, "case_name", "patent_name", "invention_name")),
      item("request-date", "申请日", iprDateText(pick(data, "case_request_date", "application_date"))),
      item("authorization-date", "授权日", iprDateText(pick(data, "authorization_date"))),
      item("source-people", "案源人", pick(data, "case_origin_people_name", "case_source")),
      item("agent", "代理人", pick(data, "agent", "procurator_name")),
      item("writer", "撰稿人", pick(data, "writer", "copywriter_name")),
      item("source-date", "案源日", iprDateText(pick(data, "case_origin_date", "source_date"))),
      item("first-instance-date", "初审公告", iprDateText(pick(data, "first_instance_date"))),
      item("trade-type", "商标类型", tradeTypeText(data)),
      item("trademark-ids", "商标类别", pick(data, "trademark_ids")),
      item("ref-case-no", "关联案号", pick(data, "ref_case_no")),
      item("applicant", "申请人", pick(data, "applicant_name", "applicant", "applicants")),
      item("trade-product-service", "商品服务", pick(data, "trade_product_service")),
      item("customer", "客户", record.customer),
      item("manager", "案件管理人", pick(data, "case_manager", "case_officer_name")),
    ];
  }
  return [
    item("serial", "案件编号", record.serial_no || data.case_no),
    item("type", "案件类型", pick(data, "case_type_name", "case_type", "application_type")),
    item("phase", "案件阶段", pick(data, "case_phase") || record.status),
    item("register-date", "立案日", iprDateText(pick(data, "case_register_date", "accepted_at"))),
    item("request-no", "申请号", pick(data, "case_request_no", "application_no")),
    item("name", data.case_kind === "商标" ? "商标名称" : data.case_kind === "专利" ? "专利名称" : "案件名称", pick(data, "case_name", "patent_name", "invention_name")),
    item("request-date", "申请日", iprDateText(pick(data, "case_request_date", "application_date"))),
    item("authorization-date", "授权日", iprDateText(pick(data, "authorization_date"))),
    item("source-people", "案源人", pick(data, "case_origin_people_name", "case_source")),
    item("agent", "代理人", pick(data, "agent", "procurator_name")),
    item("writer", "撰稿人", pick(data, "writer", "copywriter_name")),
    item("first-annual-year", "首年年费年度", annualYearText(pick(data, "first_annual_year", "annual_fee_year"))),
    item("source-date", "案源日", iprDateText(pick(data, "case_origin_date", "source_date"))),
    item("ref-case-no", "关联案号", pick(data, "ref_case_no")),
    item("card-no", "证件号码", pick(data, "card_no")),
    item("relief-rate", "费用减缓比例", reliefRateText(pick(data, "cost_slow_rate", "relief_rate"))),
    item("applicant", "申请人", pick(data, "applicant_name", "applicant", "applicants")),
    item("inventor", "发明人", pick(data, "inventor", "case_inventor", "inventors")),
    item("customer", "客户", record.customer),
    item("manager", "案件管理人", pick(data, "case_manager", "case_officer_name")),
  ];
}

export function iprCaseFlags(record: IprCaseLike): IprCaseFlag[] {
  const data = record.data || {};
  if (isTrademarkCase(record)) {
    return [
      { key: "priority", label: "优先权", checked: iprFlagChecked(data.has_priority) },
      { key: "foreign", label: "涉外案件", checked: iprFlagChecked(data.has_foreign) },
      { key: "color", label: "颜色保护", checked: iprFlagChecked(data.has_trade_color_protected) },
      { key: "voice", label: "声音标志", checked: iprFlagChecked(data.has_trade_voice_protected) },
      { key: "three-d", label: "三维标志", checked: iprFlagChecked(data.has_trade3_d_protected) },
    ];
  }
  return [
    { key: "priority", label: "优先权", checked: iprFlagChecked(data.has_priority) },
    { key: "foreign", label: "涉外案件", checked: iprFlagChecked(data.has_foreign) },
    { key: "relief", label: "费用减缓", checked: iprFlagChecked(data.has_relief) },
    { key: "private-inventor", label: "不公发明人", checked: iprFlagChecked(data.has_private_inventor) },
    { key: "iu", label: "一发一实", checked: iprFlagChecked(data.has_iu) },
  ];
}

// “修改”时各格的输入方式和保存字段（后端 /ipr/cases/{id}/info）；案件编号、案件类型、客户不在这里改。
export type IprCaseEditField = { field: string; type: "applicant" | "application-type" | "text" | "textarea" | "date" | "phase" | "annual-year" | "relief-rate" | "trade-type"; sources: string[] };
export const IPR_CASE_EDIT_FIELDS: Record<string, IprCaseEditField> = {
  phase: { field: "case_phase", type: "phase", sources: ["case_phase"] },
  "register-date": { field: "case_register_date", type: "date", sources: ["case_register_date", "accepted_at"] },
  "request-no": { field: "case_request_no", type: "text", sources: ["case_request_no", "application_no"] },
  name: { field: "case_name", type: "text", sources: ["case_name", "patent_name", "invention_name"] },
  "request-date": { field: "case_request_date", type: "date", sources: ["case_request_date", "application_date"] },
  "authorization-date": { field: "authorization_date", type: "date", sources: ["authorization_date"] },
  "source-people": { field: "case_origin_people_name", type: "text", sources: ["case_origin_people_name", "case_source"] },
  agent: { field: "agent", type: "text", sources: ["agent", "procurator_name"] },
  writer: { field: "writer", type: "text", sources: ["writer", "copywriter_name"] },
  "first-annual-year": { field: "first_annual_year", type: "annual-year", sources: ["first_annual_year", "annual_fee_year"] },
  "source-date": { field: "case_origin_date", type: "date", sources: ["case_origin_date", "source_date"] },
  "ref-case-no": { field: "ref_case_no", type: "text", sources: ["ref_case_no"] },
  "card-no": { field: "card_no", type: "text", sources: ["card_no"] },
  "relief-rate": { field: "cost_slow_rate", type: "relief-rate", sources: ["cost_slow_rate", "relief_rate"] },
  type: { field: "application_type", type: "application-type", sources: ["application_type", "case_type_name", "case_type"] },
  applicant: { field: "applicant_name", type: "applicant", sources: ["applicant_name", "applicant", "applicants"] },
  inventor: { field: "inventor", type: "text", sources: ["inventor", "case_inventor", "inventors"] },
  manager: { field: "case_manager", type: "text", sources: ["case_manager", "case_officer_name"] },
  "first-instance-date": { field: "first_instance_date", type: "date", sources: ["first_instance_date"] },
  "trade-type": { field: "trade_type_name", type: "trade-type", sources: ["trade_type_name"] },
  "trademark-ids": { field: "trademark_ids", type: "text", sources: ["trademark_ids"] },
  "trade-product-service": { field: "trade_product_service", type: "textarea", sources: ["trade_product_service"] },
};
export const IPR_CASE_FLAG_FIELDS: Record<string, string> = {
  priority: "has_priority", foreign: "has_foreign", relief: "has_relief", "private-inventor": "has_private_inventor", iu: "has_iu",
  color: "has_trade_color_protected", voice: "has_trade_voice_protected", "three-d": "has_trade3_d_protected",
};

/** 进入修改时每格的初始值（日期取 YYYY-MM-DD，减缓比例统一成 1.00/0.85/0.70）。 */
export function iprCaseEditValues(record: IprCaseLike): Record<string, string> {
  const data = record.data || {};
  const values: Record<string, string> = {};
  for (const [key, config] of Object.entries(IPR_CASE_EDIT_FIELDS)) {
    const raw = text(pick(data, ...config.sources));
    values[key] = config.type === "trade-type" ? tradeTypeText(data)
      : config.type === "date" ? iprDateText(raw)
      : config.type === "relief-rate" && raw ? Number(raw).toFixed(2)
      : config.type === "annual-year" ? (/^\d+$/.test(raw) ? raw : "")
      : raw;
  }
  return values;
}
