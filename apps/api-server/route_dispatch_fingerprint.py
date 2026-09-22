"""Fingerprint actual route dispatch using every literal path segment as a probe.

Samples are drawn from all literal segments present in the route table, so any
parameterised route that could swallow a literal sibling is exercised.
Usage:  python route_dispatch_fingerprint.py <output-file>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from starlette.routing import Match  # noqa: E402

from app.main import app  # noqa: E402


def literal_segments() -> list[str]:
    found = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        if not path:
            continue
        for segment in path.split("/"):
            if segment and not (segment.startswith("{") and segment.endswith("}")):
                found.add(segment)
    return sorted(found)


def sample_paths(path: str, samples: list[str]) -> list[str]:
    out = []
    for sample in samples:
        parts = []
        for segment in path.split("/"):
            if segment.startswith("{") and segment.endswith("}"):
                name = segment[1:-1]
                parts.append(f"{sample}/{sample}" if name.endswith(":path") else sample)
            else:
                parts.append(segment)
        out.append("/".join(parts) or "/")
    return out


def resolve(method: str, path: str) -> str:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("testclient", 123),
    }
    for route in app.router.routes:
        try:
            match, _ = route.matches(scope)
        except Exception:
            continue
        if match == Match.FULL:
            endpoint = getattr(route, "endpoint", None)
            if endpoint is None:
                return f"<{type(route).__name__}>"
            return f"{endpoint.__module__}.{endpoint.__qualname__}"
    return "<NO MATCH>"


def main(target: str) -> None:
    samples = literal_segments()
    print(f"probe values from literal segments: {len(samples)}")

    cases = []
    seen = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if not path:
            continue
        for method in sorted(methods):
            for sample in sample_paths(path, samples):
                key = (method, sample)
                if key in seen:
                    continue
                seen.add(key)
                cases.append(key)

    lines = []
    for method, sample in sorted(cases):
        lines.append(f"{method:8s} {sample:75s} -> {resolve(method, sample)}")
    Path(target).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"dispatch cases: {len(lines)} -> {target}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "route_dispatch.txt")
