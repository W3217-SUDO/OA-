import { useEffect, useState } from "react";
import { Button, Empty, Input, Modal, Space, Spin, Tree, message } from "antd";
import { FileOutlined, FolderOpenOutlined, SearchOutlined } from "@ant-design/icons";
import { api } from "../api";
import { buildAgentDocumentTree } from "../legal/constants";
import type { CaseAgentDocument } from "../legal/types";
import { errorText, type Material, type WorkspaceCase } from "./types";

type Props = { mode: "case" | "materials" | null; onClose: () => void; selectedCase: WorkspaceCase | null; onCase: (item: WorkspaceCase | null) => void; selectedMaterials: Material[]; onMaterials: (items: Material[]) => void; privateCount: number };

export function CaseMaterialsPicker({ mode, onClose, selectedCase, onCase, selectedMaterials, onMaterials, privateCount }: Props) {
  const [keyword, setKeyword] = useState("");
  const [cases, setCases] = useState<WorkspaceCase[]>([]);
  const [documents, setDocuments] = useState<CaseAgentDocument[]>([]);
  const [checked, setChecked] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!mode) return;
    let active = true;
    setLoading(true); setError("");
    const timer = window.setTimeout(async () => {
      try {
        if (mode === "case") {
          const { data } = await api.get<{ items: WorkspaceCase[] }>("/records", { params: { module: "case", keyword, page: 1, page_size: 50, exclude_archived: true } });
          if (active) setCases(data.items);
        } else if (selectedCase) {
          const { data } = await api.get<{ documents: CaseAgentDocument[] }>(`/case-spaces/${selectedCase.id}/context`);
          if (active) { setDocuments(data.documents); setChecked(selectedMaterials.map((item) => item.id).filter((id) => data.documents.some((item) => item.id === id))); }
        }
      } catch (failure) { if (active) setError(errorText(failure, "案件材料加载失败")); }
      finally { if (active) setLoading(false); }
    }, mode === "case" ? 250 : 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [mode, keyword, selectedCase?.id]);
  const updateChecked = (ids: number[]) => {
    if (ids.length + privateCount > 12) { message.warning("每次提问最多选择12份材料"); return; }
    setChecked(ids);
  };
  return <Modal open={!!mode} title={mode === "case" ? "关联案件" : `选择案件材料 · ${selectedCase?.serial_no || ""}`} width={680} onCancel={onClose} footer={mode === "materials" ? <Space><Button onClick={onClose}>取消</Button><Button type="primary" disabled={loading || !!error} onClick={() => { onMaterials(documents.filter((item) => checked.includes(item.id)).map((item) => ({ id: item.id, name: item.original_name, case_id: selectedCase?.id }))); onClose(); }}>使用所选材料{checked.length ? `（${checked.length}）` : ""}</Button></Space> : null}>
    {mode === "case" && <Input prefix={<SearchOutlined />} value={keyword} allowClear placeholder="搜索案号、案件名称或客户" onChange={(event) => setKeyword(event.target.value)} />}
    {error ? <div className="workspace-picker-error">{error}</div> : <Spin spinning={loading}>
      <div className="workspace-picker-content">
        {mode === "case" ? <>
          {selectedCase && <Button type="text" block onClick={() => { onCase(null); onClose(); }}>取消案件关联</Button>}
          {cases.map((item) => <button key={item.id} className="workspace-case-option" onClick={() => { onCase(item); onClose(); }}><FolderOpenOutlined /><div><b>{item.serial_no}</b><span>{item.title}</span></div></button>)}
          {!loading && !cases.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可访问的案件" />}
        </> : <>
          <div className="workspace-section-heading"><span><FileOutlined /> 已选择 {checked.length} 份</span><Space><Button type="text" size="small" onClick={() => updateChecked(documents.map((item) => item.id))}>全选</Button><Button type="text" size="small" onClick={() => setChecked([])}>清空</Button></Space></div>
          {!!documents.length && <Tree checkable selectable={false} defaultExpandAll treeData={buildAgentDocumentTree(documents)} checkedKeys={checked.map((id) => `document:${id}`)} onCheck={(keys) => { const values = Array.isArray(keys) ? keys : keys.checked; updateChecked(values.filter((key) => String(key).startsWith("document:")).map((key) => Number(String(key).slice(9)))); }} />}
          {!loading && !documents.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="案件中暂无可读取材料" />}
        </>}
      </div>
    </Spin>}
  </Modal>;
}
