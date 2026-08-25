const SOURCE_LABELS: Record<string, string> = {
  FCM_Contract_File: "合同历史附件",
  AWS_OfficialDocument_File: "公文历史附件",
};

const RECOVERY_LABELS: Record<string, string> = {
  metadata_only_source_blob_missing: "仅保留元数据，源文件缺失",
  quarantined_parent_missing: "父记录缺失，已隔离",
  quarantined_parent_ambiguous: "父记录存在歧义，已隔离",
  quarantined_path_collision: "旧路径冲突，已隔离",
};

const QUARANTINE_LABELS: Record<string, string> = {
  parent_missing: "父记录缺失",
  parent_ambiguous: "父记录存在歧义",
  controller_path_collision: "旧控制器路径冲突",
};

export const legacyAttachmentSourceLabel = (value?: string) =>
  SOURCE_LABELS[value || ""] || value || "—";

export const legacyAttachmentRecoveryLabel = (value?: string) =>
  RECOVERY_LABELS[value || ""] || value || "—";

export const legacyAttachmentQuarantineLabel = (values?: string[]) =>
  values?.length ? values.map((value) => QUARANTINE_LABELS[value] || value).join("、") : "—";
