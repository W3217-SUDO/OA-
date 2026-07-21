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


def main() -> None:
    backend_source = BACKEND.read_text(encoding="utf-8")
    server: dict[str, list[str]] = {}
    for method, _, path in SERVER_ROUTE.findall(backend_source):
        full_path = path.replace("{{", "{").replace("}}", "}")
        server.setdefault(method.lower(), []).append(full_path)

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
