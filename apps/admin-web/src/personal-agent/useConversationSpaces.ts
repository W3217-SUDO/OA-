import { useRef, useState } from "react";
import type { ConversationWorkspace } from "./types";
import { conversationWorkspaceKey } from "./conversationWorkspace";

export type ConversationView = { workspace?: ConversationWorkspace; revision: number };

export function useConversationSpaces() {
  const [workspace, setWorkspace] = useState<ConversationWorkspace>();
  const view = useRef<ConversationView>({ revision: 0 });
  const capture = () => ({ ...view.current });
  const isCurrent = (ticket: ConversationView) => ticket.revision === view.current.revision
    && (ticket.workspace ? conversationWorkspaceKey(ticket.workspace) : undefined) === (view.current.workspace ? conversationWorkspaceKey(view.current.workspace) : undefined);
  const change = (next?: ConversationWorkspace) => {
    view.current = { workspace: next, revision: view.current.revision + 1 };
    setWorkspace(next);
    return capture();
  };
  return { workspace, capture, isCurrent, change };
}
