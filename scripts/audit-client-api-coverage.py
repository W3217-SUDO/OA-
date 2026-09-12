"""静态核对 React 中调用的 API 是否存在对应 FastAPI 路由。

该检查只验证方法与路径契约，不能替代权限、状态机和端到端业务测试。
"""

from __future__ import annotations

import ast
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


def paths_compatible(client_path: str, server_path: str) -> bool:
    # Optional chaining inside ${...} is not a URL query delimiter.
    client_path = re.sub(r"\$\{[^}]+\}", "{dynamic}", client_path)
    client_parts = client_path.split("?", 1)[0].strip("/").split("/")
    server_parts = server_path.strip("/").split("/")
    if len(client_parts) != len(server_parts):
        return False
    for client, server in zip(client_parts, server_parts, strict=True):
        client_pattern = re.sub(r"\{[^}]+\}", "*", client)
        server_pattern = re.sub(r"\{[^}]+\}", "*", server)
        if client_pattern == server_pattern:
            continue
        dynamic, literal = (client_pattern, server_pattern) if "*" in client_pattern else (server_pattern, client_pattern)
        if "*" in literal or not re.fullmatch(re.escape(dynamic).replace(r"\*", "[^/]+"), literal):
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


def area_route_entries(source: str) -> list[tuple[list[str], str]]:
    """Preserve FastAPI registration order without importing the application."""
    entries = []
    for node in ast.parse(source).body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # Python applies stacked decorators from the bottom up.
        for decorator in reversed(node.decorator_list):
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            owner = decorator.func.value
            method = decorator.func.attr.lower()
            if not isinstance(owner, ast.Name) or owner.id != "router":
                continue
            if method not in {"get", "post", "put", "patch", "delete", "head", "options", "api_route"}:
                raise AssertionError(f"Unsupported area route decorator: {method}")
            path_node = decorator.args[0] if decorator.args else next(
                (keyword.value for keyword in decorator.keywords if keyword.arg == "path"), None
            )
            if isinstance(path_node, ast.Constant) and isinstance(path_node.value, str):
                path = path_node.value
            elif isinstance(path_node, ast.JoinedStr):
                parts = []
                for part in path_node.values:
                    if isinstance(part, ast.Constant) and isinstance(part.value, str):
                        parts.append(part.value)
                    elif isinstance(part, ast.FormattedValue) and ast.unparse(part.value) == "settings.api_prefix":
                        continue
                    else:
                        raise AssertionError(f"Unsupported dynamic area route: {ast.unparse(path_node)}")
                path = "".join(parts)
            else:
                raise AssertionError(f"Missing or unsupported path on {node.name}")
            methods = [method]
            if method == "api_route":
                methods_node = next((item.value for item in decorator.keywords if item.arg == "methods"), None)
                methods = [value.lower() for value in ast.literal_eval(methods_node)] if methods_node else ["get"]
            entries.append((methods, path))
    return entries


def sliced_router_routes(backend: Path, source: str) -> dict[str, list[str]]:
    tree = ast.parse(source)
    imports = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.areas."):
            for name in node.names:
                if name.name == "router":
                    imports[name.asname or name.name] = backend.parent.joinpath(*node.module.split(".")[1:]).with_suffix(".py")
    server: dict[str, list[str]] = {}
    cache = {}
    for node in tree.body:
        call = node.value if isinstance(node, ast.Expr) else None
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != "include_route_slice":
            continue
        if len(call.args) != 4 or ast.unparse(call.args[0]) != "app":
            raise AssertionError("Unsupported include_route_slice arguments")
        name = ast.unparse(call.args[1])
        if name not in imports:
            raise AssertionError(f"Unresolved area router: {name}")
        if name not in cache:
            cache[name] = area_route_entries(imports[name].read_text(encoding="utf-8"))
        entries = cache[name]
        start, stop = (ast.literal_eval(arg) for arg in call.args[2:])
        if not (isinstance(start, int) and isinstance(stop, int) and 0 <= start < stop <= len(entries)):
            raise AssertionError(f"Invalid {name} route slice [{start}:{stop}] of {len(entries)}")
        for methods, path in entries[start:stop]:
            for method in methods:
                server.setdefault(method, []).append(path)
    return server


def resolve_router_source(module: Path, symbol: str, visited=None) -> str:
    """Follow explicit local re-exports, never import startup/database code."""
    visited = set() if visited is None else visited
    key = (module, symbol)
    if key in visited:
        raise AssertionError(f"Cyclic router import: {symbol}")
    visited.add(key)
    source = module.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            return ast.get_source_segment(source, node)
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == symbol for target in node.targets):
            return source
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        for name in node.names:
            if (name.asname or name.name) != symbol:
                continue
            if node.level:
                base = module.parent
                for _ in range(node.level - 1):
                    base = base.parent
                target = base.joinpath(*node.module.split(".")).with_suffix(".py")
            elif node.module.startswith("app."):
                base = module.parent
                while base.name != "app" and base != base.parent:
                    base = base.parent
                target = base.joinpath(*node.module.split(".")[1:]).with_suffix(".py")
            else:
                raise AssertionError(f"Router import outside application: {node.module}")
            return resolve_router_source(target, name.name, visited)
    raise AssertionError(f"Unresolved router symbol: {symbol}")


def main() -> None:
    backend_source = BACKEND.read_text(encoding="utf-8")
    server = sliced_router_routes(BACKEND, backend_source)
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
    for include_call in included_router_calls(backend_source):
        if "prefix=settings.api_prefix" not in include_call:
            continue
        used_names = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*router\b", include_call, re.IGNORECASE)
        for name in used_names:
            router_source = resolve_router_source(BACKEND, name)
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
