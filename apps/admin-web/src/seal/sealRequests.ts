import type { AxiosRequestConfig } from "axios";
import { api } from "../api";
import { sealErrorMessage, sealResponseIsFailure } from "../sealWorkflowPolicy";

type SealRequestFailure = Error & { response?: { data: unknown } };

export function ensureSealSuccess<T extends { data?: unknown }>(response: T, failureMessage: string): T {
  if (sealResponseIsFailure(response.data)) {
    const failure: SealRequestFailure = new Error(sealErrorMessage(response.data, failureMessage));
    failure.response = { data: response.data };
    throw failure;
  }
  return response;
}

export async function postSeal(url: string, data?: unknown) {
  return ensureSealSuccess(await api.post(url, data), "用印操作失败");
}

export async function patchSeal(url: string, data?: unknown) {
  return ensureSealSuccess(await api.patch(url, data), "用印保存失败");
}

export async function deleteSeal(url: string) {
  return ensureSealSuccess(await api.delete(url), "用印删除失败");
}

export async function postSealBlob(url: string, data: unknown, config: AxiosRequestConfig) {
  const response = await api.post(url, data, config);
  if (response.data instanceof Blob && response.data.type.includes("json")) {
    let payload: unknown;
    try {
      payload = JSON.parse(await response.data.text());
    } catch (cause) {
      throw new Error("服务器返回的下载信息格式无效", { cause });
    }
    ensureSealSuccess({ data: payload }, "打包下载失败");
    throw new Error("服务器没有返回可下载的文件");
  }
  return ensureSealSuccess(response, "打包下载失败");
}
