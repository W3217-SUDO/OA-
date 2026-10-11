import { originalFinanceRoutes } from "../config/routeMetadata";

export type FinanceQueryResource =
  | "feeRes" | "contractPaymentRes" | "invoiceRes" | "refundRes" | "caseRes"
  | "customerRes" | "incomingRes" | "txRes" | "recRes" | "sumRes" | "profileRes"
  | "settlementRes" | "refundReviewRes" | "paymentPackageRes" | "internalDetailRes"
  | "invoiceMineRes" | "invoicePendingRes" | "invoiceCompanyRes" | "invoiceUnissuedRes"
  | "generalSettlementRes" | "archiveSettlementRes" | "feeQueryRes" | "peopleRes";

// 只声明当前页面的真实依赖；未加载资源不生成空响应，也不覆盖其他页面的数据。
export function financeRouteResources(route: string, tab: string, source?: string): FinanceQueryResource[] {
  const resources: FinanceQueryResource[] = [
    "feeRes", "invoiceRes", "caseRes", "customerRes", "profileRes", "peopleRes",
  ];
  if (route !== "finance-payment-query" && (!source || source === "fees")) resources.push("contractPaymentRes");
  if (!originalFinanceRoutes.includes(route)) {
    resources.push("refundRes", "sumRes", "incomingRes");
    if (tab === "transactions") resources.push("txRes");
    if (tab === "reconcile") resources.push("recRes");
    return resources;
  }
  if (source === "incoming") resources.push("incomingRes");
  if (!source || source === "fees" || source === "feeQuery") resources.push("txRes");
  if (source === "paymentPackages") resources.push("paymentPackageRes");
  if (source === "settlements") resources.push("settlementRes");
  if (source === "refundReviewFees") resources.push("refundReviewRes");
  if (source === "generalSettlements") resources.push("generalSettlementRes");
  if (source === "archiveSettlements") resources.push("archiveSettlementRes");
  if (route === "finance-internal-detail" || route === "finance-internal-company")
    resources.push("internalDetailRes");
  if (route === "finance-invoice-mine") resources.push("invoiceMineRes");
  if (route === "finance-invoice-pending") resources.push("invoicePendingRes");
  if (route === "finance-invoice-company") resources.push("invoiceCompanyRes");
  if (source === "unissuedFees") resources.push("invoiceUnissuedRes");
  if (route === "finance-fee-query" || route === "finance-refund")
    resources.push("feeQueryRes");
  return resources;
}

export async function loadFinanceQueryResources<T extends Record<FinanceQueryResource, () => Promise<any>>>(
  resources: readonly FinanceQueryResource[], loaders: T,
): Promise<Partial<{ [K in FinanceQueryResource]: Awaited<ReturnType<T[K]>> }>> {
  const entries = await Promise.all(resources.map(async (key) => [key, await loaders[key]()] as const));
  return Object.fromEntries(entries) as Partial<{ [K in FinanceQueryResource]: Awaited<ReturnType<T[K]>> }>;
}
