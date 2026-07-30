"""Hybrid Generator Module with LLM + Template Fallback & Policy Enforcement."""

import logging
from typing import Any, Dict, Optional

from schemas.recommendation import (
    RecommendationContext,
    StructuredEducationalPrompt,
    RecommendationResponse,
    HintLevelEnum,
    TeachingStrategy,
)
from services.llm.gemini_client import gemini_client, GeminiClient
from .response_generator import BaseGenerator, TemplateGenerator

logger = logging.getLogger(__name__)


class HybridGenerator(BaseGenerator):
    """Hybrid recommendation generator that attempts Google Gemini 2.5 Flash API calls
    and seamlessly falls back to TemplateGenerator upon any error, timeout, or policy violation.
    """

    def __init__(
        self,
        client: Optional[GeminiClient] = None,
        fallback_generator: Optional[TemplateGenerator] = None,
    ):
        self.client = client or gemini_client
        self.fallback = fallback_generator or TemplateGenerator()

    def generate(
        self,
        prompt: StructuredEducationalPrompt,
        context: RecommendationContext,
        concept_knowledge: Dict[str, Any]
    ) -> RecommendationResponse:
        """Generates structured educational recommendation using Gemini, with Template fallback."""
        strategy = prompt.teaching_strategy

        try:
            logger.info("HybridGenerator: Attempting LLM recommendation generation via Gemini 2.5 Flash...")
            
            # Build unified text prompt for Gemini
            full_user_prompt = (
                f"{prompt.problem_context_summary}\n\n"
                f"{prompt.concept_knowledge_summary}\n\n"
                f"{prompt.reflection_prompt_directive}\n\n"
                f"Assigned Strategy Rules: Allow Code = {strategy.allow_code}, "
                f"Allow Pseudocode = {strategy.allow_pseudocode}, Hint Level = {strategy.hint_level.value}."
            )
            print("\n" + "=" * 80)
            print("FULL USER PROMPT:")
            print(full_user_prompt)
            print("=" * 80 + "\n")
            llm_output = self.client.generate_structured_json(
                system_instruction=prompt.system_instruction,
                user_prompt=full_user_prompt
            )

            if llm_output and isinstance(llm_output, dict):
                validated_response = self._apply_policy_and_build_response(
                    llm_output=llm_output,
                    strategy=strategy,
                    context=context
                )
                if validated_response:
                    logger.info("HybridGenerator: Successfully generated and validated LLM recommendation.")
                    return validated_response

            logger.warning("HybridGenerator: LLM generation returned invalid or empty payload. Falling back to TemplateGenerator.")

        except Exception as e:
            logger.error("HybridGenerator: Exception during Gemini execution: %s. Falling back to TemplateGenerator.", e)

        # Fallback to TemplateGenerator
        logger.info("HybridGenerator: Executing fallback to TemplateGenerator.")
        return self.fallback.generate(prompt, context, concept_knowledge)

    def _apply_policy_and_build_response(
        self,
        llm_output: Dict[str, Any],
        strategy: TeachingStrategy,
        context: RecommendationContext
    ) -> Optional[RecommendationResponse]:
        """Validates LLM output fields and strictly enforces pedagogical policy constraints."""
        title = llm_output.get("title") or strategy.hint_level.value.replace("_", " ").title()
        message = llm_output.get("message")
        next_step = llm_output.get("next_step")
        reflection = llm_output.get("reflection_question")
        encouragement = llm_output.get("encouragement") or "Keep up the active problem solving!"

        # Ensure required fields are present
        if not message or not next_step or not reflection:
            logger.warning("HybridGenerator: Missing required fields in LLM output (message, next_step, or reflection_question).")
            return None

        # Enforce Policy Guards on Code Disclosures
        code_snippet = llm_output.get("code")
        complexity_info = llm_output.get("complexity")

        # PART 4 STRICT POLICY: If strategy forbids code, strip code snippet completely
        if not strategy.allow_code:
            if code_snippet:
                logger.info("HybridGenerator Policy Guard: Stripped code snippet disallowed by strategy '%s'", strategy.hint_level.value)
            code_snippet = None
            complexity_info = None
        else:
            # If strategy allows code (FULL_SOLUTION), ensure code string is present
            if not code_snippet:
                solution_codes = context.session.raw_telemetry.get("solution_code", {}) if context.session.raw_telemetry else {}
                code_snippet = solution_codes.get(context.problem.language.lower(), "# Reference solution code\npass")
            if not complexity_info:
                complexity_info = {"time": "O(N)", "space": "O(1)"}

        metadata = {
            "problem_name": context.problem.problem_name,
            "topic": context.problem.topic,
            "subtopic": context.problem.subtopic,
            "language": context.problem.language,
            "solver_prediction": context.prediction.solver_prediction,
            "hint_prediction": context.prediction.hint_prediction,
            "confidence": context.prediction.hint_confidence,
            "generator_type": "Gemini_2.5_Flash",
        }

        return RecommendationResponse(
            title=str(title),
            level=strategy.hint_level.value,
            message=str(message),
            next_step=str(next_step),
            reflection_question=str(reflection),
            encouragement=str(encouragement),
            confidence=context.prediction.hint_confidence,
            code=code_snippet,
            complexity=complexity_info,
            metadata=metadata,
            status="success"
        )
