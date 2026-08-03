export const refundPageSizeOptions = [10, 15, 20, 50, 100, 200];
export const refundStatusOptions = ["全部", "草稿", "待审批", "退款办理中", "已退款", "已驳回"];

const refundFilterParams = (status = "", group = "", scope = "company") => ({
  ...(status && status !== "全部" ? { status } : {}),
  ...(group ? { group } : {}),
  scope,
});

export const refundRequestParams = (
  page,
  pageSize,
  status = "",
  group = "",
  scope = "company",
) => ({
  page,
  page_size: pageSize,
  ...refundFilterParams(status, group, scope),
});

export const refundListRequest = (page, pageSize, status = "", group = "", scope = "company") => ({
  url: "/finance/refunds/query",
  params: refundRequestParams(page, pageSize, status, group, scope),
});

export const refundExportRequestParams = (status = "", group = "", scope = "company") =>
  refundFilterParams(status, group, scope);

export const refundSelectedExportRequestParams = (
  ids,
  status = "",
  group = "",
  scope = "company",
) => ({
  ids: [...new Set(ids)].join(","),
  ...refundFilterParams(status, group, scope),
});

export const refundAmountUpdateRequest = (id, amount, comment = "") => ({
  url: `/finance/refunds/${id}/amount`,
  method: "patch",
  body: { amount, comment },
});

export const refundBatchStatusRequest = (ids, status, comment = "") => ({
  url: "/finance/refunds/status",
  method: "post",
  body: { ids: [...new Set(ids)], status, comment },
});

export const refundListErrorMessage = (error) =>
  error?.response?.data?.detail || "退款列表查询出错.";

export const refundLoadFailure = (state, error) => ({
  state,
  message: refundListErrorMessage(error),
});

export const normalizeRefundResponse = (data, fallbackPage = 1, fallbackPageSize = 15) => ({
  items: Array.isArray(data?.items) ? data.items : [],
  total: Number(data?.total || 0),
  page: Number(data?.page || fallbackPage),
  pageSize: Number(data?.page_size || fallbackPageSize),
});

// The legacy CaseFee partial renders the refund progress separately from the
// refund application workflow status. Keep that distinction when a fee row is
// displayed in the query/print tables.
export const caseFeeRefundStatusLabel = (row) => {
  const data = row?.data || row || {};
  const status = String(
    data.refund_status ?? data.refundStatus ?? row?.refund_status ?? "",
  );
  if (status === "R100") return "\u4e0d\u518d\u529e\u7406";
  const requested = Number(
    data.refund_requested_amount ?? data.refund_amount ?? 0,
  );
  const refunded = Number(data.refunded_amount ?? 0);
  if (requested > 0 && refunded >= requested) return "\u5df2\u9000";
  if (requested > 0 || refunded > 0) return "\u672a\u9000";
  return "\u672a\u9000";
};
