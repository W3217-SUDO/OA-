import type { IprFinanceFeeType,IprLawsuitFee,IprRecord } from "./types";

export const IPR_DETAIL_DEFAULT_PAGE = 1;
export const IPR_DETAIL_DEFAULT_PAGE_SIZE = 15;

export const isLegacyIprRecord = (record: IprRecord) =>
  Number(record.data?.legacy_ipr_case_id || record.data?.legacy_case_id || 0) > 0;

export const isIprLawsuit = (record: IprRecord | null) =>
  record?.data?.case_category === "litigation";

export const IPR_LAWSUIT_FIELDS = ["court_case_no", "court_name", "judge", "clerk", "plaintiff", "defendant", "third_parties"] as const;

export const IPR_LAWSUIT_FEE_OPTIONS = [
  { value: "诉讼费", label: "诉讼费", feeType: "官方费用" },
  { value: "保全费", label: "保全费", feeType: "官方费用" },
  { value: "公告费", label: "公告费", feeType: "官方费用" },
  { value: "鉴定费", label: "鉴定费", feeType: "官方费用" },
  { value: "执行费", label: "执行费", feeType: "官方费用" },
  { value: "其他", label: "其他", feeType: "其他费用" },
] as const satisfies ReadonlyArray<{ value: string; label: string; feeType: IprFinanceFeeType }>;

export const lawsuitFeeFromRecord = (record: IprRecord): IprLawsuitFee => ({
  id: record.id,
  title: record.title,
  fee_type: record.data?.fee_type,
  amount: record.data?.amount,
  fee_date: record.data?.fee_date,
  status: record.status,
  remark: record.description,
});

export const personDisplayName = (value?: unknown) =>
  String(value || "").trim() || "姓名待维护";

export const statusColor: Record<string, string> = {
  草稿: "default",
  待立案审核: "gold",
  在办: "blue",
  已驳回: "red",
  已结案: "green",
};

export const CUSTOMER_IPR_RELATION_STORAGE_KEY =
  "sunhold:customer-ipr-relation";
export const IPR_WARNING_TARGET_STORAGE_KEY = "sunhold:ipr-warning-target";

export const IPR_ROLE_VIEW_BY_ROUTE: Record<string, { roleView: string; label: string }> = {
  "ipr-source-person": { roleView: "source_person", label: "我是案源人" },
  "ipr-procurator": { roleView: "procurator", label: "我是代理人" },
  "ipr-copywriter": { roleView: "copywriter", label: "我是撰稿人" },
  "ipr-officer": { roleView: "officer", label: "我是处理人" },
  "ipr-business-owner": { roleView: "business_owner", label: "我是案件管理人" },
};

export const consumeCustomerIprRelationKeyword = () => {
  try {
    const raw = window.sessionStorage.getItem(CUSTOMER_IPR_RELATION_STORAGE_KEY);
    window.sessionStorage.removeItem(CUSTOMER_IPR_RELATION_STORAGE_KEY);
    if (!raw) return "";
    const parsed = JSON.parse(raw) as { serial_no?: string; title?: string; at?: number };
    if (!parsed || (parsed.at && Date.now() - Number(parsed.at) > 60 * 60 * 1000)) return "";
    return String(parsed.title || parsed.serial_no || "").trim();
  } catch {
    return "";
  }
};
