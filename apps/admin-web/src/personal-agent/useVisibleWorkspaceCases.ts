import { useEffect, useState } from "react";
import { api } from "../api";
import { errorText, type WorkspaceCase } from "./types";

export function useVisibleWorkspaceCases(active: boolean, keyword: string, includeArchived = false) {
  const [items, setItems] = useState<WorkspaceCase[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    setLoading(true); setError("");
    const timer = window.setTimeout(() => {
      void api.get<{ items: WorkspaceCase[] }>("/records", {
        params: { module: "case", keyword, page: 1, page_size: 50, exclude_archived: !includeArchived }, signal: controller.signal,
      }).then(({ data }) => { if (!controller.signal.aborted) setItems(data.items); })
        .catch((failure) => { if (!controller.signal.aborted) setError(errorText(failure, "可访问案件加载失败")); })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 250);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [active, keyword, revision, includeArchived]);
  return { items, loading, error, retry: () => setRevision((value) => value + 1) };
}
