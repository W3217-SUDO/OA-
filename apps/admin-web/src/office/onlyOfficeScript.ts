import type { OnlyOfficeApi } from "./types";

let loadedUrl = "";
let loading: Promise<OnlyOfficeApi> | null = null;

export function loadOnlyOfficeScript(documentServerUrl: string): Promise<OnlyOfficeApi> {
  const server = new URL(documentServerUrl, window.location.origin);
  if (server.origin !== window.location.origin || !["/office", "/office/"].includes(server.pathname) || server.search || server.hash || server.username || server.password) {
    return Promise.reject(new Error("Office 服务地址必须为本站 /office/"));
  }
  server.pathname = "/office/";
  const url = new URL("web-apps/apps/api/documents/api.js", server).href;
  if (loading) {
    if (loadedUrl !== url) return Promise.reject(new Error("Office 服务地址与已加载的编辑器不一致"));
    return loading;
  }
  loadedUrl = url;
  loading = new Promise<OnlyOfficeApi>((resolve, reject) => {
    const script = document.createElement("script");
    let timer: number;
    const finish = () => {
      window.clearTimeout(timer);
      script.onload = null;
      script.onerror = null;
    };
    const fail = (message: string) => {
      finish();
      script.remove();
      reject(new Error(message));
    };
    script.src = url;
    script.async = true;
    script.onload = () => {
      const sdk = (window as Window & { DocsAPI?: OnlyOfficeApi }).DocsAPI;
      if (!sdk || typeof sdk.DocEditor !== "function") {
        fail("Office 脚本未提供文档编辑器");
        return;
      }
      finish();
      resolve(sdk);
    };
    script.onerror = () => fail("Office 编辑器加载失败");
    timer = window.setTimeout(() => fail("Office 编辑器加载超时"), 30000);
    document.head.appendChild(script);
  }).catch((error: unknown) => {
    loading = null;
    loadedUrl = "";
    throw error;
  });
  return loading;
}
