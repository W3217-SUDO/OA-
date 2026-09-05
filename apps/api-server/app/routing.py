"""Compose area routers without changing the monolith's first-match order."""
from fastapi import APIRouter, FastAPI
from collections import Counter


def include_route_slice(app: FastAPI, router: APIRouter, start: int, stop: int) -> None:
    """Include an ordered contiguous slice, retaining all FastAPI route metadata.

    Area routers contain HTTP endpoints only. Application lifespan, middleware,
    exception handlers and pre-existing router factories stay in main.py.
    """
    if not 0 <= start < stop <= len(router.routes):
        raise ValueError(f"Invalid area route slice [{start}:{stop}] of {len(router.routes)}")
    app.include_router(APIRouter(routes=router.routes[start:stop]))


def verify_route_coverage(app: FastAPI, routers: list[APIRouter]) -> None:
    """Fail at import if an area endpoint is omitted or included more than once.

    FastAPI clones routes during inclusion, but keeps each endpoint callable.
    Comparing callable identity plus path and methods also handles legacy
    duplicate function names and multiple decorators on one callable.
    """
    def key(route):
        return (route.endpoint, route.path, tuple(sorted(route.methods or [])))

    expected = Counter(key(route) for router in routers for route in router.routes)
    endpoints = {item[0] for item in expected}
    actual = Counter(key(route) for route in app.routes if getattr(route, "endpoint", None) in endpoints)
    missing, repeated = expected - actual, actual - expected
    if missing or repeated:
        describe = lambda entries: [(path, methods, count) for (_, path, methods), count in entries.items()]
        raise RuntimeError(f"Area route composition is incomplete: missing={describe(missing)}; repeated={describe(repeated)}. Update main.py route composition.")
