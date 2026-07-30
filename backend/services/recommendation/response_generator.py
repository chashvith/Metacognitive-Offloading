"""Response Generator Module with Pluggable Abstractions."""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

from schemas.recommendation import (
    RecommendationContext,
    StructuredEducationalPrompt,
    RecommendationResponse,
    HintLevelEnum,
)

logger = logging.getLogger(__name__)


class BaseGenerator(ABC):
    """Abstract Base Class for content generation.
    
    Decouples educational strategy and prompt building from rendering mechanism.
    Allows seamless swapping between template-based and LLM-backed generators.
    """

    @abstractmethod
    def generate(
        self,
        prompt: StructuredEducationalPrompt,
        context: RecommendationContext,
        concept_knowledge: Dict[str, Any]
    ) -> RecommendationResponse:
        """Generates structured educational recommendation response."""
        pass


class TemplateGenerator(BaseGenerator):
    """Version 1 Implementation: Generates educational responses using template lookups and concept knowledge."""

    def __init__(self, templates_dir: Path | str | None = None):
        if templates_dir is None:
            self.templates_dir = Path(__file__).resolve().parent.parent.parent / "templates"
        else:
            self.templates_dir = Path(templates_dir)

    def _load_template(self, hint_level: HintLevelEnum) -> Dict[str, Any]:
        """Loads JSON template file for the specified hint level."""
        level_str = hint_level.value
        template_file = self.templates_dir / level_str / "default.json"

        if template_file.exists():
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Error reading template file %s: %s", template_file, e)

        # Fallback default template map
        return {
            "title": hint_level.value.replace("_", " ").title(),
            "level": hint_level.value,
            "message_template": "Focus on the core concept and step-by-step logic.",
            "next_step_template": "Review your logic systematically.",
            "reflection_question_template": "{reflection_question}",
            "encouragement": "Keep going! Active problem solving builds strong intuition.",
            "include_code": hint_level == HintLevelEnum.FULL_SOLUTION,
            "include_complexity": hint_level == HintLevelEnum.FULL_SOLUTION,
        }

    def generate(
        self,
        prompt: StructuredEducationalPrompt,
        context: RecommendationContext,
        concept_knowledge: Dict[str, Any]
    ) -> RecommendationResponse:
        """Generates a RecommendationResponse using template rendering."""
        strategy = prompt.teaching_strategy
        level = strategy.hint_level
        template_data = self._load_template(level)

        hints_map = concept_knowledge.get("hints", {}).get(level.value, {})

        # Extract concept data & defaults
        concept_name = concept_knowledge.get("name", context.problem.topic)
        explanation = concept_knowledge.get("explanation", "Deconstruct the problem step-by-step.")

        # Determine message text
        msg_template = template_data.get("message_template", "{concept_explanation}")
        message = hints_map.get("message") or msg_template.format(
            problem_name=context.problem.problem_name,
            concept_explanation=explanation,
            concept_name=concept_name,
            guided_message=hints_map.get("message", explanation),
            pseudocode=concept_knowledge.get("pseudocode", ""),
            full_solution_message=hints_map.get("message", f"Solution breakdown for {context.problem.problem_name}")
        )

        # Determine next step text
        next_step_template = template_data.get("next_step_template", "{concept_next_step}")
        next_step = hints_map.get("next_step") or next_step_template.format(
            concept_next_step=hints_map.get("next_step", "Identify the core operation in your current logic."),
            guided_next_step=hints_map.get("next_step", "Trace variable updates for a single iteration."),
            pseudocode_next_step=hints_map.get("next_step", "Implement the pseudocode logic in your code."),
            language=context.problem.language
        )

        # Determine reflection question
        concept_reflections = concept_knowledge.get("reflection_questions", [])
        default_reflection = concept_reflections[0] if concept_reflections else "What is the expected state after your main loop?"
        reflection_question = hints_map.get("reflection_question", default_reflection)

        encouragement = hints_map.get("encouragement") or template_data.get(
            "encouragement", "You're making good progress! Keep thinking through your approach."
        )

        # Handle optional code snippet and complexity for full_solution level
        code_snippet = None
        complexity_info = None

        if strategy.allow_code and level == HintLevelEnum.FULL_SOLUTION:
            solution_codes = concept_knowledge.get("solution_code", {})
            lang_key = context.problem.language.lower()
            code_snippet = solution_codes.get(lang_key) or solution_codes.get("python") or "# Reference solution\npass"
            complexity_info = concept_knowledge.get("complexity", {"time": "O(N)", "space": "O(1)"})

        metadata = {
            "problem_name": context.problem.problem_name,
            "topic": context.problem.topic,
            "subtopic": context.problem.subtopic,
            "language": context.problem.language,
            "solver_prediction": context.prediction.solver_prediction,
            "hint_prediction": context.prediction.hint_prediction,
            "confidence": context.prediction.hint_confidence,
            "generator_type": "TemplateGenerator",
        }

        response = RecommendationResponse(
            title=template_data.get("title", level.value.replace("_", " ").title()),
            level=level.value,
            message=message,
            next_step=next_step,
            reflection_question=reflection_question,
            encouragement=encouragement,
            confidence=context.prediction.hint_confidence,
            code=code_snippet,
            complexity=complexity_info,
            metadata=metadata,
            status="success",
        )

        logger.info("TemplateGenerator successfully rendered response for level '%s'", level.value)
        return response
