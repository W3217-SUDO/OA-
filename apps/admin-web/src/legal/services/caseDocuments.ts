import { api } from "../../api";
import type { AttachmentRow } from "../types";

// 合同目录同时展示主案合同及合并来源合同附件，保留原始归属和分类。
export function caseContractDocuments(primary: AttachmentRow[], related: AttachmentRow[]) {
  const files = new Map(primary.map(item => [item.id, item]));
  for (const item of related) {
    if (item.document_category === "合同文档") files.set(item.id, item);
  }
  return [...files.values()];
}

// 案件文档本地分页展示，需要取全接口分页，不能只展示前 200 个文件。
export async function loadCaseDocuments(caseId: number) {
  const items: AttachmentRow[] = [];
  let page = 1;
  let pages = 1;
  do {
    const { data } = await api.get(`/cases/${caseId}/documents`, { params: { page, page_size: 200 } });
    items.push(...data.items);
    pages = data.pages;
    page += 1;
  } while (page <= pages);
  return { data: { items } };
}
