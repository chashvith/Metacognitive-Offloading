"""Recommendation Routes."""

from fastapi import APIRouter
from schemas.snapshot import RecommendationRequest, RecommendationResponse
from services.recommendation_service import recommendation_service

router = APIRouter(tags=["Recommendation"])


@router.post("/recommend", response_model=RecommendationResponse)
async def recommend_endpoint(request: RecommendationRequest):
    """POST /recommend - Evaluates student session snapshot and provides intervention advice."""
    result = recommendation_service.recommend(request.snapshot)
    return result
