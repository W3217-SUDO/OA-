// 501618（高勤兰 11-05）：知识产权中心 › 案件文件 下补齐的收据、发票导入和上传，名称、顺序照旧系统。
export type IprFeeFilePage = {
  label: string;
  kind: "receipt-import" | "invoice-import-case" | "invoice-import-contract" | "case-upload";
  rule: string;
  /** case-upload：挂到案件上的文档类型。 */
  category?: string;
  /** case-upload：只查这类案件（专利 / 商标）。 */
  caseKind?: string;
};

const PENDING_FEES = "老案件费用迁移前，文件先挂成案件文档，在案件页“发票文件”里能看到。";

export const IPR_FEE_FILE_PAGES: Record<string, IprFeeFilePage> = {
  "ipr-receipt-custom-import": {
    label: "收据自定义文件导入", kind: "receipt-import",
    rule: `文件命名规则：A(系统案号)F(费用号)，例 A21800025F21002.jpg；可以一个文件，也可以 zip 打包多个。先“上传文件”看识别结果，再“开始导入”。${PENDING_FEES}`,
  },
  "ipr-invoice-import-case": {
    label: "发票文件导入(案件)", kind: "invoice-import-case",
    rule: `文件命名规则：系统开出的发票号，例 888888.jpg；可 zip 打包。按发票号找到开票记录，挂到发票关联的案件上。${PENDING_FEES}`,
  },
  "ipr-invoice-import-contract": {
    label: "发票文件导入(合同)", kind: "invoice-import-contract",
    rule: "文件命名规则：系统开出的发票号，例 888888.jpg；可 zip 打包。按发票号找到合同的开票记录，挂到开票记录上。",
  },
  "ipr-patent-invoice-upload": {
    label: "专利发票上传", kind: "case-upload", category: "发票", caseKind: "专利",
    rule: `按案件编号或申请号、客户查出专利案件，勾选后上传一个发票文件，同时挂到勾选的每个案件上。${PENDING_FEES}`,
  },
  "ipr-patent-receipt-upload": {
    label: "专利收据上传", kind: "case-upload", category: "官费收据", caseKind: "专利",
    rule: `按案件编号或申请号、客户查出专利案件，勾选后上传一个收据文件，同时挂到勾选的每个案件上。${PENDING_FEES}`,
  },
  "ipr-other-invoice-upload": {
    label: "其他案件发票上传", kind: "case-upload", category: "发票", caseKind: "商标",
    rule: `按案件编号或申请号、客户查出商标等非专利案件，勾选后上传一个发票文件，同时挂到勾选的每个案件上。${PENDING_FEES}`,
  },
};
