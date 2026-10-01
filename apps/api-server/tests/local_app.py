"""本地测试专用 ASGI 入口，独立分发清理请求。"""

from fastapi import FastAPI
from starlette.types import Receive, Scope, Send

from tests.environment import validate_loaded_test_settings, validate_test_environment

validate_test_environment()

from app.config import settings

validate_loaded_test_settings(settings)

from app.main import app as production_app
from tests.cleanup_router import router as cleanup_router


cleanup_app = FastAPI()
cleanup_app.include_router(cleanup_router)


@cleanup_app.get(f"{settings.api_prefix}/testing/health", include_in_schema=False)
async def testing_health() -> dict[str, str]:
    return {"service": "oa-local-testing", "app_env": settings.app_env}


class LocalTestApp:
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith(f"{settings.api_prefix}/testing/"):
            await cleanup_app(scope, receive, send)
            return
        await production_app(scope, receive, send)


app = LocalTestApp()
