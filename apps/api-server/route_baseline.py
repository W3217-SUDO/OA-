"""Dump the full ordered route table so a refactor can be proven not to change routing.

Usage:  python route_baseline.py <output-file>
Compare before/after with:  diff baseline.txt after.txt
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.main import app  # noqa: E402


def dump(target: str) -> None:
    lines = []
    for index, route in enumerate(app.routes):
        path = getattr(route, "path", "")
        methods = ",".join(sorted(getattr(route, "methods", None) or []))
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None:
            name = type(route).__name__
        else:
            name = f"{endpoint.__module__}.{endpoint.__qualname__}"
        lines.append(f"{index:4d}  {methods:18s}  {path:70s}  {name}")
    Path(target).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"routes dumped: {len(lines)} -> {target}")


if __name__ == "__main__":
    dump(sys.argv[1] if len(sys.argv) > 1 else "route_baseline.txt")
