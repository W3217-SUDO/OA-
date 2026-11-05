// 陶国南 11-05 19:29：钉钉电脑版里“问题反馈”页一直停在“正在加载页面...”——页面文件都下载成功了，
// 但加载既不成功也不报错，原来“加载失败就自动刷新一次”的处理等不到失败。超过这个时间就当作失败处理。
export const PAGE_LOAD_TIMEOUT_MS = 30_000;

export function withPageLoadTimeout<T>(loading: Promise<T>, ms = PAGE_LOAD_TIMEOUT_MS): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error("页面资源加载超时")), ms);
  });
  return Promise.race([loading, timeout]).finally(() => clearTimeout(timer));
}
