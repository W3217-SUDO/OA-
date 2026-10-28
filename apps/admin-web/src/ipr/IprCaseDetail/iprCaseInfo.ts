// 知识产权案件详情页的“案件信息”区，字段和顺序按原沪知系统案件页（BUG20261028001）。
// 迁移数据字段名沿用旧库（case_name、case_request_no……），新建案件用新字段名，按顺序取第一个有值的。

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

const percentText = (value: unknown) => {
  const raw = text(value);
  if (!raw) return "";
  const number = Number(raw);
  if (!Number.isFinite(number) || number <= 0) return raw;
  return number <= 1 ? `${Math.round(number * 100)}%减缓` : `${number}%减缓`;
};

/** 旧库是 T/F，新建案件是布尔值。 */
export const iprFlagChecked = (value: unknown) => value === true || ["T", "t", "true", "1", "是"].includes(String(value ?? ""));

export function iprCaseInfoItems(record: IprCaseLike): IprCaseInfoItem[] {
  const data = record.data || {};
  const item = (key: string, label: string, value: unknown): IprCaseInfoItem => ({ key, label, value: text(value) || "—" });
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
    item("first-annual-year", "首年年费年度", pick(data, "first_annual_year", "annual_fee_year")),
    item("source-date", "案源日", iprDateText(pick(data, "case_origin_date", "source_date"))),
    item("ref-case-no", "关联案号", pick(data, "ref_case_no")),
    item("card-no", "证件号码", pick(data, "card_no")),
    item("relief-rate", "费用减缓比例", percentText(pick(data, "cost_slow_rate", "relief_rate"))),
    item("applicant", "申请人", pick(data, "applicant_name", "applicant", "applicants")),
    item("inventor", "发明人", pick(data, "inventor", "case_inventor", "inventors")),
    item("customer", "客户", record.customer),
    item("manager", "案件管理人", pick(data, "case_manager", "case_officer_name")),
  ];
}

export function iprCaseFlags(record: IprCaseLike): IprCaseFlag[] {
  const data = record.data || {};
  return [
    { key: "priority", label: "优先权", checked: iprFlagChecked(data.has_priority) },
    { key: "foreign", label: "涉外案件", checked: iprFlagChecked(data.has_foreign) },
    { key: "relief", label: "费用减缓", checked: iprFlagChecked(data.has_relief) },
    { key: "private-inventor", label: "不公发明人", checked: iprFlagChecked(data.has_private_inventor) },
    { key: "iu", label: "一发一实", checked: iprFlagChecked(data.has_iu) },
  ];
}
