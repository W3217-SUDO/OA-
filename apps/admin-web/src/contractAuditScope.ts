type PendingContractRecord = {
  status: string;
  data?: { current_approver?: unknown };
};

export const filterPendingContractApprovals = <T extends PendingContractRecord>(
  records: readonly T[],
  username: string,
): T[] => {
  const currentUsername = String(username || "").trim();
  if (!currentUsername) return [];
  return records.filter(
    (record) =>
      record.status === "审批中" &&
      String(record.data?.current_approver || "").trim() === currentUsername,
  );
};
