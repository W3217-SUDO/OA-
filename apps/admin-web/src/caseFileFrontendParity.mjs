const flattenOptions = (options) => (Array.isArray(options)
  ? options.flatMap((item) => [item, ...flattenOptions(item?.options)])
  : []);

export const getCaseFilePagination = () => ({
  defaultPageSize: 10,
  pageSizeOptions: [10, 20, 50, 100],
  showSizeChanger: true,
  showTotal: (total) => `\u5171 ${total} \u9879`,
});

export const getCaseAttachmentUploadValidationError = (file) => {
  if (!file) return "\u8bf7\u9009\u62e9\u6587\u4ef6\u8fdb\u884c\u4e0a\u4f20";
  if (Number(file.size) === 0) return "\u6587\u4ef6\u6ca1\u6709\u4efb\u4f55\u5185\u5bb9";
  return "";
};

export const getCaseFileRenameValidationError = (nextName, currentName) => {
  const next = String(nextName ?? "").trim();
  if (!next || /[\\/]/.test(next) || next.lastIndexOf(".") === 0) return "\u6587\u4ef6\u540d\u4e0d\u80fd\u4e3a\u7a7a\u4e14\u4e0d\u80fd\u5305\u542b\u8def\u5f84";
  // The legacy controller only rejects an empty basename; it does not lock the extension.
  void currentName;
  return "";
};

export const getCaseAttachmentSelectionValidationError = (keys, action) =>
  Array.isArray(keys) && keys.length ? "" : `\u8bf7\u9009\u62e9\u9700\u8981${String(action ?? "\u64cd\u4f5c")}\u7684\u6848\u4ef6\u6587\u4ef6`;

export const hasCaseFileTypeOption = (value, options) => {
  const requested = String(value ?? "").trim();
  return Boolean(requested && flattenOptions(options).some((item) => String(item?.value ?? "").trim() === requested));
};
