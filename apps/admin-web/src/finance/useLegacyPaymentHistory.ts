import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { LegacyFinanceRecord } from "./types";

export type LegacyPaymentView =
  | "mine"
  | "audit"
  | "waiting"
  | "print"
  | "package"
  | "writeoff"
  | "query";

export type LegacyPaymentRow = {
  id: number;
  legacy_id: string;
  status_code: string;
  status_label: string;
  primary_amount: number | null;
  legacy_contract_no: string | null;
  legacy_customer_no: string | null;
  application_no: string | null;
  application_date: string | null;
  applicant: string | null;
  deadline: string | null;
  payment_date: string | null;
  package_no: string | null;
  payer_name: string | null;
  payment_type_id: number | null;
  case_numbers: string[];
  read_only: true;
};

type LegacyPaymentHistoryResponse = {
  items: LegacyPaymentRow[];
  total: number;
  page: number;
  page_size: number;
  amount_visible: boolean;
  status_counts: Record<string, number>;
  read_only: true;
};

export const paymentStatusLabels: Record<string, string> = {
  "0": "创建待提交",
  "1": "待审批",
  "2": "审批中",
  "3": "待付款",
  "4": "已驳回",
  "5": "已作废",
  "6": "待核销",
  "7": "已付款",
};

const allStatusCodes = Object.keys(paymentStatusLabels);

export const paymentHistoryViews: Record<LegacyPaymentView, {
  title: string;
  description: string;
  statusCodes: string[];
  emptyText: string;
}> = {
  mine: {
    title: "我的历史请款单",
    description: "按旧系统申请人和原始请款状态查看历史记录。",
    statusCodes: allStatusCodes,
    emptyText: "没有符合条件的本人历史请款单。",
  },
  audit: {
    title: "历史待审批请款单",
    description: "仅显示旧系统中由当前用户待审批的请款单。",
    statusCodes: ["1"],
    emptyText: "旧库中没有由当前用户待审批的请款单。",
  },
  waiting: {
    title: "历史待付款请款单",
    description: "仅显示旧系统请款状态为待付款（状态 3）的记录。",
    statusCodes: ["3"],
    emptyText: "旧库当前没有待付款（状态 3）的请款单。其他状态可在历史付款单查询中查看。",
  },
  print: {
    title: "历史可打包请款单",
    description: "这里对应旧系统可打包请款子列表（请款状态 3）。旧“付款打包-打印”主表列的是待打包付款包（付款包状态 1），两种状态不能混用。",
    statusCodes: ["3"],
    emptyText: "旧库当前没有可打包（状态 3）的历史请款单。",
  },
  package: {
    title: "历史付款包关联请款单",
    description: "显示旧系统中处于待核销或已付款状态的关联请款单；此处不对历史付款包执行管理操作。",
    statusCodes: ["6", "7"],
    emptyText: "没有符合条件的历史付款包关联请款单。",
  },
  writeoff: {
    title: "历史待核销请款单",
    description: "仅显示旧系统请款状态为待核销（状态 6）的记录。",
    statusCodes: ["6"],
    emptyText: "旧库当前没有待核销（状态 6）的请款单。",
  },
  query: {
    title: "历史请款单查询",
    description: "按旧系统保留的原始状态和业务日期查询历史请款单。",
    statusCodes: allStatusCodes,
    emptyText: "没有符合条件的历史请款单。",
  },
};

export function useLegacyPaymentHistory(view: LegacyPaymentView) {
  const [result, setResult] = useState<LegacyPaymentHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [keyword, setKeyword] = useState("");
  const [statusCode, setStatusCode] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(30);
  const [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<LegacyPaymentRow | null>(null);
  const [detail, setDetail] = useState<LegacyFinanceRecord | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const detailRequest = useRef(0);

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError("");
    void api.get<LegacyPaymentHistoryResponse>("/finance/legacy-payment-history", {
      params: {
        view,
        keyword: keyword || undefined,
        status_code: statusCode || undefined,
        page,
        page_size: pageSize,
      },
    }).then(({ data }) => {
      if (!current) return;
      if (data.read_only !== true || data.items.some((item) => item.read_only !== true)) {
        throw new Error("历史请款接口未确认只读状态");
      }
      setResult(data);
    }).catch((requestError) => {
      if (!current) return;
      setResult(null);
      setError(requestError?.response?.data?.detail || requestError?.message || "历史请款加载失败");
    }).finally(() => {
      if (current) setLoading(false);
    });
    return () => { current = false; };
  }, [view, keyword, statusCode, page, pageSize, revision]);

  const openDetail = async (row: LegacyPaymentRow) => {
    const request = ++detailRequest.current;
    setSelected(row);
    setDetail(null);
    setDetailError("");
    setDetailLoading(true);
    try {
      const { data } = await api.get<LegacyFinanceRecord>(`/finance/legacy-history/${row.id}`);
      if (request === detailRequest.current) setDetail(data);
    } catch (requestError: any) {
      if (request === detailRequest.current) {
        setDetailError(requestError?.response?.data?.detail || "历史请款明细加载失败");
      }
    } finally {
      if (request === detailRequest.current) setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    detailRequest.current += 1;
    setSelected(null);
    setDetail(null);
    setDetailError("");
    setDetailLoading(false);
  };

  return {
    result, loading, error, statusCode, page, pageSize,
    selected, detail, detailLoading, detailError,
    setKeyword, setStatusCode, setPage, setPageSize, setRevision,
    openDetail, closeDetail,
  };
}
