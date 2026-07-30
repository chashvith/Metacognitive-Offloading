"""Recommendation Engine Orchestrator Service."""

import logging
from typing import Any, Dict, Optional

from schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
)
from .context_builder import RecommendationContextBuilder
from .policy_engine import PolicyEngine
from .knowledge_base import ConceptKnowledgeBase
from .prompt_builder import StructuredPromptBuilder
from .response_generator import BaseGenerator, TemplateGenerator
from .hybrid_generator import HybridGenerator
from .validator import RecommendationValidator

logger = logging.getLogger(__name__)


class RecommendationService:
    """Orchestrator service executing the Recommendation Engine pipeline:
    
    ContextBuilder -> PolicyEngine -> KnowledgeBase -> PromptBuilder -> Generator -> Validator
    """

    def __init__(self, generator: Optional[BaseGenerator] = None):
        self.context_builder = RecommendationContextBuilder()
        self.policy_engine = PolicyEngine()
        self.knowledge_base = ConceptKnowledgeBase()
        self.prompt_builder = StructuredPromptBuilder()
        self.generator = generator or HybridGenerator()
        self.validator = RecommendationValidator()

    def recommend(self, request: RecommendationRequest | Dict[str, Any]) -> RecommendationResponse:
        """Executes the end-to-end recommendation pipeline.

        Args:
            request: RecommendationRequest Pydantic object or raw payload dictionary.

        Returns:
            RecommendationResponse structured output.
        """
        # 0. Convert raw dictionary payload if needed
        if isinstance(request, dict):
            # Check if dict wraps payload under 'snapshot' key or contains root attributes
            if "snapshot" in request and isinstance(request["snapshot"], dict) and len(request) == 1:
                snap = request["snapshot"]
                request_obj = RecommendationRequest(
                    problem_name=snap.get("problem_name", "Unknown Problem"),
                    topic=snap.get("topic", "Arrays"),
                    subtopic=snap.get("subtopic", "Fundamentals"),
                    difficulty=snap.get("difficulty", "Easy"),
                    language=snap.get("language", "python"),
                    student_code=snap.get("student_code", ""),
                    solver_prediction=snap.get("solver_prediction"),
                    solver_confidence=snap.get("solver_confidence"),
                    hint_prediction=snap.get("hint_prediction"),
                    hint_confidence=snap.get("hint_confidence"),
                    snapshot=snap
                )
            else:
                request_obj = RecommendationRequest(**request)
        else:
            request_obj = request

        logger.info("RecommendationService beginning orchestration pipeline...")

        # 1. Build unified domain context
        context = self.context_builder.build_context(request_obj)

        # 2. Determine educational teaching strategy (ML hint prediction is strictly preserved)
        strategy = self.policy_engine.determine_strategy(context)

        # 3. Retrieve concept knowledge from knowledge base
        concept_knowledge = self.knowledge_base.get_concept(
            topic=context.problem.topic,
            subtopic=context.problem.subtopic
        )

        # 4. Construct structured LLM-ready prompt
        prompt = self.prompt_builder.build_prompt(
            context=context,
            strategy=strategy,
            concept_knowledge=concept_knowledge
        )

        # 5. Generate content via pluggable Generator (TemplateGenerator in V1)
        raw_response = self.generator.generate(
            prompt=prompt,
            context=context,
            concept_knowledge=concept_knowledge
        )

        # 6. Validate policy guardrails & response integrity
        validated_response = self.validator.validate(
            response=raw_response,
            strategy=strategy
        )

        logger.info(
            "RecommendationService pipeline execution complete for problem '%s' at hint level '%s'",
            context.problem.problem_name,
            validated_response.level
        )
        return validated_response


# Global singleton instance
recommendation_service = RecommendationService()
