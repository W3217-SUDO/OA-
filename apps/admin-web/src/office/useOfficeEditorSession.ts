import { message } from "antd";
import { useEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import { closeOfficeSession, createOfficeSession, getOfficeSession, officeErrorMessage, renewOfficeSession } from "./officeEditorApi";
import { loadOnlyOfficeScript } from "./onlyOfficeScript";
import type { OfficeEditorSession, OfficeEditorTarget, OfficeSessionStatus, OnlyOfficeEditor } from "./types";

type SessionPhase = "loading" | "ready" | "closing" | "error";

export function useOfficeEditorSession(
  target: OfficeEditorTarget,
  mountRef: RefObject<HTMLDivElement | null>,
  onStored: () => Promise<unknown>,
  onClosed: () => void,
) {
  const [phase, setPhase] = useState<SessionPhase>("loading");
  const [error, setError] = useState("");
  const [statusError, setStatusError] = useState("");
  const [closePending, setClosePending] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [storedVersion, setStoredVersion] = useState<string | null>(null);
  const callbacks = useRef({ onStored, onClosed });
  callbacks.current = { onStored, onClosed };
  const closeAction = useRef<(() => void) | null>(null);

  useEffect(() => {
    let active = true;
    let session: OfficeEditorSession | null = null;
    let editor: OnlyOfficeEditor | null = null;
    let currentStatus: OfficeSessionStatus | null = null;
    let savedVersion: string | null = null;
    let baselineInitialized = false;
    let initializing = true;
    let initializationFailed = false;
    let attachmentRefreshFailed = false;
    let hasChanges = false;
    let closeRequested = false;
    let closeStartedAt = 0;
    let closingRequest = false;
    let closeSubmitted = false;
    let polling = false;
    let documentReady = false;
    let readyTimer: number | undefined;

    const destroyEditor = () => {
      window.clearTimeout(readyTimer);
      editor?.destroyEditor();
      editor = null;
    };
    const fail = (text: string) => {
      if (!active) return;
      setError(text);
      setPhase("error");
    };
    const applyStatus = async (status: OfficeSessionStatus) => {
      currentStatus = status;
      if (!active) return;
      // 服务端确认关闭保存已完成或确无新改动后，才允许断开编辑器。
      if (closeRequested && status.close_ready === true) destroyEditor();
      // 只有服务端存储版本变化才表示回写成功，编辑器事件不作为保存凭据。
      if (!baselineInitialized) {
        savedVersion = status.saved_version;
        baselineInitialized = true;
      } else if (status.saved_version && status.saved_version !== savedVersion) {
        savedVersion = status.saved_version;
        setStoredVersion(status.saved_version);
        setSavedAt(status.saved_at);
        try {
          await callbacks.current.onStored();
        } catch (refreshError: unknown) {
          attachmentRefreshFailed = true;
          fail(`文件已回写，附件列表刷新失败：${officeErrorMessage(refreshError)}`);
        }
      }
      if (!active) return;
      if (status.status === "failed" || status.status === "expired") {
        setClosePending(closeRequested);
        const text = status.error || (status.status === "expired" ? "Office 编辑会话已过期" : "Office 文件回写失败");
        if (!closeRequested) editor?.denyEditingRights(text);
        fail(text);
      } else if (status.status === "closed") {
        setClosePending(false);
        if (closeRequested) {
          if (!initializationFailed && !attachmentRefreshFailed) callbacks.current.onClosed();
        } else if (!initializationFailed) {
          editor?.denyEditingRights("Office 编辑会话已关闭");
          fail("Office 编辑会话已关闭");
        }
      } else if (status.status === "closing") {
        setClosePending(true);
      }
    };
    const sendClose = async () => {
      if (!session || closingRequest) return;
      closingRequest = true;
      closeSubmitted = true;
      try {
        await applyStatus(await closeOfficeSession(target, session.session_id));
      } catch (closeError: unknown) {
        closeSubmitted = false;
        const text = `Office 会话关闭失败：${officeErrorMessage(closeError)}`;
        if (active) fail(text);
        else message.error(text);
      } finally {
        closingRequest = false;
      }
    };
    const beginClose = () => {
      if (!active || closingRequest) return;
      closeRequested = true;
      closeSubmitted = false;
      closeStartedAt = Date.now();
      setClosePending(true);
      setPhase("closing");
      window.clearTimeout(readyTimer);
      if (!initializing && (!session || currentStatus?.status === "closed")) {
        setClosePending(false);
        callbacks.current.onClosed();
        return;
      }
      void sendClose();
    };
    closeAction.current = () => {
      if (editor && !closeRequested) editor.requestClose();
      else beginClose();
    };
    const poll = async () => {
      if (!active || !session || initializing || polling) return;
      if (currentStatus?.status === "closed" || currentStatus?.status === "expired" || (currentStatus?.status === "failed" && !closeRequested)) return;
      polling = true;
      try {
        const latest = await getOfficeSession(target, session.session_id);
        if (active) setStatusError("");
        await applyStatus(latest);
        if (!active || latest.status === "closed" || latest.status === "expired" || (latest.status === "failed" && !closeRequested)) return;
        if (closeRequested) {
          if (closeStartedAt && Date.now() - closeStartedAt > 60000) {
            fail("Office 最终回写尚未完成，仍在查询服务端状态");
            closeStartedAt = 0;
          }
        } else if (Date.parse(latest.expires_at) - Date.now() <= 60000) {
          await applyStatus(await renewOfficeSession(target, session.session_id));
        }
      } catch (statusError: unknown) {
        if (active) setStatusError(`Office 会话状态读取失败：${officeErrorMessage(statusError)}`);
      } finally {
        polling = false;
      }
    };
    const initialize = async () => {
      // 避免 StrictMode 的首次效果清理创建多余的远程编辑会话。
      await Promise.resolve();
      if (!active) return;
      try {
        session = await createOfficeSession(target);
        if (!active) {
          await closeOfficeSession(target, session.session_id);
          return;
        }
        if (closeRequested) {
          return;
        }
        currentStatus = await getOfficeSession(target, session.session_id);
        savedVersion = currentStatus.saved_version;
        baselineInitialized = true;
        if (!active || closeRequested) return;
        if (currentStatus.status !== "editing" && currentStatus.status !== "saved") {
          throw new Error(currentStatus.error || "Office 编辑会话不可用");
        }
        const sdk = await loadOnlyOfficeScript(session.document_server_url);
        if (!active || closeRequested) return;
        const mount = mountRef.current;
        if (!mount) throw new Error("Office 编辑区域未挂载");
        const placeholder = document.createElement("div");
        placeholder.id = `office-editor-${session.session_id}`;
        mount.replaceChildren(placeholder);
        editor = new sdk.DocEditor(placeholder.id, {
          ...session.config,
          events: {
            onDocumentReady: () => {
              documentReady = true;
              window.clearTimeout(readyTimer);
              if (active && !closeRequested) setPhase("ready");
            },
            onDocumentStateChange: (event) => {
              if (event.data === true) hasChanges = true;
            },
            onRequestClose: beginClose,
            onError: (event) => {
              window.clearTimeout(readyTimer);
              const detail = typeof event.data === "object" ? event.data : undefined;
              fail(`Office 编辑器错误${detail?.errorCode === undefined ? "" : ` (${detail.errorCode})`}：${detail?.errorDescription || "文档编辑服务异常"}`);
            },
          },
        });
        if (!documentReady) readyTimer = window.setTimeout(() => {
          initializationFailed = true;
          beginClose();
          fail("Office 文档加载超时");
        }, 45000);
      } catch (initializationError: unknown) {
        if (!active) {
          message.error(`Office 会话清理失败：${officeErrorMessage(initializationError)}`);
          return;
        }
        initializationFailed = true;
        if (session) beginClose();
        fail(`Office 编辑器打开失败：${officeErrorMessage(initializationError)}`);
      } finally {
        initializing = false;
        if (active && closeRequested && session && !closeSubmitted) await sendClose();
      }
    };
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!hasChanges || currentStatus?.status === "closed") return;
      event.preventDefault();
      event.returnValue = "";
    };
    setPhase("loading");
    setError("");
    setStatusError("");
    setClosePending(false);
    setStoredVersion(null);
    setSavedAt(null);
    const timer = window.setInterval(() => void poll(), 3000);
    window.addEventListener("beforeunload", warnBeforeUnload);
    void initialize();
    return () => {
      active = false;
      window.clearInterval(timer);
      window.removeEventListener("beforeunload", warnBeforeUnload);
      if (session && !closeSubmitted && currentStatus?.status !== "closed" && currentStatus?.status !== "expired") {
        void closeOfficeSession(target, session.session_id).catch((cleanupError: unknown) => {
          message.error(`Office 会话清理失败：${officeErrorMessage(cleanupError)}`);
        });
      }
      destroyEditor();
    };
  }, [target.caseId, target.attachmentId, mountRef]);

  return { phase, error: [error, statusError].filter(Boolean).join("；"), closePending, savedAt, storedVersion, requestClose: () => closeAction.current?.() };
}
