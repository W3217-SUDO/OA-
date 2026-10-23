import { DownOutlined, UpOutlined } from "@ant-design/icons";
import { Button,Card,Collapse } from "antd";
import { useEffect, useId, useState } from "react";
import { getCaseDetailSectionVisibility } from "../../caseDetailSectionVisibility";
import type { CaseRow } from "../types";
import { caseCourtDisplay } from "../courtDisplay";

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

export function caseHeaderHearingLawyers(data: Record<string, unknown>): string[] {
  // Keep field precedence and token normalization aligned with core/cases.py.
  const firstPopulated = (fields: string[]): string[] => {
    for (const field of fields) {
      const raw = data[field];
      const values = Array.isArray(raw) ? raw : [raw];
      const tokens = values.flatMap((value) => String(value || "").split(/[,，、;/；\n]+/))
        .map((value) => value.trim())
        .filter((value) => value && !["—", "-", "无", "未分配", "【待补充中文姓名】"].includes(value));
      if (tokens.length) return [...new Set(tokens)];
    }
    return [];
  };
  const explicit = firstPopulated([
    "hearing_lawyer_usernames", "hearing_lawyer_username", "court_lawyer_username",
    "hearing_lawyers", "hearing_lawyer", "court_lawyer",
  ]);
  return explicit.length ? explicit : firstPopulated([
    "handling_lawyer_usernames", "handling_lawyer_username", "handling_lawyers",
  ]).slice(0, 1);
}

const isFilledDetailValue = (value: unknown) => !["", "-", "—", "null", "none", "undefined"].includes(String(value ?? "").trim().toLowerCase());
const detailText = (value: unknown) => isFilledDetailValue(value) ? String(value).trim() : "—";

/** 10.22 第15行：刑事检察机关窗口按一审/二审/再审分组，字段与“检察院信息”弹窗一致。 */
export const CRIMINAL_PROCURATORATE_DISPLAY_LEVELS = [["first", "一审"], ["second", "二审"], ["retrial", "再审"]] as const;
export function criminalProcuratorateLevelValues(data: Record<string, any>, level: "first" | "second" | "retrial") {
  const name = data[`${level}_procuratorate_name`] || (level === "retrial" ? data.last_procuratorate_name : "");
  return {
    name,
    case_no: data[`${level}_procuratorate_case_no`],
    address: data[`${level}_procuratorate_address`],
    operator: data[`${level}_procuratorate_operator`],
    phone: data[`${level}_procuratorate_phone`],
  };
}

/** 10.22 第18行：刑事受害人取新建时填写的“原告”，为空显示“—”，不回退为客户。 */
export function criminalVictimNames(data: Record<string, any>, caseDetailNames: (value: unknown) => string): string {
  const fromList = Array.isArray(data.plaintiffs) && data.plaintiffs.length ? caseDetailNames(data.plaintiffs) : "";
  return detailText(fromList || data.plaintiff);
}

interface SummarySectionProps {
  title: string;
  expanded: boolean;
  onToggle: () => void;
  panelId: string;
  children: React.ReactNode;
}

const CaseSummarySection = ({ title, expanded, onToggle, panelId, children }: SummarySectionProps) => (
  <section className="case-court-summary" aria-label={title}>
    <div className="case-court-summary-title">
      <span>{title}</span>
      <Button
        type="text"
        size="small"
        className="case-summary-section-toggle"
        aria-expanded={expanded}
        aria-controls={panelId}
        aria-label={`${expanded ? "收起" : "展开"}${title}`}
        title={`${expanded ? "收起" : "展开"}${title}`}
        icon={expanded ? <UpOutlined /> : <DownOutlined />}
        onClick={onToggle}
      />
    </div>
    <div id={panelId} className="case-court-summary-grid case-criminal-summary-grid" hidden={!expanded}>{children}</div>
  </section>
);

