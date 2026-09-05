import { Modal, Button } from "antd";
import type { Row, ClueWorkspace, ClueEvidenceRow, Attachment } from "./types";
import ClueDetailHeader from "./ClueDetail/ClueDetailHeader";
import ClueEvidencePanel from "./ClueDetail/ClueEvidencePanel";

interface InvestigationDetailModalProps {
  open: boolean;
  investigationDetail: Row | null;
  clueWorkspace: ClueWorkspace | null;
  clueWorkspaceLoading: boolean;
  selectedEvidenceId: number | null;
  projectedPersonDisplayName: (displayName: unknown, username: unknown) => string;
  onClose: () => void;
  onOpenLinkedCustomer: (name: string) => void;
  onOpenLinkedInvestigation: (serialNo: string, module: "investigation" | "clue" | "task") => void;
  onOpenLinkedCase: (caseNo: string) => void;
  onOpenLinkedNotary: (recordId?: number, certificateNo?: string) => void;
  onSelectEvidence: (id: number | null) => void;
  onEditEvidence: () => void;
  onDownloadFile: (file: Attachment) => void;
  onDeleteEvidence: () => void;
}

export default function InvestigationDetailModal({
  open,
  investigationDetail,
  clueWorkspace,
  clueWorkspaceLoading,
  selectedEvidenceId,
  projectedPersonDisplayName,
  onClose,
  onOpenLinkedCustomer,
  onOpenLinkedInvestigation,
  onOpenLinkedCase,
  onOpenLinkedNotary,
  onSelectEvidence,
  onEditEvidence,
  onDownloadFile,
  onDeleteEvidence,
}: InvestigationDetailModalProps) {
  return (
    <Modal
      width={1040}
      open={open}
      title={`调查详情：${investigationDetail?.serial_no || ""}`}
      footer={<Button onClick={onClose}>关闭</Button>}
      onCancel={onClose}
    >
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
          selectedEvidenceId={selectedEvidenceId}
          onSelectEvidence={onSelectEvidence}
          onEditEvidence={onEditEvidence}
          onDeleteEvidence={onDeleteEvidence}
          onDownloadFile={onDownloadFile}
        />
      )}
    </Modal>
  );
}
