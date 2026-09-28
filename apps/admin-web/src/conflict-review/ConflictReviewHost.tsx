import { useEffect, useState } from "react";
import { Modal } from "antd";
import { ConflictReviewPanel } from "./ConflictReviewPanel";
import { CONFLICT_REVIEW_OPEN_EVENT } from "./events";
import type { ConflictReviewOpenDetail } from "./events";

export function ConflictReviewHost() {
  const [reviewId, setReviewId] = useState<number | null>(null);
  useEffect(() => {
    const listener = (event: Event) => setReviewId((event as CustomEvent<ConflictReviewOpenDetail>).detail.reviewId);
    window.addEventListener(CONFLICT_REVIEW_OPEN_EVENT, listener);
    return () => window.removeEventListener(CONFLICT_REVIEW_OPEN_EVENT, listener);
  }, []);
  return <Modal open={reviewId !== null} title="利益冲突审查与反馈" width={960} zIndex={1800} footer={null} onCancel={() => setReviewId(null)} destroyOnHidden styles={{ body: { maxHeight: "75vh", overflowY: "auto" } }}>
    {reviewId !== null && <ConflictReviewPanel key={reviewId} reviewId={reviewId} />}
  </Modal>;
}
