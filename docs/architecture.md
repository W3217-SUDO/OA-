# Architecture Boundary

## Core parity layer

- FastAPI exposes APIs that reproduce legacy controllers, status transitions,
  permission checks, numbering rules, and stored-procedure behavior.
- SQLAlchemy maps the existing SQL Server schema without renaming or reshaping
  legacy fields.
- Vue 3 reproduces the legacy menu tree, tabs, forms, tables, dialogs, and
  page layout. The old running page is the screenshot comparison baseline.
- Relationships absent from SQL Server foreign keys are recovered from C#
  controllers, ViewModels, Razor pages, JavaScript, and stored procedures and
  recorded in a relationship registry.

## Extension layer

- DingTalk identity mapping, synchronization, ingestion jobs, notification
  delivery, retries, and delivery logs live in an extension schema.
- Agent threads, skills, checkpoints, documents, proposed actions, approvals,
  and audit records live in an extension schema.
- Extensions reference stable legacy business identifiers but never redefine
  ownership, permissions, or workflow state.
- Agent write operations retain explicit human approval and execute through
  the same FastAPI application services used by ordinary UI actions.

## Acceptance gates

Each migrated page requires:

1. Legacy route, menu, permission, and field inventory.
2. Database read/write and status-transition contract tests.
3. Role-based workflow tests with representative accounts.
4. Old/new browser screenshots at the same viewport.
5. Data-count and relationship checks after writes.
6. A ledger entry recording implementation, automated tests, and browser
   acceptance separately.

