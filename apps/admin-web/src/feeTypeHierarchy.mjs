const text = (value) => String(value ?? "").trim();

const PRESET_NAMES = {
  official: new Set(["一审诉讼费", "二审诉讼费", "再审诉讼费", "公证费", "调解金额", "判决金额", "保全费", "执行费"]),
  "third-party": new Set(["检索费", "公告费", "担保费", "鉴定费", "公证服务费"]),
  agency: new Set(["律师代理费", "律师咨询费", "律师培训费", "律师见证费", "平台代理费"]),
};

export const feeTypeSelection = (catalog, feeTypeId) =>
  (Array.isArray(catalog) ? catalog : []).find((item) => Number(item.id) === Number(feeTypeId));

const presetMatches = (item, preset) => {
  if (!preset) return true;
  if (preset === "other") return item.base_fee_type === "其他费用" && !PRESET_NAMES["third-party"].has(item.name);
  if (preset === "official") return item.base_fee_type === "官方费用";
  if (preset === "agency") return item.base_fee_type === "代理费";
  return PRESET_NAMES[preset]?.has(item.name) ?? true;
};

export const selectableFeeTypes = (catalog, scope, preset = "") =>
  (Array.isArray(catalog) ? catalog : []).filter((item) =>
    item?.is_active !== false && item?.selectable === true &&
    (!text(scope) || (item.expense_scopes || []).includes(text(scope))) &&
    presetMatches(item, preset),
  );

export const feeTypeTreeData = (catalog, scope, preset = "") => {
  const rows = Array.isArray(catalog) ? catalog : [];
  const byCode = new Map(rows.map((item) => [text(item.code), item]));
  const allowed = selectableFeeTypes(rows, scope, preset);
  const included = new Set();
  allowed.forEach((item) => {
    let cursor = item;
    const seen = new Set();
    while (cursor && !seen.has(text(cursor.code))) {
      included.add(text(cursor.code));
      seen.add(text(cursor.code));
      cursor = byCode.get(text(cursor.parent_code || cursor.extra?.parent_code));
    }
  });
  const nodes = new Map(
    rows.filter((item) => included.has(text(item.code))).map((item) => [text(item.code), {
      value: Number(item.id),
      title: item.name,
      selectable: allowed.some((candidate) => Number(candidate.id) === Number(item.id)),
      children: [],
    }]),
  );
  const roots = [];
  rows.filter((item) => included.has(text(item.code))).forEach((item) => {
    const node = nodes.get(text(item.code));
    const parent = nodes.get(text(item.parent_code || item.extra?.parent_code));
    if (parent) parent.children.push(node);
    else roots.push(node);
  });
  const clearEmpty = (node) => ({
    ...node,
    children: node.children.length ? node.children.map(clearEmpty) : undefined,
  });
  return roots.map(clearEmpty);
};

export const initialFeeTypeId = (catalog, scope, preset = "", preferredName = "") => {
  const options = selectableFeeTypes(catalog, scope, preset);
  return Number(options.find((item) => item.name === preferredName)?.id || options[0]?.id || 0) || undefined;
};
