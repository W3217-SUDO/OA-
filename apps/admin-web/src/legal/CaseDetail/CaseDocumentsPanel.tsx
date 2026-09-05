import {
CloseOutlined,
EditOutlined,
FileWordOutlined,
FolderOpenOutlined,
FolderOutlined,
PlusCircleFilled,
RobotOutlined,
} from "@ant-design/icons";
import { Alert,Button,Dropdown,Select,Space,Table,Tag } from "antd";
import dayjs from "dayjs";
import type { Key } from "react";
import { dispatchCaseDocumentGenerationMenuClick } from "../../caseDocumentGenerationActions.mjs";
import { getLegacyCaseDocumentGenerationItems } from "../constants";
import type { AttachmentRow,CaseDetailCapabilities,CaseDocumentFolderEditor,CaseRow } from "../types";

interface CaseDocTreeItem {
  label: string;
  category: string;
  type: string;
  parent?: string;
  custom?: boolean;
}

interface CaseDocumentsPanelProps {
  viewingCase: CaseRow;
  counselDocTree: CaseDocTreeItem[];
  expandedCounselDocGroups: Record<string, boolean>;
  activeCounselDocCategory: string;
  activeCounselDocLabel: string;
  isAiSpaceFolder: boolean;
  toggleCounselDocGroup: (category: string) => void;
  selectCounselDocCategory: (category: string) => void;
  counselDetailCapabilities: CaseDetailCapabilities;
  openCaseDocumentFolderEditor: (editor: CaseDocumentFolderEditor) => void;
  deleteCaseDocumentFolder: (name: string) => void;
  counselDetailUploadRef: React.RefObject<HTMLInputElement | null>;
  uploadCounselDetailAttachment: (file?: File) => Promise<unknown>;
  filteredCounselDetailAttachments: AttachmentRow[];
  selectedCounselAttachmentKeys: Key[];
  setSelectedCounselAttachmentKeys: (keys: Key[]) => void;
  getCaseFilePagination: typeof import("../../caseFileFrontendParity.mjs").getCaseFilePagination;
  previewCounselDetailAttachment: (row: AttachmentRow) => Promise<unknown>;
  downloadCounselDetailAttachment: (row: AttachmentRow) => Promise<unknown>;
  openEditAiDraft: (item: AttachmentRow) => Promise<unknown>;
  openCaseWordEditor: (item: AttachmentRow) => Promise<unknown>;
  openCounselAttachmentRename: (row: AttachmentRow) => void;
  openPromoteAiDraft: (row: AttachmentRow) => void;
  deleteAiDraft: (row: AttachmentRow) => void;
  unlockCounselDetailAttachment: (row: AttachmentRow) => Promise<unknown>;
  canApplySealToCounselAttachment: (item: AttachmentRow) => boolean;
  openCounselAttachmentSeal: (row: AttachmentRow) => Promise<unknown>;
  caseDocumentGenerationError: string;
  setCaseDocumentGenerationError: (error: string) => void;
  counselUploadCategory: string;
  setCounselUploadCategory: (value: string) => void;
  activeCounselUploadCategoryOptions: { value: string; label: string }[];
  openCreateAiDraft: () => void;
  caseDocumentGenerationMenuOpen: boolean;
  setCaseDocumentGenerationMenuOpen: (open: boolean) => void;
  generatingCaseDocumentType: string | null;
  generateCaseDocument: (type: string) => Promise<unknown>;
  handleCounselDocumentMoreAction: (key: string) => void;
  canApplySealToSelectedCounselDocument: boolean;
}

