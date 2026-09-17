const text = (value) => String(value ?? "").trim();

export const feeTypeSelection = (catalog, feeTypeId) =>
  (Array.isArray(catalog) ? catalog : []).find((item) => Number(item.id) === Number(feeTypeId) || item.alias_ids?.includes(Number(feeTypeId)));

const presetMatches = (item, preset, scope) => {
  if (!preset) return true;
  if (preset === "agency") {
    if (text(scope) === "平台") return item.fee_group === preset && item.platform_agency;
    return item.fee_group === preset && !item.platform_agency;
  }
  return item.fee_group === preset;
};

export const selectableFeeTypes = (catalog, scope, preset = "") => {
  const matching = (Array.isArray(catalog) ? catalog : []).filter((item) =>
    item?.is_active !== false && item?.selectable === true &&
    (!text(scope) || (item.expense_scopes || []).includes(text(scope))) &&
    presetMatches(item, preset, scope),
  );
  return matching;
};

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
