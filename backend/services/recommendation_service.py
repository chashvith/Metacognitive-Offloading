"""Pedagogical Recommendation Engine Service."""

import logging
from typing import Any, Dict
from .ml_service import ml_service

logger = logging.getLogger(__name__)


class RecommendationService:
    """Service to evaluate student struggle telemetry and generate recommendations."""

    def recommend(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates struggle level and outputs intervention recommendation.

        Args:
            snapshot: Student coding session snapshot.

        Returns:
            Recommendation response dictionary.
        """
        # Execute ML predictions
        predictions = ml_service.predict_full(snapshot)
        solver_pred = predictions.get("solver", {})
        hint_pred = predictions.get("hint", {})

        struggle_score = snapshot.get("current_struggle_score", 0.0)
        compile_errors = snapshot.get("compile_errors", 0)
        pause_duration = snapshot.get("pause_duration", 0.0)
        solver_status = solver_pred.get("prediction", "Likely to Solve")
        hint_recommendation = hint_pred.get("prediction", "No Hint")

        # Determine struggle level
        if struggle_score >= 0.5 or solver_status == "Unlikely to Solve" or compile_errors >= 5:
            struggle_level = "High"
            intervention_type = "Active Assistance"
            recommended_action = f"Provide {hint_recommendation}. Student is experiencing significant struggle."
        elif struggle_score >= 0.25 or compile_errors >= 2 or pause_duration > 60:
            struggle_level = "Medium"
            intervention_type = "Nudge"
            recommended_action = f"Suggest checking syntax or offer a {hint_recommendation}."
        else:
            struggle_level = "Low"
            intervention_type = "Observe"
            recommended_action = "Allow independent problem solving. No intervention required."

        return {
            "status": "success",
            "struggle_level": struggle_level,
            "recommended_action": recommended_action,
            "intervention_type": intervention_type,
            "details": {
                "struggle_score": struggle_score,
                "solver_prediction": solver_status,
                "hint_prediction": hint_recommendation,
                "solver_confidence": solver_pred.get("confidence", 0.5),
                "hint_confidence": hint_pred.get("confidence", 0.5)
            }
        }


# Global singleton instance
recommendation_service = RecommendationService()
