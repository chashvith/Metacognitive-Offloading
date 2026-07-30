"""Recommendation Context Builder Module."""

import logging
from typing import Any, Dict
from schemas.recommendation import (
    RecommendationRequest,
    RecommendationContext,
    ProblemContext,
    StudentContext,
    PredictionContext,
    SessionContext,
    HintLevelEnum,
)
from services.ml_service import ml_service

logger = logging.getLogger(__name__)


class RecommendationContextBuilder:
    """Factory builder for constructing unified domain RecommendationContext objects."""

    def build_context(self, request: RecommendationRequest) -> RecommendationContext:
        """Aggregates request metadata, student code, telemetry snapshot, and ML predictions.

        Args:
            request: RecommendationRequest payload.

        Returns:
            Fully initialized RecommendationContext.
        """
        snapshot = request.snapshot or {}

        # Extract problem metadata with fallback to snapshot or defaults
        prob_name = request.problem_name if (request.problem_name and request.problem_name != "Unknown Problem") else snapshot.get("problem_name", request.problem_name or "Unknown Problem")
        topic_val = request.topic if (request.topic and request.topic != "Arrays") else snapshot.get("topic", request.topic or "Arrays")
        subtopic_val = request.subtopic if (request.subtopic and request.subtopic != "Fundamentals") else snapshot.get("subtopic", request.subtopic or "Fundamentals")
        diff_val = request.difficulty if (request.difficulty and request.difficulty != "Easy") else snapshot.get("difficulty", request.difficulty or "Easy")
        lang_val = request.language if (request.language and request.language != "python") else snapshot.get("language", request.language or "python")

        problem = ProblemContext(
            problem_name=prob_name,
            topic=topic_val,
            subtopic=subtopic_val,
            difficulty=diff_val,
            language=lang_val,
        )

        student = StudentContext(
            student_code=request.student_code or snapshot.get("student_code", "")
        )

        session = SessionContext(
            struggle_score=float(snapshot.get("current_struggle_score", 0.0)),
            compile_attempts=int(snapshot.get("compile_attempts", 0)),
            compile_errors=int(snapshot.get("compile_errors", 0)),
            runtime_errors=int(snapshot.get("runtime_errors", 0)),
            pause_duration=float(snapshot.get("pause_duration", 0.0)),
            chars_typed=int(snapshot.get("chars_typed", 0)),
            chars_deleted=int(snapshot.get("chars_deleted", 0)),
            raw_telemetry=snapshot,
        )

        # Check if ML predictions are explicitly passed; if missing, invoke MLService
        solver_pred = request.solver_prediction
        solver_conf = request.solver_confidence
        hint_pred = request.hint_prediction
        hint_conf = request.hint_confidence

        if solver_pred is None or hint_pred is None:
            logger.info("Executing ML predictions via MLService for snapshot context...")
            ml_results = ml_service.predict_full(snapshot)
            solver_res = ml_results.get("solver", {})
            hint_res = ml_results.get("hint", {})

            if solver_pred is None:
                solver_pred = solver_res.get("prediction", "Likely to Solve")
                solver_conf = solver_res.get("confidence", 0.5)

            if hint_pred is None:
                hint_pred = hint_res.get("prediction", "No Hint")
                hint_conf = hint_res.get("confidence", 0.5)

        prediction = PredictionContext(
            solver_prediction=str(solver_pred),
            solver_confidence=float(solver_conf if solver_conf is not None else 0.5),
            hint_prediction=str(hint_pred),
            hint_confidence=float(hint_conf if hint_conf is not None else 0.5),
            normalized_hint_level=HintLevelEnum.from_string(str(hint_pred)),
        )

        context = RecommendationContext(
            problem=problem,
            student=student,
            prediction=prediction,
            session=session,
            is_regeneration=request.is_regeneration or False,
        )

        logger.debug("Built RecommendationContext: %s", context.model_dump())
        return context
