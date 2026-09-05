"""Compile and compare the pre-split API contract without starting its lifespan.

Run --capture once against the original main.py, then run without arguments.
No requests or business data are written; SQLite is forced to :memory:.
"""
from __future__ import annotations

import ast
import builtins
from collections import defaultdict
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import symtable
import subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"
BASELINE = REFERENCE / "api-contract-before.json"
sys.path.insert(0, str(ROOT))


def stable(value):
    value = str(value)
    value = re.sub(r"app\.[A-Za-z_][A-Za-z_0-9.]*\.", "", value)
    value = re.sub(r" at 0x[0-9a-fA-F]+", "", value)
    return value


def dependency(dep):
    return {"name": dep.name, "call": getattr(dep.call, "__qualname__", None), "use_cache": dep.use_cache,
            "security_scopes": dep.security_scopes,
            "parameters": {kind: [(f.name, f.alias, stable(f.field_info)) for f in getattr(dep, kind)]
                           for kind in ("path_params", "query_params", "header_params", "cookie_params", "body_params")},
            "dependencies": [dependency(child) for child in dep.dependencies]}


def lifespan_functions(callback):
    # FastAPI wraps every included router's lifespan. Compare substantive hooks,
    # discarding the empty default router context rather than wrapper depth.
    if inspect.isfunction(callback) and callback.__name__ == "merged_lifespan":
        return [name for cell in callback.__closure__ or () for name in lifespan_functions(cell.cell_contents)]
    if inspect.isfunction(callback):
        return [callback.__qualname__]
    return []


