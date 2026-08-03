export declare const refundPageSizeOptions: number[];
export declare const refundStatusOptions: string[];
export declare const refundRequestParams: (
  page: number,
  pageSize: number,
  status?: string,
  group?: string,
  scope?: string,
) => {
  page: number;
  page_size: number;
  status?: string;
  group?: string;
  scope: string;
};
export declare const refundListRequest: (
  page: number,
  pageSize: number,
  status?: string,
  group?: string,
  scope?: string,
) => { url: string; params: ReturnType<typeof refundRequestParams> };
export declare const refundExportRequestParams: (
  status?: string,
  group?: string,
  scope?: string,
) => { status?: string; group?: string; scope: string };
export declare const refundSelectedExportRequestParams: (
  ids: number[],
  status?: string,
  group?: string,
  scope?: string,
) => { ids: string; status?: string; group?: string; scope: string };
export declare const refundAmountUpdateRequest: (
  id: number,
  amount: number,
  comment?: string,
) => { url: string; method: "patch"; body: { amount: number; comment: string } };
export declare const refundBatchStatusRequest: (
  ids: number[],
  status: string,
  comment?: string,
) => {
  url: string;
  method: "post";
  body: { ids: number[]; status: string; comment: string };
};
export declare const refundListErrorMessage: (error: any) => string;
export declare const refundLoadFailure: (state: any, error: any) => {
  state: any;
  message: string;
};
export declare const normalizeRefundResponse: (
  data: Record<string, any> | undefined,
  fallbackPage?: number,
  fallbackPageSize?: number,
) => {
  items: any[];
  total: number;
  page: number;
  pageSize: number;
};
export declare const caseFeeRefundStatusLabel: (row: any) => string;
