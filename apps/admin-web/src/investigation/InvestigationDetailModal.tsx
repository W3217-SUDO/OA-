import { Modal, Button } from "antd";
import type { Row, ClueWorkspace, Attachment } from "./types";
import ClueDetailHeader from "./ClueDetail/ClueDetailHeader";
import ClueEvidencePanel from "./ClueDetail/ClueEvidencePanel";

export interface InvestigationDetailContentProps {
  investigationDetail: Row | null;
  clueWorkspace: ClueWorkspace | null;
  clueWorkspaceLoading: boolean;
  selectedEvidenceId: number | null;
  projectedPersonDisplayName: (displayName: unknown, username: unknown) => string;
  onOpenLinkedCustomer: (name: string) => void;
  onOpenLinkedInvestigation: (serialNo: string, module: "investigation" | "clue" | "task") => void;
  onOpenLinkedCase: (caseNo: string) => void;
  onOpenLinkedNotary: (recordId?: number, certificateNo?: string) => void;
  onSelectEvidence: (id: number | null) => void;
  onEditEvidence: () => void;
  onDownloadFile: (file: Attachment) => void;
  onDeleteEvidence: () => void;
}

interface InvestigationDetailModalProps extends InvestigationDetailContentProps {
  open: boolean;
  onClose: () => void;
}

export function InvestigationDetailContent({
  investigationDetail,
  clueWorkspace,
  clueWorkspaceLoading,
  selectedEvidenceId,
  projectedPersonDisplayName,
  onOpenLinkedCustomer,
  onOpenLinkedInvestigation,
  onOpenLinkedCase,
  onOpenLinkedNotary,
  onSelectEvidence,
  onEditEvidence,
  onDownloadFile,
  onDeleteEvidence,
}: InvestigationDetailContentProps) {
  const showEvidence = Boolean(
    investigationDetail &&
      ["待取证", "已取证", "待公证", "已转案件"].includes(investigationDetail.status),
  );
  return <>
      <ClueDetailHeader
        investigationDetail={investigationDetail}
        projectedPersonDisplayName={projectedPersonDisplayName}
        onOpenLinkedCustomer={onOpenLinkedCustomer}
        onOpenLinkedInvestigation={onOpenLinkedInvestigation}
        onOpenLinkedCase={onOpenLinkedCase}
        onOpenLinkedNotary={onOpenLinkedNotary}
      />
      {investigationDetail?.module === "clue" && (
        <ClueEvidencePanel
          clueWorkspace={clueWorkspace}
          clueWorkspaceLoading={clueWorkspaceLoading}
          showEvidence={showEvidence}
          selectedEvidenceId={selectedEvidenceId}
          onSelectEvidence={onSelectEvidence}
          onEditEvidence={onEditEvidence}
          onDeleteEvidence={onDeleteEvidence}
          onDownloadFile={onDownloadFile}
        />
      )}
  </>;
}

export default function InvestigationDetailModal(props: InvestigationDetailModalProps) {
  return <Modal
    width={1040}
    open={props.open}
    title={`调查详情：${props.investigationDetail?.serial_no || ""}`}
    footer={<Button onClick={props.onClose}>关闭</Button>}
    onCancel={props.onClose}
  >
    <InvestigationDetailContent {...props} />
  </Modal>;
}