export const CaseDocumentsPanel = ({
  viewingCase,
  counselDocTree,
  expandedCounselDocGroups,
  activeCounselDocCategory,
  activeCounselDocLabel,
  isAiSpaceFolder,
  toggleCounselDocGroup,
  selectCounselDocCategory,
  counselDetailCapabilities,
  openCaseDocumentFolderEditor,
  deleteCaseDocumentFolder,
  counselDetailUploadRef,
  uploadCounselDetailAttachment,
  filteredCounselDetailAttachments,
  selectedCounselAttachmentKeys,
  setSelectedCounselAttachmentKeys,
  getCaseFilePagination,
  previewCounselDetailAttachment,
  downloadCounselDetailAttachment,
  openEditAiDraft,
  openCaseWordEditor,
  openCounselAttachmentRename,
  openPromoteAiDraft,
  deleteAiDraft,
  unlockCounselDetailAttachment,
  canApplySealToCounselAttachment,
  openCounselAttachmentSeal,
  caseDocumentGenerationError,
  setCaseDocumentGenerationError,
  counselUploadCategory,
  setCounselUploadCategory,
  activeCounselUploadCategoryOptions,
  openCreateAiDraft,
  caseDocumentGenerationMenuOpen,
  setCaseDocumentGenerationMenuOpen,
  generatingCaseDocumentType,
  generateCaseDocument,
  handleCounselDocumentMoreAction,
  canApplySealToSelectedCounselDocument,
}: CaseDocumentsPanelProps) => {
  return (
    <div className="case-documents-layout">
      <aside className="case-detail-doc-tree" aria-label="案件文档目录">
        {counselDocTree.map((item,index)=>(
          <div className="case-doc-tree-row" key={`${item.category}-${item.type}-${index}`}>
          <button
            className={`${item.type==="child"?"case-doc-child":"case-doc-folder"} ${item.category==="AI空间"?"case-doc-ai-space":""} ${item.type==="group"&&expandedCounselDocGroups[item.category]?"case-doc-folder-open":""} ${activeCounselDocCategory===item.category?"case-doc-active":""}`}
            onClick={()=>item.type==="group"?toggleCounselDocGroup(item.category):selectCounselDocCategory(item.category)}
            title={`查看${item.label}`}
            aria-expanded={item.type==="group"?expandedCounselDocGroups[item.category]:undefined}
          >
            <span className="case-doc-caret" aria-hidden="true">{item.type==="group"?(expandedCounselDocGroups[item.category]?"▾":"▸"):""}</span>
            {item.category==="AI空间"?<RobotOutlined className="case-doc-icon"/>:item.type==="group"&&expandedCounselDocGroups[item.category]?<FolderOpenOutlined className="case-doc-icon"/>:<FolderOutlined className="case-doc-icon"/>}
            <span>{item.label}</span>
          </button>
          {counselDetailCapabilities.can_write&&item.category==="案件文档全部"&&(
            <Button type="text" className="case-doc-tree-action case-doc-tree-add" icon={<PlusCircleFilled/>} title="新增自定义案件文档目录" aria-label="新增自定义案件文档目录" onClick={()=>openCaseDocumentFolderEditor({mode:"create"})}/>
          )}
          {counselDetailCapabilities.can_write&&item.custom&&activeCounselDocCategory===item.category&&<><Button type="text" className="case-doc-tree-action" icon={<EditOutlined/>} title={`重命名目录${item.label}`} aria-label={`重命名目录${item.label}`} onClick={()=>openCaseDocumentFolderEditor({mode:"rename",originalName:item.label})}/><Button type="text" danger className="case-doc-tree-action" icon={<CloseOutlined/>} title={`删除目录${item.label}`} aria-label={`删除目录${item.label}`} onClick={()=>deleteCaseDocumentFolder(item.label)}/></>}
          </div>
        ))}
      </aside>
      <div className="case-document-list">
      <input ref={counselDetailUploadRef} hidden type="file" onChange={event=>void uploadCounselDetailAttachment(event.target.files?.[0])}/>
      <Table rowKey="id" size="small" pagination={getCaseFilePagination()} scroll={{x:940}} dataSource={filteredCounselDetailAttachments} rowSelection={{selectedRowKeys:selectedCounselAttachmentKeys,onChange:setSelectedCounselAttachmentKeys}} locale={{emptyText:<Space direction="vertical" size={10}><span>没有查到文档。</span>{counselDetailCapabilities.can_upload_attachment&&<Button type="primary" onClick={()=>counselDetailUploadRef.current?.click()}>上传文件</Button>}</Space>}} columns={[
        {title:"序号",key:"sequence",width:70,render:(_:unknown,_row:AttachmentRow,index:number)=>index+1},
        {title:"上传人",dataIndex:"uploader_display_name",width:110,render:(_:unknown,row:AttachmentRow)=>row.uploader_display_name||row.uploader||"—"},
        {title:"文件名称",dataIndex:"original_name",width:360,ellipsis:true},
        {title:"上传时间",dataIndex:"created_at",width:180,render:(value:string)=>value&&dayjs(value).isValid()?dayjs(value).format("YYYY-MM-DD HH:mm:ss"):"—"},
        {title:"操作",key:"actions",width:isAiSpaceFolder?410:420,render:(_:unknown,row:AttachmentRow)=><Space size={0}><Button type="link" onClick={()=>void previewCounselDetailAttachment(row)}>查看</Button><Button type="link" onClick={()=>void downloadCounselDetailAttachment(row)}>下载</Button>{counselDetailCapabilities.can_write&&isAiSpaceFolder&&/\.(docx|md|txt)$/i.test(row.original_name)&&<Button type="link" onClick={()=>void openEditAiDraft(row)}>编辑</Button>}{counselDetailCapabilities.can_write&&!isAiSpaceFolder&&row.record_id===viewingCase.id&&/.docx?$/i.test(row.original_name)&&<Button type="link" onClick={()=>void openCaseWordEditor(row)}>在线编辑</Button>}{counselDetailCapabilities.can_write&&<Button type="link" onClick={()=>openCounselAttachmentRename(row)}>重命名</Button>}{counselDetailCapabilities.can_write&&isAiSpaceFolder&&<Button type="link" onClick={()=>openPromoteAiDraft(row)}>转入正式系统</Button>}{counselDetailCapabilities.can_delete_attachment&&isAiSpaceFolder&&<Button type="link" danger onClick={()=>deleteAiDraft(row)}>删除</Button>}{counselDetailCapabilities.can_write&&row.record_id===viewingCase.id&&row.is_locked&&<Button type="link" onClick={()=>void unlockCounselDetailAttachment(row)}>解锁</Button>}{counselDetailCapabilities.can_write&&canApplySealToCounselAttachment(row)&&<Button type="link" onClick={()=>void openCounselAttachmentSeal(row)}>申请用印</Button>}</Space>},
      ]}/>
      {caseDocumentGenerationError && <Alert
        type="error"
        showIcon
        closable
        message={caseDocumentGenerationError}
        onClose={() => setCaseDocumentGenerationError("")}
        className="case-document-generation-error"
      />}
      <Space wrap className="case-document-toolbar">
        <Select value={counselUploadCategory} disabled={isAiSpaceFolder} style={{width:180}} onChange={setCounselUploadCategory} options={activeCounselUploadCategoryOptions}/>
        {counselDetailCapabilities.can_write&&isAiSpaceFolder&&<Button icon={<FileWordOutlined/>} onClick={openCreateAiDraft}>新建 Word 文档</Button>}
        {counselDetailCapabilities.can_upload_attachment && <Button type="primary" onClick={()=>counselDetailUploadRef.current?.click()}>上传文件</Button>}
        {counselDetailCapabilities.can_generate_document && <Dropdown
          trigger={["click"]}
          placement="bottomLeft"
          autoAdjustOverflow={false}
          getPopupContainer={() => document.body}
          classNames={{root:"case-document-generation-popup"}}
          open={caseDocumentGenerationMenuOpen}
          onOpenChange={setCaseDocumentGenerationMenuOpen}
          menu={{
            items: getLegacyCaseDocumentGenerationItems().map(([key, label]) => ({key, label, disabled:Boolean(generatingCaseDocumentType)})),
            onClick: (event) => dispatchCaseDocumentGenerationMenuClick(event, (key) => {
              setCaseDocumentGenerationMenuOpen(false);
              void generateCaseDocument(key);
            }),
          }}
        ><Button
          loading={Boolean(generatingCaseDocumentType)}
          aria-haspopup="menu"
          aria-expanded={caseDocumentGenerationMenuOpen}
        >生成操作</Button></Dropdown>}
        {counselDetailCapabilities.can_write && <Dropdown trigger={["click"]} menu={{items:[{key:"delete",label:"删除"},...(canApplySealToSelectedCounselDocument?[{key:"seal",label:"申请用印"}]:[]),{key:"move",label:"更改文档目录"}],onClick:({key})=>handleCounselDocumentMoreAction(key)}}><Button>更多操作</Button></Dropdown>}
        {activeCounselDocCategory&&<Tag color="green">当前目录：{activeCounselDocLabel}</Tag>}
      </Space>
      </div>
    </div>
  );
};

