# API Area architecture

The application entry point is `app.main:app`. Each of the twelve Area packages
owns a real `APIRouter` and its endpoint implementations. Shared functions live
in `app.core`, and request/response models in `app.models_shared`.

- `core.dependencies`: external/library/ORM/security imports.
- `core.constants`: configuration constants, shared mutable caches and agent runtime.
- `core.lifecycle`: original schema initialization, lifespan and validation handler.
- `core.permissions`, `formatters`, `projections`, `storage`, `legacy_sync`: common implementations.
- `core.cases`, `contracts`, `crm`, `documents`, `finance`, `investigation`, `ipr`,
  `system`, `tasks`: remaining shared business helpers.

There are no star imports, reverse imports from `app.main`, or injected shared
namespaces. Definition-time types/constants have explicit module imports;
cross-module function references have explicit local imports inside their callers.
This handles mutually dependent business functions without loading a partially
initialized entry point. Every Area and core module can be imported independently.

`main.py` composes the application and preserves explicit compatibility exports
for existing `from app.main import name` consumers. New code and monkeypatches
must use the canonical owner shown in `reference/area-split-manifest.json`.
Rebinding a compatibility-exported variable in main does not rebind its owner.

## Route order and additions

The original application interleaves Area endpoints and five pre-existing router
factory inclusions. `main.py` includes contiguous Area slices at those exact
positions. This preserves first-match semantics for static/dynamic path overlaps,
duplicate function names, multiple decorators, operation IDs and OpenAPI metadata.

When adding/removing an Area route, update the corresponding `include_route_slice`
calls in main. Prefer adding a new contiguous slice at the intended registration
position and keep existing route order unchanged. `verify_route_coverage` runs at
application import and fails loudly on omitted or duplicate endpoints; slice bounds
are also checked. An added route cannot silently remain unregistered.

## Verification and historical extraction

From `apps/api-server`, run `python test_lean_main.py` (or
`python scripts/verify_area_split.py`). This checks all 763 ordered application
routes, 614 OpenAPI paths and 338 schemas against the frozen pre-refactor contract,
all 1,616 original definitions, imports and route-coverage failure cases. It uses
in-memory SQLite settings and temporary uploads; no lifespan, business requests,
browser, or real database is started.

The exact original file and its SHA256 are preserved in `reference/` as a `.txt`
reference, never as an application entry point. `scripts/rebuild_area_split.py`
reproduces this one-time extraction. The old `split_v2.py` and
`generate_lean_main.py` commands now invoke that audited extractor. It refuses to
overwrite implementations edited since extraction. Old incomplete drafts are
archived, not importable alternatives.

Generated Python and manifest files use explicit UTF-8/LF on every platform;
their manifest hashes refer to those exact LF bytes. The archived original retains
its original bytes, including line endings: `reference/.gitattributes` marks that
single `.txt` file `-text`, so Git must not normalize it. The verifier checks both
the untouched original SHA256 and generated LF byte hashes after checkout.

The verifier fixes only its own process to `PYTHONHASHSEED=2`. FastAPI 0.116
selects a multi-method route's generated operation ID from an unordered set;
the frozen original contract used the POST suffix for that route. The original
archive is separately verified under the same seed. Production behavior and the
archived OpenAPI hash are unchanged; no schema fields are ignored or normalized.

Maintain the modules directly after this refactor. The frozen verification script
is evidence of the structural migration, not a rule forbidding future API changes.
For an intentional later API change, retain this original reference, add a new
versioned baseline with the expected contract differences reviewed, and update
the regression tests for that change. Do not overwrite the pre-refactor baseline
or rerun the extractor to discard subsequent work.
