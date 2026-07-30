"""Educational Policy Engine Module."""

import logging
from schemas.recommendation import RecommendationContext, TeachingStrategy, HintLevelEnum

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Evaluates recommendation context and enforces educational policy rules.
    
    CRITICAL POLICY GUARDRAIL: The PolicyEngine strictly preserves the hint level
    predicted by the ML model. It NEVER overrides or alters the ML hint level.
    """

    def determine_strategy(self, context: RecommendationContext) -> TeachingStrategy:
        """Translates ML hint prediction into explicit TeachingStrategy rules.

        Args:
            context: RecommendationContext containing domain context objects.

        Returns:
            TeachingStrategy instance.
        """
        hint_level = context.prediction.normalized_hint_level

        logger.info(
            "PolicyEngine processing predicted hint level: '%s' (raw: '%s')",
            hint_level.value,
            context.prediction.hint_prediction
        )

        if hint_level == HintLevelEnum.NO_HINT:
            strategy = TeachingStrategy(
                hint_level=HintLevelEnum.NO_HINT,
                allow_code=False,
                allow_pseudocode=False,
                allow_algorithm_reveal=False,
                require_reflection_question=True,
                tone="supportive_and_encouraging",
                max_hint_depth="encouragement_only"
            )
        elif hint_level == HintLevelEnum.CONCEPT:
            strategy = TeachingStrategy(
                hint_level=HintLevelEnum.CONCEPT,
                allow_code=False,
                allow_pseudocode=False,
                allow_algorithm_reveal=False,
                require_reflection_question=True,
                tone="conceptual_scaffolding",
                max_hint_depth="underlying_concept_only"
            )
        elif hint_level == HintLevelEnum.GUIDED:
            strategy = TeachingStrategy(
                hint_level=HintLevelEnum.GUIDED,
                allow_code=False,
                allow_pseudocode=False,
                allow_algorithm_reveal=True,
                require_reflection_question=True,
                tone="actionable_step_guidance",
                max_hint_depth="next_logical_step"
            )
        elif hint_level == HintLevelEnum.PSEUDOCODE:
            strategy = TeachingStrategy(
                hint_level=HintLevelEnum.PSEUDOCODE,
                allow_code=False,
                allow_pseudocode=True,
                allow_algorithm_reveal=True,
                require_reflection_question=True,
                tone="algorithmic_structure",
                max_hint_depth="language_independent_pseudocode"
            )
        elif hint_level == HintLevelEnum.FULL_SOLUTION:
            strategy = TeachingStrategy(
                hint_level=HintLevelEnum.FULL_SOLUTION,
                allow_code=True,
                allow_pseudocode=True,
                allow_algorithm_reveal=True,
                require_reflection_question=True,
                tone="comprehensive_reference",
                max_hint_depth="full_code_and_complexity"
            )
        else:
            # Default fallback adhering to concept level
            strategy = TeachingStrategy(
                hint_level=HintLevelEnum.CONCEPT,
                allow_code=False,
                allow_pseudocode=False,
                allow_algorithm_reveal=False,
                require_reflection_question=True,
                tone="conceptual_scaffolding",
                max_hint_depth="underlying_concept_only"
            )

        return strategy
