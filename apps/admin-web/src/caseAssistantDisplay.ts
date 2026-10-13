type CaseAssistantData = Record<string, unknown>;

const populatedValues = (value: unknown): unknown[] => {
  const values = Array.isArray(value) ? value : [value];
  // The API uses an em dash for an unassigned assistant. It is an empty
  // display state, not a person reference that should be resolved again.
  return values.filter((item) => {
    const text = String(item ?? "").trim();
    return text && text !== "—";
  });
};

export const caseAssistantDisplayValues = (data: CaseAssistantData | null | undefined): unknown[] => {
  if (!data) return [];
  const legacy = typeof data.legacy_record === "object" && data.legacy_record
    ? data.legacy_record as CaseAssistantData
    : {};
  const candidates = [
    data.assistant_usernames_display_names,
    data.assistants,
    data.assistant_display_names,
    data.assistants_display_names,
    data.assistant_usernames,
    data.assistant_display_name,
    data.assistant,
    data.assistant_username,
    legacy.CaseAssistantName,
    legacy.CaseAssistant,
  ];
  // Migrated rows can contain a legacy scalar display value alongside a newer
  // username array. Prefer the most complete projection so a populated scalar
  // never hides additional assistants stored in another compatible field.
  return candidates.reduce<unknown[]>((best, candidate) => {
    const values = populatedValues(candidate);
    return values.length > best.length ? values : best;
  }, []);
};
