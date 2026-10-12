import { useCallback, useEffect, useRef, useState } from "react";
import type { AttachmentRow } from "../types";

export type CaseInvoiceBatchState = {
    sourceAttachmentIds: number[];
    attachmentIds: number[];
    rows: AttachmentRow[];
    loading: boolean;
    error: string;
    resultUnconfirmed: boolean;
};

export type CaseInvoiceImportResult = {
    processed: number;
    matched: number;
    unmatched: number;
    result_attachment_ids: number[];
};

const emptyBatch = (): CaseInvoiceBatchState => ({ sourceAttachmentIds: [], attachmentIds: [], rows: [], loading: false, error: "", resultUnconfirmed: false });

export function useCaseInvoiceBatch(active: boolean) {
    const [state, setState] = useState(emptyBatch);
    const current = useRef(state);
    const sequence = useRef(0);
    const enabled = useRef(false);

    const update = useCallback((requestId: number, patch: Partial<CaseInvoiceBatchState>) => {
        if (!enabled.current || requestId !== sequence.current) return;
        current.current = { ...current.current, ...patch };
        setState(current.current);
    }, []);

    useEffect(() => {
        enabled.current = active;
        sequence.current += 1;
        current.current = emptyBatch();
        setState(current.current);
        return () => {
            enabled.current = false;
            sequence.current += 1;
        };
    }, [active]);

    const begin = useCallback((replace = false) => {
        if (!enabled.current || current.current.loading) return undefined;
        const requestId = ++sequence.current;
        // 新上传先结束旧批次的展示；失败不能把旧成功项当成本次结果。
        update(requestId, { ...(replace ? emptyBatch() : {}), loading: true, error: "" });
        return requestId;
    }, [update]);

    const isCurrent = useCallback((requestId: number) => enabled.current && requestId === sequence.current, []);
    const pendingIds = state.sourceAttachmentIds.filter(id => state.rows.some(row => row.id === id && row.record_id === null));
    const error = state.resultUnconfirmed
        ? `导入结果未确认：只能查询源文件状态，完整结果清单未恢复，请勿重复导入。${state.error}`
        : state.error;
    return { ...state, error, current, begin, update, isCurrent, canImport: active && !state.loading && !state.error && !state.resultUnconfirmed && pendingIds.length > 0 };
}

export type CaseInvoiceBatch = ReturnType<typeof useCaseInvoiceBatch>;
export type LoadCaseInvoiceBatch = (attachmentIds?: number[], requestId?: number) => Promise<void>;
