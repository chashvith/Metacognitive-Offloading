"""Generic Prediction Engine Module.

Provides a unified, reusable inference engine for machine learning models.
Orchestrates snapshot validation, model loading, feature alignment, prediction,
confidence evaluation, and structured JSON response formatting.
"""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from utils.confidence import compute_confidence
from utils.feature_aligner import align_features
from utils.model_loader import load_model_artifacts
from utils.validator import validate_snapshot

logger = logging.getLogger(__name__)


class PredictionEngine:
    """Reusable generic prediction engine for machine learning inference."""

    def __init__(self, models_dir: Path | str = "models"):
        """Initializes the prediction engine.

        Args:
            models_dir: Directory containing model binaries and metadata files.
        """
        self.models_dir = Path(models_dir)

    def predict(
        self,
        snapshot: Dict[str, Any],
        model_name: str = "solver_model",
        target_positive_label: str = "Solved",
        target_negative_label: str = "Not Solved"
    ) -> Dict[str, Any]:
        """Runs model inference on a single student snapshot dictionary.

        Args:
            snapshot: Student coding session snapshot dictionary.
            model_name: Name of the model binary (without .json extension).
            target_positive_label: Label string for positive prediction (1).
            target_negative_label: Label string for negative prediction (0).

        Returns:
            Structured response dictionary containing status, prediction, probability, confidence, and timestamp.
        """
        try:
            # Step 1: Input Validation
            is_valid, validation_error = validate_snapshot(snapshot)
            if not is_valid:
                return {
                    "status": "error",
                    "message": f"Invalid snapshot. {validation_error}"
                }

            # Step 2: Model Artifact Loading
            model, feature_columns, metadata, load_error = load_model_artifacts(
                model_name=model_name,
                models_dir=self.models_dir
            )

            if load_error or model is None or not feature_columns:
                return {
                    "status": "error",
                    "message": load_error or "Model or feature metadata not found."
                }

            # Step 3: Feature Alignment
            X_aligned = align_features(snapshot, feature_columns)

            # Step 4: Prediction Execution
            pred_class_raw = model.predict(X_aligned)[0]
            pred_class = int(pred_class_raw)

            try:
                proba_arr = model.predict_proba(X_aligned)[0]
                solve_prob = float(proba_arr[1]) if len(proba_arr) > 1 else float(proba_arr[0])
            except Exception as exc:
                logger.warning("predict_proba failed, fallback to binary prediction: %s", exc)
                solve_prob = 1.0 if pred_class == 1 else 0.0

            solve_prob = float(round(max(0.0, min(1.0, solve_prob)), 4))

            # Step 5: Confidence Calculation
            confidence_level = compute_confidence(solve_prob)

            # Step 6: Response Formatting
            prediction_label = target_positive_label if pred_class == 1 else target_negative_label
            model_version = str(metadata.get("version", "1.0")) if metadata else "1.0"
            timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            response = {
                "status": "success",
                "prediction": prediction_label,
                "solve_probability": solve_prob,
                "confidence": confidence_level,
                "model_version": model_version,
                "timestamp": timestamp_str
            }
            logger.info("Prediction completed successfully for model '%s': %s", model_name, response["prediction"])
            return response

        except Exception as exc:
            logger.error("Unhandled exception during prediction execution: %s", exc, exc_info=True)
            return {
                "status": "error",
                "message": "An internal error occurred during prediction."
            }
