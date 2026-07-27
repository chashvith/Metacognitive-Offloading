"""Solver Model Prediction Module."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .engine import PredictionEngine

logger = logging.getLogger(__name__)


def predict_solver(
    snapshot: Dict[str, Any],
    models_dir: Optional[Path | str] = None
) -> Dict[str, Any]:
    """Generates problem-solving prediction for a student session snapshot."""
    engine = PredictionEngine(models_dir=models_dir) if models_dir else PredictionEngine()
    return engine.predict(
        snapshot=snapshot,
        model_name="solver_model",
        target_positive_label="Likely to Solve",
        target_negative_label="Unlikely to Solve"
    )
