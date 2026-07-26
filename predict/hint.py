"""Hint Prediction Specific Inference Module.

Provides solver/hint prediction functionality wrapping the core model loading,
feature alignment, metadata validation, and confidence assessment utilities.
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

HINT_CLASS_MAPPING: Dict[int, str] = {
    0: "No Hint",
    1: "Concept Hint",
    2: "Guided Hint",
    3: "Pseudocode",
    4: "Full Solution"
}


def predict_hint(
    snapshot: Dict[str, Any],
    models_dir: Optional[Path | str] = None
) -> Dict[str, Any]:
    """Generates a hint level prediction for a single student snapshot dictionary.

    Args:
        snapshot: Student coding session snapshot dictionary.
        models_dir: Optional directory path to model artifacts.

    Returns:
        Structured response dictionary with prediction results or error status.
    """
    base_dir = Path(models_dir) if models_dir else Path("models")

    try:
        # Step 1: Model Artifact Loading & Metadata Validation
        model, feature_columns, metadata, load_error = load_model_artifacts(
            model_name="hint_model",
            models_dir=base_dir,
            cols_filename="hint_feature_columns.json",
            meta_filename="hint_model_metadata.json"
        )

        if load_error or metadata is None:
            return {
                "status": "error",
                "message": "Hint Prediction Model is not available.",
                "reason": load_error or "Metadata missing.",
                "model_status": "unavailable",
                "model_version": "1.0"
            }

        # Check metadata status
        model_status = metadata.get("status", "unknown")
        if model_status != "ready":
            failure_reason = metadata.get("failure_reason", "Model status is not ready.")
            logger.warning("Hint Prediction Model is not ready (status: '%s', reason: '%s').", model_status, failure_reason)
            return {
                "status": "error",
                "message": "Hint Prediction Model is not available.",
                "reason": failure_reason,
                "model_status": model_status,
                "model_version": str(metadata.get("version", "1.0"))
            }

        if model is None or not feature_columns:
            return {
                "status": "error",
                "message": "Hint Prediction Model is not available.",
                "reason": "Model binary or feature columns file not loaded.",
                "model_status": "unavailable",
                "model_version": str(metadata.get("version", "1.0"))
            }

        # Step 2: Snapshot Validation
        is_valid, validation_error = validate_snapshot(snapshot)
        if not is_valid:
            return {
                "status": "error",
                "message": "Invalid snapshot.",
                "errors": [validation_error] if validation_error else ["Unknown validation error."]
            }

        # Step 3: Feature Alignment
        X_aligned = align_features(snapshot, feature_columns)

        # Step 4: Prediction & Probabilities
        predicted_level = int(model.predict(X_aligned)[0])
        predicted_name = HINT_CLASS_MAPPING.get(predicted_level, "Unknown Hint")

        try:
            proba_arr = model.predict_proba(X_aligned)[0]
        except Exception as exc:
            logger.warning("predict_proba failed, fallback to 1.0 probability for predicted class: %s", exc)
            proba_arr = [0.0] * 5
            if predicted_level < len(proba_arr):
                proba_arr[predicted_level] = 1.0

        probabilities: Dict[str, float] = {}
        for level, name in HINT_CLASS_MAPPING.items():
            if level < len(proba_arr):
                probabilities[name] = float(round(proba_arr[level], 4))
            else:
                probabilities[name] = 0.0

        highest_prob = float(round(max(proba_arr) if len(proba_arr) > 0 else 0.0, 4))
        confidence = compute_confidence(highest_prob)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        model_version = str(metadata.get("version", "1.0"))

        response = {
            "status": "success",
            "prediction": predicted_name,
            "predicted_hint": predicted_name,
            "hint_level": predicted_level,
            "confidence": confidence,
            "highest_probability": highest_prob,
            "solve_probability": highest_prob,
            "probabilities": probabilities,
            "model_name": str(metadata.get("model_name", "Hint Prediction Model")),
            "model_version": model_version,
            "prediction_timestamp": timestamp_str,
            "timestamp": timestamp_str
        }

        logger.info("Hint prediction completed: %s (level %d, confidence %s).", predicted_name, predicted_level, confidence)
        return response

    except Exception as exc:
        logger.error("Unhandled runtime exception during hint prediction: %s", exc, exc_info=True)
        return {
            "status": "error",
            "message": "Prediction failed.",
            "details": str(exc)
        }
