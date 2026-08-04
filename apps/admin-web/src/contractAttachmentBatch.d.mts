export type ContractAttachmentDeleteResult =
  | { id: number; status: "fulfilled" }
  | { id: number; status: "rejected"; reason?: unknown };

export declare const buildContractAttachmentDeletePlan: (ids?: readonly (number | string | bigint)[]) => number[];
export declare const summarizeContractAttachmentDeleteResults: (
  results?: readonly ContractAttachmentDeleteResult[],
) => { deleted: number; failed: Array<{ id: number; message: string }> };
