import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { CONFLICT_REVIEW_UPDATED_EVENT } from "./events";
import type { ConflictRecordState } from "./types";

export function useConflictReview(recordId?: number, active = true) {
  const [loaded, setLoaded] = useState<{ recordId: number; state: ConflictRecordState } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision((value) => value + 1), []);
  useEffect(() => {
    setLoaded(null);
    setError("");
    if (!active || !recordId) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true);
    api.get<ConflictRecordState>(`/conflict-reviews/record/${recordId}`, { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setLoaded({ recordId, state: data }); })
      .catch((cause: any) => {
        if (!controller.signal.aborted && cause?.code !== "ERR_CANCELED") setError(cause?.response?.data?.detail || "利益冲突审查状态加载失败");
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [recordId, active, revision]);
  useEffect(() => {
    const listener = () => reload();
    window.addEventListener(CONFLICT_REVIEW_UPDATED_EVENT, listener);
    return () => window.removeEventListener(CONFLICT_REVIEW_UPDATED_EVENT, listener);
  }, [reload]);
  const state = loaded && loaded.recordId === recordId ? loaded.state : null;
  return { recordId, state, loading, error, reload, blocked: Boolean(active && recordId && (!state || loading || error || state.blocking)) };
}

export type ConflictReviewGuard = ReturnType<typeof useConflictReview>;
