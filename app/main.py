from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, user
from app.core.config import settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan,
)

# Registry for feature routers. Each new module under app/api/routes/
# should be included here, e.g. from app.api.routes import user; app.include_router(user.router).
app.include_router(health.router)
app.include_router(user.router)


@app.get("/")
def root() -> dict:
    return {"status": "ok"}
