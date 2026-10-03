import type { AttachmentRow, CaseFileTypeOption } from "../types";

export type CaseDocumentTreeItem = {
  label: string;
  category: string;
  type: string;
  parent?: string;
  custom?: boolean;
  depth?: number;
  legacyTypeId?: number;
  parentMissing?: boolean;
};

export function findCaseDocumentFolder(nodes: CaseFileTypeOption[], value: string): CaseFileTypeOption | undefined {
  for (const node of nodes) {
    if (node.value === value) return node;
    const child = findCaseDocumentFolder(node.options || [], value);
    if (child) return child;
  }
  return undefined;
}

export function flattenLegacyCaseFolders(nodes: CaseFileTypeOption[], expanded: Record<string, boolean>, depth = 0, parent?: string): CaseDocumentTreeItem[] {
  const result: CaseDocumentTreeItem[] = [];
  for (const node of nodes) {
    const group = Boolean(node.options?.length) || node.legacy_type_id === 3 || node.legacy_type_id === 7;
    result.push({ label: node.label, category: node.value, type: group ? "group" : depth ? "child" : "folder",
      parent, depth, custom: node.native_custom, legacyTypeId: node.legacy_type_id,
      parentMissing: node.legacy_parent_missing });
    if (group && expanded[node.value] !== false) {
      result.push(...flattenLegacyCaseFolders(node.options || [], expanded, depth + 1, node.value));
    }
  }
  return result;
}

export function filterLegacyCaseFolder(files: AttachmentRow[], folder?: CaseFileTypeOption): AttachmentRow[] | null {
  if (!folder?.legacy_folder_id) return null;
  const relatedCategories: Record<number, string[]> = {
    1: ["客户文档"], 2: ["合同文档"], 3: ["鉴别资料", "调查文档", "取证文档"],
    4: ["鉴别资料"], 5: ["调查文档"], 6: ["取证文档"],
  };
  return files.filter(file => {
    if (file.legacy_document_folder_key) return file.legacy_document_folder_key === folder.value;
    if (file.source_module !== "case") {
      return (relatedCategories[folder.legacy_type_id || 0] || []).includes(file.document_category || file.category);
    }
    // 未指定旧目录的生成文件和后来新增文件，只能按唯一分类名匹配，不能混入同名目录。
    return folder.legacy_unique_name === true && file.record_id === folder.legacy_record_id
      && file.category === folder.label;
  });
}
