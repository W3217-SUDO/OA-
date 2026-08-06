# 8.4 Excel Browser Evidence

Target: `http://150.158.3.104:8089/`

| Excel row | Status | Browser evidence |
| --- | --- | --- |
| 2 | Accepted | Employee view shows the five read-only tabs. Employee modification provides the new leave, new matter, archive upload, and commission configuration actions. No mutation was submitted. |
| 3 | Accepted | The customer-manager directory on the new-customer page shows HR person names such as Test2 and Fan Wenling rather than the ceshi/fwl account identifiers. Accounts without an active HR record are excluded. No customer form was saved. |
| 4 | Accepted | The customer source and contact-account controls use the same person labels. Verified directory names render as names; a verified English HR name renders as English, while an unmatched account renders as Name pending maintenance. No customer form was saved. |
| 5 | Accepted | On the new-customer page, Test2 and Fan Wenling were selected consecutively as customer managers. Both name tags remained visible at the same time. The form was not saved. |
| 6 | Accepted | The contact-account control accepted Test2 and Fan Wenling consecutively and retained both visible name tags. The form was not saved. |
| 7 | Accepted | Clicking the contract count 7 for customer Test Customer 8.3 opened My Contracts with that customer name populated and exactly seven matching contract rows. It no longer opens the unfiltered contract list. |
| 8 | Accepted | In My Customers, after selecting Test Customer 8.3, More Actions now exposes Release to Public Pool. It opens a confirmation dialog explaining the customer will leave the current owner and enter the public pool. The dialog was cancelled; no customer data was changed. |
| 9 | Accepted | In Share Customer for Test Customer 8.3, searching `范` now returns Fan Wenling rather than role-text records. After selecting Fan Wenling, searching `测` returns Test2 and both selected person tags remain visible. The dialog was cancelled; no share relationship was written. |
| 10 | Accepted | In the sidebar, Customer Management was open. Opening Contract Center automatically closed Customer Management, leaving only Contract Center expanded. No application data was changed. |
| 11 | Accepted | Customer detail -> new contract pre-fills customer `测试客户8.3` and title `测试客户8.3合同`; the title input is enabled. Direct contract-center new contract leaves customer and title blank. The compact legacy-style number is `SHHT` plus two-digit year and five-digit day sequence, replacing the former timestamp-length number. No draft was submitted. |
| 12 | Accepted | No screenshot was embedded in this row. Contract New contains no approver-settings control. Contract approvers are configured by an administrator from the employee profile, then used by the submission workflow. No setting was changed. |
| 13 | Accepted | No screenshot was embedded in this row. Contract New shows an editable Contract Name textbox and a selectable Contract Category combobox; neither is fixed to a hard-coded value. No draft was submitted. |
| 15 | Accepted | Contract New shows the four ordered stages: Contract Basic Information, Submit for Approval, Contract Approval, and Contract Seal. The page supports completing approval without requiring a seal request. No draft was submitted. |

Server validation for row 11: `node --test contractNewDefaults.test.mjs` (8/8), `npm run build`, API health `ok`, and HTTP 8089 `200`.

Server validation for rows 3-4: `node --test contractPeoplePresentation.test.mjs customerUiContractParityI10.test.mjs` (11/11), `npm run build`, and HTTP 8089 `200`.
