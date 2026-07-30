"""Recommendation API Router."""

from fastapi import APIRouter
from schemas.recommendation import RecommendationRequest, RecommendationResponse, FeedbackRequest
from services.recommendation_service import recommendation_service

router = APIRouter(tags=["Recommendation"])


@router.post("/recommend", response_model=RecommendationResponse)
async def recommend_endpoint(request: RecommendationRequest):
    """POST /recommend - Evaluates student code/telemetry snapshot and provides structured educational guidance."""
    return recommendation_service.recommend(request)

@router.post("/feedback")
async def feedback_endpoint(request: FeedbackRequest):
    """POST /feedback - Accepts thumbs up/down for a given hint."""
    import logging
    logger = logging.getLogger("cognitive_coach_backend")
    logger.info(f"Received feedback '{request.rating}' for session {request.session_id}")
    return {"status": "success"}
