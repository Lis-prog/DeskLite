from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, health, metrics, tickets
from app.core.config import settings
from app.core.security_headers import SecurityHeadersMiddleware

_is_production = settings.app_env.lower() == "production"

_is_production = settings.app_env.lower() == "production"

app = FastAPI(
    title="DeskLite API",
    version="0.1.0",
    docs_url=None if _is_production else "/docs",
    openapi_url=None if _is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

# All v1 routers mount under /api/v1
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(tickets.router, prefix="/api/v1")


@app.get("/", tags=["meta"])
def root():
    return {"name": "DeskLite API", "docs": "/docs", "health": "/api/v1/health"}
