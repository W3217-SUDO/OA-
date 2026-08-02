export type LegacyCaseListMode = "list" | "schedule" | "phase" | "execution";

export type LegacyCaseListDefaults = {
  pageSize: number;
  sortField: string;
  sortDirection: "asc" | "desc";
  includeTodayHearing: boolean;
};

const LEGACY_CASE_LIST_DEFAULTS: Record<LegacyCaseListMode, LegacyCaseListDefaults> = {
  list: { pageSize: 10, sortField: "T.LawfulDay", sortDirection: "desc", includeTodayHearing: false },
  schedule: { pageSize: 15, sortField: "T.LawfulDay", sortDirection: "asc", includeTodayHearing: true },
  phase: { pageSize: 15, sortField: "T.LawfulDay", sortDirection: "asc", includeTodayHearing: true },
  execution: { pageSize: 10, sortField: "T.LawfulDay", sortDirection: "asc", includeTodayHearing: false },
};

export const LEGACY_COMPANY_CASE_ROUTES = [
  "case-company-civil",
  "case-company-criminal",
  "case-company-arbitration",
  "case-company-schedule",
  "case-company-execution",
] as const;

export const getLegacyCaseListMode = (initialView: string): LegacyCaseListMode => {
  if (initialView === "case-company-schedule") return "schedule";
  if (initialView === "case-company-execution") return "execution";
  if (initialView.includes("phase")) return "phase";
  return "list";
};

export const getLegacyCaseListDefaults = (initialView: string): LegacyCaseListDefaults => ({
  ...LEGACY_CASE_LIST_DEFAULTS[getLegacyCaseListMode(initialView)],
});

export const getLegacyCaseListPageSizeOptions = () => [10, 15, 20, 50, 100, 200];

export const getLegacyCaseListOperationLabels = () => ({
  query: "查询",
  reset: "重置",
  exportSelected: "导出选中",
  exportAll: "导出全部",
  exportManifest: "导出归档清单",
  participant: "修改当事人",
  phase: "修改案件阶段",
  court: "修改法院信息",
  delete: "删除案件",
});

export type LegacyCaseListOperationState = {
  canView: boolean;
  canDelete: boolean;
  canParticipant: boolean;
  canPhase: boolean;
  canCourt: boolean;
  readOnly: boolean;
};

export const getLegacyCaseListOperationState = ({
  role,
  status,
  selectedCount,
  isCompanySchedule,
}: {
  role: string;
  status: string;
  selectedCount: number;
  isCompanySchedule?: boolean;
}): LegacyCaseListOperationState => {
  const readOnly = status === "待归档审核" || status === "已归档" || status === "已合并";
  const hasSingleSelection = selectedCount === 1;
  const hasSelection = selectedCount === 0 ? false : selectedCount > 0;
  const canWrite = !readOnly && role !== "";
  return {
    canView: hasSingleSelection,
    canDelete: false,
    canParticipant: hasSingleSelection && canWrite,
    canPhase: hasSingleSelection && canWrite,
    canCourt: hasSingleSelection && canWrite && Boolean(isCompanySchedule),
    readOnly,
  };
};
