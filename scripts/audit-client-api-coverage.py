"""静态核对 React 中调用的 API 是否存在对应 FastAPI 路由。

该检查只验证方法与路径契约，不能替代权限、状态机和端到端业务测试。
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "apps" / "admin-web" / "src"
BACKEND = ROOT / "apps" / "api-server" / "app" / "main.py"

CLIENT_CALL = re.compile(
    r"api\.(get|post|put|patch|delete)\(\s*([`\"'])(/[^`\"']+)\2",
    re.IGNORECASE,
)
SERVER_ROUTE = re.compile(
    r"@app\.(get|post|put|patch|delete)\(f?([\"'])\{settings\.api_prefix\}([^\"']+)\2",
    re.IGNORECASE,
)
SERVER_API_ROUTE = re.compile(
    r"@app\.api_route\(\s*f?([\"'])\{settings\.api_prefix\}([^\"']+)\1\s*,\s*methods=\[([^\]]+)\]",
    re.IGNORECASE,
)
ROUTER_ROUTE = re.compile(
    r"@router\.(get|post|put|patch|delete)\(f?([\"'])(/[^\"']+)\2",
    re.IGNORECASE,
)
ROUTER_IMPORT = re.compile(r"from \.([A-Za-z_][A-Za-z0-9_]*) import ([^\n]+)")


def paths_compatible(client_path: str, server_path: str) -> bool:
    client_parts = client_path.split("?", 1)[0].strip("/").split("/")
    server_parts = server_path.strip("/").split("/")
    if len(client_parts) != len(server_parts):
        return False
    for client, server in zip(client_parts, server_parts, strict=True):
        client_dynamic = bool(re.fullmatch(r"\$\{[^}]+\}", client))
        server_dynamic = bool(re.fullmatch(r"\{[^}]+\}", server))
        if not client_dynamic and not server_dynamic and client != server:
            return False
    return True


def included_router_calls(source: str) -> list[str]:
    """Return complete ``include_router(...)`` calls without guessing nesting."""
    calls: list[str] = []
    marker = "app.include_router("
    start = 0
    while (found := source.find(marker, start)) >= 0:
        index = found + len(marker) - 1
        depth = 0
        for end in range(index, len(source)):
            if source[end] == "(":
                depth += 1
            elif source[end] == ")":
                depth -= 1
                if depth == 0:
                    calls.append(source[index + 1 : end])
                    start = end + 1
                    break
        else:
            raise AssertionError("include_router 调用括号未闭合")
    return calls


def main() -> None:
    backend_source = BACKEND.read_text(encoding="utf-8")
    server: dict[str, list[str]] = {}
    for method, _, path in SERVER_ROUTE.findall(backend_source):
        full_path = path.replace("{{", "{").replace("}}", "}")
        server.setdefault(method.lower(), []).append(full_path)
    for _, path, methods in SERVER_API_ROUTE.findall(backend_source):
        full_path = path.replace("{{", "{").replace("}}", "}")
        for method in re.findall(r"[\"']([A-Za-z]+)[\"']", methods):
            server.setdefault(method.lower(), []).append(full_path)

    # Routers are valid FastAPI route owners too.  Discover only modules whose
    # imported router/factory is actually passed to ``include_router`` so a
    # dormant helper module cannot satisfy a client call accidentally.
    imported_router_modules: dict[str, Path] = {}
    for module_name, imported_names in ROUTER_IMPORT.findall(backend_source):
        module_path = BACKEND.parent / f"{module_name}.py"
        if not module_path.is_file():
            continue
        for imported_name in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*router\b", imported_names, re.IGNORECASE):
            imported_router_modules[imported_name] = module_path
    for include_call in included_router_calls(backend_source):
        if "prefix=settings.api_prefix" not in include_call:
            continue
        used_names = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*router\b", include_call, re.IGNORECASE)
        for name in used_names:
            module_path = imported_router_modules.get(name)
            if not module_path:
                continue
            router_source = module_path.read_text(encoding="utf-8")
            for method, _, path in ROUTER_ROUTE.findall(router_source):
                server.setdefault(method.lower(), []).append(path.replace("{{", "{").replace("}}", "}"))

    unmatched: list[str] = []
    total = 0
    for source_path in sorted(FRONTEND.rglob("*.tsx")):
        source = source_path.read_text(encoding="utf-8")
        for match in CLIENT_CALL.finditer(source):
            total += 1
            method, _, client_path = match.groups()
            if not any(paths_compatible(client_path, server_path) for server_path in server.get(method.lower(), [])):
                line = source.count("\n", 0, match.start()) + 1
                unmatched.append(f"{source_path.relative_to(ROOT)}:{line}: {method.upper()} {client_path}")

    if unmatched:
        raise AssertionError("前端调用不存在的 API：\n" + "\n".join(unmatched))
    print(f"CLIENT_API_COVERAGE_OK: {total} frontend calls match FastAPI routes")


if __name__ == "__main__":
    main()
