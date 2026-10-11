-- 沪知原生产回款已逐笔进入 incoming_payments；按认领和分配事实恢复工作流状态。
-- 执行前必须完成 incoming_payments 的限定范围备份及校验。
BEGIN;

DO $$
DECLARE
    source_count bigint;
    active_count bigint;
    matched_count bigint;
    mismatch_count bigint;
BEGIN
    SELECT count(*) INTO source_count
    FROM incoming_payments
    WHERE source_kind = 'hz_crm_20260930';

    SELECT count(*) INTO active_count
    FROM legacy_finance_records
    WHERE source_table = 'FAM_AR_Payment' AND is_active;

    SELECT count(*), count(*) FILTER (
        WHERE round(i.amount::numeric, 2) <> round(l.primary_amount::numeric, 2)
           OR i.received_date <> (l.source_payload->>'CashedDate')::date
           OR abs(i.allocated_amount::numeric - COALESCE((
               SELECT sum((allocation->>'amount')::numeric)
               FROM jsonb_array_elements(i.allocations::jsonb) AS allocation
           ), 0)) > 0.005
    ) INTO matched_count, mismatch_count
    FROM legacy_finance_records AS l
    JOIN incoming_payments AS i
      ON i.receipt_no = concat('HZ-RCPT-', l.source_payload->>'PaymentId')
     AND i.source_kind = 'hz_crm_20260930'
    WHERE l.source_table = 'FAM_AR_Payment' AND l.is_active;

    IF source_count <> active_count OR matched_count <> active_count OR mismatch_count <> 0 THEN
        RAISE EXCEPTION 'Imported receipt source mapping is incomplete or inconsistent: source %, active %, matched %, mismatched %',
            source_count, active_count, matched_count, mismatch_count;
    END IF;

    IF EXISTS (
        SELECT 1 FROM incoming_payments
        WHERE source_kind = 'hz_crm_20260930'
          AND status <> '源状态未记录'
          AND status <> CASE
              WHEN allocated_amount > 0 AND allocated_amount >= amount - 0.005 THEN '已分配'
              WHEN allocated_amount > 0 THEN '部分分配'
              WHEN trim(COALESCE(claimed_customer, '')) <> '' THEN '待分配'
              ELSE '待认领'
          END
    ) THEN
        RAISE EXCEPTION 'Imported receipt status changed after preflight';
    END IF;
END $$;

UPDATE incoming_payments
SET status = CASE
        WHEN allocated_amount > 0 AND allocated_amount >= amount - 0.005 THEN '已分配'
        WHEN allocated_amount > 0 THEN '部分分配'
        WHEN trim(COALESCE(claimed_customer, '')) <> '' THEN '待分配'
        ELSE '待认领'
    END
WHERE source_kind = 'hz_crm_20260930'
  AND status = '源状态未记录';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM incoming_payments
        WHERE source_kind = 'hz_crm_20260930' AND status = '源状态未记录'
    ) THEN
        RAISE EXCEPTION 'Imported receipt status restoration is incomplete';
    END IF;
END $$;

COMMIT;
