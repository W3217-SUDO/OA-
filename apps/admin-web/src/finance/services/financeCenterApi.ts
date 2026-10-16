import type { AxiosRequestConfig } from "axios";
import { api } from "../../api";
import type { FinanceScope } from "../types";

/** 回款及结算请求共用中心参数，沿用原认证、错误处理及缓存链路。 */
export function financeCenterApi(financeScope: FinanceScope) {
  const scoped = (url: string, config?: AxiosRequestConfig): AxiosRequestConfig | undefined =>
    /^\/finance\/(incoming-payments|general-settlements|archive-settlements|settlements|legacy-history)(\/|$)/.test(url)
      ? { ...config, params: { ...config?.params, finance_scope: financeScope } }
      : config;
  return {
    get<T = any>(url: string, config?: AxiosRequestConfig) {
      return api.get<T>(url, scoped(url, config));
    },
    post<T = any>(url: string, data?: unknown, config?: AxiosRequestConfig) {
      return api.post<T>(url, data, scoped(url, config));
    },
    put<T = any>(url: string, data?: unknown, config?: AxiosRequestConfig) {
      return api.put<T>(url, data, scoped(url, config));
    },
    delete<T = any>(url: string, config?: AxiosRequestConfig) {
      return api.delete<T>(url, scoped(url, config));
    },
  };
}
