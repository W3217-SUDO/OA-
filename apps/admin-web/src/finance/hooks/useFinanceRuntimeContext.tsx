import { useMemo } from "react";
import { createFinanceActionGate } from "../../financeActionGate.mjs";
import { createLatestRequestGuard } from "../../financeRefundHelpers.mjs";
import { initialSessionUser, parseContractPaymentSource } from "../constants";
export function useFinanceRuntimeContext(initialView: string) {
    const sessionUser = useMemo(initialSessionUser, []);
    const financeActionGates = useMemo(() => ({
        archiveSettlement: createFinanceActionGate(),
        generalSettlement: createFinanceActionGate(),
        paymentPackage: createFinanceActionGate(),
    }), []);
    const refundRequestGuard = useMemo(() => createLatestRequestGuard(), []);
    const invoiceDetailRequestGuard = useMemo(() => createLatestRequestGuard(), []);
    const refundDetailRequestGuard = useMemo(() => createLatestRequestGuard(), []);
    const contractPaymentSourceSearch = initialView === "finance-payment-mine" && typeof window !== "undefined"
        ? window.location.search
        : "";
    const contractPaymentSource = useMemo(() => parseContractPaymentSource(initialView, contractPaymentSourceSearch), [initialView, contractPaymentSourceSearch]);
    return { sessionUser, financeActionGates, refundRequestGuard, invoiceDetailRequestGuard, refundDetailRequestGuard, contractPaymentSourceSearch, contractPaymentSource };
}
