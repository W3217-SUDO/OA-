"""Deterministic, lossless structural extraction of the archived monolith.

Dependencies are ordinary, explicit Python imports. Runtime cross-module
function references are imported inside the caller to avoid import cycles.
The archive is a reference input only and is never executed by the application.
"""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import symtable

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
ARCHIVE = ROOT / "reference" / "main.before-area-split.py.txt"
HTTP = {"get", "post", "put", "patch", "delete", "options", "head", "api_route"}
AREA_PREFIXES = {
    "hr": ("hr",), "legal": ("cases", "case-spaces", "case-litigant-candidates", "seals", "records", "communications", "hearings", "hearing-sms"),
    "finance": ("finance", "receivables"), "ipr": ("ipr",),
    "contract": ("contracts", "contract-payment-applications"),
    "crm": ("customers", "customer-portal", "law-firms", "notaries"),
    "investigation": ("investigations",), "tp": ("tasks", "vip-tasks"),
    "wms": ("warehouse", "evidence", "WMS"), "rpt": ("reports",),
    "aws": ("official-outgoing", "documents"),
}


def route_decorators(node):
    return [d for d in getattr(node, "decorator_list", []) if isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute) and isinstance(d.func.value, ast.Name)
            and d.func.value.id == "app" and d.func.attr in HTTP]


def route_area(node):
    dec = route_decorators(node)[0]
    arg = dec.args[0]
    path = arg.value if isinstance(arg, ast.Constant) else "".join(p.value for p in arg.values if isinstance(p, ast.Constant))
    path = path.removeprefix("/api/v1")
    first = path.strip("/").split("/")[0]
    return next((area for area, prefixes in AREA_PREFIXES.items() if first in prefixes), "system")


def core_module(name):
    if name == "_system_action_definitions":
        return "app.core.constants"
    if name in {"lifespan", "_upgrade_schema", "_backfill_clue_generated_case_register_dates", "request_validation_error_handler"}:
        return "app.core.lifecycle"
    if name.startswith("_sync_legacy") or name.startswith("_legacy_"):
        return "app.core.legacy_sync"
    if any(part in name for part in ("permission", "capabilit", "_visible", "_can_", "_require_", "_ensure_", "_identity", "_role_", "_access", "_scope")):
        return "app.core.permissions"
    if any(part in name for part in ("attachment", "_upload", "_file_path", "_storage", "_preview_", "_pdf_", "_xlsx_", "_docx_")):
        return "app.core.storage"
    if any(part in name for part in ("_public", "_projection", "_project_")):
        return "app.core.projections"
    if any(part in name for part in ("display", "_format", "_parse", "_normalize", "_serialize", "_to_", "_text", "_date", "_money", "_decimal")):
        return "app.core.formatters"
    for area, markers in [
        ("finance", ("finance", "fee", "payment", "refund", "receipt", "invoice", "reconciliation", "receivable", "settlement", "expense")),
        ("ipr", ("ipr",)), ("contracts", ("contract",)),
        ("investigation", ("investigation", "clue", "notary", "evidence", "warehouse")),
        ("tasks", ("task", "reminder", "notification", "workflow")),
        ("crm", ("customer", "law_firm", "contact")),
        ("documents", ("document", "template", "agent", "seal", "word_")),
        ("cases", ("case", "hearing", "litigant", "court")),
    ]:
        if any(part in name for part in markers):
            return "app.core." + area
    return "app.core.system"


def imported_names(node):
    if isinstance(node, ast.Import):
        return {a.asname or a.name.split(".")[0] for a in node.names}
    if isinstance(node, ast.ImportFrom):
        return {a.asname or a.name for a in node.names}
    return set()


def assigned_names(node):
    """Only assignments in module scope, excluding comprehension locals."""
    class Assignments(ast.NodeVisitor):
        names = None
        def __init__(self): self.names = set()
        def visit_Name(self, item):
            if isinstance(item.ctx, ast.Store): self.names.add(item.id)
        def visit_ListComp(self, item): pass
        def visit_SetComp(self, item): pass
        def visit_DictComp(self, item): pass
        def visit_GeneratorExp(self, item): pass
        def visit_Lambda(self, item): pass
    visitor = Assignments()
    visitor.visit(node)
    return visitor.names


