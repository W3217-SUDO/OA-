export type LibreOfficeEditorTarget = {
  caseId: number;
  attachmentId: number;
  filename: string;
};

export type LibreOfficeSession = {
  session_id: string;
  editor_url: string;
  editor_origin: string;
  postmessage_origin: string;
  access_token: string;
  access_token_ttl: number;
  expires_at: string;
  filename: string;
};

export type CollaboraMessage = {
  MessageId: string;
  Values?: Record<string, unknown> | null;
};

export type LibreOfficeSessionStatus = {
  session_id: string;
  status: "opening" | "active" | "closing" | "closed" | "expired";
  save_status: "idle" | "saving" | "saved" | "error";
  version: string;
  last_saved_at: string | null;
  error: string | null;
  expires_at: string;
  lease_expires_at: string | null;
};
