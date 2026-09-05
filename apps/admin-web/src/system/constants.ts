import type { ParameterRow, ParameterRelationKind, ParameterRelationEditor } from "./types";

export const categoryByRoute: Record<string, string> = {
  "system-parameters-case-type": "case_type",
  "system-parameters-fee-type": "fee_type",
  "system-parameters-case-phase": "case_phase",
  "system-parameters-court": "court",
  "system-parameters-notary": "notary_office",
  "system-parameters-notary-office": "notary_office",
  "system-parameters-cause": "cause",
  "system-parameters-payment": "payment_type",
  "system-parameters-customer-type": "customer_type",
  "system-parameters-case-file-type": "case_file_type",
  "system-parameters-ipr-case-file-type": "ipr_case_file_type",
  "system-parameters-district": "district",
  "system-parameters-court-officer": "court_officer",
};

export const categoryTitle: Record<string, string> = {
  case_type: "案件类型",
  fee_type: "费用类型",
  case_phase: "案件阶段",
  court: "法院",
  notary_office: "公证处",
  cause: "案由",
  payment_type: "付款类型",
  customer_type: "客户类型",
  case_file_type: "案件文件类型",
  district: "地区",
  court_officer: "法院工作人员",
};
categoryTitle.ipr_case_file_type = "知识产权案件文件类型";

export const categoryPlaceholder: Record<string, string> = {
  case_type: "案件类型名称",
  fee_type: "费用类型名称",
  case_phase: "案件阶段名称",
  court: "法院名称",
  notary_office: "公证处名称",
  cause: "案由名称",
  payment_type: "付款单位名称",
  customer_type: "客户类型名称",
  case_file_type: "案件文件类型名称",
  district: "地区名称",
  court_officer: "工作人员姓名",
};
categoryPlaceholder.ipr_case_file_type = "知识产权案件文件类型名称";

export const extraFields: Record<string, { key: string; label: string }[]> = {
  case_type: [{ key: "letter_code", label: "类型字母名称" }],
  fee_type: [{ key: "parent_code", label: "上级费用类型" }],
  case_phase: [
    { key: "parent_code", label: "上级阶段Id" },
    { key: "case_type", label: "案件类型" },
  ],
  notary_office: [{ key: "number_template", label: "公证号模板" }],
  cause: [{ key: "parent_code", label: "上级案由Id" }],
  payment_type: [
    { key: "nature", label: "付款性质" },
    { key: "payee", label: "收款单位" },
    { key: "account_bank", label: "开户行" },
    { key: "account", label: "账号信息" },
  ],
  case_file_type: [{ key: "parent_code", label: "上级文件类型代码" }],
  district: [{ key: "parent_code", label: "上级地区代码" }],
  court_officer: [
    { key: "court_code", label: "法院代码" },
    { key: "role", label: "职务" },
    { key: "phone", label: "联系电话" },
  ],
};

export const formatTime = (value: string) =>
  value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "—";

export function sanitizeShareDaysInput(value: unknown): string {
  return String(value ?? "").replace(/\D/g, "");
}

export function cleanShareDaysInputEvent(event: {
  currentTarget: { value: string };
}): string {
  const sanitized = sanitizeShareDaysInput(event.currentTarget.value);
  event.currentTarget.value = sanitized;
  return sanitized;
}

export function isShareDaysValueValid(value: unknown): boolean {
  const normalized = sanitizeShareDaysInput(value);
  if (!normalized || normalized !== String(value ?? "")) return false;
  const days = Number(normalized);
  return Number.isInteger(days) && days >= 1 && days <= 3650;
}

export function sanitizeCompanyDigitsInput(value: unknown): string {
  return String(value ?? "").replace(/\D/g, "");
}

export function cleanCompanyDigitsInputEvent(event: {
  currentTarget: { value: string };
}): string {
  const sanitized = sanitizeCompanyDigitsInput(event.currentTarget.value);
  event.currentTarget.value = sanitized;
  return sanitized;
}

export function caseFileTypeParentOptions(
  rows: ParameterRow[],
  editingParameterId?: number,
): { value: string; label: string }[] {
  return rows
    .filter(
      (row) =>
        row.category === "case_file_type" &&
        row.is_active &&
        row.id !== editingParameterId,
    )
    .sort(
      (left, right) =>
        left.sort_order - right.sort_order || left.code.localeCompare(right.code),
    )
    .map((row) => ({ value: row.code, label: `${row.name}（${row.code}）` }));
}

