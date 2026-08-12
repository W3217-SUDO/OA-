# Parity Ledger

The current source of truth is the locally running legacy application:
`http://localhost:8091/Console/Index`.

| ID | Domain | Legacy source | Legacy database boundary | FastAPI | Vue 3 | Automated test | Browser acceptance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P-001 | Authorization | `SYS_Menu`, `HR_Role`, `HR_Role_Permissions`, `HR_Staff`, `IPR_User`, `IPR_UserRole` | Existing tables only | Pending | Pending | Pending | Pending |
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
