"""核对后端系统菜单与前端实际页面分派的结构覆盖。"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROUTE_EVALUATOR = r"""
const fs = require('node:fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
const signature = /function canonicalRoute\(route:\s*string\):\s*string\s*\{/;
const match = signature.exec(source);
if (!match) throw new Error('找不到前端 canonicalRoute 函数');
let depth = 0;
let end = -1;
for (let index = match.index + match[0].length - 1; index < source.length; index++) {
  if (source[index] === '{') depth++;
  if (source[index] === '}' && --depth === 0) { end = index + 1; break; }
}
if (end < 0) throw new Error('前端 canonicalRoute 函数未闭合');
const implementation = source.slice(match.index, end).replace(
  /function canonicalRoute\(route:\s*string\):\s*string/,
  'function canonicalRoute(route)',
);
const canonicalRoute = new Function(`${implementation}\nreturn canonicalRoute;`)();
const routes = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(routes.map((route) => canonicalRoute(route))));
"""


def declared_menus(source: str) -> list[tuple[str, str, str, str, int]]:
    menus: list[tuple[str, str, str, str, int]] = []
    for statement in ast.parse(source).body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "DEFAULT_SYSTEM_MENUS"
            for target in statement.targets
        ):
            menus = ast.literal_eval(statement.value)
        elif (
            isinstance(statement, ast.AugAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == "DEFAULT_SYSTEM_MENUS"
            and isinstance(statement.op, ast.Add)
        ):
            menus.extend(ast.literal_eval(statement.value))
    if not menus or any(len(row) != 5 for row in menus):
        raise AssertionError("DEFAULT_SYSTEM_MENUS 必须声明非空的五字段菜单行")
    return menus


def check_hierarchy(menus: list[tuple[str, str, str, str, int]]) -> list[str]:
    keys = [row[0] for row in menus]
    duplicate_keys = [key for key, count in Counter(keys).items() if count > 1]
    if duplicate_keys:
        raise AssertionError(f"系统菜单存在重复 key：{duplicate_keys}")
    parents = {row[0]: row[1] for row in menus}
    for key, parent in parents.items():
        if parent and parent not in parents:
            raise AssertionError(f"系统菜单 {key} 的父级不存在：{parent}")
        visited = {key}
        cursor = parent
        while cursor:
            if cursor in visited:
                raise AssertionError(f"系统菜单存在父级环：{key}")
            visited.add(cursor)
            cursor = parents[cursor]
    has_children = {parent for parent in parents.values() if parent}
    return [key for key in keys if key not in has_children]


def check_server_menu_guard(constants_source: str, router_source: str) -> None:
    constants = ast.parse(constants_source)
    declarations = [
        statement.value for statement in constants.body
        if isinstance(statement, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "SYSTEM_MENU_ROUTE_KEYS" for target in statement.targets)
    ]
    if len(declarations) != 1 or not isinstance(declarations[0], ast.SetComp) or not any(
        isinstance(node, ast.Name) and node.id == "DEFAULT_SYSTEM_MENUS"
        for node in ast.walk(declarations[0])
    ):
        raise AssertionError("系统路由白名单必须从 DEFAULT_SYSTEM_MENUS 生成")
    router = ast.parse(router_source)
    comparisons = [
        node for node in ast.walk(router)
        if isinstance(node, ast.Compare)
        and any(isinstance(comparator, ast.Name) and comparator.id == "SYSTEM_MENU_ROUTE_KEYS" for comparator in node.comparators)
    ]
    if not any(any(isinstance(operator, ast.In) for operator in node.ops) for node in comparisons):
        raise AssertionError("系统菜单导航缺少已声明路由过滤")
    if not any(any(isinstance(operator, ast.NotIn) for operator in node.ops) for node in comparisons):
        raise AssertionError("系统菜单写入缺少未声明路由拒绝")


def canonical_routes(app_file: Path, leaves: list[str]) -> list[str]:
    result = subprocess.run(
        ["node", "-e", CANONICAL_ROUTE_EVALUATOR, str(app_file)],
        input=json.dumps(leaves, ensure_ascii=False), text=True, encoding="utf-8", errors="strict",
        capture_output=True, check=False,
    )
    if result.returncode:
        raise AssertionError(f"执行前端 canonicalRoute 失败：{result.stderr.strip()}")
    routes = json.loads(result.stdout)
    if len(routes) != len(leaves) or any(not isinstance(route, str) for route in routes):
        raise AssertionError("前端 canonicalRoute 返回了无效路由")
    return routes


def page_dispatch(app_source: str) -> tuple[set[str], set[str]]:
    start = app_source.find("const requestedPage =")
    end = app_source.find("const currentPage =", start)
    if start < 0 or end < 0:
        raise AssertionError("前端页面分派入口不存在")
    expression = app_source[start:end]
    if not re.search(r":\s*\(\s*<Card\b", expression):
        raise AssertionError("前端页面分派缺少未知路由展示分支")
    exact = set(re.findall(r'route\s*===\s*"([^"]+)"', expression))
    prefixes = set(re.findall(r'route\.startsWith\("([^"]+)"\)', expression))
    for array in re.findall(r'\[([^\]]+)\]\.includes\(route\)', expression, re.DOTALL):
        exact.update(re.findall(r'"([^"]+)"', array))
    if not exact or not prefixes:
        raise AssertionError("前端页面分派缺少可核对的具体路由条件")
    return exact, prefixes


def audit(root: Path) -> tuple[int, int]:
    constants_source = (root / "apps/api-server/app/core/constants.py").read_text(encoding="utf-8")
    router_source = (root / "apps/api-server/app/areas/system/router.py").read_text(encoding="utf-8")
    app_file = root / "apps/admin-web/src/App.tsx"
    app_source = app_file.read_text(encoding="utf-8")
    menus = declared_menus(constants_source)
    leaves = check_hierarchy(menus)
    check_server_menu_guard(constants_source, router_source)
    exact, prefixes = page_dispatch(app_source)
    routes = canonical_routes(app_file, leaves)
    uncovered = [
        (key, route) for key, route in zip(leaves, routes, strict=True)
        if route not in exact and not any(route.startswith(prefix) for prefix in prefixes)
    ]
    if uncovered:
        raise AssertionError(f"系统菜单叶子未映射到前端页面分派：{uncovered}")
    return len(menus), len(leaves)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="待审计的源码根目录")
    args = parser.parse_args()
    nodes, leaves = audit(args.root.resolve())
    print(f"MENU_COVERAGE_OK: {nodes} nodes / {leaves} leaves / 0 uncovered")


if __name__ == "__main__":
    main()
