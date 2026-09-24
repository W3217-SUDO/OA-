import { Form, Input, Select } from "antd";
import type { FormInstance } from "antd";
import type { CaseLitigantPartyField } from "./types";

type Identity = { name: string; organization_type: string; identity_no: string };
type IdentityValues = { organization_type: string; identity_no: string };
type IdentityFormValues = Record<CaseLitigantPartyField, Record<string, IdentityValues>>;

const identityFields: Record<CaseLitigantPartyField, string> = {
  plaintiffs: "plaintiff_identities",
  defendants: "defendant_identities",
  third_parties: "third_party_identities",
};

const roleLabels: Record<CaseLitigantPartyField, string> = {
  plaintiffs: "原告",
  defendants: "被告",
  third_parties: "第三人",
};

const organizationOptions = ["公司企业", "事业单位", "机关团体", "个人", "个体工商户", "其他"]
  .map((value) => ({ value, label: value }));

export function casePartyIdentityFormValues(data: Record<string, unknown>): IdentityFormValues {
  const result = { plaintiffs: {}, defendants: {}, third_parties: {} } as IdentityFormValues;
  for (const role of Object.keys(identityFields) as CaseLitigantPartyField[]) {
    const stored = data[identityFields[role]];
    if (!Array.isArray(stored)) continue;
    for (const item of stored as Identity[]) {
      if (!item || typeof item.name !== "string" || !item.name.trim()) continue;
      result[role][item.name.trim()] = {
        organization_type: String(item.organization_type || ""),
        identity_no: String(item.identity_no || ""),
      };
    }
  }
  return result;
}

export function collectCasePartyIdentities(values: Record<string, any>) {
  const result: Record<string, Identity[]> = {};
  for (const role of Object.keys(identityFields) as CaseLitigantPartyField[]) {
    const selected = Array.isArray(values[role]) ? values[role] as string[] : [];
    result[identityFields[role]] = selected.flatMap((name) => {
      const identity = values.party_identities?.[role]?.[name] as IdentityValues | undefined;
      if (!identity?.organization_type && !identity?.identity_no) return [];
      return [{
        name,
        organization_type: String(identity.organization_type || "").trim(),
        identity_no: String(identity.identity_no || "").trim(),
      }];
    });
  }
  return result;
}

function PartyIdentityRow({ form, role, name, original }: {
  form: FormInstance;
  role: CaseLitigantPartyField;
  name: string;
  original?: IdentityValues;
}) {
  const organizationPath = ["party_identities", role, name, "organization_type"];
  const identityPath = ["party_identities", role, name, "identity_no"];
  const organizationType = Form.useWatch(organizationPath, form);
  const identityNo = Form.useWatch(identityPath, form);
  const unchanged = Boolean(original && original.organization_type === organizationType && original.identity_no === identityNo);
  const isPerson = organizationType === "个人";
  return <div className="form-grid" key={name}>
    <div>{name}</div>
    <Form.Item label="组织类型" name={organizationPath} rules={unchanged ? [] : [{ required: Boolean(identityNo), message: "请选择组织类型" }]}>
      <Select allowClear options={organizationOptions} />
    </Form.Item>
    <Form.Item label={isPerson ? "身份证号" : "统一社会信用代码"} name={identityPath} rules={unchanged ? [] : [
      { required: Boolean(organizationType), message: "请输入证件号" },
      { pattern: isPerson ? /^\d{17}[\dXx]$/ : /^[0-9A-Za-z]{18}$/, message: "请输入18位有效证件号" },
    ]}>
      <Input maxLength={18} />
    </Form.Item>
  </div>;
}

export function CasePartyIdentityFields({ form, role, originals }: {
  form: FormInstance;
  role: CaseLitigantPartyField;
  originals: IdentityFormValues;
}) {
  const selected = Form.useWatch(role, form);
  const names = Array.isArray(selected) ? selected.filter((name): name is string => typeof name === "string" && Boolean(name.trim())) : [];
  if (!names.length) return null;
  return <section>
    <h4>{roleLabels[role]}证件信息</h4>
    {names.map((name) => <PartyIdentityRow key={name} form={form} role={role} name={name} original={originals[role][name]} />)}
  </section>;
}
