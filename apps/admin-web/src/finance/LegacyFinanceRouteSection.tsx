import { useEffect, useState } from "react";
import { Alert, Collapse, message } from "antd";
import { api } from "../api";
import { LegacyHistoryPanel } from "./LegacyHistoryPanel";
import type { LegacyFinanceRecord, LegacyFinanceSummary } from "./types";

type LegacyKind = LegacyFinanceRecord["record_kind"];

function routeHistoryKinds(route: string): LegacyKind[] {
  if (route.startsWith("finance-receipts-")) return ["ar_payment"];
  if (route === "finance-payment-package-manage" || route === "finance-payment-writeoff") {
    return ["ap_packing", "ap_payment"];
  }
  if (route.startsWith("finance-payment-")) return ["ap_payment", "ap_packing"];
  if (route.startsWith("finance-invoice-")) return ["invoice"];
  if (route === "finance-internal-detail" || route === "finance-internal-company") {
    return ["internal_fee", "internal_payment", "internal_packing"];
  }
  if (route === "finance-internal-writeoff" || route === "finance-internal-done") {
    return ["internal_packing", "internal_payment", "internal_fee"];
  }
  if (route.startsWith("finance-internal-")) {
    return ["internal_payment", "internal_fee", "internal_packing"];
  }
  if (route.startsWith("finance-settlement-") || route.startsWith("finance-archive-fee-")) {
    return ["case_fee", "internal_fee", "internal_payment"];
  }
  if (["finance-query", "finance-fee-query", "finance-refund"].includes(route)) {
    return ["case_fee", "internal_fee"];
  }
  return [];
}

const emptySummary: LegacyFinanceSummary = {
  records: [],
  allocations: [],
  audits: [],
  orphan_allocations: [],
  orphan_files: [],
  orphan_audits: [],
  amount_visible: false,
  read_only: true,
};

export function LegacyFinanceRouteSection({ route }: { route: string }) {
  const kinds = routeHistoryKinds(route);
  const [kind, setKind] = useState<LegacyKind | "">(kinds[0] || "");
  const [rows, setRows] = useState<LegacyFinanceRecord[]>([]);
  const [meta, setMeta] = useState({ page: 1, pageSize: 30, total: 0 });
  const [summary, setSummary] = useState<LegacyFinanceSummary>(emptySummary);
  const [keyword, setKeyword] = useState("");
  const [statusCode, setStatusCode] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<LegacyFinanceRecord | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    if (!kinds.length) return;
    let current = true;
    setLoading(true);
    void api.get("/finance/legacy-history", {
      params: {
        record_kind: kind,
        status_code: statusCode.trim(),
        keyword: keyword.trim(),
        include_inactive: includeInactive,
        page: meta.page,
        page_size: meta.pageSize,
      },
    }).then(({ data }) => {
      if (!current) return;
      setRows(data.items || []);
      setMeta((previous) => ({
        ...previous,
        total: Number(data.total || 0),
      }));
      setSummary({ ...emptySummary, amount_visible: data.amount_visible !== false });
    }).catch((error) => {
      if (current) message.error(error?.response?.data?.detail || "历史财务记录加载失败");
    }).finally(() => {
      if (current) setLoading(false);
    });
    return () => { current = false; };
  }, [route, kind, includeInactive, meta.page, meta.pageSize, revision]);

  if (!kinds.length) return null;

  const load = (page = meta.page, pageSize = meta.pageSize) => {
    setMeta((previous) => ({ ...previous, page, pageSize }));
    setRevision((previous) => previous + 1);
  };

  const openDetail = async (recordId: number) => {
    setDetailLoading(true);
    setDetail(null);
    try {
      const { data } = await api.get(`/finance/legacy-history/${recordId}`);
      setDetail(data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "历史财务明细加载失败");
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <Collapse
      style={{ marginTop: 12 }}
      defaultActiveKey={["history"]}
      items={[{
        key: "history",
        label: `旧系统历史记录（只读，共 ${meta.total} 条）`,
        children: <>
          <Alert
            type="info"
            showIcon
            title="历史记录与现行审批数据分别显示"
            description="可查看旧系统原始财务记录及关联明细；历史记录不会进入现行审批、付款或开票操作。"
          />
          <LegacyHistoryPanel
            compact
            availableKinds={kinds}
            rows={rows}
            loading={loading}
            meta={meta}
            summary={summary}
            detail={detail}
            detailLoading={detailLoading}
            keyword={keyword}
            kind={kind}
            statusCode={statusCode}
            includeInactive={includeInactive}
            onKeywordChange={setKeyword}
            onKindChange={(value) => { setKind(value as LegacyKind | ""); setMeta((previous) => ({ ...previous, page: 1 })); }}
            onStatusCodeChange={setStatusCode}
            onIncludeInactiveChange={(value) => { setIncludeInactive(value); setMeta((previous) => ({ ...previous, page: 1 })); }}
            onLoad={load}
            onOpenDetail={(recordId) => void openDetail(recordId)}
            onCloseDetail={() => { setDetail(null); setDetailLoading(false); }}
          />
        </>,
      }]}
    />
  );
}
