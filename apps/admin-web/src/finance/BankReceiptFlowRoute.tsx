import { useEffect, useState } from "react";
import { Select } from "antd";
import { BANK_FLOW_UPLOADED_EVENT, receiptBankCode } from "./bankReceiptScope";
import { NewFlowLines, type BankPageFlowStatus } from "./BankFlowPage";
import { FinanceOriginalRoutesView, type FinanceOriginalRoutesViewProps } from "./FinanceOriginalRoutesView";
import type { FinanceScope } from "./types";

// 279951（审核部 10-29 提、11-02 确认）：回款(工行/中信/中行/招商) 和旧系统一样，上传的流水先留在本页“未导入”，
// 勾选点“导入”才进回款管理，“删除”只删未导入的。和“银行原始流水”同一张表、同一套接口，不会重复生成到账单。
// 入库状态选“已导入”时显示本页原来的到账列表（已进回款管理的流水）。
export function BankReceiptFlowRoute({ routesView, financeScope }: {
  routesView: FinanceOriginalRoutesViewProps;
  financeScope: FinanceScope;
}) {
  const bank = receiptBankCode(routesView.initialView);
  const query = routesView.originalQueryView;
  const [status, setStatus] = useState<BankPageFlowStatus>("未导入");

  useEffect(() => setStatus("未导入"), [bank]);
  useEffect(() => {
    const uploaded = () => setStatus("未导入");
    window.addEventListener(BANK_FLOW_UPLOADED_EVENT, uploaded);
    return () => window.removeEventListener(BANK_FLOW_UPLOADED_EVENT, uploaded);
  }, []);

  // “查看待确认”（未分中心）等不能上传的状态仍走原列表。
  if (!bank || !query.routeConfig?.upload || financeScope === "unclassified") {
    return <FinanceOriginalRoutesView {...routesView} />;
  }
  if (status === "已导入") {
    const statusPicker = (
      <span className="finance-bank-flow-status">
        入库状态{" "}
        <Select
          size="middle"
          style={{ width: 110 }}
          value="已导入"
          onChange={(value: BankPageFlowStatus) => setStatus(value)}
          options={[
            { value: "未导入", label: "未导入" },
            { value: "已导入", label: "已导入" },
            { value: "已删除", label: "已删除" },
          ]}
        />
      </span>
    );
    return <FinanceOriginalRoutesView {...routesView} originalQueryView={{ ...query, extraActions: statusPicker }} />;
  }
  return (
    <section className="finance-original-panel">
      <input
        ref={query.bankUploadRef}
        hidden
        type="file"
        onChange={(event) => void query.onImportBankStatement(event.target.files?.[0])}
      />
      <div className="finance-original-title"><h5>{query.title}</h5></div>
      <NewFlowLines
        key={`${bank}-${status}`}
        financeScope={financeScope}
        fixedBank={bank}
        initialStatus={status}
        onUpload={() => query.bankUploadRef.current?.click()}
        onShowImported={() => setStatus("已导入")}
      />
    </section>
  );
}
