import { useEffect, useRef, useState } from "react";
import { Alert, Button, Checkbox, Input, Select } from "antd";
import { api } from "../api";
import { litigationPositions, mirroredPosition, partyCategories, partyCategory, type ClassifiedCaseParty } from "./casePartyClassification";
import "./case-party-classification.css";

interface Client { id: number; name: string; number: string; credit_code: string; organization_type: string }
interface Props { value?: ClassifiedCaseParty[]; onChange?: (value: ClassifiedCaseParty[]) => void; defaultLitigationStatus?: string }

export function CasePartyClassificationEditor({ value = [], onChange, defaultLitigationStatus = "原告" }: Props) {
  const [clients, setClients] = useState<Client[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const sequence = useRef(0);
  useEffect(() => {
    const request = ++sequence.current;
    const timer = window.setTimeout(() => {
      setLoading(true);
      void api.get("/customers/party-directory/clients", { params: { keyword: search } }).then(({ data }) => {
        if (request !== sequence.current) return;
        if (!Array.isArray(data.items)) throw new Error("委托客户查询响应无效");
        setClients(data.items); setError("");
      }).catch(cause => { if (request === sequence.current) { setClients([]); setError(cause.response?.data?.detail || cause.message || "委托客户加载失败"); } })
        .finally(() => { if (request === sequence.current) setLoading(false); });
    }, 250);
    return () => { window.clearTimeout(timer); ++sequence.current; };
  }, [search]);
  const update = (index: number, patch: Partial<ClassifiedCaseParty>) => {
    const next = value.map((item, at) => at === index ? { ...item, ...patch } : item);
    const ownPositions = [...new Set(next.filter(item => item.party_standpoint === "我方" && item.party_type === "当事人").map(item => item.litigation_status))];
    onChange?.(next.map(item => item.party_standpoint === "对方" && item.party_type === "当事人" && !item.litigation_status_overridden && ownPositions.length === 1
      ? { ...item, litigation_status: mirroredPosition[ownPositions[0]] } : item));
  };
  return <div className="case-party-classification">
    <Alert type="info" showIcon title="客户是委托主体，当事人按本案立场分类。历史未分类主体须人工确认；保存不会把对方主体加入 CRM。" />
    {error && <Alert type="error" showIcon title={error} />}
    {value.map((party, index) => <section key={party.id || index} className={`case-classified-party ${party.party_standpoint === "对方" ? "case-party-opponent" : ""}`}>
      <div className="case-party-heading"><strong>{partyCategory(party)?.label || "待确认分类"}</strong><Button danger onClick={() => onChange?.(value.filter((_, at) => at !== index))}>移除此主体</Button></div>
      <div className="case-party-fields">
        <label>分类<Select aria-label="当事人分类" value={partyCategory(party)?.value} options={[...partyCategories]} onChange={key => {
          const kind = partyCategories.find(item => item.value === key)!;
          update(index, { party_standpoint: kind.standpoint, party_type: kind.type, is_client_principal: kind.principal,
            ...(kind.standpoint === "对方" ? { related_client_id: null, related_client_name: undefined } : {}),
            ...(kind.type === "第三人" ? { litigation_status: "第三人" } : kind.type === "关联方" ? { litigation_status: "其他" } : {}) });
        }} /></label>
        <label>主体名称<Input aria-label="主体名称" value={party.name} maxLength={256} onChange={event => update(index, { name: event.target.value })} /></label>
        <label>主体性质<Select aria-label="主体性质" value={party.subject_kind} options={["自然人", "法人", "其他组织"].map(item => ({ value: item, label: item }))} onChange={subject_kind => update(index, { subject_kind })} /></label>
        <label>{party.subject_kind === "自然人" ? "证件号码（可选）" : "统一社会信用代码"}<Input aria-label="主体证件号码" value={party.credit_code} maxLength={64} onChange={event => update(index, { credit_code: event.target.value.toUpperCase() })} /></label>
        <label>诉讼地位<Select aria-label="诉讼地位" value={party.litigation_status} disabled={party.party_type === "第三人" || party.party_type === "关联方" || (party.party_standpoint === "对方" && !party.litigation_status_overridden)} options={litigationPositions.map(item => ({ value: item, label: item }))} onChange={litigation_status => update(index, { litigation_status })} /></label>
        {party.party_standpoint === "对方" && party.party_type === "当事人" && <label className="case-party-override"><Checkbox checked={party.litigation_status_overridden} onChange={event => update(index, { litigation_status_overridden: event.target.checked })}>复杂案情手动覆盖诉讼地位</Checkbox></label>}
        {party.party_standpoint === "我方" && <label>关联实际委托客户{party.party_type === "当事人" ? "（必填）" : "（可选）"}<Select aria-label="关联实际委托客户" showSearch filterOption={false} loading={loading} onSearch={setSearch} value={party.related_client_id ? { value: party.related_client_id, label: party.related_client_name || clients.find(item => item.id === party.related_client_id)?.name || `客户编号 ${party.related_client_id}` } : undefined} labelInValue allowClear
          options={clients.map(item => ({ value: item.id, label: `${item.name}（${item.number}）` }))} onChange={selection => {
            const client = clients.find(item => item.id === selection?.value);
            update(index, { related_client_id: client?.id ?? null, related_client_name: client?.name,
              ...(client && party.is_client_principal ? { name: client.name, credit_code: client.credit_code, subject_kind: client.organization_type === "个人" ? "自然人" : ["个体工商户", "其他"].includes(client.organization_type) ? "其他组织" : "法人" } : {}) });
          }} /></label>}
        <label className="case-party-remark">备注<Input.TextArea aria-label="主体备注" value={party.remark} maxLength={500} autoSize={{ minRows: 1, maxRows: 3 }} onChange={event => update(index, { remark: event.target.value })} /></label>
      </div>
    </section>)}
    <Button type="dashed" block onClick={() => onChange?.([...value, { name: "", credit_code: "", is_client_principal: false, litigation_status: defaultLitigationStatus, litigation_status_overridden: false, remark: "" }])}>新增案件主体</Button>
  </div>;
}
