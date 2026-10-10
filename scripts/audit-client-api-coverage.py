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
    r"api\.(get|post|put|patch|delete)(?:<[^()]+>)?\(\s*([`\"'])(/[^`\"']+)\2",
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


def route_path(node: ast.expr | None) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute) and ast.unparse(node) == "settings.api_prefix":
        return ""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return route_path(node.left) + route_path(node.right)
    if isinstance(node, ast.JoinedStr):
        parts = []
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                parts.append(part.value)
            elif isinstance(part, ast.FormattedValue) and ast.unparse(part.value) == "settings.api_prefix":
                continue
            else:
                raise AssertionError(f"Unsupported dynamic area route: {ast.unparse(node)}")
        return "".join(parts)
    raise AssertionError(f"Missing or unsupported area route: {ast.unparse(node) if node else 'None'}")


def area_route_entries(
    source: str, module: Path | None = None, app_root: Path | None = None,
    visited: frozenset[Path] = frozenset(),
) -> list[tuple[list[str], str]]:
    """按注册顺序静态读取模块路由及其子路由。"""
    if module in visited:
        raise AssertionError(f"Cyclic area router include: {module}")
    visited = visited | {module} if module else visited
    tree = ast.parse(source)
    prefix = ""
    imports: dict[str, Path] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and module and app_root:
            if node.level:
                target = module.parent
                for _ in range(node.level - 1):
                    target = target.parent
                target = target.joinpath(*node.module.split(".")).with_suffix(".py")
            elif node.module.startswith("app."):
                target = app_root.joinpath(*node.module.split(".")[1:]).with_suffix(".py")
            else:
                continue
            for imported in node.names:
                if imported.name == "router":
                    imports[imported.asname or imported.name] = target
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "router" for target in node.targets):
            call = node.value
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "APIRouter":
                prefix_node = next((item.value for item in call.keywords if item.arg == "prefix"), None)
                prefix = route_path(prefix_node) if prefix_node else ""

    entries: list[tuple[list[str], str]] = []
    for node in tree.body:
        call = node.value if isinstance(node, ast.Expr) else None
        if (
            isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name) and call.func.value.id == "router"
            and call.func.attr == "include_router"
        ):
            if not module or not app_root or len(call.args) != 1 or not isinstance(call.args[0], ast.Name):
                raise AssertionError(f"Unsupported area router include: {ast.unparse(call)}")
            name = call.args[0].id
            if name not in imports:
                raise AssertionError(f"Unresolved area subrouter: {name}")
            child = imports[name]
            entries.extend((methods, prefix + path) for methods, path in area_route_entries(
                child.read_text(encoding="utf-8"), child, app_root, visited,
            ))
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # 装饰器由内到外执行，顺序必须与 FastAPI 注册顺序一致。
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
            methods = [method]
            if method == "api_route":
                methods_node = next((item.value for item in decorator.keywords if item.arg == "methods"), None)
                methods = [value.lower() for value in ast.literal_eval(methods_node)] if methods_node else ["get"]
            entries.append((methods, prefix + route_path(path_node)))
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
        if (
            isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name) and call.func.value.id == "app"
            and call.func.attr == "include_router" and call.args
            and isinstance(call.args[0], ast.Name) and call.args[0].id in imports
        ):
            name = call.args[0].id
            entries = area_route_entries(
                imports[name].read_text(encoding="utf-8"), imports[name], backend.parent,
            )
            for methods, path in entries:
                for method in methods:
                    server.setdefault(method, []).append(path)
            continue
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != "include_route_slice":
            continue
        if len(call.args) != 4 or ast.unparse(call.args[0]) != "app":
            raise AssertionError("Unsupported include_route_slice arguments")
        name = ast.unparse(call.args[1])
        if name not in imports:
            raise AssertionError(f"Unresolved area router: {name}")
        if name not in cache:
            cache[name] = area_route_entries(
                imports[name].read_text(encoding="utf-8"), imports[name], backend.parent,
            )
        entries = cache[name]
        def slice_bound(value: ast.expr) -> int:
            if isinstance(value, ast.Constant) and type(value.value) is int:
                return value.value
            if (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id == "len"
                and len(value.args) == 1
                and not value.keywords
                and isinstance(value.args[0], ast.Attribute)
                and value.args[0].attr == "routes"
                and isinstance(value.args[0].value, ast.Name)
                and value.args[0].value.id == name
            ):
                return len(entries)
            raise AssertionError(f"Unsupported {name} route slice bound: {ast.unparse(value)}")

        start, stop = (slice_bound(arg) for arg in call.args[2:])
        if not (isinstance(start, int) and isinstance(stop, int) and 0 <= start < stop <= len(entries)):
            raise AssertionError(f"Invalid {name} route slice [{start}:{stop}] of {len(entries)}")
        for methods, path in entries[start:stop]:
            for method in methods:
                server.setdefault(method, []).append(path)
    for method, paths in registered_helper_routes(backend, source).items():
        server.setdefault(method, []).extend(paths)
    return server


