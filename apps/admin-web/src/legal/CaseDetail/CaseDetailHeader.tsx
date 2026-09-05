import { Button,Card } from "antd";
import { getCaseDetailSectionVisibility } from "../../caseDetailSectionVisibility";
import type { CaseRow } from "../types";

interface CaseDetailHeaderProps {
  viewingCase: CaseRow;
  casePersonDisplayName: (source: unknown, displayName?: unknown) => React.ReactNode;
  casePersonDisplayNames: (sources: unknown) => React.ReactNode;
  caseAssistantDisplayNames: (data: Record<string, unknown> | null | undefined) => React.ReactNode;
  renderCaseLitigantAgentSummary: (value: unknown) => React.ReactNode;
  caseDetailDate: (value: unknown) => string;
  caseDetailNames: (value: unknown) => string;
  legacyCaseParticipantDisplayNames: (data: Record<string, any>) => React.ReactNode;
  openRelatedCustomer: (target: { id?: number; serial_no?: string; title?: string }) => void;
  openRelatedContract: (target: { id?: number; serial_no?: string }) => void;
  openRelatedClue: (target: { id?: number; serial_no?: string }) => void;
  openRelatedOriginalCase: (target: { id?: number; serial_no?: string }) => void;
  isCaseDetailView: boolean;
  returnToCaseList: () => void;
}

