import dayjs, { type Dayjs } from "dayjs";

// 501613：知识产权中心“我的案件”的分组、筛选参数和剩余天数（页面和单元测试共用）。

/** 501616：“我的案件”页上方“新建案件”：跳到专利案件页并直接打开新建弹窗。 */
export const IPR_CREATE_FROM_MY_CASES_KEY = "sunhold:ipr-create-from-my-cases";
export type GroupKey = "business_owner" | "source_person" | "procurator" | "copywriter" | "mine" | "invalid";
export type FilterValues = {
  applicant?: string; case_phase?: string; case_type?: string; source_person?: string; copywriter?: string;
  procurator?: string; customer?: string; case_no?: string; trademark_class?: string; title?: string; keyword?: string;
  application_dates?: [Dayjs | null, Dayjs | null] | null;
};

export const IPR_MY_CASE_GROUPS: { key: GroupKey; label: string; roleView: string }[] = [
  { key: "source_person", label: "我是案源人", roleView: "my:source_person" },
  { key: "business_owner", label: "我是管理人", roleView: "my:business_owner" },
  { key: "procurator", label: "我是代理人", roleView: "my:procurator" },
  { key: "copywriter", label: "我是撰稿人", roleView: "my:copywriter" },
  { key: "mine", label: "我的案件", roleView: "my:mine" },
  { key: "invalid", label: "失效案件", roleView: "invalid" },
];

/** 501690：“我的案件”下 6 个菜单各对应一个分组；ipr-my-cases 是分组本身，旧链接按“我的案件”打开。 */
export const IPR_MY_CASE_ROUTES: Record<string, GroupKey> = {
  "ipr-my-cases": "mine", "ipr-my-mine": "mine", "ipr-my-invalid": "invalid",
  "ipr-source-person": "source_person", "ipr-business-owner": "business_owner",
  "ipr-procurator": "procurator", "ipr-copywriter": "copywriter",
};

export const IPR_MY_CASE_MENU = [
  { key: "ipr-source-person", label: "我是案源人" }, { key: "ipr-business-owner", label: "我是管理人" },
  { key: "ipr-procurator", label: "我是代理人" }, { key: "ipr-copywriter", label: "我是撰稿人" },
  { key: "ipr-my-mine", label: "我的案件" }, { key: "ipr-my-invalid", label: "失效案件" },
];

export const FILTERS: { name: Exclude<keyof FilterValues, "application_dates">; label: string; placeholder?: string }[] = [
  { name: "applicant", label: "申请人" }, { name: "case_phase", label: "案件阶段" }, { name: "case_type", label: "案件类型" },
  { name: "source_person", label: "案源人" }, { name: "copywriter", label: "撰稿人" }, { name: "procurator", label: "代理人" },
  { name: "customer", label: "客户名称" }, { name: "case_no", label: "案号/申请号" }, { name: "trademark_class", label: "商标类别" },
  { name: "title", label: "案件名称" }, { name: "keyword", label: "关键字", placeholder: "案号、申请号、案件名称、客户名称" },
];

export const text = (value: unknown) => String(value ?? "").trim();
export const dateText = (value: unknown) => text(value).slice(0, 10);

/** 剩余天数：截止日减今天；过期显示“已过期”，没有截止日留空。 */
export function remainingDays(deadline: unknown, today = dayjs()): string {
  const value = dateText(deadline);
  if (!value) return "";
  const days = dayjs(value).startOf("day").diff(today.startOf("day"), "day");
  if (Number.isNaN(days)) return "";
  return days < 0 ? "已过期" : String(days);
}

export function myCaseQueryParams(roleView: string, values: FilterValues) {
  const params: Record<string, string> = { role_view: roleView, case_category: "non_litigation" };
  for (const { name } of FILTERS) {
    const value = text(values[name]);
    if (value) params[name] = value;
  }
  const [from, to] = values.application_dates || [];
  if (from) params.date_from = from.format("YYYY-MM-DD");
  if (to) params.date_to = to.format("YYYY-MM-DD");
  return params;
}

