import { Alert, Button, message } from "antd";
import { api } from "../api";
import { rememberCustomerDetailTarget } from "../customerDetailNavigation";
import { partyCategory, type ClassifiedCaseParty } from "./casePartyClassification";

export function CasePartyClassificationSummary({ classified, parties, onNavigate }: {
  classified: boolean; parties: ClassifiedCaseParty[]; onNavigate?: (route: string) => void;
}) {
  const openClient = async (party: ClassifiedCaseParty) => {
    try {
      const { data } = await api.get(`/records/${party.related_client_id}`);
      if (data.module !== "customer") throw new Error("关联对象不是客户");
      rememberCustomerDetailTarget({ id: data.id, serial_no: data.serial_no, title: data.title });
      onNavigate?.(`customer-detail-${data.id}-${encodeURIComponent(data.title)}`);
    } catch (cause: any) {
      message.error(cause.response?.data?.detail || cause.message || "关联客户不存在或无权查看");
    }
  };
  if (!classified) return <Alert type="warning" title="历史当事人尚未分类，请通过修改当事人逐一人工确认；系统不会自动推断委托关系。" />;
  return <div className="case-party-classification">{parties.map(party => <section className="case-classified-party" key={party.id}>
    <strong>{partyCategory(party)?.label} · {party.name}</strong>
    <p>主体性质：{party.subject_kind}　诉讼地位：{party.litigation_status}{party.litigation_status_overridden ? "（手动覆盖）" : ""}</p>
    <p>{party.subject_kind === "自然人" ? "证件号码" : "统一社会信用代码"}：{party.credit_code || "未登记"}</p>
    <p>关联委托客户：{party.related_client_id && onNavigate ? <Button type="link" onClick={() => void openClient(party)}>{party.related_client_name || `客户编号 ${party.related_client_id}`}</Button> : "无"}</p>
    {party.remark && <p>备注：{party.remark}</p>}
  </section>)}</div>;
}
