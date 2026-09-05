import { ReloadOutlined } from "@ant-design/icons";
import type { TablePaginationConfig } from "antd";
import { Button,Input,message,Space,Table } from "antd";
import type { CaseDetailCapabilities,CaseRow } from "../types";

interface CaseCluesPanelProps {
  clues: CaseRow[];
  pagination: TablePaginationConfig;
  loading: boolean;
  searchInput: string;
  setSearchInput: (value: string) => void;
  clueKeyword: string;
  setClueKeyword: (value: string) => void;
  cluePage: number;
  cluePageSize: number;
  capabilities: CaseDetailCapabilities;
  viewingCase: CaseRow | null | undefined;
  onSearch: (caseRow: CaseRow, page: number, pageSize: number, keyword: string) => Promise<unknown>;
  onRefresh: (caseRow: CaseRow, page: number, pageSize: number) => Promise<unknown>;
  onOpenClue: (row: CaseRow) => void;
  onOpenClueWorkspace: (row: CaseRow) => void;
  onCreateTask: (caseRow: CaseRow) => void;
}

export const CaseCluesPanel = ({
  clues,
  pagination,
  loading,
  searchInput,
  setSearchInput,
  clueKeyword,
  setClueKeyword,
  cluePage,
  cluePageSize,
  capabilities,
  viewingCase,
  onSearch,
  onRefresh,
  onOpenClue,
  onOpenClueWorkspace,
  onCreateTask,
}: CaseCluesPanelProps) => {
  return (<div className="case-legacy-tab-panel">
    <Space wrap style={{ marginBottom: 10 }}>
      <Input.Search
        aria-label="搜索关联线索"
        allowClear
        placeholder="线索号、店铺、地址、公证书号"
        value={searchInput}
        onChange={(event) => {
          const value = event.target.value;
          setSearchInput(value);
          if (!value && clueKeyword && viewingCase) {
            setClueKeyword("");
            void onSearch(viewingCase, 1, cluePageSize, "")
              .catch((error: any) => message.error(error?.response?.data?.detail || "关联线索加载失败"));
          }
        }}
        onSearch={(value) => {
          const keyword = value.trim();
          setClueKeyword(keyword);
          if (viewingCase) void onSearch(viewingCase, 1, cluePageSize, keyword)
            .catch((error: any) => message.error(error?.response?.data?.detail || "关联线索搜索失败"));
        }}
        style={{ width: 300 }}
      />
      <Button icon={<ReloadOutlined />} loading={loading} onClick={() => viewingCase && void onRefresh(viewingCase, cluePage, cluePageSize)
        .catch((error: any) => message.error(error?.response?.data?.detail || "关联线索加载失败"))}>刷新</Button>
    </Space>
    <Table rowKey="id" size="small" tableLayout="fixed" loading={loading} pagination={pagination} scroll={{x:1800}} dataSource={clues} locale={{ emptyText: "没有查询到关联线索" }} columns={[
      {title:"序号",width:65,align:"center",render:(_:unknown,_row:CaseRow,index:number)=>(cluePage-1)*cluePageSize+index+1},
      {title:"线索号",dataIndex:"serial_no",width:155,render:(value:string,row:CaseRow)=><Button type="link" className="case-cell-link" onClick={()=>onOpenClue(row)}>{value||"—"}</Button>},
      {title:"调查时间",width:150,render:(_:unknown,row:CaseRow)=>String(row.data.investigated_at||row.data.collected_at||row.data.investigation_time||row.data.investigation_date||"").replace("T"," ").slice(0,19)||"—"},
      {title:"店铺名称",width:180,ellipsis:true,render:(_:unknown,row:CaseRow)=>row.data.shop_name||row.data.store_name||row.title||"—"},
      {title:"店铺地址",width:250,ellipsis:true,render:(_:unknown,row:CaseRow)=>row.data.shop_address||row.data.address||row.data.location_address||"—"},
      {title:"公证书号",width:180,render:(_:unknown,row:CaseRow)=>row.data.certificate_no||row.data.notary_no||"—"},
      {title:"公证书状态",width:120,render:(_:unknown,row:CaseRow)=>row.data.certificate_status||row.data.notary_status||"—"},
      {title:"公证书入库时间",width:150,render:(_:unknown,row:CaseRow)=>String(row.data.certificate_stored_at||row.data.notary_stored_at||row.data.storage_date||"").replace("T"," ").slice(0,19)||"—"},
      {title:"件数",width:80,align:"right",render:(_:unknown,row:CaseRow)=>row.data.item_count??row.data.evidence_count??row.data.quantity??"—"},
      {title:"仓库名称",width:130,render:(_:unknown,row:CaseRow)=>row.data.warehouse_name||row.data.warehouse||"—"},
      {title:"仓库位置",width:120,render:(_:unknown,row:CaseRow)=>row.data.warehouse_location||row.data.storage_location||row.data.location||"—"},
      {title:"证物状态",width:110,render:(_:unknown,row:CaseRow)=>row.data.evidence_status||row.data.warehouse_status||"—"},
      {title:"操作",width:90,fixed:"right",render:(_:unknown,row:CaseRow)=><Button type="link" onClick={()=>void onOpenClueWorkspace(row)}>查看</Button>},
    ]}/>
    {capabilities.can_create_case_task&&<div className="case-legacy-bottom-actions"><Button onClick={()=>viewingCase && onCreateTask(viewingCase)}>发布任务</Button></div>}
  </div>);
};