def globals_used(table):
    names = {s.get_name() for s in table.get_symbols() if s.is_global() and s.is_referenced()}
    for child in table.get_children():
        names.update(globals_used(child))
    return names


def import_lines(groups, indent=""):
    lines = []
    for module, names in sorted(groups.items()):
        if not names:
            continue
        ordered = sorted(names)
        lines.append(indent + f"from {module} import (")
        for start in range(0, len(ordered), 5):
            lines.append(indent + "    " + ", ".join(ordered[start:start + 5]) + ",")
        lines.append(indent + ")")
    return lines


def rebuild():
    previous_hashes = ROOT / "reference" / "generated-files-sha256.json"
    if previous_hashes.exists():
        hashes = json.loads(previous_hashes.read_text(encoding="utf-8"))
        edited = [name for name, digest in hashes.items() if not (ROOT / name).exists() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
        if edited:
            raise SystemExit(f"Refusing to overwrite edited generated files: {edited}. Maintain the split modules directly; this is the historical extractor.")
    if not ARCHIVE.exists():
        ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        ARCHIVE.write_bytes((APP / "main.py").read_bytes())
    raw = ARCHIVE.read_bytes()
    source = raw.decode("utf-8-sig")
    lines = source.splitlines()
    tree = ast.parse(source)
    symbols = symtable.symtable(source, str(ARCHIVE), "exec")
    scopes = {(s.get_name(), s.get_lineno()): s for s in symbols.get_children()}
    owners = {}
    function_names = set()
    modules = defaultdict(list)
    node_owner = {}
    route_counts = Counter()

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = "app.core.dependencies"
            for name in imported_names(node): owners[name] = module
        elif isinstance(node, ast.ClassDef):
            module = "app.models_shared"
            owners[node.name] = module
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            module = f"app.areas.{route_area(node)}.router" if route_decorators(node) else core_module(node.name)
            owners[node.name] = module
            function_names.add(node.name)
        elif any(isinstance(n, ast.Name) and n.id == "app" for n in ast.walk(node)):
            module = "app.main"
            owners["app"] = module
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "model_rebuild":
            module = "app.models_shared"
        else:
            module = "app.core.constants"
            for name in assigned_names(node):
                owners[name] = module
        node_owner[id(node)] = module
        modules[module].append(node)

    # All originals expose the final binding; duplicate route definitions retain
    # separate endpoint objects in the router, exactly as Python decorators do.
    stats = {"source_sha256": hashlib.sha256(raw).hexdigest(), "functions": len([n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]),
             "models": len([n for n in tree.body if isinstance(n, ast.ClassDef)]), "owners": dict(sorted(owners.items())),
             "definitions": [], "route_order": []}
    module_imports = defaultdict(lambda: defaultdict(set))
    output = defaultdict(list)

    for node in tree.body:
        module = node_owner[id(node)]
        if module == "app.main":
            continue
        start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        end = node.end_lineno
        body_lines = lines[start - 1:end]
        local_imports = defaultdict(set)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            referenced = globals_used(scopes[(node.name, node.lineno)])
            # Definitions' decorators/defaults/annotations execute in the parent
            # scope and are not included in the function's symbol table.
            eager = list(getattr(node, "decorator_list", []))
            if isinstance(node, ast.ClassDef):
                eager += node.bases + [k.value for k in node.keywords]
            else:
                eager += [node.args] + ([node.returns] if node.returns else [])
            eager_names = {n.id for a in eager for n in ast.walk(a) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            referenced |= eager_names
            for name in referenced:
                owner = owners.get(name)
                if owner and owner != module and name != "app":
                    if name in function_names and name not in eager_names and not isinstance(node, ast.ClassDef):
                        local_imports[owner].add(name)
                    else:
                        module_imports[module][owner].add(name)
            if local_imports:
                first = node.body[0]
                after_doc = isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)
                insert_at = first.end_lineno - start + 1 if after_doc else first.lineno - start
                body_lines[insert_at:insert_at] = import_lines(local_imports, "    ")
            if route_decorators(node):
                for dec in route_decorators(node):
                    index = dec.lineno - start
                    body_lines[index] = body_lines[index].replace("@app.", "@router.", 1)
            elif node.name == "request_validation_error_handler":
                body_lines = body_lines[len(node.decorator_list):]
            stats["definitions"].append({"name": node.name, "line": node.lineno, "module": module, "kind": type(node).__name__,
                                          "ast_sha256": hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()})
        elif isinstance(node, ast.ImportFrom) and node.level:
            # The original lived in app; the dependency module lives in core.
            body_lines = [ast.unparse(ast.ImportFrom(module="app" + ("." + node.module if node.module else ""), names=node.names, level=0))]
        elif not isinstance(node, (ast.Import, ast.ImportFrom)):
            for name in {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}:
                owner = owners.get(name)
                if owner and owner != module:
                    module_imports[module][owner].add(name)
            if any(isinstance(n, ast.Name) and n.id == "__file__" for n in ast.walk(node)):
                body_lines = [line.replace("Path(__file__).resolve().parent.parent", "Path(__file__).resolve().parents[2]") for line in body_lines]
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "logger" for t in node.targets):
                body_lines = ['logger = logging.getLogger("app.main")']
        output[module].append("\n".join(body_lines))

    for module, chunks in output.items():
        path = ROOT / (module.replace(".", "/") + ".py")
        path.parent.mkdir(parents=True, exist_ok=True)
        prefix = ['"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""']
        prefix += import_lines(module_imports[module])
        if module.startswith("app.areas."):
            prefix += ["from fastapi import APIRouter", "", "router = APIRouter()"]
            (path.parent / "__init__.py").write_text('"""Area implementation package."""\n', encoding="utf-8", newline="\n")
        path.write_text("\n".join(prefix) + "\n\n\n" + "\n\n\n".join(chunks) + "\n", encoding="utf-8", newline="\n")
    (APP / "core" / "__init__.py").write_text('"""Shared implementations and infrastructure; no dependency on app.main."""\n', encoding="utf-8", newline="\n")
    (APP / "areas" / "__init__.py").write_text('"""Business HTTP routing areas."""\n', encoding="utf-8", newline="\n")

    # Preserve original import compatibility without star imports or namespace
    # injection. Runtime code should import the canonical owner directly.
    compatibility = defaultdict(set)
    for name, owner in owners.items():
        if owner != "app.main": compatibility[owner].add(name)
    main = ['"""Application composition. Business implementations live in areas/ and core/."""']
    main += import_lines(compatibility)
    for area in sorted({route_area(n) for n in tree.body if route_decorators(n)}):
        main.append(f"from app.areas.{area}.router import router as {area}_router")
    main += ["from app.routing import include_route_slice, verify_route_coverage", "", ""]
    pending = None

    def flush():
        nonlocal pending
        if pending:
            area, first, stop = pending
            main.append(f"include_route_slice(app, {area}_router, {first}, {stop})")
            pending = None

    for node in tree.body:
        if route_decorators(node):
            area = route_area(node)
            first = route_counts[area]
            count = len(route_decorators(node))
            route_counts[area] += count
            if pending and pending[0] == area:
                pending[2] = first + count
            else:
                flush()
                pending = [area, first, first + count]
            stats["route_order"].append({"name": node.name, "line": node.lineno, "area": area, "start": first, "count": count})
        elif node_owner[id(node)] == "app.main":
            flush()
            main.append("\n".join(lines[node.lineno - 1:node.end_lineno]))
        elif getattr(node, "name", None) == "request_validation_error_handler":
            flush()
            main.append("app.exception_handler(RequestValidationError)(request_validation_error_handler)")
    flush()
    main.append("verify_route_coverage(app, [" + ", ".join(area + "_router" for area in sorted(route_counts)) + "])")
    (APP / "main.py").write_text("\n".join(main) + "\n", encoding="utf-8", newline="\n")
    stats["routes_by_area"] = dict(sorted(route_counts.items()))
    (ROOT / "reference" / "area-split-manifest.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    generated = [ROOT / (module.replace(".", "/") + ".py") for module in output] + [APP / "main.py"]
    previous_hashes.write_text(json.dumps({p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(generated)}, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"functions": stats["functions"], "models": stats["models"], "routes_by_area": stats["routes_by_area"], "modules": len(output), "main_lines": len(main)}, indent=2))


if __name__ == "__main__":
    rebuild()
