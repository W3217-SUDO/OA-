import dayjs from "dayjs";
import { receiptBankCode } from "../bankReceiptScope";

export function incomingPaymentQueryParams(
  view: string, query: Record<string, unknown>, page?: number, pageSize?: number,
) {
  const encode = (value: unknown): unknown => {
    if (dayjs.isDayjs(value)) {
      if (!value.isValid()) throw new Error("回款查询日期无效");
      return value.format("YYYY-MM-DD");
    }
    return Array.isArray(value) ? value.map(encode) : value;
  };
  return {
    bank_source: receiptBankCode(view), view,
    filters: JSON.stringify(Object.fromEntries(Object.entries(query).map(([key, value]) => [key, encode(value)]))),
    ...(page === undefined ? {} : { page, page_size: pageSize }),
  };
}
