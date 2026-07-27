"""Snapshot and API Request/Response Schemas."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class SnapshotSchema(BaseModel):
    """Pydantic model representing a student coding session snapshot."""
    difficulty: Optional[str] = Field(default="Easy", description="Problem difficulty (Easy, Medium, Hard)")
    language: Optional[str] = Field(default="python", description="Programming language")
    topic: Optional[str] = Field(default="Arrays", description="Problem topic")
    subtopic: Optional[str] = Field(default="General", description="Problem subtopic")
    elapsed_time: float = Field(default=0.0, ge=0.0, description="Time spent in seconds")
    progress_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Completion progress (0.0 - 1.0)")
    current_struggle_score: float = Field(default=0.0, ge=0.0, description="Calculated struggle score")
    chars_typed: int = Field(default=0, ge=0, description="Total characters typed")
    chars_deleted: int = Field(default=0, ge=0, description="Total characters deleted")
    pause_count: int = Field(default=0, ge=0, description="Number of editing pauses")
    pause_duration: float = Field(default=0.0, ge=0.0, description="Total duration of pauses in seconds")
    compile_attempts: int = Field(default=0, ge=0, description="Total compilation attempts")
    compile_errors: int = Field(default=0, ge=0, description="Compilation failure count")
    successful_runs: int = Field(default=0, ge=0, description="Successful code execution count")
    runtime_errors: int = Field(default=0, ge=0, description="Runtime error count")
    deletion_ratio: float = Field(default=0.0, ge=0.0, description="Ratio of deleted characters to typed characters")
    typing_speed: float = Field(default=0.0, ge=0.0, description="Characters typed per minute")
    compile_failure_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of compile errors to attempts")
    average_pause_duration: float = Field(default=0.0, ge=0.0, description="Average duration per pause")

    class Config:
        json_schema_extra = {
            "example": {
                "difficulty": "Easy",
                "language": "java",
                "topic": "Arrays",
                "subtopic": "Two Pointers",
                "elapsed_time": 92.0,
                "progress_ratio": 0.56,
                "current_struggle_score": 0.125,
                "chars_typed": 251,
                "chars_deleted": 19,
                "pause_count": 1,
                "pause_duration": 6.705,
                "compile_attempts": 1,
                "compile_errors": 1,
                "successful_runs": 0,
                "runtime_errors": 0,
                "deletion_ratio": 0.075,
                "typing_speed": 163.7,
                "compile_failure_rate": 1.0,
                "average_pause_duration": 6.705
            }
        }


class PredictRequest(BaseModel):
    """Request payload containing a student snapshot."""
    snapshot: Dict[str, Any]


class PredictResponse(BaseModel):
    """Prediction API output response format."""
    prediction: str
    confidence: float
    status: Optional[str] = "success"
    solve_probability: Optional[float] = None
    timestamp: Optional[str] = None


class FullPredictResponse(BaseModel):
    """Full prediction response combining Solver and Hint models."""
    status: str = "success"
    solver: Dict[str, Any]
    hint: Dict[str, Any]


class RecommendationRequest(BaseModel):
    """Request schema for recommendation engine."""
    snapshot: Dict[str, Any]


class RecommendationResponse(BaseModel):
    """Output schema from recommendation engine."""
    status: str = "success"
    struggle_level: str
    recommended_action: str
    intervention_type: str
    details: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check endpoint response schema."""
    status: str = "running"
