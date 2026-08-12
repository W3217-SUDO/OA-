# Parity Ledger

The current source of truth is the locally running legacy application:
`http://localhost:8091/Console/Index`.

| ID | Domain | Legacy source | Legacy database boundary | FastAPI | Vue 3 | Automated test | Browser acceptance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P-001 | Authorization | `SYS_Menu`, `HR_Role`, `HR_Role_Permissions`, `HR_Staff`, `IPR_User`, `IPR_UserRole` | Existing tables only | Staff-scoped legacy menu tree complete | Legacy navigation shell complete | Passed: backend role/menu contract tests; frontend tests/build | Passed: `5174` loads staff `1` menu tree and expands 用印中心 |
| P-004 | Official document / seal | `Areas/AWS/OfficialDocument*`; menu `8101` | `AWS_OfficialDocument`, `AWS_OfficialDocument_Audit`, `AWS_OfficialDocument_File`; soft links via `CaseNo`, `ContractNo`, `CustomerNo`, `OfficialDocumentGuid` | Read-only list contract complete; write workflow pending | List, filters, status-menu routing and empty state complete; write controls pending | Passed: status/select and response-envelope tests; frontend build | Passed: old list captured and local pending-status list verified; write workflow pending |
| P-002 | DingTalk extension | New-system DingTalk module | `EXT_DingTalk*` only, references legacy identities | Pending | Pending | Pending | Pending |
| P-003 | Agent extension | New-system agent module | `EXT_Agent*` only, references legacy case/customer/contract keys | Pending | Pending | Pending | Pending |

## Rules

- A line cannot be marked browser-accepted from unit tests alone.
- New extension tables must have explicit links to the legacy identifier they
  reference. They must not change old table semantics or replace old workflow
  state.
- A legacy module is not considered migrated until its route, menu item,
  role permission, fields, read/write behavior, and layout have entries in the
  ledger.

## Official Document Inventory

- Root menu `8101` has three entry groups: 我的用印申请, 用印审核, 行政用印.
- The legacy list has filters for application number, applicant, application
  date range, case number, contract number, customer name, status, type, and
  file name; its table exposes application, document, seal, customer, and
  audit information.
- Application types are 合同用印, 案件用印, 行政用印. The captured status options
  are 待审核, 已审待用印, 审核拒绝, 已撤回, 已用印.
- Creation flows exist for a standalone application and for applications
  initiated from a contract or case. The contract/case flows carry the related
  contract, customer, and files into the official-document record.
