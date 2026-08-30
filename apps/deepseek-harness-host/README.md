# Sunhold DeepSeek Harness Host

This is the local DeepSeek Harness sidecar used by the OA case agent. It owns
the agent execution loop and plugin ecosystem; OA continues to own identity,
case-space authorization, conversation visibility, approval, and all business
writes.

The sidecar is intentionally bound to loopback. The API server configures a
custom OpenAI-compatible route from the existing `LANGGRAPH_API_BASE_URL`,
`LANGGRAPH_API_KEY`, and `LANGGRAPH_MODEL` settings. No model secret belongs in
this package or its configuration files.

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-deepseek-harness.ps1
```

Then set `AGENT_RUNTIME_BACKEND=deepseek-harness` for the API server. Set it
back to `langgraph` for immediate rollback.
