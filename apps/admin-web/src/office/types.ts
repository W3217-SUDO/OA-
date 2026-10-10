export type OfficeEditorTarget = {
  caseId: number;
  attachmentId: number;
  name: string;
};

export type OfficeSessionStatus = {
  status: "editing" | "saved" | "closing" | "closed" | "expired" | "failed";
  close_ready: boolean;
  expires_at: string;
  saved_version: string | null;
  saved_at: string | null;
  error: string | null;
};

export type OnlyOfficeConfig = {
  documentType: "word";
  document: { key: string; title: string; fileType: string; url: string };
  editorConfig: { mode: "edit"; callbackUrl: string; [key: string]: unknown };
  token: string;
  [key: string]: unknown;
};

export type OfficeEditorSession = {
  session_id: string;
  attachment_id: number;
  name: string;
  document_server_url: string;
  config: OnlyOfficeConfig;
  expires_at: string;
  status: "editing";
  close_ready: boolean;
};

export type OnlyOfficeEvent = {
  data?: boolean | { errorCode?: number; errorDescription?: string };
};

export type OnlyOfficeEditor = {
  destroyEditor: () => void;
  requestClose: () => void;
  denyEditingRights: (message: string) => void;
};

export type OnlyOfficeApi = {
  DocEditor: new (id: string, config: OnlyOfficeConfig & {
    events: {
      onDocumentReady: () => void;
      onDocumentStateChange: (event: OnlyOfficeEvent) => void;
      onRequestClose: () => void;
      onError: (event: OnlyOfficeEvent) => void;
    };
  }) => OnlyOfficeEditor;
};
