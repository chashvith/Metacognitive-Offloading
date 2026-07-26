"""Solver Model Specific Inference Module.

Provides a dedicated wrapper for student problem-solving predictions,
utilizing the generic PredictionEngine.
"""

import logging
from typing import Any, Dict, Optional
from pathlib import Path

from predict.engine import PredictionEngine

logger = logging.getLogger(__name__)


def predict_solver(
    snapshot: Dict[str, Any],
    models_dir: Optional[Path | str] = None
) -> Dict[str, Any]:
    """Generates problem-solving prediction for a student session snapshot.

    Args:
        snapshot: Input student session snapshot dictionary.
        models_dir: Optional directory override for model artifacts.

    Returns:
        Structured response dictionary containing prediction results or error status.
    """
    engine = PredictionEngine(models_dir=models_dir) if models_dir else PredictionEngine()
    return engine.predict(
        snapshot=snapshot,
        model_name="solver_model",
        target_positive_label="Solved",
        target_negative_label="Not Solved"
    )
