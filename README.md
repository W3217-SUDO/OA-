# Sunhold Legacy Parity Rebuild

This repository rebuilds the locally running legacy system at
`http://localhost:8091/Console/Index` with FastAPI and Vue 3.

## Non-negotiable parity rules

1. The legacy application is the behavioral and visual source of truth.
2. Existing SQL Server table names, columns, types, nullability, defaults,
   indexes, procedures, triggers, status values, and soft relationships are
   preserved exactly.
3. Legacy pages are accepted only after workflow, permission, data, and visual
   parity checks pass in the Codex browser.
4. DingTalk ingestion and agent functionality are retained as extensions.
   They use dedicated extension tables and adapters and do not change legacy
   table semantics.
5. The legacy runtime, its database, and the current 8089 test system remain
   untouched until an independently deployed module passes acceptance.

## Verified local baseline

- Runtime: `legacy-gdcrm-101-local-20260812/source/GD.CRM.WEB`
- Database: `PRD_CRM_GD_20200211` on the local SQL Server instance
- Source files: 5,777
- Controllers: 199
- Razor views: 1,095
- Database tables: 239
- Database columns: 3,951
- Stored procedures: 125
- Approximate rows: 50,558,423

Run `scripts/export-legacy-baseline.ps1` to regenerate the read-only database
inventory under `artifacts/`.

## Local demo layout

The first Vue 3 + Python demo keeps the UI and automation boundaries explicit:

```text
backend/
  app/
    api/agent.py          # Agent capability and run contract
    main.py               # FastAPI application
  cli/oa_cli.py           # CLI client using the same HTTP contract
frontend/
  src/components/         # Reusable legacy-style shell and Agent widgets
  src/services/agentApi.ts # Browser client for Agent API
  src/types/agent.ts       # Shared frontend contract types
  src/views/AgentCenterView.vue
```

Run the local demo from two terminals (production hosts are never contacted):

```powershell
# terminal 1
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8012

# terminal 2
cd frontend
npm run dev
```

The Vue shell is available at `http://127.0.0.1:5174`. The header `Agent`
button opens the local read-only Agent demo. The same capability can be called
from the CLI with `python -m cli.oa_cli capabilities` or
`python -m cli.oa_cli run --skill legacy.page.explain --input "控制台"`.
