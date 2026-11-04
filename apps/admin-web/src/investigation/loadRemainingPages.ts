/** 第 1 页已取到后，按每页 100 条把第 2 页起的数据取全；一次最多并发 4 个请求，按页码顺序拼好（501338）。 */
export async function loadRemainingPages<T>(total: number, fetchPage: (page: number) => Promise<T[]>, pageSize = 100, concurrency = 4): Promise<T[]> {
  const pages = Math.ceil(total / pageSize);
  const results: T[][] = [];
  for (let start = 2; start <= pages; start += concurrency) {
    const batch = Array.from({ length: Math.min(concurrency, pages - start + 1) }, (_, index) => start + index);
    results.push(...await Promise.all(batch.map((page) => fetchPage(page))));
  }
  return results.flat();
}
