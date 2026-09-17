import { api } from "../../api";
import type { AttachmentRow } from "../types";

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
