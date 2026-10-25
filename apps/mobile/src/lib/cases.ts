// 字段取值顺序与网页端保持一致：
// legal/constants.tsx caseDetailNames、legal/CaseDetail/CaseDetailHeader.tsx、legal/courtDisplay.ts、
// legal/CaseCenterPage.tsx casePersonDisplayName。

export type PersonOption = { value: string; label: string };

const joinNames = (value: unknown): string => {
  if (Array.isArray(value)) return value.map((item) => String(item || "").trim()).filter(Boolean).join("、");
  return String(value || "").trim();
};

export function caseParties(data: Record<string, any>) {
  return {
    plaintiff: joinNames(Array.isArray(data.plaintiffs) && data.plaintiffs.length ? data.plaintiffs : data.plaintiff),
    defendant: joinNames(Array.isArray(data.defendants) && data.defendants.length ? data.defendants : data.opponent || data.defendant),
  };
}

export function caseHeaderHearingLawyers(data: Record<string, unknown>): string[] {
  const firstPopulated = (fields: string[]): string[] => {
    for (const field of fields) {
      const raw = data[field];
      const values = Array.isArray(raw) ? raw : [raw];
      const tokens = values
        .flatMap((value) => String(value || "").split(/[,，、;/；\n]+/))
        .map((value) => value.trim())
        .filter((value) => value && !["—", "-", "无", "未分配", "【待补充中文姓名】"].includes(value));
      if (tokens.length) return [...new Set(tokens)];
    }
    return [];
  };
  const explicit = firstPopulated(["hearing_lawyer_usernames", "hearing_lawyer_username", "court_lawyer_username", "hearing_lawyers", "hearing_lawyer", "court_lawyer"]);
  return explicit.length ? explicit : firstPopulated(["handling_lawyer_usernames", "handling_lawyer_username", "handling_lawyers"]).slice(0, 1);
}

/** 账号换成姓名；历史数据里保留的中文姓名原样显示。 */
export function casePersonName(source: unknown, options: PersonOption[], displayName?: unknown): string {
  const explicit = String(displayName || "").trim();
  if (explicit && !["姓名待维护", "【待补充中文姓名】"].includes(explicit)) return explicit;
  const normalized = String(source || "").trim();
  if (!normalized) return "—";
  const option = options.find((item) => {
    const name = item.label.replace(/（[^（）]*）$/, "").trim();
    return item.value === normalized || item.label === normalized || name === normalized;
  });
  const matched = option?.label.replace(/（[^（）]*）$/, "").trim();
  if (matched) return matched;
  return /[㐀-鿿]/.test(normalized) ? normalized : "姓名待维护";
}

export function courtDisplay(data: Record<string, any>, level: string): string {
  const display = data.court_displays?.[level];
  if (!display) return "法院名称未加载";
  if (display.status === "empty") return "—";
  if (display.status === "unresolved") return `法院无法解析（${display.raw}），请完善法院参数`;
  return display.name;
}

export type CourtLevel = { label: string; court: string; caseNo: string; hearingDate: string; courtroom: string };

export function courtLevels(data: Record<string, any>): CourtLevel[] {
  const first: CourtLevel = {
    label: "一审",
    court: courtDisplay(data, "first"),
    caseNo: data.first_court_case_no || data.first_instance_case_no || data.court_case_no || "",
    hearingDate: data.first_court_hearing_date || data.hearing_date || "",
    courtroom: data.first_court_courtroom || data.courtroom || "",
  };
  const others: CourtLevel[] = [
    { label: "二审", court: courtDisplay(data, "second"), caseNo: data.second_court_case_no || data.second_instance_case_no || "", hearingDate: data.second_court_hearing_date || "", courtroom: data.second_court_courtroom || "" },
    { label: "执行", court: courtDisplay(data, "execution"), caseNo: data.execution_court_case_no || "", hearingDate: data.execution_court_hearing_date || "", courtroom: data.execution_court_courtroom || "" },
    { label: "再审", court: courtDisplay(data, "retrial"), caseNo: data.retrial_court_case_no || "", hearingDate: data.retrial_court_hearing_date || "", courtroom: data.retrial_court_courtroom || "" },
  ];
  // 一审始终显示；其他审级只在有数据时显示。
  const filled = (value: string) => !!value && value !== "—" && value !== "法院名称未加载";
  return [first, ...others.filter((item) => filled(item.court) || item.caseNo || item.hearingDate)];
}
