import { message } from "antd";
import { useEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import { postCollaboraMessage, prepareCollaboraHost, readCollaboraMessage, validateLibreOfficeSession } from "./collaboraPostMessage";
import { closeLibreOfficeSession, createLibreOfficeSession, getLibreOfficeSession, libreOfficeError } from "./libreOfficeApi";
import type { LibreOfficeEditorTarget, LibreOfficeSession, LibreOfficeSessionStatus } from "./types";

type SessionActions = { save: () => void; close: () => void; frameLoaded: () => void; frameFailed: () => void };
type SessionCallbacks = { onStored: () => Promise<unknown>; onClosed: () => void };

export function useLibreOfficeSession(target: LibreOfficeEditorTarget, frameRef: RefObject<HTMLIFrameElement | null>, callbacks: SessionCallbacks) {
  const targetKey = target.scope === "personal" ? `personal:${target.fileId}` : `case:${target.caseId}:${target.attachmentId}`;
  const [session, setSession] = useState<LibreOfficeSession | null>(null);
  const [status, setStatus] = useState<LibreOfficeSessionStatus | null>(null);
  const [ready, setReady] = useState(false);
  const [closing, setClosing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [pollError, setPollError] = useState("");
  const callbacksRef = useRef(callbacks);
  const actionsRef = useRef<SessionActions | null>(null);
  callbacksRef.current = callbacks;

  useEffect(() => {
    let mounted = true;
    let completed = false;
    let config: LibreOfficeSession | null = null;
    let current: LibreOfficeSessionStatus | null = null;
    let frameReady = false;
    let documentReady = false;
    let closeRequested = false;
    let closePosted = false;
    let closeSent = false;
    let closeSaveAcknowledged = false;
    let closeUnmodified = false;
    let closeBeforeReady = false;
    let frameSubmitted = false;
    let openingFinished = false;
    let failed = false;
    let pendingSave: "manual" | "close" | null = null;
    let observedVersion: string | null = null;
    let pollPromise: Promise<LibreOfficeSessionStatus | null> | null = null;
    let pollTimer: number | undefined;
    let loadTimer: number | undefined;
    let commandTimer: number | undefined;

    const fail = (reason: string) => { failed = true; if (mounted) setError(reason); };
    const complete = () => {
      if (!mounted || completed) return;
      completed = true;
      window.clearTimeout(commandTimer);
      callbacksRef.current.onClosed();
    };
    const applyStatus = (value: LibreOfficeSessionStatus) => {
      if (!config || value.session_id !== config.session_id || !value.version) throw new Error("服务器返回的编辑会话或版本不匹配");
      current = value;
      setStatus(value);
      if (observedVersion !== null && observedVersion !== value.version) {
        void callbacksRef.current.onStored().catch((cause: unknown) => fail(libreOfficeError(cause, "刷新附件列表")));
      }
      observedVersion = value.version;
      if (value.save_status === "error") fail(value.error || "服务器未完成文档保存，请重试保存");
      if (value.status === "expired") {
        documentReady = false;
        closeRequested = false;
        closeSaveAcknowledged = false;
        setReady(false);
        setClosing(false);
        window.clearTimeout(commandTimer);
        fail("编辑会话已过期，未确认的修改不能视为已保存");
      }
      if (value.status === "closed") {
        documentReady = false;
        setReady(false);
        if (value.save_status !== "error") complete();
      }
      if (closeSaveAcknowledged) void finishClose();
    };
    const poll = (): Promise<LibreOfficeSessionStatus | null> => {
      if (pollPromise) return pollPromise;
      if (!config || completed) return Promise.resolve(current);
      pollPromise = getLibreOfficeSession(target, config.session_id).then((value) => {
        if (mounted) { applyStatus(value); setPollError(""); }
        return value;
      }).catch((cause: unknown) => {
        if (mounted) setPollError(libreOfficeError(cause, "查询编辑会话"));
        return null;
      }).finally(() => { pollPromise = null; });
      return pollPromise;
    };
    const send = (MessageId: string, Values?: Record<string, unknown> | null) => {
      if (!config) throw new Error("编辑会话尚未创建");
      postCollaboraMessage(frameRef.current, config.editor_origin, { MessageId, Values });
    };
    const startSave = (purpose: "manual" | "close") => {
      if (!documentReady || pendingSave || closeSent) return;
      pendingSave = purpose;
      setSaving(true);
      send("Action_Save", { DontTerminateEdit: false, DontSaveIfUnmodified: false, Notify: true });
      window.clearTimeout(commandTimer);
      commandTimer = window.setTimeout(() => fail("保存确认超时，编辑器仍保留，不能视为已保存或关闭"), 60000);
    };
    const abortClose = (reason: string) => {
      closeRequested = false;
      closePosted = false;
      closeSaveAcknowledged = false;
      setClosing(false);
      fail(reason);
    };
    const finishClose = async () => {
      if (!mounted || completed || !config || !current || closePosted || closeSent || !closeSaveAcknowledged) return;
      if (current.save_status === "error") { abortClose(current.error || "服务器保存失败，不能关闭编辑器"); return; }
      if (current.save_status === "saving") return;
      if (current.save_status !== "saved" && !closeUnmodified) return;
      closePosted = true;
      try {
        const value = await closeLibreOfficeSession(target, config.session_id);
        if (!mounted) return;
        applyStatus(value);
        if (completed || value.status === "expired") return;
        if (value.status !== "closing") throw new Error("服务器未进入关闭状态，编辑器仍保留");
        closeSent = true;
        send("Action_Close", null);
        commandTimer = window.setTimeout(() => fail("关闭确认超时，服务器尚未确认解锁，请勿视为已关闭"), 60000);
      } catch (cause) { abortClose(libreOfficeError(cause, "关闭编辑会话")); }
    };
    const notifyUnreadyClose = () => {
      if (!closeBeforeReady || !closePosted || closeSent || completed || current?.status !== "closing") return false;
      if (!frameReady && !documentReady) return false;
      // 未加载的文档不接受 Action_Close，使用引擎专用的加载期结束指令。
      send(documentReady ? "Action_Close" : "Close_Session", null);
      closeSent = true;
      closeRequested = true;
      setClosing(true);
      window.clearTimeout(loadTimer);
      window.clearTimeout(commandTimer);
      commandTimer = window.setTimeout(() => {
        closeRequested = false;
        setClosing(false);
        fail("关闭确认超时，服务器尚未确认解锁，编辑器仍保留，可重试关闭");
      }, 60000);
      return true;
    };
    const continueClose = () => {
      if (closeRequested && documentReady && !pendingSave && !closeSent && !closeSaveAcknowledged) startSave("close");
    };
    const requestClose = async () => {
      if (completed || closeRequested) return;
      if (!config) {
        if (openingFinished && failed) complete();
        else { closeRequested = true; setClosing(true); }
        return;
      }
      if (current?.status === "expired" || current?.status === "closed") { complete(); return; }
      closeRequested = true;
      setClosing(true);
      try {
        if (frameSubmitted && documentReady && !closeBeforeReady) continueClose();
        else {
          closeBeforeReady = true;
          const value = await closeLibreOfficeSession(target, config.session_id);
          if (!mounted) return;
          applyStatus(value);
          if (completed) return;
          if (value.status === "expired") { closeRequested = false; setClosing(false); return; }
          if (value.status !== "closing") throw new Error("服务器未进入关闭状态，编辑器仍保留");
          closePosted = true;
          closeSent = false;
          if (!notifyUnreadyClose()) {
            closeRequested = false;
            setClosing(false);
            fail("编辑器尚未建立通信，服务器会话未解锁，编辑器仍保留，可重试关闭");
          }
        }
      } catch (cause) {
        abortClose(libreOfficeError(cause, "关闭编辑会话"));
      }
    };
    const onMessage = (event: MessageEvent) => {
      if (!config || completed) return;
      try {
        const incoming = readCollaboraMessage(event, frameRef.current, config.editor_origin);
        if (!incoming) return;
        if (incoming.MessageId === "App_LoadingStatus") {
          if (incoming.Values?.Status === "Frame_Ready") {
            frameReady = true;
            prepareCollaboraHost(frameRef.current, config.editor_origin);
            notifyUnreadyClose();
          }
          if (incoming.Values?.Status === "Document_Loaded" && current?.status !== "expired" && current?.status !== "closed") {
            documentReady = true;
            window.clearTimeout(loadTimer);
            if (closeBeforeReady) notifyUnreadyClose();
            else { setReady(true); continueClose(); }
          }
        } else if (incoming.MessageId === "UI_Close") {
          void requestClose();
        } else if (incoming.MessageId === "Action_Save_Resp" && pendingSave) {
          const purpose = pendingSave;
          pendingSave = null;
          setSaving(false);
          window.clearTimeout(commandTimer);
          const unmodified = incoming.Values?.result === "unmodified";
          if (incoming.Values?.success !== true && !unmodified) {
            abortClose("编辑器保存失败，文档仍保留，请重试保存");
            return;
          }
          // 引擎事件仅协调结束编辑；实际保存和关闭以服务器状态为准。
          void (async () => {
            if (pollPromise) await pollPromise;
            if (!mounted || completed) return;
            if (purpose === "close") { closeSaveAcknowledged = true; closeUnmodified = unmodified; }
            const value = await poll();
            if (!mounted || completed || !value) return;
            if (purpose === "close") await finishClose();
            else continueClose();
          })().catch((cause: unknown) => fail(libreOfficeError(cause, "结束编辑器")));
        } else if (incoming.MessageId === "Action_Load_Resp" && incoming.Values?.success === false) {
          fail("文档加载失败，编辑器尚未就绪");
        }
      } catch (cause) { fail(libreOfficeError(cause, "编辑器通信")); }
    };
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (config && !completed && current?.status !== "expired") { event.preventDefault(); event.returnValue = ""; }
    };
    actionsRef.current = {
      save: () => {
        try { if (!closeRequested) { setError(""); startSave("manual"); } }
        catch (cause) { pendingSave = null; setSaving(false); fail(libreOfficeError(cause, "请求文档保存")); }
      },
      close: () => { void requestClose(); },
      frameLoaded: () => {
        if (!config || completed) return;
        try { prepareCollaboraHost(frameRef.current, config.editor_origin); }
        catch (cause) { fail(libreOfficeError(cause, "准备编辑器通信")); }
      },
      frameFailed: () => fail("编辑器页面加载失败"),
    };
    window.addEventListener("message", onMessage);
    window.addEventListener("beforeunload", beforeUnload);

    void (async () => {
      // 延后到有效 effect，避免 StrictMode 探测创建重复会话。
      await Promise.resolve();
      if (!mounted) return;
      try {
        config = await createLibreOfficeSession(target);
        if (!mounted) {
          await closeLibreOfficeSession(target, config.session_id);
          return;
        }
        validateLibreOfficeSession(config, window.location.origin);
        const initial = await getLibreOfficeSession(target, config.session_id);
        if (!mounted) return;
        applyStatus(initial);
        if (completed || initial.status === "expired") return;
        if (closeRequested) {
          const value = await closeLibreOfficeSession(target, config.session_id);
          if (mounted) applyStatus(value);
          return;
        }
        frameSubmitted = true;
        setSession(config);
        loadTimer = window.setTimeout(() => fail("文档加载超时，编辑会话尚未就绪"), 60000);
      } catch (cause) {
        if (mounted) fail(libreOfficeError(cause, "打开文档"));
        else message.error(libreOfficeError(cause, "释放未打开的编辑会话"));
        if (closeRequested && mounted) { closeRequested = false; setClosing(false); }
      } finally {
        openingFinished = true;
      }
    })();
    const schedulePoll = () => {
      pollTimer = window.setTimeout(() => {
        if (!mounted || completed) return;
        void poll().then(() => { if (mounted && !completed) schedulePoll(); });
      }, 2000);
    };
    schedulePoll();
    return () => {
      mounted = false;
      actionsRef.current = null;
      window.clearTimeout(pollTimer);
      window.clearTimeout(loadTimer);
      window.clearTimeout(commandTimer);
      window.removeEventListener("message", onMessage);
      window.removeEventListener("beforeunload", beforeUnload);
    };
  }, [targetKey, frameRef]);

  return {
    session, status, ready, closing, saving, error, pollError,
    save: () => actionsRef.current?.save(),
    close: () => actionsRef.current?.close(),
    frameLoaded: () => actionsRef.current?.frameLoaded(),
    frameFailed: () => actionsRef.current?.frameFailed(),
  };
}
