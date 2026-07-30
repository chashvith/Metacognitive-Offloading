"""Concept Knowledge Base Module."""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ConceptKnowledgeBase:
    """Manages loading and querying of concept-based educational knowledge files."""

    def __init__(self, knowledge_dir: Path | str | None = None):
        if knowledge_dir is None:
            self.knowledge_dir = Path(__file__).resolve().parent.parent.parent / "knowledge"
        else:
            self.knowledge_dir = Path(knowledge_dir)

        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_concept: Dict[str, Any] = {}
        self._load_default_concept()

    def _load_default_concept(self) -> None:
        """Loads default_concept.json as global fallback."""
        default_file = self.knowledge_dir / "default_concept.json"
        if default_file.exists():
            try:
                with open(default_file, "r", encoding="utf-8") as f:
                    self._default_concept = json.load(f)
                logger.info("Loaded default concept knowledge base from %s", default_file)
            except Exception as e:
                logger.error("Failed to load default concept knowledge file: %s", e)
                self._default_concept = self._fallback_in_memory_concept()
        else:
            logger.warning("default_concept.json not found at %s. Using in-memory fallback.", default_file)
            self._default_concept = self._fallback_in_memory_concept()

    def _fallback_in_memory_concept(self) -> Dict[str, Any]:
        """Provides minimal in-memory fallback if JSON loading fails."""
        return {
            "concept_id": "generic_fallback",
            "name": "General Problem Solving",
            "explanation": "Break down the problem systematically into smaller subproblems.",
            "hints": {
                "no_hint": {
                    "message": "Keep working through your logic.",
                    "next_step": "Test your current approach on simple inputs.",
                    "reflection_question": "What is the expected state after your main loop?"
                },
                "concept": {
                    "message": "Focus on selecting the right data structure for efficiency.",
                    "next_step": "Identify which operation consumes the most runtime.",
                    "reflection_question": "What data structure could optimize your access time?"
                },
                "guided": {
                    "message": "Verify your loop conditions and state updates.",
                    "next_step": "Trace your variables through one iteration.",
                    "reflection_question": "What state invariant must hold true?"
                },
                "pseudocode": {
                    "message": "FOR item IN input:\n    PROCESS item",
                    "next_step": "Translate pseudocode steps to your target language.",
                    "reflection_question": "How do you handle edge cases?"
                },
                "full_solution": {
                    "message": "Iterate systematically maintaining clean state variables.",
                    "next_step": "Compare reference solution with your approach.",
                    "reflection_question": "Can space complexity be further reduced?"
                }
              },
            "reflection_questions": [
                "What assumptions are you making about inputs?"
            ],
            "pseudocode": "FOR item IN input:\n    PROCESS item",
            "solution_code": {
                "python": "# Generic reference solution\npass",
                "java": "// Generic reference solution",
                "cpp": "// Generic reference solution"
            },
            "complexity": {"time": "O(N)", "space": "O(1)"}
        }

    def get_concept(self, topic: str, subtopic: str) -> Dict[str, Any]:
        """Retrieves concept knowledge dictionary for a given topic and subtopic.

        Args:
            topic: High-level topic (e.g., 'Arrays', 'HashMaps', 'Graphs').
            subtopic: Subtopic or concept key (e.g., 'Fundamentals', 'BFS', 'Two Pointers').

        Returns:
            Dict containing concept explanation, hints, reflection questions, pseudocode, solutions.
        """
        # Normalize topic directory and concept filename
        topic_clean = (topic or "general").strip().lower().replace(" ", "_")
        subtopic_clean = (subtopic or "fundamentals").strip().lower().replace(" ", "_")

        cache_key = f"{topic_clean}/{subtopic_clean}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Candidate paths to inspect
        candidate_paths = [
            self.knowledge_dir / topic_clean / f"{subtopic_clean}.json",
            self.knowledge_dir / topic_clean / "fundamentals.json",
            self.knowledge_dir / f"{topic_clean}.json"
        ]

        for path in candidate_paths:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        concept_data = json.load(f)
                    self._cache[cache_key] = concept_data
                    logger.info("Found concept knowledge at %s", path)
                    return concept_data
                except Exception as e:
                    logger.error("Error reading concept file %s: %s", path, e)

        logger.info("No concept file found for topic '%s' / subtopic '%s'. Using default concept.", topic, subtopic)
        return self._default_concept
