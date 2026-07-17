from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth_dependencies import require_auth
from app.config import settings
from app.db import engine
from app.middleware import security_middleware
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.health import router as health_router
from app.routes.model_endpoints import router as model_endpoints_router
from app.routes.model_profiles import router as model_profiles_router
from app.routes.persona import router as persona_router
from app.routes.tools import router as tools_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if settings.production else "/docs",
    redoc_url=None if settings.production else "/redoc",
    openapi_url=None if settings.production else "/openapi.json",
)
app.middleware("http")(security_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(auth_router)

private_route_dependencies = [Depends(require_auth)]
app.include_router(model_endpoints_router, dependencies=private_route_dependencies)
app.include_router(model_profiles_router, dependencies=private_route_dependencies)
app.include_router(persona_router, dependencies=private_route_dependencies)
app.include_router(tools_router, dependencies=private_route_dependencies)
app.include_router(chat_router, dependencies=private_route_dependencies)
