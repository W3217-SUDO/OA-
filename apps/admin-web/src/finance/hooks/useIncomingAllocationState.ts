import { useState } from "react";
import type { AllocationCandidate, IncomingPayment } from "../types";

/** 回款分配的筛选、金额、选择及弹窗状态只在分配流程内维护。 */
export function useIncomingAllocationState() {
  const [allocateTarget, setAllocateTarget] = useState<IncomingPayment | null>(null);
  const [allocationCandidates, setAllocationCandidates] = useState<AllocationCandidate[]>([]);
  const [allocationLoading, setAllocationLoading] = useState(false);
  const [selectedAllocationKeys, setSelectedAllocationKeys] = useState<(string | number)[]>([]);
  const [allocationAmounts, setAllocationAmounts] = useState<Record<string, number>>({});
  const [allocationKeyword, setAllocationKeyword] = useState("");
  const [allocationStage, setAllocationStage] = useState("");
  const [allocationFeeType, setAllocationFeeType] = useState("");
  const [allocationComment, setAllocationComment] = useState("");
  const [allocationValidationError, setAllocationValidationError] = useState("");

  const filteredAllocationCandidates = allocationCandidates.filter((row) => {
    const needle = allocationKeyword.trim().toLocaleLowerCase();
    const keywordMatched = !needle || [
      row.case_no,
      row.case_title,
      row.plaintiff,
      row.defendant,
      row.contract_no,
    ].some((value) => String(value || "").toLocaleLowerCase().includes(needle));
    return keywordMatched
      && (!allocationStage || row.case_stage === allocationStage)
      && (!allocationFeeType || row.fee_type === allocationFeeType);
  });

  const closeIncomingAllocation = () => {
    setAllocateTarget(null);
    setAllocationCandidates([]);
    setSelectedAllocationKeys([]);
    setAllocationValidationError("");
  };
  const clearAllocationFilters = () => {
    setAllocationKeyword("");
    setAllocationStage("");
    setAllocationFeeType("");
  };
  const setAllocationAmount = (key: string, value: number) => {
    setAllocationAmounts((current) => ({ ...current, [key]: value }));
  };

  return {
    allocateTarget,
    setAllocateTarget,
    allocationCandidates,
    setAllocationCandidates,
    filteredAllocationCandidates,
    allocationLoading,
    setAllocationLoading,
    selectedAllocationKeys,
    setSelectedAllocationKeys,
    allocationAmounts,
    setAllocationAmounts,
    allocationKeyword,
    setAllocationKeyword,
    allocationStage,
    setAllocationStage,
    allocationFeeType,
    setAllocationFeeType,
    allocationComment,
    setAllocationComment,
    allocationValidationError,
    setAllocationValidationError,
    closeIncomingAllocation,
    clearAllocationFilters,
    setAllocationAmount,
  };
}