export const CaseDetailHeader = ({
  viewingCase,
  casePersonDisplayName,
  casePersonDisplayNames,
  caseAssistantDisplayNames,
  renderCaseLitigantAgentSummary,
  caseDetailDate,
  caseDetailNames,
  legacyCaseParticipantDisplayNames,
  openRelatedCustomer,
  openRelatedContract,
  openRelatedClue,
  openRelatedOriginalCase,
}: CaseDetailHeaderProps) => {
  return (
    <>
      <Card size="small" title="案件信息" className="case-counsel-detail-card">
        <div className="case-legacy-summary-scroll">
          <table className="case-legacy-summary" data-testid="case-legacy-summary">
            <colgroup><col className="case-legacy-label"/><col/><col className="case-legacy-label"/><col/><col className="case-legacy-label"/><col/><col className="case-legacy-label"/><col/></colgroup>
            <tbody>
              <tr><th>我方案号</th><td>{viewingCase.serial_no||"—"}</td><th>起诉案由</th><td>{viewingCase.data.cause_or_charge||viewingCase.data.cause_of_action||"—"}</td><th>案件阶段</th><td>{viewingCase.status||"—"}</td><th>原告</th><td>{viewingCase.data.plaintiff||viewingCase.customer||"—"}</td></tr>
              <tr><th>案件名称</th><td colSpan={3}>{viewingCase.title||"—"}</td><th>开庭律师</th><td>{casePersonDisplayName(viewingCase.data.hearing_lawyer||viewingCase.data.handling_lawyers?.[0],viewingCase.data.hearing_lawyer_display_name)}</td><th>被告</th><td>{viewingCase.data.defendant||viewingCase.data.opponent||caseDetailNames(viewingCase.data.defendants)}</td></tr>
              <tr><th>案件参与人</th><td colSpan={7}>{legacyCaseParticipantDisplayNames(viewingCase.data)}</td></tr>
              <tr><th>原告代理人</th><td colSpan={3}>{renderCaseLitigantAgentSummary(viewingCase.data.plaintiff_agents)}</td><th>被告代理人</th><td colSpan={3}>{renderCaseLitigantAgentSummary(viewingCase.data.defendant_agents)}</td></tr>
              <tr><th>第三人代理人</th><td colSpan={7}>{renderCaseLitigantAgentSummary(viewingCase.data.third_party_agents)}</td></tr>
              <tr><th>客户</th><td colSpan={3}><Button type="link" className="case-cell-link" onClick={() => openRelatedCustomer({ id: Number(viewingCase.data.customer_id) || undefined, serial_no: viewingCase.data.customer_no, title: viewingCase.customer })}>{viewingCase.customer||"—"}</Button></td><th>经办律师</th><td>{casePersonDisplayNames(viewingCase.data.handling_lawyers)}</td><th>第三人</th><td>{viewingCase.data.third_party||caseDetailNames(viewingCase.data.third_parties)}</td></tr>
              <tr><th>合同号</th><td>{viewingCase.data.contract_no?<Button type="link" className="case-cell-link" onClick={() => openRelatedContract({ id: Number(viewingCase.data.contract_record_id) || undefined, serial_no: viewingCase.data.contract_no })}>{viewingCase.data.contract_no}</Button>:"—"}</td><th>调查员</th><td>{casePersonDisplayName(viewingCase.data.investigator,viewingCase.data.investigator_display_name)}</td><th>律师助理</th><td>{caseAssistantDisplayNames(viewingCase.data)}</td><th>公证书号</th><td>{viewingCase.data.notarial_no||viewingCase.data.notary_no||viewingCase.data.certificate_no||"—"}</td></tr>
              <tr><th>线索号</th><td colSpan={3}>{String(viewingCase.data.clue_no||viewingCase.data.investigation_clue||viewingCase.data.source_clue_no||viewingCase.data.investigation_clue_nos||"").trim()?<Button type="link" className="case-cell-link" onClick={() => openRelatedClue({ id: Number(viewingCase.data.clue_record_id || viewingCase.data.investigation_clue_id) || undefined, serial_no: viewingCase.data.clue_no || viewingCase.data.investigation_clue || viewingCase.data.source_clue_no || viewingCase.data.investigation_clue_nos })}>{caseDetailNames(viewingCase.data.investigation_clue_nos||viewingCase.data.clue_no||viewingCase.data.investigation_clue||viewingCase.data.source_clue_no)}</Button>:"—"}</td><th>立案日期</th><td>{caseDetailDate(viewingCase.data.case_register_date||viewingCase.data.filing_date||viewingCase.data.first_court_filing_date)}</td><th>仓库位置</th><td>{viewingCase.data.warehouse||viewingCase.data.warehouse_location||viewingCase.data.storage_location||viewingCase.data.location||viewingCase.data.deposit_address||"—"}</td></tr>
              <tr><th>原案件号</th><td colSpan={3}>{String(viewingCase.data.original_case_no||viewingCase.data.origin_case_no||viewingCase.data.source_case_no||"").trim()?<Button type="link" className="case-cell-link" onClick={() => openRelatedOriginalCase({ id: Number(viewingCase.data.original_case_id||viewingCase.data.source_case_id)||undefined, serial_no: viewingCase.data.original_case_no||viewingCase.data.origin_case_no||viewingCase.data.source_case_no })}>{viewingCase.data.original_case_no||viewingCase.data.origin_case_no||viewingCase.data.source_case_no}</Button>:"—"}</td><th>复制/关联说明</th><td colSpan={3}>{viewingCase.data.copy_comment||viewingCase.data.relation_comment||"—"}</td></tr>
              <tr><th>诉讼标的</th><td>{viewingCase.data.litigation_subject||viewingCase.data.litigation_amount||"—"}</td><th>判决/调解金额</th><td>{viewingCase.data.judgment_amount||viewingCase.data.settlement_amount||viewingCase.data.mediation_amount||"—"}</td><th>分案日期</th><td>{caseDetailDate(viewingCase.data.case_divisional_date||viewingCase.data.assignment_date)}</td><th>案源人</th><td>{casePersonDisplayName(viewingCase.data.business_owner||viewingCase.data.source_person||viewingCase.owner,viewingCase.data.business_owner_display_name||viewingCase.data.source_person_display_name||viewingCase.owner_display_name)}</td></tr>
            </tbody>
          </table>
        </div>
      </Card>
      {viewingCase.data.case_type !== "法律顾问" && getCaseDetailSectionVisibility(viewingCase.data, viewingCase.status).court && <section className="case-court-summary" aria-label="法院信息">
        <div className="case-court-summary-title">法院信息</div>
        <div className="case-court-summary-grid">
          {getCaseDetailSectionVisibility(viewingCase.data, viewingCase.status).firstCourt && <>
            <p><strong>一审法院</strong><span>{viewingCase.data.first_court_name||viewingCase.data.first_instance_court||viewingCase.data.court||"—"}</span></p>
            <p><strong>法庭</strong><span>{viewingCase.data.first_court_courtroom||viewingCase.data.courtroom||"—"}</span></p>
            <p><strong>一审案号</strong><span>{viewingCase.data.first_court_case_no||viewingCase.data.first_instance_case_no||viewingCase.data.court_case_no||"—"}</span></p>
            <p><strong>立案时间</strong><span>{viewingCase.data.first_court_filing_date||viewingCase.data.filing_date||"—"}</span></p>
            <p><strong>开庭时间</strong><span>{viewingCase.data.first_court_hearing_date||viewingCase.data.hearing_date||"—"}</span></p>
            <p><strong>判决日期</strong><span>{viewingCase.data.first_court_judgment_date||viewingCase.data.judgment_date||"—"}</span></p>
          </>}
          {getCaseDetailSectionVisibility(viewingCase.data, viewingCase.status).secondCourt && <>
            <p><strong>二审法院</strong><span>{viewingCase.data.second_court_name||viewingCase.data.second_instance_court||"—"}</span></p>
            <p><strong>二审法庭</strong><span>{viewingCase.data.second_court_courtroom||"—"}</span></p>
            <p><strong>二审案号</strong><span>{viewingCase.data.second_court_case_no||viewingCase.data.second_instance_case_no||"—"}</span></p>
            <p><strong>二审立案日期</strong><span>{viewingCase.data.second_court_filing_date||"—"}</span></p>
            <p><strong>二审开庭日期</strong><span>{viewingCase.data.second_court_hearing_date||"—"}</span></p>
          </>}
          {getCaseDetailSectionVisibility(viewingCase.data, viewingCase.status).executionCourt && <>
            <p><strong>执行法院</strong><span>{viewingCase.data.execution_court_name||"—"}</span></p>
            <p><strong>法庭</strong><span>{viewingCase.data.execution_court_courtroom||"—"}</span></p>
            <p><strong>执行案号</strong><span>{viewingCase.data.execution_court_case_no||"—"}</span></p>
            <p><strong>立案时间</strong><span>{viewingCase.data.execution_court_filing_date||"—"}</span></p>
            <p><strong>开庭时间</strong><span>{viewingCase.data.execution_court_hearing_date||"—"}</span></p>
            <p><strong>生效日期</strong><span>{viewingCase.data.effective_date||"—"}</span></p>
          </>}
        </div>
      </section>}
      {getCaseDetailSectionVisibility(viewingCase.data, viewingCase.status).archive && <section className="case-archive-summary" aria-label="归档信息">
        <div className="case-court-summary-title">归档信息</div>
        <div className="case-court-summary-grid case-archive-summary-grid">
          <p><strong>归档类型</strong><span>{viewingCase.data.archive_type === "deficit" ? "亏损归档" : viewingCase.data.archive_type === "normal" ? "正常归档" : "—"}</span></p>
          <p><strong>提交人</strong><span>{viewingCase.data.archive_submitter ? casePersonDisplayName(viewingCase.data.archive_submitter, viewingCase.data.archive_submitter_display_name) : "—"}</span></p>
          <p><strong>提交时间</strong><span>{viewingCase.data.archive_submitted_at || "—"}</span></p>
          <p><strong>提交备注</strong><span>{viewingCase.data.archive_submit_comment || "—"}</span></p>
          <p><strong>审核状态</strong><span>{viewingCase.data.archive_status || "—"}</span></p>
          {viewingCase.data.archive_type === "deficit" && <>
            <p><strong>内部审核人</strong><span>{viewingCase.data.archive_internal_reviewer ? casePersonDisplayName(viewingCase.data.archive_internal_reviewer, viewingCase.data.archive_internal_reviewer_display_name) : "—"}</span></p>
            <p><strong>内部审核时间</strong><span>{viewingCase.data.archive_internal_reviewed_at || "—"}</span></p>
            <p><strong>内部审核意见</strong><span>{viewingCase.data.archive_internal_review_comment || "—"}</span></p>
          </>}
          <p><strong>审核人</strong><span>{viewingCase.data.archive_reviewer ? casePersonDisplayName(viewingCase.data.archive_reviewer, viewingCase.data.archive_reviewer_display_name) : "—"}</span></p>
          <p><strong>审核时间</strong><span>{viewingCase.data.archive_reviewed_at || viewingCase.data.archived_at || "—"}</span></p>
          <p><strong>审核备注</strong><span>{viewingCase.data.archive_review_comment || viewingCase.data.archive_reject_reason || "—"}</span></p>
          <p><strong>归档号</strong><span>{viewingCase.data.archive_no || "—"}</span></p>
        </div>
      </section>}
    </>
  );
};
