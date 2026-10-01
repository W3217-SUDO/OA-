import { useCallback, useEffect, useState } from "react";
import { message } from "antd";
import type { FormInstance } from "antd";
import { api } from "../api";
import { sealAttachmentListFailureMessage, sealFilePagination } from "../sealWorkflowPolicy";
import type { AttachmentRow } from "./types";

type SourceAttachmentsOptions = {
  createOpen: boolean;
  sourceRecordId: number | null;
  createForm: Pick<FormInstance, "getFieldValue" | "setFieldValue">;
};

type ResetOptions = { clearLoading?: boolean; clearSelection?: boolean };

export function useSealSourceAttachments({ createOpen, sourceRecordId, createForm }: SourceAttachmentsOptions) {
  const [attachments, setAttachments] = useState<AttachmentRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(sealFilePagination.defaultPageSize);
  const [total, setTotal] = useState(0);

  const reset = useCallback(({ clearLoading = false, clearSelection = false }: ResetOptions = {}) => {
    setAttachments([]);
    setPage(1);
    setPageSize(sealFilePagination.defaultPageSize);
    setTotal(0);
    if (clearLoading) setLoading(false);
    if (clearSelection) createForm.setFieldValue("source_attachment_ids", []);
  }, [createForm]);

  useEffect(() => {
    if (!createOpen) return;
    if (sourceRecordId === null) {
      reset({ clearSelection: true });
      return;
    }
    let active = true;
    const nextPageSize = sealFilePagination.defaultPageSize;
    setLoading(true);
    setPage(1);
    setPageSize(nextPageSize);
    setTotal(0);
    api.get("/attachments", { params: { record_id: sourceRecordId, page: 1, page_size: nextPageSize } })
      .then(({ data }) => {
        if (!active) return;
        const items: AttachmentRow[] = Array.isArray(data.items) ? data.items : [];
        setAttachments(items);
        setPage(Number(data.page) || 1);
        setPageSize(Number(data.page_size) || nextPageSize);
        setTotal(Number(data.total) || items.length);
        const availableIds = new Set(items.map((item) => Number(item.id)));
        const selectedIds = createForm.getFieldValue("source_attachment_ids");
        if (Array.isArray(selectedIds)) {
          const nextIds = selectedIds.map((id) => Number(id)).filter((id) => Number.isFinite(id) && availableIds.has(id));
          if (nextIds.length !== selectedIds.length) createForm.setFieldValue("source_attachment_ids", nextIds);
        }
      })
      .catch((error: unknown) => {
        if (!active) return;
        setAttachments([]);
        const detail = (error as { response?: { data?: { detail?: string }; status?: number } })?.response;
        message.error(detail?.data?.detail || sealAttachmentListFailureMessage(detail?.status));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [createForm, createOpen, reset, sourceRecordId]);

  const loadMore = async () => {
    if (sourceRecordId === null || loading) return;
    if (total > 0 && attachments.length >= total) return;
    const nextPage = page + 1;
    setLoading(true);
    try {
      const { data } = await api.get("/attachments", {
        params: { record_id: sourceRecordId, page: nextPage, page_size: pageSize },
      });
      const items: AttachmentRow[] = Array.isArray(data.items) ? data.items : [];
      setAttachments((current) => {
        const seen = new Set(current.map((item) => Number(item.id)));
        return [...current, ...items.filter((item) => !seen.has(Number(item.id)))];
      });
      setPage(Number(data.page) || nextPage);
      setPageSize(Number(data.page_size) || pageSize);
      setTotal(Number(data.total) || total);
    } catch (error: unknown) {
      const detail = (error as { response?: { data?: { detail?: string }; status?: number } })?.response;
      message.error(detail?.data?.detail || sealAttachmentListFailureMessage(detail?.status));
    } finally {
      setLoading(false);
    }
  };

  const selectAll = async () => {
    if (sourceRecordId === null || loading) return;
    setLoading(true);
    try {
      const allItems: AttachmentRow[] = [];
      let nextPage = 1;
      let nextTotal = 0;
      let nextPageSize = pageSize || sealFilePagination.defaultPageSize;
      while (allItems.length < nextTotal || nextPage === 1) {
        const { data } = await api.get("/attachments", {
          params: { record_id: sourceRecordId, page: nextPage, page_size: nextPageSize },
        });
        const items: AttachmentRow[] = Array.isArray(data.items) ? data.items : [];
        const seen = new Set(allItems.map((item) => Number(item.id)));
        allItems.push(...items.filter((item) => !seen.has(Number(item.id))));
        nextTotal = Number(data.total) || allItems.length;
        nextPageSize = Number(data.page_size) || nextPageSize;
        const resolvedPage = Number(data.page) || nextPage;
        if (!items.length || allItems.length >= nextTotal) break;
        nextPage = resolvedPage + 1;
      }
      setAttachments(allItems);
      setPage(Math.max(1, nextPage));
      setPageSize(nextPageSize);
      setTotal(nextTotal || allItems.length);
      createForm.setFieldValue("source_attachment_ids", allItems.map((item) => item.id));
    } catch (error: unknown) {
      const detail = (error as { response?: { data?: { detail?: string }; status?: number } })?.response;
      message.error(detail?.data?.detail || sealAttachmentListFailureMessage(detail?.status));
    } finally {
      setLoading(false);
    }
  };

  return { attachments, loading, total, reset, loadMore, selectAll };
}
