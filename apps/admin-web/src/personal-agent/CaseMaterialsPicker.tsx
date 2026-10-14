import { useEffect, useState } from "react";
import { Button, Empty, Input, Modal, Space, Spin, Tree, message } from "antd";
import { ArrowLeftOutlined, FileOutlined, FolderOpenOutlined, SearchOutlined } from "@ant-design/icons";
import { api } from "../api";
import { buildAgentDocumentTree } from "../legal/constants";
import type { CaseAgentDocument } from "../legal/types";
import { errorText, type Material, type WorkspaceCase } from "./types";
import { useVisibleWorkspaceCases } from "./useVisibleWorkspaceCases";
import "./workspace-context.css";

type Props = { mode: "case" | "materials" | null; onClose: () => void; selectedCase: WorkspaceCase | null; onCase: (item: WorkspaceCase | null) => void; selectedMaterials: Material[]; onMaterials: (items: Material[]) => void; privateCount: number; onSelection?: (item: WorkspaceCase, materials: Material[]) => void };

export function CaseMaterialsPicker({ mode, onClose, selectedCase, onCase, selectedMaterials, onMaterials, privateCount, onSelection }: Props) {
  const [keyword, setKeyword] = useState("");
  const [documents, setDocuments] = useState<CaseAgentDocument[]>([]);
  const [checked, setChecked] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectionCase, setSelectionCase] = useState<WorkspaceCase | null>(null);
  const [selectionMode, setSelectionMode] = useState<"case" | "materials">("case");
  const activeMode = onSelection ? selectionMode : mode;
  const activeCase = onSelection ? selectionCase : selectedCase;
  const cases = useVisibleWorkspaceCases(!!mode && activeMode === "case", keyword, !!onSelection);
  const currentLoading = activeMode === "case" ? cases.loading : loading;
  const currentError = activeMode === "case" ? cases.error : error;
  useEffect(() => {
    if (!mode || !onSelection) return;
    setSelectionCase(selectedCase);
    setSelectionMode(mode);
  }, [mode]);
  useEffect(() => {
    if (!mode || activeMode !== "materials" || !activeCase) return;
    let active = true;
    setLoading(true); setError("");
    const timer = window.setTimeout(async () => {
      try {
        const { data } = await api.get<{ documents: CaseAgentDocument[] }>(`/case-spaces/${activeCase.id}/context`);
        if (active) { setDocuments(data.documents); setChecked(activeCase.id === selectedCase?.id ? selectedMaterials.map((item) => item.id).filter((id) => data.documents.some((item) => item.id === id)) : []); }
      } catch (failure) { if (active) setError(errorText(failure, "案件材料加载失败")); }
      finally { if (active) setLoading(false); }
    }, 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [mode, activeMode, activeCase?.id]);
  const updateChecked = (ids: number[]) => {
    if (ids.length + privateCount > 12) { message.warning("每次提问最多选择12份材料"); return; }
    setChecked(ids);
  };
  const confirmMaterials = () => {
    const materials = documents.filter((item) => checked.includes(item.id)).map((item) => ({ id: item.id, name: item.original_name, case_id: activeCase?.id }));
    if (onSelection) {
      if (!activeCase || !materials.length) return;
      onSelection(activeCase, materials);
    } else onMaterials(materials);
    onClose();
  };
  return <Modal rootClassName={onSelection ? "assistant-case-materials-picker" : undefined} open={!!mode} title={activeMode === "case" ? (onSelection ? "选择案件文件 · 先选择案件" : "关联案件") : `选择案件材料 · ${activeCase?.serial_no || ""}`} width={680} onCancel={onClose} footer={activeMode === "materials" ? <Space><Button onClick={onClose}>取消</Button><Button type="primary" disabled={currentLoading || !!currentError || (!!onSelection && !checked.length)} onClick={confirmMaterials}>{onSelection ? "引用所选文件" : "使用所选材料"}{checked.length ? `（${checked.length}）` : ""}</Button></Space> : null}>
    {activeMode === "case" && <Input prefix={<SearchOutlined />} value={keyword} allowClear placeholder="搜索案号、案件名称或客户" onChange={(event) => setKeyword(event.target.value)} />}
    {currentError ? <div className="workspace-picker-error">{currentError}</div> : <Spin spinning={currentLoading}>
      <div className="workspace-picker-content">
        {activeMode === "case" ? <>
          {!onSelection && selectedCase && <Button type="text" block onClick={() => { onCase(null); onClose(); }}>取消案件关联</Button>}
          {cases.items.map((item) => <button type="button" key={item.id} className="workspace-case-option" onClick={() => {
            if (onSelection) { setSelectionCase(item); setChecked([]); setDocuments([]); setSelectionMode("materials"); }
            else { onCase(item); onClose(); }
          }}><FolderOpenOutlined /><div><b>{item.serial_no}</b><span>{item.title}</span></div></button>)}
          {!currentLoading && !cases.items.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可访问的案件" />}
        </> : <>
          {onSelection && <div className="workspace-section-heading"><Button type="text" icon={<ArrowLeftOutlined />} onClick={() => setSelectionMode("case")}>重新选案</Button><span>{activeCase?.title}</span></div>}
          <div className="workspace-section-heading"><span><FileOutlined /> 已选择 {checked.length} 份</span><Space><Button type="text" size="small" onClick={() => updateChecked(documents.map((item) => item.id))}>全选</Button><Button type="text" size="small" onClick={() => setChecked([])}>清空</Button></Space></div>
          {!!documents.length && <Tree checkable selectable={false} defaultExpandAll treeData={buildAgentDocumentTree(documents)} checkedKeys={checked.map((id) => `document:${id}`)} onCheck={(keys) => { const values = Array.isArray(keys) ? keys : keys.checked; updateChecked(values.filter((key) => String(key).startsWith("document:")).map((key) => Number(String(key).slice(9)))); }} />}
          {!currentLoading && !documents.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="案件中暂无可读取材料" />}
        </>}
      </div>
    </Spin>}
  </Modal>;
}
