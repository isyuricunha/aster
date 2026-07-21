from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import (  # noqa: F401
    agent_dispatch_models,
    agent_models,
    agent_notification_models,
    agent_run_scope_models,
    automation_models,
    communication_models,
    image_models,
    retrieval_models,
    skill_models,
)
from app.auth_dependencies import require_auth
from app.config import settings
from app.conversation_titles import ConversationTitleMiddleware
from app.db import engine
from app.imap_sync_patch import install_imap_sync_patch
from app.middleware import security_middleware
from app.routes.agent_notifications import router as agent_notifications_router
from app.routes.agent_rules import router as agent_rules_router
from app.routes.agent_runs import router as agent_runs_router
from app.routes.agents import router as agents_router
from app.routes.auth import router as auth_router
from app.routes.automations import private_router as automations_router
from app.routes.chat import router as chat_router
from app.routes.communication_drafts import router as communication_drafts_router
from app.routes.communications import router as communications_router
from app.routes.health import router as health_router
from app.routes.images import router as images_router
from app.routes.knowledge import router as knowledge_router
from app.routes.memory import router as memory_router
from app.routes.model_endpoints import router as model_endpoints_router
from app.routes.model_profiles import router as model_profiles_router
from app.routes.persona import router as persona_router
from app.routes.skills import router as skills_router
from app.routes.tasks import router as tasks_router
from app.routes.tools import router as tools_router
from app.routes.webhooks import router as webhook_router

install_imap_sync_patch()


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
app.add_middleware(ConversationTitleMiddleware)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(webhook_router)

private_route_dependencies = [Depends(require_auth)]
app.include_router(model_endpoints_router, dependencies=private_route_dependencies)
app.include_router(model_profiles_router, dependencies=private_route_dependencies)
app.include_router(persona_router, dependencies=private_route_dependencies)
app.include_router(tools_router, dependencies=private_route_dependencies)
app.include_router(memory_router, dependencies=private_route_dependencies)
app.include_router(knowledge_router, dependencies=private_route_dependencies)
app.include_router(images_router, dependencies=private_route_dependencies)
app.include_router(automations_router, dependencies=private_route_dependencies)
app.include_router(tasks_router, dependencies=private_route_dependencies)
app.include_router(skills_router, dependencies=private_route_dependencies)
app.include_router(communications_router, dependencies=private_route_dependencies)
app.include_router(communication_drafts_router, dependencies=private_route_dependencies)
app.include_router(agents_router, dependencies=private_route_dependencies)
app.include_router(agent_runs_router, dependencies=private_route_dependencies)
app.include_router(agent_rules_router, dependencies=private_route_dependencies)
app.include_router(agent_notifications_router, dependencies=private_route_dependencies)
app.include_router(chat_router, dependencies=private_route_dependencies)
