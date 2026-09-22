"""Detect order-sensitive route pairs, robustly.

A route A registered earlier shadows a route B registered later when some concrete
path matches A's pattern and also matches B's pattern -- A wins, so B is unreachable
for that path. Both patterns may contain parameters, so we compare by generating
concrete sample paths from each pattern and testing them against the other pattern.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.main import app  # noqa: E402

SAMPLES = ["zzz", "1", "aaa-bbb"]


def pattern_to_regex(path: str) -> re.Pattern:
    parts = []
    for segment in path.split("/"):
        if segment.startswith("{") and segment.endswith("}"):
            name = segment[1:-1]
            parts.append(r".+" if name.endswith(":path") else r"[^/]+")
        else:
            parts.append(re.escape(segment))
    return re.compile("^" + "/".join(parts) + "$")


def sample_paths(path: str) -> list[str]:
    """Concrete paths this pattern can match, one per sample value."""
    out = []
    for sample in SAMPLES:
        parts = []
        for segment in path.split("/"):
            if segment.startswith("{") and segment.endswith("}"):
                name = segment[1:-1]
                parts.append(f"{sample}/{sample}" if name.endswith(":path") else sample)
            else:
                parts.append(segment)
        out.append("/".join(parts))
    return out


routes = []
for route in app.routes:
    path = getattr(route, "path", None)
    methods = getattr(route, "methods", None) or set()
    endpoint = getattr(route, "endpoint", None)
    if not path or not endpoint:
        continue
    routes.append((path, frozenset(methods), f"{endpoint.__module__}.{endpoint.__qualname__}"))

conflicts = []
for i, (path_a, methods_a, name_a) in enumerate(routes):
    regex_a = pattern_to_regex(path_a)
    for path_b, methods_b, name_b in routes[i + 1:]:
        if not (methods_a & methods_b):
            continue
        if any(regex_a.match(sample) for sample in sample_paths(path_b)):
            conflicts.append((path_a, path_b, name_a, name_b))

print(f"order-sensitive pairs: {len(conflicts)}")
for path_a, path_b, name_a, name_b in conflicts:
    same = "同模块" if name_a.rsplit(".", 1)[0] == name_b.rsplit(".", 1)[0] else "跨模块"
    print(f"  [{same}] {path_a}  shadows  {path_b}")
    print(f"      earlier: {name_a}")
    print(f"      later:   {name_b}")
