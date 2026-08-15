"""Pydantic request/response models.

Convention: models on this module, feature logic in app/routers/.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
