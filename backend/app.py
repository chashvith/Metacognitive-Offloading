"""FastAPI Application Main Entry Point."""

import sys
from pathlib import Path

# Add backend directory to sys.path to guarantee module imports
backend_path = Path(__file__).resolve().parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import health, predict, recommendation
from services.ml_service import ml_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cognitive_coach_backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager: Pre-loads ML models ONCE at application startup."""
    logger.info("FastAPI starting up...")
    ml_service.load()
    yield
    logger.info("FastAPI shutting down...")


app = FastAPI(
    title="Cognitive Coach - Metacognitive Offloading API",
    description="FastAPI Backend for student telemetry analysis, solver prediction, and hint recommendation.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for VS Code Extension or frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router)
app.include_router(predict.router)
app.include_router(recommendation.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
