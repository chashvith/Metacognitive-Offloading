"""Recommendation API Router."""

from fastapi import APIRouter
from schemas.recommendation import RecommendationRequest, RecommendationResponse
from services.recommendation_service import recommendation_service

router = APIRouter(tags=["Recommendation"])


@router.post("/recommend", response_model=RecommendationResponse)
async def recommend_endpoint(request: RecommendationRequest):
    """POST /recommend - Evaluates student code/telemetry snapshot and provides structured educational guidance."""
    return recommendation_service.recommend(request)
