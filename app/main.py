from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, health, user
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"ENVIRONMENT = {settings.environment}")

    if settings.environment != "test":
        init_db()

    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan,
)
register_exception_handlers(app)
# Allowed frontend origins, parsed from comma-separated CORS_ORIGINS setting.
allowed_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registry for feature routers. Each new module under app/api/routes/
# should be included here, e.g. from app.api.routes import user; app.include_router(user.router).
app.include_router(auth.router)
app.include_router(health.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")


@app.get("/api/v1")
def root() -> dict:
    return {"status": "ok"}
