const messageFromReason = (reason) => String(
  reason?.response?.data?.detail
  || reason?.response?.data?.message
  || reason?.message
  || "合同附件删除失败",
).trim() || "合同附件删除失败";

export const buildContractAttachmentDeletePlan = (ids = []) => [...new Set(
  ids.map((value) => Number(value)).filter((value) => Number.isFinite(value) && value > 0),
)];

export const summarizeContractAttachmentDeleteResults = (results = []) => ({
  deleted: results.filter((result) => result?.status === "fulfilled").length,
  failed: results
    .filter((result) => result?.status === "rejected")
    .map((result) => ({ id: Number(result.id || 0), message: messageFromReason(result.reason) })),
});
