const listValue = (value) =>
  Array.isArray(value) ? value.join(",") : String(value || "");

const internalFeePageIdByRoute = {
  "finance-internal-archive": "5001004005",
};

export const internalFeeExportRequestParams = ({
  scope = "company",
  query = {},
  ids = [],
  initialView = "",
}) => {
  const paidRange = query.routeField8;
  const requestedPaymentStatus =
    query.routeField7 && query.routeField7 !== "全部"
      ? String(query.routeField7)
      : "";
  const params = {
    scope,
    case_no: query.routeField0 || "",
    handling_lawyer: query.routeField1 || "",
    assistant: query.routeField2 || "",
    source_person: query.routeField3 || "",
    customer: query.routeField4 || "",
    customer_manager: query.routeField5 || "",
    investigator: query.routeField6 || "",
    payment_status: ["已付", "未付"].includes(requestedPaymentStatus)
      ? requestedPaymentStatus
      : "",
    paid_from: paidRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
    paid_to: paidRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
    payee: query.routeField9 || "",
    case_stages: listValue(query.routeField10),
    fee_types: listValue(query.routeField11),
  };
  const pageId = internalFeePageIdByRoute[initialView] || "";
  if (pageId) params.page_id = pageId;
  const uniqueIds = [...new Set(ids.map(Number).filter((id) => Number.isInteger(id) && id > 0))];
  if (uniqueIds.length) params.ids = uniqueIds.join(",");
  return params;
};
