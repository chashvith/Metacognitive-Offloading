"""Health Check Route."""

from fastapi import APIRouter
from schemas.snapshot import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """GET /health - Returns the operational status of the FastAPI backend."""
    return {"status": "running"}
