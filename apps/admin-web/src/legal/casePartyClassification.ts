export interface ClassifiedCaseParty {
  id?: string;
  name: string;
  party_standpoint?: "我方" | "对方";
  party_type?: "当事人" | "关联方" | "第三人";
  is_client_principal: boolean;
  related_client_id?: number | null;
  related_client_name?: string;
  subject_kind?: "自然人" | "法人" | "其他组织";
  credit_code: string;
  litigation_status: string;
  litigation_status_overridden: boolean;
  remark: string;
}

export const partyCategories = [
  { value: "W_CLIENT", label: "我方客户（委托人）", standpoint: "我方", type: "当事人", principal: true },
  { value: "W_LITIGANT", label: "我方当事人（非委托人）", standpoint: "我方", type: "当事人", principal: false },
  { value: "W_AFFILIATE", label: "我方关联方", standpoint: "我方", type: "关联方", principal: false },
  { value: "W_THIRD", label: "我方第三人", standpoint: "我方", type: "第三人", principal: false },
  { value: "O_PARTY", label: "对方当事人", standpoint: "对方", type: "当事人", principal: false },
  { value: "O_THIRD", label: "对方第三人", standpoint: "对方", type: "第三人", principal: false },
] as const;
export const litigationPositions = ["原告", "被告", "申请人", "被申请人", "第三人", "其他"];
export const mirroredPosition: Record<string, string> = { 原告: "被告", 被告: "原告", 申请人: "被申请人", 被申请人: "申请人", 第三人: "第三人", 其他: "其他" };
export const partyCategory = (party: ClassifiedCaseParty) => partyCategories.find(item => item.standpoint === party.party_standpoint && item.type === party.party_type && item.principal === party.is_client_principal);

/** 历史资料只保留原名称与诉讼地位，不凭客户名称推断立场或委托关系。 */
export function casePartiesForEditor(data: Record<string, any>): ClassifiedCaseParty[] {
  if (data.case_party_schema_version === 1) return (data.case_parties || []).map((item: ClassifiedCaseParty) => ({ ...item }));
  return ([ ["plaintiffs", "plaintiff", "原告", "plaintiff_identities"], ["defendants", "opponent", "被告", "defendant_identities"], ["third_parties", "third_party", "第三人", "third_party_identities"] ]).flatMap(([field, singular, position, identityField]) => {
    const names = Array.isArray(data[field]) ? data[field] : data[singular] ? [data[singular]] : [];
    return names.map((name: string) => {
      const identity = (data[identityField] || []).find((item: any) => item.name === name);
      return { name, is_client_principal: false, credit_code: identity?.identity_no || "", subject_kind: identity?.organization_type === "个人" ? "自然人" : identity?.organization_type ? "法人" : undefined,
        litigation_status: position, litigation_status_overridden: false, remark: "" };
    });
  });
}

export function classifiedPartyPayload(parties: ClassifiedCaseParty[]) {
  if (!parties?.length) throw new Error("请至少录入一名我方当事人并完成分类");
  for (const party of parties) {
    if (!party.name?.trim() || !partyCategory(party) || !party.subject_kind || !litigationPositions.includes(party.litigation_status)) throw new Error("请完整填写每名主体的名称、分类、性质和诉讼地位");
    if (party.subject_kind === "法人" && !/^[A-Za-z0-9]{18}$/.test(party.credit_code)) throw new Error(`${party.name}须填写18位统一社会信用代码`);
    if (party.party_standpoint === "我方" && party.party_type === "当事人" && !party.related_client_id) throw new Error(`${party.name}须关联实际委托客户`);
  }
  const names = (positions: string[]) => parties.filter(item => item.party_type !== "关联方" && positions.includes(item.litigation_status)).map(item => item.name.trim());
  return { case_parties: parties.map(({ related_client_name: _name, ...party }) => party), plaintiffs: names(["原告", "申请人"]), defendants: names(["被告", "被申请人"]), third_parties: names(["第三人"]) };
}

export function defaultCasePartyPosition(caseType: string, position: string): string {
  if (caseType === "法律顾问") return "其他";
  if (String(position || "").includes("第三人")) return "第三人";
  const defendant = String(position || "").includes("被告");
  if (caseType === "仲裁") return defendant ? "被申请人" : "申请人";
  return defendant ? "被告" : "原告";
}
