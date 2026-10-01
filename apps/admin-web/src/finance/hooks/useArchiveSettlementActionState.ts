import { useState } from "react";
import type { ArchiveSettlementTarget } from "../types";

/** 归档费结算审核、回滚和重提的弹窗状态独立于列表查询状态。 */
export function useArchiveSettlementActionState() {
  const [archiveSettlementReviewTargets, setArchiveSettlementReviewTargets] = useState<ArchiveSettlementTarget[]>([]);
  const [archiveSettlementReviewApproved, setArchiveSettlementReviewApproved] = useState(true);
  const [archiveSettlementReviewComment, setArchiveSettlementReviewComment] = useState("");
  const [archiveSettlementRollbackTargets, setArchiveSettlementRollbackTargets] = useState<ArchiveSettlementTarget[]>([]);
  const [archiveSettlementRollbackComment, setArchiveSettlementRollbackComment] = useState("");
  const [archiveSettlementReapplyTargets, setArchiveSettlementReapplyTargets] = useState<ArchiveSettlementTarget[]>([]);
  const [archiveSettlementReapplyComment, setArchiveSettlementReapplyComment] = useState("");

  const closeArchiveSettlementReview = () => {
    setArchiveSettlementReviewTargets([]);
    setArchiveSettlementReviewComment("");
  };
  const closeArchiveSettlementRollback = () => {
    setArchiveSettlementRollbackTargets([]);
    setArchiveSettlementRollbackComment("");
  };
  const closeArchiveSettlementReapply = () => {
    setArchiveSettlementReapplyTargets([]);
    setArchiveSettlementReapplyComment("");
  };

  return {
    archiveSettlementReviewTargets, setArchiveSettlementReviewTargets,
    archiveSettlementReviewApproved, setArchiveSettlementReviewApproved,
    archiveSettlementReviewComment, setArchiveSettlementReviewComment,
    archiveSettlementRollbackTargets, setArchiveSettlementRollbackTargets,
    archiveSettlementRollbackComment, setArchiveSettlementRollbackComment,
    archiveSettlementReapplyTargets, setArchiveSettlementReapplyTargets,
    archiveSettlementReapplyComment, setArchiveSettlementReapplyComment,
    closeArchiveSettlementReview, closeArchiveSettlementRollback, closeArchiveSettlementReapply,
  };
}
