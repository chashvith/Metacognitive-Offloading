"""Prediction Routes for Solver and Hint Models."""

from fastapi import APIRouter, HTTPException, status
from schemas.snapshot import PredictRequest, PredictResponse, FullPredictResponse
from services.ml_service import ml_service

router = APIRouter(prefix="/predict", tags=["Predictions"])


@router.post("/solver", response_model=PredictResponse)
async def predict_solver_endpoint(request: PredictRequest):
    """POST /predict/solver - Predicts whether a student will solve the problem."""
    result = ml_service.predict_solver(request.snapshot)
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Prediction failed.")
        )
    return {
        "prediction": result.get("prediction", "Unknown"),
        "confidence": result.get("confidence", 0.5),
        "status": "success",
        "solve_probability": result.get("solve_probability"),
        "timestamp": result.get("timestamp")
    }


@router.post("/hint", response_model=PredictResponse)
async def predict_hint_endpoint(request: PredictRequest):
    """POST /predict/hint - Predicts the minimum effective hint level required."""
    result = ml_service.predict_hint(request.snapshot)
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Hint prediction failed.")
        )
    return {
        "prediction": result.get("prediction", "No Hint"),
        "confidence": result.get("confidence", 0.5),
        "status": "success",
        "timestamp": result.get("timestamp")
    }


@router.post("/full", response_model=FullPredictResponse)
async def predict_full_endpoint(request: PredictRequest):
    """POST /predict/full - Runs both solver and hint models concurrently."""
    result = ml_service.predict_full(request.snapshot)
    return {
        "status": "success",
        "solver": result.get("solver", {}),
        "hint": result.get("hint", {})
    }
