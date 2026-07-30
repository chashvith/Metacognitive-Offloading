"""Structured Prompt Builder Module."""

import logging
from typing import Any, Dict
from schemas.recommendation import (
    RecommendationContext,
    TeachingStrategy,
    StructuredEducationalPrompt,
    HintLevelEnum,
)

logger = logging.getLogger(__name__)


class StructuredPromptBuilder:
    """Combines RecommendationContext, TeachingStrategy, and Concept Knowledge
    into a structured educational prompt formatted for Gemini 2.5 Flash.
    """

    def build_prompt(
        self,
        context: RecommendationContext,
        strategy: TeachingStrategy,
        concept_knowledge: Dict[str, Any]
    ) -> StructuredEducationalPrompt:
        """Constructs a StructuredEducationalPrompt incorporating telemetry, predictions, and code.

        Args:
            context: Unified RecommendationContext containing problem, student, prediction, session data.
            strategy: Educational TeachingStrategy policy object.
            concept_knowledge: Concept knowledge dictionary from KnowledgeBase.

        Returns:
            StructuredEducationalPrompt object.
        """
        hint_level = strategy.hint_level.value

        system_instruction = (
            "You are an expert AI Programming Tutor (Cognitive Coach). Your objective is to provide "
            "scaffolded, metacognitive guidance to help students solve programming problems actively.\n\n"
            "STRICT RULES:\n"
            "1. Be concise, direct, and constructive. Avoid fluff, excessive praise, or filler.\n"
            "2. Reference the student's actual code logic and variable names when applicable.\n"
            "3. NEVER hallucinate non-existent libraries or syntax.\n"
            "4. STRICTLY ENFORCE THE ASSIGNED HINT LEVEL:\n"
            "   - 'no_hint': Offer encouragement only. DO NOT provide hints, logic, or code.\n"
            "   - 'concept': Explain the core CS concept and intuition ONLY. DO NOT provide code or pseudocode.\n"
            "   - 'guided': Provide actionable, step-by-step logical guidance for the next step. DO NOT provide solution code.\n"
            "   - 'pseudocode': Provide language-independent pseudocode explaining the algorithm. DO NOT provide working code in student's language.\n"
            "   - 'full_solution': Provide complete, clean, commented reference solution code and time/space complexity.\n"
            "5. OUTPUT FORMAT: Respond strictly with a single JSON object containing keys:\n"
            '   "title", "level", "message", "next_step", "reflection_question", "encouragement", "code" (optional), "complexity" (optional).'
        )

        raw_snap = context.session.raw_telemetry or {}

        student_code = context.student.student_code or "# No student code written yet"
        compile_errors = context.session.compile_errors
        compile_attempts = context.session.compile_attempts
        struggle_score = context.session.struggle_score
        pause_duration = context.session.pause_duration
        chars_typed = context.session.chars_typed
        chars_deleted = context.session.chars_deleted
        progress_ratio = raw_snap.get("progress_ratio", 0.0)

        concept_name = concept_knowledge.get("name", context.problem.topic)
        explanation = concept_knowledge.get("explanation", "")

        problem_summary = (
            f"--- PROBLEM & STUDENT CONTEXT ---\n"
            f"Problem Name: {context.problem.problem_name}\n"
            f"Topic: {context.problem.topic} ({context.problem.subtopic})\n"
            f"Difficulty: {context.problem.difficulty}\n"
            f"Language: {context.problem.language}\n\n"
            f"--- ML MODEL PREDICTIONS ---\n"
            f"Solver Prediction: {context.prediction.solver_prediction} (Confidence: {context.prediction.solver_confidence:.2f})\n"
            f"Hint Prediction: {context.prediction.hint_prediction} (Confidence: {context.prediction.hint_confidence:.2f})\n"
            f"Assigned Strategy Hint Level: {hint_level}\n\n"
            f"--- TELEMETRY METRICS ---\n"
            f"Current Struggle Score: {struggle_score:.2f}\n"
            f"Progress Ratio: {progress_ratio:.2f}\n"
            f"Compile Attempts: {compile_attempts} | Compile Errors: {compile_errors}\n"
            f"Characters Typed: {chars_typed} | Deleted: {chars_deleted}\n"
            f"Total Pause Duration: {pause_duration:.1f}s\n\n"
            f"--- STUDENT CURRENT CODE ---\n"
            f"```{context.problem.language}\n{student_code}\n```\n"
        )

        concept_summary = (
            f"--- CONCEPT KNOWLEDGE BASE ---\n"
            f"Target Concept: {concept_name}\n"
            f"Concept Explanation: {explanation}\n"
        )

        reflection_directive = (
            f"Mandatory Reflection Directive: Formulate a single, thought-provoking metacognitive question "
            f"tailored to the student's current code state and hint level '{hint_level}'."
        )

        formatting_requirements = {
            "required_fields": ["title", "level", "message", "next_step", "reflection_question", "encouragement"],
            "allow_code": strategy.allow_code,
            "allow_pseudocode": strategy.allow_pseudocode,
            "language": context.problem.language,
            "hint_level": hint_level,
        }

        prompt = StructuredEducationalPrompt(
            system_instruction=system_instruction,
            problem_context_summary=problem_summary,
            concept_knowledge_summary=concept_summary,
            teaching_strategy=strategy,
            reflection_prompt_directive=reflection_directive,
            formatting_requirements=formatting_requirements,
        )

        logger.debug("Built StructuredEducationalPrompt for level '%s'", hint_level)
        return prompt
