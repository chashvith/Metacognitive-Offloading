"""Domain Schemas for Recommendation Engine."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class HintLevelEnum(str, Enum):
    """Supported pedagogical hint levels."""
    NO_HINT = "no_hint"
    CONCEPT = "concept"
    GUIDED = "guided"
    PSEUDOCODE = "pseudocode"
    FULL_SOLUTION = "full_solution"

    @classmethod
    def from_string(cls, label: str) -> "HintLevelEnum":
        """Normalizes prediction string to HintLevelEnum."""
        clean = (label or "").strip().lower()
        if "no" in clean:
            return cls.NO_HINT
        elif "concept" in clean:
            return cls.CONCEPT
        elif "guided" in clean or "step" in clean:
            return cls.GUIDED
        elif "pseudo" in clean:
            return cls.PSEUDOCODE
        elif "full" in clean or "solution" in clean:
            return cls.FULL_SOLUTION
        return cls.CONCEPT  # Fallback default if unknown string


class SolverPredictionEnum(str, Enum):
    """Supported solver prediction status."""
    LIKELY = "Likely to Solve"
    UNLIKELY = "Unlikely to Solve"
    NEEDS_HELP = "Needs Help"

    @classmethod
    def from_string(cls, label: str) -> "SolverPredictionEnum":
        clean = (label or "").strip().lower()
        if "unlikely" in clean or "needs" in clean:
            return cls.UNLIKELY
        return cls.LIKELY


# --- Domain-Specific Context Objects ---

class ProblemContext(BaseModel):
    """Domain context for problem metadata."""
    problem_name: str = Field(default="Unknown Problem", description="Name of the coding problem")
    topic: str = Field(default="Arrays", description="Primary topic e.g. Arrays, HashMaps, Graphs")
    subtopic: str = Field(default="Fundamentals", description="Subtopic e.g. Two Pointers, Collisions")
    difficulty: str = Field(default="Easy", description="Problem difficulty (Easy, Medium, Hard)")
    language: str = Field(default="python", description="Programming language used by student")


class StudentContext(BaseModel):
    """Domain context for student code and state."""
    student_code: str = Field(default="", description="Current code written by the student")


class PredictionContext(BaseModel):
    """Domain context for ML model predictions."""
    solver_prediction: str = Field(default="Likely to Solve", description="Solver model prediction string")
    solver_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Solver model confidence score")
    hint_prediction: str = Field(default="No Hint", description="Hint model prediction string")
    hint_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Hint model confidence score")
    normalized_hint_level: HintLevelEnum = Field(default=HintLevelEnum.NO_HINT, description="Normalized hint enum")


class SessionContext(BaseModel):
    """Domain context for student telemetry session metrics."""
    struggle_score: float = Field(default=0.0, ge=0.0, description="Calculated struggle score")
    compile_attempts: int = Field(default=0, ge=0, description="Total compile attempts")
    compile_errors: int = Field(default=0, ge=0, description="Compilation failure count")
    runtime_errors: int = Field(default=0, ge=0, description="Runtime execution failure count")
    pause_duration: float = Field(default=0.0, ge=0.0, description="Total duration of editing pauses in seconds")
    chars_typed: int = Field(default=0, ge=0, description="Characters typed")
    chars_deleted: int = Field(default=0, ge=0, description="Characters deleted")
    raw_telemetry: Dict[str, Any] = Field(default_factory=dict, description="Full raw telemetry snapshot")


class RecommendationContext(BaseModel):
    """Aggregated unified context containing domain-specific context objects."""
    problem: ProblemContext = Field(default_factory=ProblemContext)
    student: StudentContext = Field(default_factory=StudentContext)
    prediction: PredictionContext = Field(default_factory=PredictionContext)
    session: SessionContext = Field(default_factory=SessionContext)
    is_regeneration: bool = Field(default=False, description="Whether this is a regenerated hint")

# --- Policy & Teaching Strategy Schemas ---

class TeachingStrategy(BaseModel):
    """Educational strategy policy parameters governing prompt building and output bounds."""
    hint_level: HintLevelEnum
    allow_code: bool = False
    allow_pseudocode: bool = False
    allow_algorithm_reveal: bool = False
    require_reflection_question: bool = True
    tone: str = "encouraging_and_scaffolded"
    max_hint_depth: str = "concept_only"


# --- Prompt Builder Output Schema ---

class StructuredEducationalPrompt(BaseModel):
    """Structured educational prompt object prepared for Template or LLM Generators."""
    system_instruction: str
    problem_context_summary: str
    concept_knowledge_summary: str
    teaching_strategy: TeachingStrategy
    reflection_prompt_directive: str
    formatting_requirements: Dict[str, Any]


# --- API Request & Response Schemas ---

class RecommendationRequest(BaseModel):
    """API payload for /recommend endpoint, accepting direct context or snapshot telemetry."""
    problem_name: Optional[str] = "Unknown Problem"
    difficulty: Optional[str] = "Easy"
    topic: Optional[str] = "Arrays"
    subtopic: Optional[str] = "Fundamentals"
    language: Optional[str] = "python"
    student_code: Optional[str] = ""
    solver_prediction: Optional[str] = None
    solver_confidence: Optional[float] = None
    hint_prediction: Optional[str] = None
    hint_confidence: Optional[float] = None
    snapshot: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Student session telemetry snapshot")
    is_regeneration: Optional[bool] = Field(default=False, description="Flag if this is a request to regenerate the hint")


class RecommendationResponse(BaseModel):
    """Structured JSON response returned to the VS Code Extension."""
    title: str = Field(description="Display title of the hint e.g. 'Concept Hint'")
    level: str = Field(description="Hint level string key e.g. 'concept', 'guided'")
    message: str = Field(description="Primary educational message explaining concept/step")
    next_step: str = Field(description="Actionable next step for the student")
    reflection_question: str = Field(description="Metacognitive question prompting student reflection")
    encouragement: str = Field(description="Supportive encouragement statement")
    confidence: float = Field(description="Confidence score associated with the recommendation")
    code: Optional[str] = Field(default=None, description="Solution code snippet (only present for full_solution)")
    complexity: Optional[Dict[str, str]] = Field(default=None, description="Time & space complexity (only for full_solution)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")
    status: str = Field(default="success")

class FeedbackRequest(BaseModel):
    """API payload for /feedback endpoint."""
    session_id: str
    rating: str