export const CaseDetailHeader = (props: CaseDetailHeaderProps) => {
 const {
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
 } = props;
  const sectionVisibility = getCaseDetailSectionVisibility(viewingCase.data, viewingCase.status);
  const [courtExpanded, setCourtExpanded] = useState(true);
  const [archiveExpanded, setArchiveExpanded] = useState(true);
  const [publicSecurityExpanded, setPublicSecurityExpanded] = useState(true);
  const [procuratorateExpanded, setProcuratorateExpanded] = useState(true);
  const sectionId = useId().replace(/:/g, "-");
  const isCriminal = viewingCase.data.case_type === "刑事案件";

  useEffect(() => {
    // 案件切换时恢复旧系统的默认展开状态，避免沿用上一案件的折叠状态。
    setCourtExpanded(true);
    setArchiveExpanded(true);
    setPublicSecurityExpanded(true);
    setProcuratorateExpanded(true);
  }, [viewingCase.id]);

  const courtPanelId = `case-court-panel-${sectionId}`;
  const archivePanelId = `case-archive-panel-${sectionId}`;
  return (
    <>
      {Array.isArray(viewingCase.data.merged_sources) && viewingCase.data.merged_sources.length > 0 &&
        <Collapse items={viewingCase.data.merged_sources.map((source: CaseRow) => ({ key: source.id, label: `合并来源：${source.serial_no} ${source.title}`, children: <CaseDetailHeader {...props} viewingCase={source} /> }))} />}
      <Card size="small" title="案件信息" className="case-counsel-detail-card">
        <div className="case-legacy-summary-scroll">
          {isCriminal ? <table className="case-legacy-summary case-criminal-summary" data-testid="case-legacy-summary" data-case-summary="criminal">
            <colgroup><col className="case-legacy-label"/><col/><col className="case-legacy-label"/><col/><col className="case-legacy-label"/><col/></colgroup>
            <tbody>
              <tr><th>我方案号</th><td>{viewingCase.serial_no||"—"}</td><th>罪名</th><td>{detailText(viewingCase.data.cause_or_charge)}</td><th>受害人</th><td>{criminalVictimNames(viewingCase.data, caseDetailNames)}</td></tr>
              <tr><th>案件名称</th><td>{viewingCase.title||"—"}</td><th>案件阶段</th><td>{viewingCase.status||"—"}</td><th>受害人代理人</th><td>{renderCaseLitigantAgentSummary(viewingCase.data.plaintiff_agents)}</td></tr>
              <tr><th>客户</th><td><Button type="link" className="case-cell-link" onClick={() => openRelatedCustomer({ id: Number(viewingCase.data.customer_id) || undefined, serial_no: viewingCase.data.customer_no, title: viewingCase.customer })}>{viewingCase.customer||"—"}</Button></td><th>经办律师</th><td>{casePersonDisplayNames(viewingCase.data.handling_lawyers)}</td><th>被告/犯罪嫌疑人</th><td>{caseDetailNames(Array.isArray(viewingCase.data.defendants) && viewingCase.data.defendants.length ? viewingCase.data.defendants : viewingCase.data.opponent || viewingCase.data.defendant)}</td></tr>
              <tr><th>合同号</th><td>{viewingCase.data.contract_no?<Button type="link" className="case-cell-link" onClick={() => openRelatedContract({ id: Number(viewingCase.data.contract_record_id || viewingCase.data.contract_id) || undefined, serial_no: viewingCase.data.contract_no })}>{viewingCase.data.contract_no}</Button>:"—"}</td><th>律师助理</th><td>{caseAssistantDisplayNames(viewingCase.data)}</td><th>被告代理人</th><td>{renderCaseLitigantAgentSummary(viewingCase.data.defendant_agents)}</td></tr>
              <tr><th>案源日期</th><td>{caseDetailDate(viewingCase.data.source_date||viewingCase.data.source_at)}</td><th>案件来源</th><td colSpan={3}>{casePersonDisplayName(viewingCase.data.business_owner||viewingCase.data.source_person||viewingCase.owner,viewingCase.data.business_owner_display_name||viewingCase.data.source_person_display_name||viewingCase.owner_display_name)}</td></tr>
            </tbody>
          </table> : <table className="case-legacy-summary" data-testid="case-legacy-summary">
            <colgroup><col className="case-legacy-label"/><col/><col className="case-legacy-label"/><col/><col className="case-legacy-label"/><col/><col className="case-legacy-label"/><col/></colgroup>
            <tbody>
              <tr><th>我方案号</th><td>{viewingCase.serial_no||"—"}</td><th>起诉案由</th><td>{viewingCase.data.cause_or_charge||viewingCase.data.cause_of_action||"—"}</td><th>案件阶段</th><td>{viewingCase.status||"—"}</td><th>原告</th><td>{viewingCase.data.plaintiff||viewingCase.customer||"—"}</td></tr>
              <tr><th>案件名称</th><td colSpan={3}>{viewingCase.title||"—"}</td><th>开庭律师</th><td>{casePersonDisplayNames(caseHeaderHearingLawyers(viewingCase.data))}</td><th>被告</th><td>{caseDetailNames(Array.isArray(viewingCase.data.defendants) && viewingCase.data.defendants.length ? viewingCase.data.defendants : viewingCase.data.opponent || viewingCase.data.defendant)}</td></tr>
              <tr><th>案件参与人</th><td colSpan={7}>{legacyCaseParticipantDisplayNames(viewingCase.data)}</td></tr>
              <tr><th>原告代理人</th><td colSpan={3}>{renderCaseLitigantAgentSummary(viewingCase.data.plaintiff_agents)}</td><th>被告代理人</th><td colSpan={3}>{renderCaseLitigantAgentSummary(viewingCase.data.defendant_agents)}</td></tr>
              <tr><th>第三人代理人</th><td colSpan={7}>{renderCaseLitigantAgentSummary(viewingCase.data.third_party_agents)}</td></tr>
              <tr><th>客户</th><td colSpan={3}><Button type="link" className="case-cell-link" onClick={() => openRelatedCustomer({ id: Number(viewingCase.data.customer_id) || undefined, serial_no: viewingCase.data.customer_no, title: viewingCase.customer })}>{viewingCase.customer||"—"}</Button></td><th>经办律师</th><td>{casePersonDisplayNames(viewingCase.data.handling_lawyers)}</td><th>第三人</th><td>{viewingCase.data.third_party||caseDetailNames(viewingCase.data.third_parties)}</td></tr>
              <tr><th>合同号</th><td>{viewingCase.data.contract_no?<Button type="link" className="case-cell-link" onClick={() => openRelatedContract({ id: Number(viewingCase.data.contract_record_id || viewingCase.data.contract_id) || undefined, serial_no: viewingCase.data.contract_no })}>{viewingCase.data.contract_no}</Button>:"—"}</td><th>调查员</th><td>{casePersonDisplayName(viewingCase.data.investigator,viewingCase.data.investigator_display_name)}</td><th>律师助理</th><td>{caseAssistantDisplayNames(viewingCase.data)}</td><th>公证书号</th><td>{viewingCase.data.notarial_no||viewingCase.data.notary_no||viewingCase.data.certificate_no||"—"}</td></tr>
              <tr><th>线索号</th><td colSpan={3}>{String(viewingCase.data.clue_no||viewingCase.data.investigation_clue||viewingCase.data.source_clue_no||viewingCase.data.investigation_clue_nos||"").trim()?<Button type="link" className="case-cell-link" onClick={() => openRelatedClue({ id: Number(viewingCase.data.clue_record_id || viewingCase.data.investigation_clue_id) || undefined, serial_no: viewingCase.data.clue_no || viewingCase.data.investigation_clue || viewingCase.data.source_clue_no || viewingCase.data.investigation_clue_nos })}>{caseDetailNames(viewingCase.data.investigation_clue_nos||viewingCase.data.clue_no||viewingCase.data.investigation_clue||viewingCase.data.source_clue_no)}</Button>:"—"}</td><th>立案日期</th><td>{caseDetailDate(viewingCase.created_at)}</td><th>仓库位置</th><td>{viewingCase.data.warehouse||viewingCase.data.warehouse_location||viewingCase.data.storage_location||viewingCase.data.location||viewingCase.data.deposit_address||"—"}</td></tr>
              <tr><th>原案件号</th><td colSpan={3}>{String(viewingCase.data.original_case_no||viewingCase.data.origin_case_no||viewingCase.data.source_case_no||"").trim()?<Button type="link" className="case-cell-link" onClick={() => openRelatedOriginalCase({ id: Number(viewingCase.data.original_case_id||viewingCase.data.source_case_id)||undefined, serial_no: viewingCase.data.original_case_no||viewingCase.data.origin_case_no||viewingCase.data.source_case_no })}>{viewingCase.data.original_case_no||viewingCase.data.origin_case_no||viewingCase.data.source_case_no}</Button>:"—"}</td><th>复制/关联说明</th><td colSpan={3}>{viewingCase.data.copy_comment||viewingCase.data.relation_comment||"—"}</td></tr>
              <tr><th>诉讼标的</th><td>{viewingCase.data.litigation_subject||viewingCase.data.litigation_amount||"—"}</td><th>判决/调解金额</th><td>{viewingCase.data.judgment_amount||viewingCase.data.settlement_amount||viewingCase.data.mediation_amount||"—"}</td><th>分案日期</th><td>{caseDetailDate(viewingCase.data.case_divisional_date||viewingCase.data.assignment_date)}</td><th>案源人</th><td>{casePersonDisplayName(viewingCase.data.business_owner||viewingCase.data.source_person||viewingCase.owner,viewingCase.data.business_owner_display_name||viewingCase.data.source_person_display_name||viewingCase.owner_display_name)}</td></tr>
            </tbody>
          </table>}
        </div>
      </Card>
      {isCriminal && <CaseSummarySection title="公安机关" expanded={publicSecurityExpanded} onToggle={() => setPublicSecurityExpanded((expanded) => !expanded)} panelId={`case-public-security-panel-${sectionId}`}>
        <p><strong>公安机关</strong><span title={detailText(viewingCase.data.public_security_name)}>{detailText(viewingCase.data.public_security_name)}</span></p>
        <p><strong>案号</strong><span>{detailText(viewingCase.data.public_security_case_no)}</span></p>
        <p><strong>地址</strong><span title={detailText(viewingCase.data.public_security_address)}>{detailText(viewingCase.data.public_security_address)}</span></p>
        <p><strong>经办人</strong><span>{detailText(viewingCase.data.public_security_operator)}</span></p>
        <p><strong>联系方式</strong><span>{detailText(viewingCase.data.public_security_phone)}</span></p>
      </CaseSummarySection>}
      {isCriminal && <CaseSummarySection title="检察机关" expanded={procuratorateExpanded} onToggle={() => setProcuratorateExpanded((expanded) => !expanded)} panelId={`case-procuratorate-panel-${sectionId}`}>
        {CRIMINAL_PROCURATORATE_DISPLAY_LEVELS.map(([level, label]) => {
          const values = criminalProcuratorateLevelValues(viewingCase.data, level);
          // 一审始终显示；二审、再审仅在有数据时显示（与法院信息审级规则一致）。
          if (level !== "first" && !Object.values(values).some(isFilledDetailValue)) return null;
          return <div key={level} className="case-procuratorate-level" style={{display:"contents"}}>
            <p><strong>{`${label}检察机关`}</strong><span title={detailText(values.name)}>{detailText(values.name)}</span></p>
            <p><strong>检察院案号</strong><span>{detailText(values.case_no)}</span></p>
            <p><strong>地址</strong><span title={detailText(values.address)}>{detailText(values.address)}</span></p>
            <p><strong>经办人</strong><span>{detailText(values.operator)}</span></p>
            <p><strong>联系方式</strong><span>{detailText(values.phone)}</span></p>
          </div>;
        })}
      </CaseSummarySection>}
      {viewingCase.data.case_type !== "法律顾问" && <section className="case-court-summary" aria-label="法院信息">
        <div className="case-court-summary-title">
          <span>法院信息</span>
          <Button
            type="text"
            size="small"
            className="case-summary-section-toggle"
            aria-expanded={courtExpanded}
            aria-controls={courtPanelId}
            aria-label={`${courtExpanded ? "收起" : "展开"}法院信息`}
            title={`${courtExpanded ? "收起" : "展开"}法院信息`}
            icon={courtExpanded ? <UpOutlined /> : <DownOutlined />}
            onClick={() => setCourtExpanded((expanded) => !expanded)}
          />
        </div>
        <div id={courtPanelId} className="case-court-summary-grid" hidden={!courtExpanded}>
          {(sectionVisibility.firstCourt || !sectionVisibility.court) && <>
            <p><strong>一审法院</strong><span title={caseCourtDisplay(viewingCase.data, "first")}>{caseCourtDisplay(viewingCase.data, "first")}</span></p>
            <p><strong>法庭</strong><span>{viewingCase.data.first_court_courtroom||viewingCase.data.courtroom||"—"}</span></p>
            <p><strong>一审案号</strong><span>{viewingCase.data.first_court_case_no||viewingCase.data.first_instance_case_no||viewingCase.data.court_case_no||"—"}</span></p>
            <p><strong>立案时间</strong><span>{viewingCase.data.first_court_filing_date||viewingCase.data.filing_date||"—"}</span></p>
            <p><strong>开庭时间</strong><span>{viewingCase.data.first_court_hearing_date||viewingCase.data.hearing_date||"—"}</span></p>
            <p><strong>判决日期</strong><span>{viewingCase.data.first_court_judgment_date||viewingCase.data.judgment_date||"—"}</span></p>
          </>}
          {sectionVisibility.secondCourt && <>
            <p><strong>二审法院</strong><span title={caseCourtDisplay(viewingCase.data, "second")}>{caseCourtDisplay(viewingCase.data, "second")}</span></p>
            <p><strong>二审法庭</strong><span>{viewingCase.data.second_court_courtroom||"—"}</span></p>
            <p><strong>二审案号</strong><span>{viewingCase.data.second_court_case_no||viewingCase.data.second_instance_case_no||"—"}</span></p>
            <p><strong>二审立案日期</strong><span>{viewingCase.data.second_court_filing_date||"—"}</span></p>
            <p><strong>二审开庭日期</strong><span>{viewingCase.data.second_court_hearing_date||"—"}</span></p>
          </>}
          {sectionVisibility.executionCourt && <>
            <p><strong>执行法院</strong><span title={caseCourtDisplay(viewingCase.data, "execution")}>{caseCourtDisplay(viewingCase.data, "execution")}</span></p>
            <p><strong>法庭</strong><span>{viewingCase.data.execution_court_courtroom||"—"}</span></p>
            <p><strong>执行案号</strong><span>{viewingCase.data.execution_court_case_no||"—"}</span></p>
            <p><strong>立案时间</strong><span>{viewingCase.data.execution_court_filing_date||"—"}</span></p>
            <p><strong>开庭时间</strong><span>{viewingCase.data.execution_court_hearing_date||"—"}</span></p>
            <p><strong>生效日期</strong><span>{viewingCase.data.effective_date||"—"}</span></p>
          </>}
          {sectionVisibility.retrialCourt && <>
            <p><strong>再审法院</strong><span title={caseCourtDisplay(viewingCase.data, "retrial")}>{caseCourtDisplay(viewingCase.data, "retrial")}</span></p>
            <p><strong>法庭</strong><span>{viewingCase.data.retrial_court_courtroom||"—"}</span></p>
            <p><strong>再审案号</strong><span>{viewingCase.data.retrial_court_case_no||"—"}</span></p>
            <p><strong>立案时间</strong><span>{viewingCase.data.retrial_court_filing_date||"—"}</span></p>
            <p><strong>开庭时间</strong><span>{viewingCase.data.retrial_court_hearing_date||"—"}</span></p>
            <p><strong>判决日期</strong><span>{viewingCase.data.retrial_court_judgment_date||"—"}</span></p>
          </>}
        </div>
      </section>}
      {sectionVisibility.archive && <section className="case-archive-summary" aria-label="归档信息">
        <div className="case-court-summary-title">
          <span>归档信息</span>
          <Button
            type="text"
            size="small"
            className="case-summary-section-toggle"
            aria-expanded={archiveExpanded}
            aria-controls={archivePanelId}
            aria-label={`${archiveExpanded ? "收起" : "展开"}归档信息`}
            title={`${archiveExpanded ? "收起" : "展开"}归档信息`}
            icon={archiveExpanded ? <UpOutlined /> : <DownOutlined />}
            onClick={() => setArchiveExpanded((expanded) => !expanded)}
          />
        </div>
        <div id={archivePanelId} className="case-court-summary-grid case-archive-summary-grid" hidden={!archiveExpanded}>
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
