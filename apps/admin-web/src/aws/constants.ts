export const archiveCategories = ["委托材料", "证据材料", "诉讼文书", "裁判文书"];

export const allCategories = [
  ...archiveCategories,
  "收文附件",
  "发文附件",
  "合同附件",
  "财务凭证",
  "普通附件",
];

export const fileSize = (n: number) =>
  n >= 1048576
    ? `${(n / 1048576).toFixed(2)} MB`
    : `${Math.max(1, Math.round(n / 1024))} KB`;

export const personDisplayName = (value: unknown) =>
  String(value || "").trim() || "姓名待维护";

export const templateCategoryOptions = [
  "诉讼文书",
  "非诉文书",
  "合同文书",
  "归档文书",
  "内部表单",
];

export const outgoingStatusOptions = ["草稿", "待审批", "已通过", "已拒绝", "已撤回", "已盖章"];
