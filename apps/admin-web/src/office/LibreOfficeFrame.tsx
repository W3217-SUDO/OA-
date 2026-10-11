import { Spin } from "antd";
import { useEffect, useRef } from "react";
import type { RefObject } from "react";
import type { LibreOfficeSession } from "./types";

type LibreOfficeFrameProps = {
  session: LibreOfficeSession;
  frameRef: RefObject<HTMLIFrameElement | null>;
  loading: boolean;
  blocked: boolean;
  onLoad: () => void;
  onError: () => void;
};

export function LibreOfficeFrame({ session, frameRef, loading, blocked, onLoad, onError }: LibreOfficeFrameProps) {
  const formRef = useRef<HTMLFormElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const submittedSession = useRef("");
  const frameName = `libreoffice-${session.session_id}`;

  useEffect(() => {
    if (submittedSession.current === session.session_id) return;
    if (!formRef.current || !frameRef.current) {
      onError();
      return;
    }
    try {
      formRef.current.submit();
      submittedSession.current = session.session_id;
    } catch {
      onError();
    }
  }, [session.session_id, frameRef, onError]);

  useEffect(() => {
    if (blocked) {
      frameRef.current?.blur();
      overlayRef.current?.focus();
    }
  }, [blocked, frameRef]);

  return <div style={{ flex: 1, minHeight: 0, position: "relative" }}>
    <form ref={formRef} method="post" action={session.editor_url} target={frameName} encType="application/x-www-form-urlencoded" style={{ display: "none" }}>
      <input type="hidden" name="access_token" value={session.access_token} readOnly />
      <input type="hidden" name="access_token_ttl" value={session.access_token_ttl} readOnly />
    </form>
    <div inert={blocked} style={{ width: "100%", height: "100%" }}>
      <iframe
        ref={frameRef}
        name={frameName}
        src="about:blank"
        title={session.filename}
        referrerPolicy="no-referrer"
        allow="clipboard-read; clipboard-write; fullscreen"
        style={{ display: "block", width: "100%", height: "100%", border: 0 }}
        onLoad={onLoad}
        onError={onError}
      />
    </div>
    {(loading || blocked) && <div ref={overlayRef} tabIndex={-1} aria-busy="true" style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", background: "rgba(255,255,255,0.85)" }}><Spin /></div>}
  </div>;
}
