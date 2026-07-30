"""LLM Generator Module wrapping GroqClient."""

import logging
from typing import Any, Dict
from schemas.recommendation import (
    RecommendationContext,
    StructuredEducationalPrompt,
    RecommendationResponse,
)
from services.llm.groq_client import groq_client, GroqClient
from .response_generator import BaseGenerator
from .hybrid_generator import HybridGenerator

logger = logging.getLogger(__name__)


class LLMGenerator(BaseGenerator):
    """LLM Generator implementation wrapping GroqClient."""

    def __init__(self, client: GroqClient = groq_client):
        self.hybrid = HybridGenerator(client=client)

    def generate(
        self,
        prompt: StructuredEducationalPrompt,
        context: RecommendationContext,
        concept_knowledge: Dict[str, Any]
    ) -> RecommendationResponse:
        """Generates LLM recommendation response."""
        return self.hybrid.generate(prompt, context, concept_knowledge)
