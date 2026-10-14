import { useState } from "react";
import { Alert, Button, Empty, Input, Modal, Spin } from "antd";
import { FolderOpenOutlined, SearchOutlined } from "@ant-design/icons";
import { useVisibleWorkspaceCases } from "./useVisibleWorkspaceCases";
import { errorText, type WorkspaceCase } from "./types";

type Props = { open: boolean; onClose: () => void; onSelect: (item: WorkspaceCase) => Promise<void>; blocked?: boolean };

export function CaseWorkspaceSelector({ open, onClose, onSelect, blocked = false }: Props) {
  const [keyword, setKeyword] = useState("");
  const [selecting, setSelecting] = useState(false);
  const [error, setError] = useState("");
  const cases = useVisibleWorkspaceCases(open, keyword, true);
  const select = async (item: WorkspaceCase) => {
    if (selecting || blocked) return;
    setSelecting(true); setError("");
    try { await onSelect(item); onClose(); }
    catch (failure) { setError(errorText(failure, "案件空间未打开")); }
    finally { setSelecting(false); }
  };
  return <Modal rootClassName="assistant-case-workspace-picker" open={open} title="选择案件空间" width={680} footer={null} onCancel={onClose} closable={!selecting} maskClosable={!selecting} keyboard={!selecting}>
    <Input prefix={<SearchOutlined />} value={keyword} allowClear disabled={selecting || blocked} aria-label="搜索案件空间" placeholder="搜索案号、案件名称或客户" onChange={(event) => setKeyword(event.target.value)} />
    {(cases.error || error) && <Alert type="error" showIcon title={cases.error || error} action={cases.error ? <Button onClick={cases.retry}>重试</Button> : undefined} />}
    <Spin spinning={cases.loading || selecting}>
      <div className="workspace-picker-content">
        {!cases.error && cases.items.map((item) => <button type="button" className="workspace-case-option" key={item.id} disabled={selecting || blocked} onClick={() => void select(item)}><FolderOpenOutlined /><div><b>{item.serial_no}</b><span>{item.title}</span></div></button>)}
        {!cases.loading && !cases.error && !cases.items.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可访问的案件" />}
      </div>
    </Spin>
  </Modal>;
}
