const text = (value) => String(value ?? "").trim();

const CASE_TYPE_CANONICAL_NAMES = new Map([
  ["民事案件", "民事争议"],
  ["民事争议", "民事争议"],
]);

const comparableText = (value) => {
  const normalized = text(value);
  return CASE_TYPE_CANONICAL_NAMES.get(normalized) || normalized;
};

const keysFor = (item) => new Set([
  comparableText(item?.id),
  comparableText(item?.code),
  comparableText(item?.name),
  comparableText(item?.value),
  comparableText(item?.label),
].filter(Boolean));

const sharesKey = (left, right) => [...keysFor(left)].some((key) => keysFor(right).has(key));

const relatedTargets = (sourceValue, relation) => {
  if (!relation) return null;
  const configuredRelations = relation.relations || {};
  const hasConfiguredRelation = Object.values(configuredRelations).some((targetIds) =>
    Array.isArray(targetIds) && targetIds.length > 0,
  );
  if (!hasConfiguredRelation) return null;
  const source = (relation.sources || []).find((item) => sharesKey(item, { value: sourceValue }));
  if (!source) return [];
  const targetIds = new Set(configuredRelations[String(source.id)] || []);
  return (relation.targets || []).filter((item) => targetIds.has(Number(item.id)));
};

export const filterCaseFileTypesForCaseType = (caseType, fileTypes, relation) => {
  const targets = relatedTargets(caseType, relation);
  if (targets === null) return Array.isArray(fileTypes) ? fileTypes : [];
  return (Array.isArray(fileTypes) ? fileTypes : []).filter((item) =>
    targets.some((target) => sharesKey(item, target)),
  );
};

export const filterCasePhasesForCaseType = (caseType, phases, relation) => {
  const targets = relatedTargets(caseType, relation);
  if (targets === null) return Array.isArray(phases) ? phases : [];
  return (Array.isArray(phases) ? phases : []).filter((item) =>
    targets.some((target) => sharesKey(item, target)),
  );
};

export const FEE_SUBTYPE_TO_TYPE = {
  "\u5b98\u8d39": "\u5b98\u65b9\u8d39\u7528",
  "\u4e00\u5ba1\u8bc9\u8bbc\u8d39": "\u5b98\u65b9\u8d39\u7528",
  "\u4e8c\u5ba1\u8bc9\u8bbc\u8d39": "\u5b98\u65b9\u8d39\u7528",
  "\u518d\u5ba1\u8bc9\u8bbc\u8d39": "\u5b98\u65b9\u8d39\u7528",
  "\u8bc9\u8bbc\u8d39": "\u5b98\u65b9\u8d39\u7528",
  "\u4fdd\u5168\u8d39": "\u5b98\u65b9\u8d39\u7528",
  "\u9274\u5b9a\u8d39": "\u5b98\u65b9\u8d39\u7528",
  "\u516c\u8bc1\u8d39": "\u5b98\u65b9\u8d39\u7528",
  "\u516c\u544a\u8d39": "\u5b98\u65b9\u8d39\u7528",
  "\u8c03\u89e3\u91d1\u989d": "\u5b98\u65b9\u8d39\u7528",
  "\u5224\u51b3\u91d1\u989d": "\u5b98\u65b9\u8d39\u7528",
  "\u6267\u884c\u8d39": "\u5b98\u65b9\u8d39\u7528",
  "\u6838\u5b9a\u6210\u672c": "\u5b98\u65b9\u8d39\u7528",
  "\u7b2c\u4e09\u65b9\u8d39\u7528": "\u5176\u4ed6\u8d39\u7528",
  "\u4ee3\u7406\u8d39": "\u4ee3\u7406\u8d39",
  "\u5176\u4ed6\u8d39\u7528": "\u5176\u4ed6\u8d39\u7528",
  "\u5185\u90e8\u8d39\u7528": "\u5185\u90e8\u8d39\u7528",
};

export const LEGACY_OFFICIAL_FEE_SUBTYPES = [
  "\u4e00\u5ba1\u8bc9\u8bbc\u8d39",
  "\u4e8c\u5ba1\u8bc9\u8bbc\u8d39",
  "\u518d\u5ba1\u8bc9\u8bbc\u8d39",
  "\u516c\u8bc1\u8d39",
  "\u8c03\u89e3\u91d1\u989d",
  "\u5224\u51b3\u91d1\u989d",
  "\u4fdd\u5168\u8d39",
  "\u6267\u884c\u8d39",
  "\u6838\u5b9a\u6210\u672c",
];

export const filterFeeSubtypesForFileType = (fileType, subtypes, relation) => {
  const targets = relatedTargets(fileType, relation);
  const all = Array.isArray(subtypes) ? subtypes : [];
  if (targets === null) return all;
  return all.filter((subtype) => targets.some((target) =>
    sharesKey({ value: FEE_SUBTYPE_TO_TYPE[subtype] || subtype }, target) ||
    sharesKey({ value: subtype }, target),
  ));
};

export const getRelatedTargetIds = (sourceValue, relation) =>
  relatedTargets(sourceValue, relation)?.map((item) => Number(item.id)) || [];
