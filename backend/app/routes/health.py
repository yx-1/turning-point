"""Health check route.

What this file does:
    Tells the frontend whether the API process is running.

What enters:
    GET /health. There is no request body and no personal data.

What happens inside:
    The function does not touch a database or calculate a chart.
    It returns a fixed payload so the React app can confirm the connection.

What it returns:
    JSON shaped like {"status": "ok", "service": "turning-point-api"}.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
@router.get("/healthz", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="turning-point-api")
