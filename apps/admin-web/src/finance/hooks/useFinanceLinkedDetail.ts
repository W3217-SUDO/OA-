import { message } from "antd";
import { useEffect, useRef } from "react";
import { consumeBusinessRecordDetailTarget } from "../../businessRecordDetailNavigation";
import { financeErrorDetail, financeErrorMessageText } from "../financeErrors";
import { loadInvoiceApplicationContext, loadInvoiceRecord } from "../services/invoicesActions";
import { loadRefundApplicantProfile } from "../services/refundsActions";
import { loadFinanceLinkedRecord, type FinanceLinkedRecord } from "../services/workflowActions";
import type { Fee, FinanceFlow } from "../types";

export type FinanceLinkedDetailResult =
  | { kind: "invoice-creation"; customerRows: Fee[]; candidateRows: Fee[]; sourceFee: Fee | undefined; customerDefaults: Record<string, unknown> }
  | { kind: "refund-creation"; record: FinanceLinkedRecord; applicantName: string | undefined }
  | { kind: "fee-detail"; record: Fee }
  | { kind: "invoice-detail"; record: FinanceFlow }
  | { kind: "refund-detail"; record: Fee };

/** 一次性消费财务深链，路由切换或卸载后不再分派旧请求结果。 */
export function useFinanceLinkedDetail(initialView: string, onResult: (result: FinanceLinkedDetailResult) => void): void {
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  useEffect(() => {
    const target = consumeBusinessRecordDetailTarget(["finance", "invoice", "refund", "finance_package", "finance_settlement", "finance_archive_settlement"]);
    if (!target) return;
    const controller = new AbortController();
    void (async () => {
      try {
        const record = await loadFinanceLinkedRecord(target.id, controller.signal);
        if (controller.signal.aborted) return;
        if (record.module === "finance" && target.action === "create_invoice") {
          const context = await loadInvoiceApplicationContext(record, controller.signal);
          if (controller.signal.aborted) return;
          const customerRows = context.customer_record ? [context.customer_record] : [];
          const candidateRows = context.items || [];
          const sourceFee = candidateRows.find((fee) => Number(fee.id) === Number(record.id));
          onResultRef.current({ kind: "invoice-creation", customerRows, candidateRows, sourceFee, customerDefaults: context.customer_defaults || {} });
          return;
        }
        if (record.module === "finance" && target.action === "create_refund") {
          const applicantName = await loadRefundApplicantProfile(controller.signal);
          if (!controller.signal.aborted) onResultRef.current({ kind: "refund-creation", record, applicantName });
          return;
        }
        if (["finance", "finance_package", "finance_settlement", "finance_archive_settlement"].includes(record.module)) {
          onResultRef.current({ kind: "fee-detail", record });
        } else if (record.module === "invoice") {
          const invoice = await loadInvoiceRecord(record.id, controller.signal);
          if (!controller.signal.aborted) onResultRef.current({ kind: "invoice-detail", record: invoice });
        } else if (record.module === "refund") {
          onResultRef.current({ kind: "refund-detail", record });
        } else {
          throw new Error("关联记录不是可查看的财务业务");
        }
      } catch (error: unknown) {
        if (!controller.signal.aborted) message.error(financeErrorDetail(error) || financeErrorMessageText(error) || "费用详情加载失败");
      }
    })();
    return () => controller.abort();
  }, [initialView]);
}
