import { useState } from "react";
import type { Fee } from "../types";

/** 普通结算申请、审核、付款和重提的弹窗状态独立于列表查询状态。 */
export function useGeneralSettlementActionState() {
  const [generalSettlementReviewTargets, setGeneralSettlementReviewTargets] = useState<Fee[]>([]);
  const [generalSettlementReviewApproved, setGeneralSettlementReviewApproved] = useState(true);
  const [generalSettlementReviewComment, setGeneralSettlementReviewComment] = useState("");
  const [generalSettlementApplyTargets, setGeneralSettlementApplyTargets] = useState<(string | number)[]>([]);
  const [generalSettlementApplyComment, setGeneralSettlementApplyComment] = useState("");
  const [generalSettlementPaymentTargets, setGeneralSettlementPaymentTargets] = useState<Fee[]>([]);
  const [generalSettlementPaymentAction, setGeneralSettlementPaymentAction] = useState<"paid" | "rollback">("paid");
  const [generalSettlementPaymentComment, setGeneralSettlementPaymentComment] = useState("");
  const [generalSettlementReapplyTargets, setGeneralSettlementReapplyTargets] = useState<Fee[]>([]);
  const [generalSettlementReapplyComment, setGeneralSettlementReapplyComment] = useState("");

  const closeGeneralSettlementApply = () => {
    setGeneralSettlementApplyTargets([]);
    setGeneralSettlementApplyComment("");
  };
  const closeGeneralSettlementReview = () => {
    setGeneralSettlementReviewTargets([]);
    setGeneralSettlementReviewComment("");
  };
  const closeGeneralSettlementPayment = () => {
    setGeneralSettlementPaymentTargets([]);
    setGeneralSettlementPaymentComment("");
  };
  const closeGeneralSettlementReapply = () => {
    setGeneralSettlementReapplyTargets([]);
    setGeneralSettlementReapplyComment("");
  };

  return {
    generalSettlementReviewTargets, setGeneralSettlementReviewTargets,
    generalSettlementReviewApproved, setGeneralSettlementReviewApproved,
    generalSettlementReviewComment, setGeneralSettlementReviewComment,
    generalSettlementApplyTargets, setGeneralSettlementApplyTargets,
    generalSettlementApplyComment, setGeneralSettlementApplyComment,
    generalSettlementPaymentTargets, setGeneralSettlementPaymentTargets,
    generalSettlementPaymentAction, setGeneralSettlementPaymentAction,
    generalSettlementPaymentComment, setGeneralSettlementPaymentComment,
    generalSettlementReapplyTargets, setGeneralSettlementReapplyTargets,
    generalSettlementReapplyComment, setGeneralSettlementReapplyComment,
    closeGeneralSettlementApply, closeGeneralSettlementReview,
    closeGeneralSettlementPayment, closeGeneralSettlementReapply,
  };
}
