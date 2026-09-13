import type { ContractPaymentCandidate } from "./types";
import type { Key } from "react";

export function contractPaymentCandidateKey(candidate: Pick<ContractPaymentCandidate, "case_fee_id" | "contract_object_id">): string {
  if (candidate.case_fee_id != null) return `fee:${candidate.case_fee_id}`;
  return `object:${candidate.contract_object_id ?? "unknown"}`;
}

export function findContractPaymentCandidate(
  candidates: ContractPaymentCandidate[],
  key: Key,
): ContractPaymentCandidate | undefined {
  return candidates.find((candidate) => contractPaymentCandidateKey(candidate) === String(key));
}
