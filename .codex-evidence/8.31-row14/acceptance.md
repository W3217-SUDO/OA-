# 8.31 row 14 acceptance

## Scope

- Workbook: `OA系统对接8.31.xlsx`, sheet `8.31`, row 14.
- Restored the legacy payment-unit workflow for both law-firm and platform fees.
- Existing units are keyword-searchable and expose payee, bank, and account.
- Missing units can be created with nature, payee, bank, and account, then are saved to `system_parameters/payment_type` and selected automatically.
- External payment submission accepts the payment-type master ID and snapshots authoritative master data. Internal settlement keeps its existing free-text flow.

## Automated verification

- Backend: `python -m unittest case_payment_unit_row14_test.py case_finance_closure_contract_test.py finance_payment_request_row28_contract_test.py` - 10/10 passed.
- Backend syntax: `python -m py_compile app/main.py` - passed.
- Frontend: `node --test casePaymentUnitRow14.test.mjs casePlatformAgencyFeeRow13.test.mjs caseAgencyFeeTypesRow12.test.mjs` - 8/8 passed after the final UI lifecycle adjustment.
- Production build: `npm.cmd run build` - passed, package remains `1.1.36`, 5639 modules transformed; only the existing chunk-size warning remains.
- `git diff --check` - passed.

## Local Chrome acceptance

- Chrome only; Codex IAB was not used.
- Law-firm fee `CODEX-831-R14-FIRM`: searched `已知收款`, selected `第14行已知收款单位｜第14行测试银行｜R14-KNOWN-ACCOUNT`, verified bank/account summary, and submitted 1400. The refreshed fee table shows requested amount 1400.
- Platform fee `CODEX-831-R14-PLATFORM`: opened the old-style seven-column payment interface, created `CODEX第14行新增收款单位` with `第14行新增银行` and `R14-NEW-ACCOUNT`, verified automatic selection, and submitted 1410. The refreshed table shows requested amount 1410.
- System center `system-parameters-payment`: the created unit is visible with nature, payee, bank, and account.
- Isolated SQLite verification: fee 18 stores payment type 110 and the known authoritative unit data; fee 19 stores payment type 111 and the newly-created authoritative unit data. Both are `待审批`.
- Browser logs contain only pre-existing Ant Design deprecation/context warnings. The row-14 `useForm` lifecycle warning was fixed with a pre-rendered modal and did not recur after reload. No runtime exception or failed business request was observed.
- API logs contain no `Traceback`, `ERROR`, exception, or HTTP 500 entry.

## Evidence

`C:\Users\Administrator\Desktop\OA系统\问题\_返工验收\8.31_第14行\local`

- `01-existing-payment-unit-selected.png`
- `02-new-payment-unit-modal.png`
- `03-new-payment-unit-selected.png`
- `04-platform-payment-submitted.png`
- `05-system-parameter-payment-unit.png`
- `06-platform-payment-persisted.png`

## Final source gate

Re-read the complete row-14 text and all three anchored screenshots (`26_row14_colC.png`, `27_row14_colD.png`, `28_row14_colD.png`). The implementation and acceptance cover both the new-system defect and the two old-system target states.
