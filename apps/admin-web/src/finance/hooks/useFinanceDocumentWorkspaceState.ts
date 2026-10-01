import { Form } from "antd";
import { useState } from "react";
import type { RecordFileFormValues, VoucherFormValues } from "../formTypes";
import type { Attachment, FinanceFlow, RecordFileTypeNode, Transaction } from "../types";

/** 业务附件与凭证各自的表单和上传状态。 */
export function useFinanceDocumentWorkspaceState() {
  const [recordFileTarget, setRecordFileTarget] = useState<FinanceFlow | null>(null);
  const [recordFileTargets, setRecordFileTargets] = useState<FinanceFlow[]>([]);
  const [recordFiles, setRecordFiles] = useState<Attachment[]>([]);
  const [recordFile, setRecordFile] = useState<File | null>(null);
  const [recordUploadFiles, setRecordUploadFiles] = useState<File[]>([]);
  const [recordFileTypeTree, setRecordFileTypeTree] = useState<RecordFileTypeNode[]>([]);
  const [recordFileForm] = Form.useForm<RecordFileFormValues>();
  const [voucherOpen, setVoucherOpen] = useState(false);
  const [voucherTarget, setVoucherTarget] = useState<Transaction | null>(null);
  const [voucherFile, setVoucherFile] = useState<File | null>(null);
  const [voucherForm] = Form.useForm<VoucherFormValues>();

  return {
    recordFileTarget, setRecordFileTarget, recordFileTargets, setRecordFileTargets,
    recordFiles, setRecordFiles, recordFile, setRecordFile,
    recordUploadFiles, setRecordUploadFiles, recordFileTypeTree, setRecordFileTypeTree,
    recordFileForm, voucherOpen, setVoucherOpen, voucherTarget, setVoucherTarget,
    voucherFile, setVoucherFile, voucherForm,
  };
}