def resolve_router_definition(module: Path, symbol: str, visited=None) -> tuple[Path, str, str]:
    """追踪显式重导出并保留定义位置，不导入启动或数据库代码。"""
    visited = set() if visited is None else visited
    key = (module, symbol)
    if key in visited:
        raise AssertionError(f"Cyclic router import: {symbol}")
    visited.add(key)
    source = module.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            return module, symbol, ast.get_source_segment(source, node)
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == symbol for target in node.targets):
            return module, symbol, source
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
            return resolve_router_definition(target, name.name, visited)
    raise AssertionError(f"Unresolved router symbol: {symbol}")


def resolve_router_source(module: Path, symbol: str, visited=None) -> str:
    """保留既有路由工厂与重导出的源码解析接口。"""
    return resolve_router_definition(module, symbol, visited)[2]


def registered_helper_routes(backend: Path, source: str) -> dict[str, list[str]]:
    """只追踪实际收到应用对象的注册函数，不扫描未调用的函数体。"""
    server: dict[str, list[str]] = {}

    def scan(module: Path, statements: list[ast.stmt], applications: set[str], stack: frozenset):
        module_tree = ast.parse(module.read_text(encoding="utf-8")) if module != backend else ast.parse(source)
        symbols = {
            imported.asname or imported.name
            for node in module_tree.body
            if isinstance(node, ast.ImportFrom) and node.module
            and (node.level or node.module.startswith("app."))
            for imported in node.names
        } | {node.name for node in module_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        def is_application(node: ast.expr) -> bool:
            return isinstance(node, ast.Name) and node.id in applications

        for statement in statements:
            if isinstance(statement, ast.Assign) and is_application(statement.value):
                applications.update(target.id for target in statement.targets if isinstance(target, ast.Name))
            call = statement.value if isinstance(statement, ast.Expr) else None
            if not isinstance(call, ast.Call):
                continue
            if isinstance(call.func, ast.Attribute) and is_application(call.func.value) and call.func.attr == "include_router":
                # 主模块的直接注册与切片沿用原解析器，这里只补函数内注册。
                if module == backend and not stack:
                    continue
                router_node = call.args[0] if len(call.args) == 1 else next(
                    (keyword.value for keyword in call.keywords if keyword.arg == "router"), None,
                )
                if not isinstance(router_node, ast.Name):
                    raise AssertionError(f"Unsupported helper router include: {ast.unparse(call)}")
                router_module, _, router_source = resolve_router_definition(module, router_node.id)
                prefix_node = next((keyword.value for keyword in call.keywords if keyword.arg == "prefix"), None)
                prefix = route_path(prefix_node) if prefix_node is not None else ""
                for methods, path in area_route_entries(router_source, router_module, backend.parent):
                    for method in methods:
                        server.setdefault(method, []).append(prefix + path)
                continue
            if not isinstance(call.func, ast.Name) or call.func.id not in symbols:
                continue
            # 既有切片已逐条校验边界，不能再把切片函数当作完整路由注册。
            if module == backend and not stack and call.func.id == "include_route_slice":
                continue
            if not any(is_application(value) for value in call.args) and not any(is_application(item.value) for item in call.keywords):
                continue
            target_module, target_symbol, function_source = resolve_router_definition(module, call.func.id)
            function = ast.parse(function_source).body[0]
            if not isinstance(function, ast.FunctionDef):
                raise AssertionError(f"Unsupported registration helper: {call.func.id}")
            key = (target_module, target_symbol)
            if key in stack:
                raise AssertionError(f"Cyclic registration helper: {target_symbol}")
            parameters = function.args.posonlyargs + function.args.args
            bound_applications = {
                parameters[index].arg for index, value in enumerate(call.args)
                if is_application(value) and index < len(parameters)
            }
            bound_applications.update(item.arg for item in call.keywords if item.arg and is_application(item.value))
            if not bound_applications:
                raise AssertionError(f"Unresolved application argument: {ast.unparse(call)}")
            scan(target_module, function.body, bound_applications, stack | {key})

    scan(backend, ast.parse(source).body, {"app"}, frozenset())
    return server


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
            prefix_match = re.search(r'\brouter\s*=\s*APIRouter\(\s*prefix\s*=\s*["\']([^"\']+)["\']', router_source)
            router_prefix = prefix_match.group(1) if prefix_match else ""
            for method, _, path in ROUTER_ROUTE.findall(router_source):
                full_path = f"{router_prefix}{path}".replace("{{", "{").replace("}}", "}")
                server.setdefault(method.lower(), []).append(full_path)

    unmatched: list[str] = []
    total = 0
    source_paths = (
        path for path in FRONTEND.rglob("*")
        if path.suffix in {".js", ".mjs", ".ts", ".tsx"}
        and not path.name.endswith(".d.ts")
    )
    for source_path in sorted(source_paths):
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
