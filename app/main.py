from fastapi import FastAPI

from app.config import settings
from app.routers import health

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
)

# Registry for feature routers. Each new module under app/routers/
# should be included here, e.g. from app.routers import items; app.include_router(items.router).
app.include_router(health.router)


@app.get("/")
def root() -> dict:
    return {"status": "ok"}
