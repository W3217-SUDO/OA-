import { CloseOutlined, SaveOutlined } from "@ant-design/icons";
import { Alert, Button, Modal, Space, Spin, Typography } from "antd";
import { useRef } from "react";
import { LibreOfficeFrame } from "./LibreOfficeFrame";
import type { LibreOfficeEditorTarget } from "./types";
import { useLibreOfficeSession } from "./useLibreOfficeSession";

type LibreOfficeEditorModalProps = {
  target: LibreOfficeEditorTarget;
  onStored: () => Promise<unknown>;
  onClosed: () => void;
};

export function LibreOfficeEditorModal({ target, onStored, onClosed }: LibreOfficeEditorModalProps) {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const editor = useLibreOfficeSession(target, frameRef, { onStored, onClosed });
  const terminal = editor.status?.status === "closed" || editor.status?.status === "expired";
  const canSave = editor.ready && !editor.closing && !editor.saving && !terminal;
  return <Modal
    open
    title={<Typography.Text ellipsis style={{ maxWidth: "calc(100% - 32px)" }}>{editor.session?.filename || target.filename}</Typography.Text>}
    width="calc(100vw - 32px)"
    style={{ top: 16, paddingBottom: 0 }}
    styles={{ body: { height: "calc(100dvh - 160px)", minHeight: 200, display: "flex", flexDirection: "column", gap: 8 } }}
    maskClosable={false}
    keyboard={false}
    closable={!editor.closing}
    onCancel={editor.close}
    footer={<div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
      <Typography.Text type="secondary">{editor.status?.last_saved_at ? `已回写 ${new Date(editor.status.last_saved_at).toLocaleString()}` : null}</Typography.Text>
      <Space>
        <Button icon={<SaveOutlined />} disabled={!canSave} loading={editor.saving} onClick={editor.save}>保存</Button>
        <Button icon={<CloseOutlined />} loading={editor.closing} disabled={editor.closing} onClick={editor.close}>{terminal ? "返回列表" : "保存并关闭"}</Button>
      </Space>
    </div>}
  >
    {editor.error && <Alert type="error" showIcon title={editor.error} />}
    {editor.pollError && <Alert type="error" showIcon title={editor.pollError} />}
    {editor.session
      ? <LibreOfficeFrame session={editor.session} frameRef={frameRef} loading={!editor.ready && !editor.error} blocked={!editor.ready || editor.closing || !!terminal} onLoad={editor.frameLoaded} onError={editor.frameFailed} />
      : <div style={{ flex: 1, display: "grid", placeItems: "center" }}>{!editor.error && <Spin />}</div>}
  </Modal>;
}