export function isCaseFileTypeParentValid(
  parentCode: unknown,
  rows: ParameterRow[],
  editingParameterId?: number,
): boolean {
  const normalized = String(parentCode || "").trim();
  return (
    !normalized ||
    caseFileTypeParentOptions(rows, editingParameterId).some(
      (option) => option.value === normalized,
    )
  );
}

export function feeTypeParentOptions(
  rows: ParameterRow[],
  editingParameterId?: number,
): { value: string; label: string }[] {
  const editing = rows.find((row) => row.id === editingParameterId);
  const childCodes = new Map<string, string[]>();
  rows.forEach((row) => {
    const parentCode = String(row.extra.parent_code || "").trim();
    if (parentCode) childCodes.set(parentCode, [...(childCodes.get(parentCode) || []), row.code]);
  });
  const excluded = new Set<string>(editing ? [editing.code] : []);
  const visit = (code: string) => {
    for (const childCode of childCodes.get(code) || []) {
      if (excluded.has(childCode)) continue;
      excluded.add(childCode);
      visit(childCode);
    }
  };
  if (editing) visit(editing.code);
  return rows
    .filter((row) => row.category === "fee_type" && row.is_active && !excluded.has(row.code))
    .sort((left, right) => left.sort_order - right.sort_order || left.code.localeCompare(right.code))
    .map((row) => ({ value: row.code, label: `${row.name}（${row.code}）` }));
}

export function feeTypeTreeRows(rows: ParameterRow[]): ParameterRow[] {
  const nodes = new Map(rows.map((row) => [row.code, { ...row, children: [] as ParameterRow[] }]));
  const roots: ParameterRow[] = [];
  const sorted = [...nodes.values()].sort(
    (left, right) => left.sort_order - right.sort_order || left.code.localeCompare(right.code),
  );
  sorted.forEach((node) => {
    const parentCode = String(node.extra.parent_code || "").trim();
    const parent = parentCode ? nodes.get(parentCode) : undefined;
    if (parent && parent.id !== node.id) parent.children!.push(node);
    else roots.push(node);
  });
  const clearEmpty = (row: ParameterRow): ParameterRow => ({
    ...row,
    children: row.children?.length ? row.children.map(clearEmpty) : undefined,
  });
  return roots.map(clearEmpty);
}

export function feeTypeRootName(row: ParameterRow, rows: ParameterRow[]): string {
  const byCode = new Map(rows.map((item) => [item.code, item]));
  const seen = new Set<string>();
  let cursor = row;
  while (cursor && !seen.has(cursor.code)) {
    seen.add(cursor.code);
    const parentCode = String(cursor.extra.parent_code || "").trim();
    const parent = parentCode ? byCode.get(parentCode) : undefined;
    if (!parent) return cursor.name;
    cursor = parent;
  }
  return row.name;
}

export const parameterRelationConfigs: Record<
  ParameterRelationKind,
  Omit<ParameterRelationEditor, "source">
> = {
  "case-type-file-types": {
    kind: "case-type-file-types",
    title: "关联文件类型",
    targetCategory: "case_file_type",
    targetLabel: "案件文件类型",
  },
  "file-type-fee-types": {
    kind: "file-type-fee-types",
    title: "关联费用类型",
    targetCategory: "fee_type",
    targetLabel: "费用类型",
  },
  "case-type-case-phases": {
    kind: "case-type-case-phases",
    title: "关联案件阶段",
    targetCategory: "case_phase",
    targetLabel: "案件阶段",
  },
};

export function relationTargetIds(payload: unknown, sourceId?: number): number[] {
  const response = payload as {
    target_ids?: unknown;
    relations?: Record<string, unknown>;
  };
  const value =
    response?.target_ids ??
    (sourceId ? response?.relations?.[String(sourceId)] : undefined);
  if (!Array.isArray(value)) return [];
  return Array.from(
    new Set(
      value
        .map((item) => Number(item))
        .filter((item) => Number.isInteger(item) && item > 0),
    ),
  );
}

export const PERSON_NAME_PLACEHOLDER = "姓名待维护";

export function personDisplayName(row?: { display_name?: string }): string {
  return String(row?.display_name || "").trim() || PERSON_NAME_PLACEHOLDER;
}
