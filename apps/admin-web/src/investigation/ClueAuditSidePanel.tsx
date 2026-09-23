import { useRef, useState } from "react";
import { Button } from "antd";
import type { Row } from "./types";
import { InvestigationDetailContent } from "./InvestigationDetailModal";
import type { InvestigationDetailContentProps } from "./InvestigationDetailModal";
import ClueReviewModal from "./ClueReviewModal";

interface ClueAuditSidePanelProps extends InvestigationDetailContentProps {
  clueReviewing: Row | null;
  clueReviewForm: any;
  onClose: () => void;
  onReview: () => void;
  onOpenClue: (serialNo: string) => void;
  onOpenCase: (serialNo: string) => void;
}

export default function ClueAuditSidePanel(props: ClueAuditSidePanelProps) {
  const [width, setWidth] = useState(640);
  const panelRef = useRef<HTMLElement>(null);
  const dragging = useRef(false);

  const resize = (clientX: number) => {
    const container = panelRef.current?.parentElement;
    if (!container) return;
    const bounds = container.getBoundingClientRect();
    const maxWidth = Math.max(400, bounds.width - 360);
    setWidth(Math.max(400, Math.min(maxWidth, bounds.right - clientX)));
  };

  return <aside ref={panelRef} className="investigation-audit-side" style={{ width }} aria-label="线索信息">
    <div className="investigation-audit-resize" role="separator" aria-label="调整线索信息面板宽度"
      aria-orientation="vertical" aria-valuemin={400} aria-valuemax={1600} aria-valuenow={width} tabIndex={0}
      onPointerDown={(event) => {
        dragging.current = true;
        event.currentTarget.setPointerCapture(event.pointerId);
        event.preventDefault();
      }}
      onPointerMove={(event) => { if (dragging.current) resize(event.clientX); }}
      onPointerUp={(event) => {
        dragging.current = false;
        event.currentTarget.releasePointerCapture(event.pointerId);
      }}
      onPointerCancel={() => { dragging.current = false; }}
      onKeyDown={(event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        event.preventDefault();
        const bounds = panelRef.current?.parentElement?.getBoundingClientRect();
        if (bounds) resize(bounds.right - width + (event.key === "ArrowLeft" ? -24 : 24));
      }}
    />
    <div className="investigation-audit-side-header">
      <strong>线索信息：{props.investigationDetail?.serial_no}</strong>
      <Button size="small" onClick={props.onClose}>关闭</Button>
    </div>
    <div className="investigation-audit-side-body">
      <InvestigationDetailContent {...props} />
      {props.clueReviewing?.id === props.investigationDetail?.id && <ClueReviewModal
        embedded
        open
        clueReviewing={props.clueReviewing}
        clueReviewForm={props.clueReviewForm}
        projectedPersonDisplayName={props.projectedPersonDisplayName}
        onOk={props.onReview}
        onCancel={props.onClose}
        onOpenClue={props.onOpenClue}
        onOpenCase={props.onOpenCase}
      />}
    </div>
  </aside>;
}
