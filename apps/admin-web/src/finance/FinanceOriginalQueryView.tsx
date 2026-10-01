import type { ReactNode, RefObject } from "react";
import { Button } from "antd";
import { PlusOutlined, ReloadOutlined, UploadOutlined } from "@ant-design/icons";
import type { ContractPaymentSourceState, OriginalRouteConfig } from "./types";

export interface FinanceOriginalQueryViewProps {
  initialView: string;
  originalKind: string;
  title: string;
  sourceNotice: ReactNode;
  fields: ReactNode;
  routeConfig: OriginalRouteConfig | undefined;
  contractPaymentSource: ContractPaymentSourceState;
  bankUploadRef: RefObject<HTMLInputElement | null>;
  onImportBankStatement: (file: File | undefined) => Promise<void>;
  onSubmit: () => void;
  onClear: () => void;
  onRefresh: () => Promise<void>;
  originalQuery: Record<string, unknown>;
  paymentPackageMeta: { page: number; pageSize: number };
  onLoadPaymentPackages: (query: Record<string, unknown>, page: number, pageSize: number) => Promise<unknown>;
  onOpenPaymentPackageEditor: () => void;
}

export function FinanceOriginalQueryView({
  initialView, originalKind, title, sourceNotice, fields, routeConfig,
  contractPaymentSource, bankUploadRef, onImportBankStatement, onSubmit, onClear,
  onRefresh, originalQuery, paymentPackageMeta, onLoadPaymentPackages,
  onOpenPaymentPackageEditor,
}: FinanceOriginalQueryViewProps) {
  const refreshRoutes = [
    "finance-payment-mine", "finance-internal-mine", "finance-payment-audit",
    "finance-payment-waiting", "finance-payment-writeoff",
  ];
  const clearRoutes = [
    "finance-payment-writeoff", "finance-settlement-pending",
    "finance-settlement-audit", "finance-settlement-payment",
    "finance-settlement-refused",
  ];
  return (
    <>
      <input
        ref={bankUploadRef}
        hidden
        type="file"
        onChange={(event) => void onImportBankStatement(event.target.files?.[0])}
      />
      <div className="finance-original-title"><h5>{title}</h5></div>
      {sourceNotice}
      <div className="finance-original-query-grid">{fields}</div>
      <div className="finance-original-query-actions">
        <Button type="primary" disabled={contractPaymentSource.active} onClick={onSubmit}>
          查询
        </Button>
        {refreshRoutes.includes(initialView) && (
          <Button
            icon={<ReloadOutlined />}
            disabled={contractPaymentSource.active}
            onClick={() => void onRefresh()}
          >
            刷新
          </Button>
        )}
        {initialView === "finance-payment-package-manage" && (
          <>
            <Button icon={<ReloadOutlined />} onClick={() => void onLoadPaymentPackages(
              originalQuery, paymentPackageMeta.page, paymentPackageMeta.pageSize,
            )}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={onOpenPaymentPackageEditor}>
              新增付款包
            </Button>
          </>
        )}
        {routeConfig?.upload && (
          <Button icon={<UploadOutlined />} onClick={() => bankUploadRef.current?.click()}>
            上传
          </Button>
        )}
        {(originalKind === "fee-query" || routeConfig?.clear || clearRoutes.includes(initialView)) && (
          <Button onClick={onClear}>清空</Button>
        )}
      </div>
    </>
  );
}
