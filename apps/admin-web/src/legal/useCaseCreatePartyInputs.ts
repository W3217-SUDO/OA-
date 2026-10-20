import { useEffect, useRef, useState } from "react";
import type { FormInstance } from "antd";

const partyFields = ["plaintiffs", "plaintiff_agents", "defendants", "defendant_agents", "third_parties", "third_party_agents"] as const;
type PartyField = typeof partyFields[number];
const identityFields: Partial<Record<PartyField, string>> = {
  plaintiffs: "plaintiff_identities",
  defendants: "defendant_identities",
  third_parties: "third_party_identities",
};

export function useCaseCreatePartyInputs(form: FormInstance, flowToken: string) {
  const pending = useRef<Partial<Record<PartyField, string>>>({});
  const [searches, setSearches] = useState<Partial<Record<PartyField, string>>>({});
  const [openField, setOpenField] = useState<PartyField | null>(null);
  useEffect(() => {
    pending.current = {};
    setSearches({});
    setOpenField(null);
  }, [flowToken]);

  const setSearch = (field: PartyField, text: string) => {
    pending.current[field] = text;
    setSearches((current) => ({ ...current, [field]: text }));
  };
  const writeNames = (field: PartyField, values: string[]) => {
    const names = [...new Set(values.map((value) => value.trim()).filter(Boolean))];
    const identityField = identityFields[field];
    const identities = identityField && form.getFieldValue(identityField);
    form.setFieldsValue({
      [field]: names,
      ...(identityField && Array.isArray(identities)
        ? { [identityField]: identities.filter((item: { name: string }) => names.includes(item.name)) }
        : {}),
    });
    setSearch(field, "");
  };
  const commitField = (field: PartyField) => {
    const text = pending.current[field]?.trim();
    if (text) writeNames(field, [...(form.getFieldValue(field) || []), ...text.split(/[,，]/)]);
  };

  // 证件弹窗及步骤按钮必须同步收录尚未回车的名称，不能依赖点击前一定触发失焦。
  const commitInputs = () => {
    partyFields.forEach(commitField);
    setOpenField(null);
  };
  const selectProps = (field: PartyField) => ({
    open: openField === field,
    onOpenChange: (open: boolean) => setOpenField((current) => open ? field : current === field ? null : current),
    searchValue: searches[field] || "",
    onSearch: (text: string) => setSearch(field, text),
    onChange: (values: string[]) => writeNames(field, values),
    onBlur: () => commitField(field),
  });
  return { selectProps, commitInputs };
}
