import { Button } from "antd";
import type { CaseLogRow } from "../types";

interface CaseLogEntryProps {
  log: CaseLogRow;
  personDisplayName: (source: unknown, displayName?: unknown) => string;
  onOpen: (log: CaseLogRow) => void;
}

export function CaseLogEntry({ log, personDisplayName, onOpen }: CaseLogEntryProps) {
  return (
    <Button className="case-log-entry" type="text" block onClick={() => onOpen(log)}>
      <time className="case-log-entry-time" dateTime={log.created_at}>{log.created_at}</time>
      <span className="case-log-entry-operator">{personDisplayName(log.operator, log.operator_display_name)}</span>
      <span className="case-log-entry-content">{log.content}</span>
    </Button>
  );
}