def capture():
    from app.main import app
    from app.config import settings
    assert settings.database_url == "sqlite+aiosqlite:///:memory:"
    contract = {"routes": [], "middleware": [], "exception_handlers": {}, "startup": [], "shutdown": []}
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        data = {"path": route.path, "name": route.name, "methods": sorted(getattr(route, "methods", []) or []),
                "endpoint": getattr(endpoint, "__qualname__", None), "signature": stable(inspect.signature(endpoint)) if endpoint else None}
        if hasattr(route, "dependant"):
            data["dependency"] = dependency(route.dependant)
        for key in ("status_code", "tags", "summary", "description", "response_description", "deprecated", "operation_id", "include_in_schema", "response_model_by_alias", "response_model_exclude_unset", "response_model_exclude_defaults", "response_model_exclude_none"):
            if hasattr(route, key): data[key] = getattr(route, key)
        contract["routes"].append(data)
    for middleware in app.user_middleware:
        contract["middleware"].append({"class": middleware.cls.__qualname__, "args": middleware.args, "kwargs": middleware.kwargs})
    contract["exception_handlers"] = {getattr(key, "__qualname__", str(key)): value.__qualname__ for key, value in app.exception_handlers.items()}
    contract["startup"] = [f.__qualname__ for f in app.router.on_startup]
    contract["shutdown"] = [f.__qualname__ for f in app.router.on_shutdown]
    contract["lifespan"] = lifespan_functions(app.router.lifespan_context)
    schema = app.openapi()
    serialized = json.dumps(schema, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    contract["openapi_sha256"] = hashlib.sha256(serialized.encode()).hexdigest()
    contract["openapi_paths"] = len(schema["paths"])
    contract["openapi_components"] = len(schema.get("components", {}).get("schemas", {}))
    # Roundtrip normalizes tuples used by FastAPI field representations.
    return json.loads(json.dumps(contract, ensure_ascii=False))


def verify_definitions():
    archive = REFERENCE / "main.before-area-split.py.txt"
    manifest = json.loads((REFERENCE / "area-split-manifest.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest["source_sha256"]
    generated_hashes = json.loads((REFERENCE / "generated-files-sha256.json").read_text(encoding="utf-8"))
    for name, digest in generated_hashes.items():
        raw = (ROOT / name).read_bytes()
        assert b"\r\n" not in raw, f"Generated source must use deterministic LF bytes: {name}"
        assert hashlib.sha256(raw).hexdigest() == digest, f"Generated source hash changed: {name}"
    old = ast.parse(archive.read_text(encoding="utf-8-sig"))
    extracted = defaultdict(list)
    for owner in sorted({d["module"] for d in manifest["definitions"]}):
        path = ROOT / (owner.replace(".", "/") + ".py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                extracted[(owner, node.name)].append(node)
    records = iter(manifest["definitions"])
    count = 0
    for original in old.body:
        if not isinstance(original, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        entry = next(records)
        assert entry["name"] == original.name and entry["line"] == original.lineno
        moved = extracted[(entry["module"], entry["name"])].pop(0)
        if not isinstance(moved, ast.ClassDef):
            moved.body = [n for n in moved.body if not (isinstance(n, ast.ImportFrom) and n.module and (n.module.startswith("app.core.") or n.module.startswith("app.areas.")))]
        for dec in getattr(moved, "decorator_list", []):
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and isinstance(dec.func.value, ast.Name) and dec.func.value.id == "router":
                dec.func.value.id = "app"
        if moved.name == "request_validation_error_handler":
            moved.decorator_list = original.decorator_list
        assert ast.dump(original, include_attributes=False) == ast.dump(moved, include_attributes=False), f"Definition changed: {original.name}@{original.lineno}"
        count += 1
    return count


def verify_global_references():
    from scripts.rebuild_area_split import globals_used
    manifest = json.loads((REFERENCE / "area-split-manifest.json").read_text(encoding="utf-8"))
    old = symtable.symtable((REFERENCE / "main.before-area-split.py.txt").read_text(encoding="utf-8-sig"), "baseline", "exec")
    builtins_names = set(vars(builtins))
    # Pre-existing unresolved names are reported, never repaired during a
    # behavior-preserving refactor or used to conceal newly lost imports.
    old_scopes = {(s.get_name(), s.get_lineno()): s for s in old.get_children()}
    old_missing = []
    new_missing = []
    for owner in sorted({d["module"] for d in manifest["definitions"]}):
        source = (ROOT / (owner.replace(".", "/") + ".py")).read_text(encoding="utf-8")
        table = symtable.symtable(source, owner, "exec")
        available = {s.get_name() for s in table.get_symbols() if s.is_assigned() or s.is_imported()}
        moved_scopes = defaultdict(list)
        for child in table.get_children(): moved_scopes[child.get_name()].append(child)
        for entry in [item for item in manifest["definitions"] if item["module"] == owner]:
            before = old_scopes[(entry["name"], entry["line"])]
            child = moved_scopes[entry["name"]].pop(0)
            existing = globals_used(before) - set(manifest["owners"]) - builtins_names
            old_missing.extend((entry["name"], entry["line"], name) for name in sorted(existing))
            for name in globals_used(child) - available - builtins_names - existing:
                new_missing.append((owner, child.get_name(), name))
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom):
                assert not any(alias.name == "*" for alias in node.names), f"Star import: {owner}"
                assert node.module != "app.main", f"Reverse main dependency: {owner}"
    assert not new_missing, f"New unresolved globals: {new_missing}"
    return sorted(old_missing)


def verify_independent_imports():
    manifest = json.loads((REFERENCE / "area-split-manifest.json").read_text(encoding="utf-8"))
    modules = sorted(set(manifest["owners"].values()) - {"app.main"})
    def check(module):
        with tempfile.TemporaryDirectory(prefix="CODEX-SPLIT-BACKEND-import-") as temporary:
            environment = {**os.environ, "DATABASE_URL": "sqlite+aiosqlite:///:memory:", "UPLOAD_ROOT": str(Path(temporary) / "uploads"), "SEED_DEMO_DATA": "false"}
            program = f"import importlib,sys; importlib.import_module({module!r}); assert 'app.main' not in sys.modules"
            result = subprocess.run([sys.executable, "-c", program], cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60)
            assert result.returncode == 0, f"Independent import failed: {module}: {result.stderr}"
            return module
    with ThreadPoolExecutor(max_workers=4) as executor:
        return len(list(executor.map(check, modules)))


def verify_coverage_guard():
    from fastapi import APIRouter, FastAPI
    from app.routing import include_route_slice, verify_route_coverage
    router = APIRouter()
    async def endpoint(): return {"ok": True}
    router.add_api_route("/first", endpoint)
    router.add_api_route("/second", endpoint)
    app = FastAPI()
    include_route_slice(app, router, 0, 1)
    try:
        verify_route_coverage(app, [router])
    except RuntimeError:
        pass
    else:
        raise AssertionError("Missing routes must stop application composition")
    include_route_slice(app, router, 1, 2)
    verify_route_coverage(app, [router])
    include_route_slice(app, router, 0, 1)
    try:
        verify_route_coverage(app, [router])
    except RuntimeError:
        pass
    else:
        raise AssertionError("Repeated route composition must fail")
    for start, stop in [(-1, 1), (0, 3), (1, 1)]:
        try:
            include_route_slice(app, router, start, stop)
        except ValueError:
            pass
        else:
            raise AssertionError("Stale slice bounds must fail")


def main():
    # FastAPI 0.116 derives the ID of an api_route(GET, POST) from a set's
    # first method. Pin the verifier process to the archived baseline's order;
    # this does not modify application behavior or normalize away schema changes.
    if os.environ.get("PYTHONHASHSEED") != "2":
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
                                cwd=ROOT, env={**os.environ, "PYTHONHASHSEED": "2"})
        raise SystemExit(result.returncode)
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["SEED_DEMO_DATA"] = "false"
    with tempfile.TemporaryDirectory(prefix="CODEX-SPLIT-BACKEND-") as temporary:
        os.environ["UPLOAD_ROOT"] = str(Path(temporary) / "uploads")
        current = capture()
    if "--capture" in sys.argv:
        if BASELINE.exists():
            raise SystemExit("Refusing to overwrite the archived baseline")
        REFERENCE.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"Captured {len(current['routes'])} ordered routes; {current['openapi_paths']} paths")
        return
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    failures = [key for key in baseline if baseline[key] != current[key]]
    if failures:
        out = REFERENCE / "api-contract-actual.json"
        out.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        raise AssertionError(f"Contract differs: {failures}; inspect {out}")
    count = verify_definitions()
    old_missing = verify_global_references()
    independent_imports = verify_independent_imports()
    verify_coverage_guard()
    for path in (ROOT / "app").rglob("*.py"):
        # Compile in memory: no __pycache__ or import side effects.
        compile(path.read_text(encoding="utf-8-sig"), str(path), "exec")
    print(json.dumps({"result": "PASS", "ordered_routes": len(current["routes"]), "paths": current["openapi_paths"],
                      "schema_components": current["openapi_components"], "openapi_sha256": current["openapi_sha256"],
                      "unchanged_definitions": count, "new_unresolved_globals": 0, "preexisting_unresolved_references": old_missing,
                      "independent_module_imports": independent_imports, "route_coverage_guards": "missing/duplicate/bounds PASS", "middleware": current["middleware"],
                      "lifespan": current["lifespan"], "database": "memory; no connections or lifespan startup", "temporary_uploads": "cleaned", "python_hash_seed": 2}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
