# 9.1 Row 37 Local Chrome Acceptance

- Environment: isolated API `127.0.0.1:8047`, web `127.0.0.1:5247`, SQLite test database.
- Browser: Google Chrome plugin/backend. Codex IAB was not used.
- Case: isolated seed case `SHMS2500149` (`business_records.id=26`).

## Result

1. Opened the case detail document tab and expanded the exact `生成操作` dropdown.
2. Clicked the unique menu item `生成归档封面`; the UI created `SHMS2500149-归档封面-20260902144301.docx`.
3. Clicked the unique menu item `生成授权委托书`; the first attempt was correctly rejected because the isolated seed case had no cause of action.
4. Added `cause_or_charge=商标侵权纠纷` to the isolated test record only, repeated the same UI action, and created `SHMS2500149-授权委托书-20260902144433.docx`.
5. Refreshed/navigated between document folders and confirmed both documents persisted in their mapped folders.
6. Database and disk checks confirmed both attachment rows and non-empty physical DOCX files: archive cover 35,769 bytes; authorization letter 36,462 bytes.

## Diagnosis

The two production menu actions are bound correctly. The earlier failure was a browser acceptance false negative caused by an imprecise duplicate-text locator; it did not click the unique visible menu item. The authorization-letter validation is also working as designed and reports missing case fields instead of silently failing.

## Evidence

- `row37-archive-cover-persisted.png`
- `row37-authorization-generated.png`

No production source change was required for these two actions.
