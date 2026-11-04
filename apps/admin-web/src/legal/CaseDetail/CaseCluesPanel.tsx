import { LinkifiedText } from "../../components/LinkifiedText";
import { ReloadOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import type { TablePaginationConfig } from "antd";
import { Button,Input,message,Space } from "antd";
import Table from "../../components/ResizableTable";
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
  onCreateTask: (caseRow: CaseRow, clues: CaseRow[]) => void;
  /** 501337：整条线索（证物、费用）移到其他案子 */
  onMoveClue?: (caseRow: CaseRow, clue: CaseRow) => void;
}

type ClueEvidence = { id: number; certificate_no?: string; certificate_status?: string; certificate_stored_at?: string; item_count?: string; warehouse_name?: string; warehouse_location?: string; evidence_status?: string };
type ClueEvidenceRow = { row_key: string; clue: CaseRow; evidence?: ClueEvidence };

/** 与旧系统一致，一个证物一行；没有证物的线索也显示一行（501294）。 */
export const clueEvidenceRows = (clues: CaseRow[]): ClueEvidenceRow[] => clues.flatMap((clue) => {
  const evidences = ((clue as CaseRow & { evidences?: ClueEvidence[] }).evidences || []);
  return evidences.length
    ? evidences.map((evidence) => ({ row_key: `${clue.id}-${evidence.id}`, clue, evidence }))
    : [{ row_key: `${clue.id}`, clue }];
});

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
  onMoveClue,
}: CaseCluesPanelProps) => {
  const [selectedClues, setSelectedClues] = useState<CaseRow[]>([]);
  useEffect(() => { setSelectedClues([]); }, [viewingCase?.id]);
  const rows = clueEvidenceRows(clues);
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
    <Table rowKey="row_key" rowSelection={{ selectedRowKeys: rows.filter(row => selectedClues.some(item => item.id === row.clue.id)).map(row => row.row_key), preserveSelectedRowKeys: true, onChange: (_, picked) => setSelectedClues([...new Map(picked.map(row => [row.clue.id, row.clue])).values()]) }} size="small" tableLayout="fixed" loading={loading} pagination={pagination} scroll={{x:1800}} dataSource={rows} locale={{ emptyText: "没有查询到关联线索" }} columns={[
      {title:"序号",width:65,align:"center",render:(_:unknown,_row:ClueEvidenceRow,index:number)=>(cluePage-1)*cluePageSize+index+1},
      {title:"线索号",width:155,render:(_:unknown,row:ClueEvidenceRow)=><Button type="link" className="case-cell-link" onClick={()=>onOpenClue(row.clue)}>{row.clue.serial_no||"—"}</Button>},
      {title:"调查时间",width:150,render:(_:unknown,{clue}:ClueEvidenceRow)=>String(clue.data.investigated_at||clue.data.collected_at||clue.data.investigation_time||clue.data.investigation_date||"").replace("T"," ").slice(0,19)||"—"},
      {title:"店铺名称",width:180,ellipsis:true,render:(_:unknown,{clue}:ClueEvidenceRow)=>clue.data.shop_name||clue.data.store_name||clue.title||"—"},
      // 与旧系统一致：没有地址的线上店铺显示店铺链接
      {title:"店铺地址",width:250,ellipsis:true,render:(_:unknown,{clue}:ClueEvidenceRow)=><LinkifiedText value={clue.data.shop_address||clue.data.address||clue.data.location_address||clue.data.store_url||clue.data.legacy_record?.StoreUrl} />},
      {title:"公证书号",width:180,render:(_:unknown,{clue,evidence}:ClueEvidenceRow)=>evidence?.certificate_no||clue.data.certificate_no||clue.data.notary_no||"—"},
      {title:"公证书状态",width:120,render:(_:unknown,{clue,evidence}:ClueEvidenceRow)=>evidence?.certificate_status||clue.data.certificate_status||clue.data.notary_status||"—"},
      {title:"公证书入库时间",width:150,render:(_:unknown,{clue,evidence}:ClueEvidenceRow)=>String(evidence?.certificate_stored_at||clue.data.certificate_stored_at||clue.data.notary_stored_at||clue.data.storage_date||"").replace("T"," ").slice(0,19)||"—"},
      {title:"件数",width:80,align:"right",render:(_:unknown,{clue,evidence}:ClueEvidenceRow)=>evidence?.item_count||clue.data.item_count||clue.data.evidence_count||clue.data.quantity||"—"},
      {title:"仓库名称",width:130,render:(_:unknown,{clue,evidence}:ClueEvidenceRow)=>evidence?.warehouse_name||clue.data.warehouse_name||clue.data.warehouse||"—"},
      {title:"仓库位置",width:120,render:(_:unknown,{clue,evidence}:ClueEvidenceRow)=>evidence?.warehouse_location||clue.data.warehouse_location||clue.data.storage_location||clue.data.location||"—"},
      {title:"证物状态",width:110,render:(_:unknown,{clue,evidence}:ClueEvidenceRow)=>evidence?.evidence_status||clue.data.evidence_status||clue.data.warehouse_status||"—"},
      {title:"操作",width:90,fixed:"right",render:(_:unknown,row:ClueEvidenceRow)=><Button type="link" onClick={()=>void onOpenClueWorkspace(row.clue)}>查看</Button>},
    ]}/>
    {(capabilities.can_create_case_task||(onMoveClue&&(capabilities.can_move_fee||capabilities.can_edit_basic)))&&<div className="case-legacy-bottom-actions">
      {capabilities.can_create_case_task&&<Button onClick={()=>{ if (!selectedClues.length) return message.warning("请先选择线索信息"); if (viewingCase) onCreateTask(viewingCase, selectedClues); }}>发布任务</Button>}
      {onMoveClue&&(capabilities.can_move_fee||capabilities.can_edit_basic)&&<Button onClick={()=>{ if (selectedClues.length !== 1) return message.warning("请选择一条线索"); if (viewingCase) onMoveClue(viewingCase, selectedClues[0]); }}>移到其他案子</Button>}
    </div>}
  </div>);
};
