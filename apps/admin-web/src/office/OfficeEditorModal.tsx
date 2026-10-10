import { Alert, Button, Modal, Spin, Typography } from "antd";
import { useRef } from "react";
import dayjs from "dayjs";
import type { OfficeEditorTarget } from "./types";
import { useOfficeEditorSession } from "./useOfficeEditorSession";

type OfficeEditorModalProps = {
  target: OfficeEditorTarget;
  onStored: () => Promise<unknown>;
  onClosed: () => void;
};

export function OfficeEditorModal({ target, onStored, onClosed }: OfficeEditorModalProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const { phase, error, closePending, savedAt, storedVersion, requestClose } = useOfficeEditorSession(target, mountRef, onStored, onClosed);
  return <Modal
    open
    forceRender
    title={<span title={target.name} style={{ display: "block", maxWidth: "calc(100% - 24px)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{target.name}</span>}
    width="calc(100vw - 24px)"
    style={{ top: 12, paddingBottom: 0, maxWidth: "none" }}
    styles={{ body: { height: "calc(100dvh - 152px)", minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" } }}
    maskClosable={false}
    keyboard={false}
    closable={phase !== "closing"}
    onCancel={requestClose}
    footer={<div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
      <Typography.Text type="secondary">
        {closePending ? "等待最终回写" : storedVersion && !error ? `最近回写${savedAt ? ` ${dayjs(savedAt).format("HH:mm:ss")}` : "成功"}` : ""}
      </Typography.Text>
      <Button loading={phase === "closing"} onClick={requestClose}>关闭</Button>
    </div>}
  >
    {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 8, flexShrink: 0 }} />}
    <div style={{ flex: 1, minHeight: 0, position: "relative" }}>
      <div ref={mountRef} inert={closePending} style={{ width: "100%", height: "100%" }} />
      {(phase === "loading" || closePending) && <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", background: "rgba(255,255,255,0.85)" }}><Spin /></div>}
    </div>
  </Modal>;
}
