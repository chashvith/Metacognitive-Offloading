"""Hint Model Prediction Module."""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import xgboost as xgb

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


def predict_hint_with_preloaded(
    snapshot: Dict[str, Any],
    model: xgb.XGBClassifier,
    feature_columns: List[str],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generates hint level prediction using pre-loaded model memory."""
    try:
        is_valid, validation_error = validate_snapshot(snapshot)
        if not is_valid:
            return {
                "status": "error",
                "message": "Invalid snapshot.",
                "errors": [validation_error] if validation_error else ["Unknown validation error."]
            }

        if model is None or not feature_columns:
            return {
                "status": "error",
                "message": "Hint Prediction Model is not available.",
                "reason": "Model binary or feature columns file not loaded."
            }

        X_aligned = align_features(snapshot, feature_columns)
        predicted_level = int(model.predict(X_aligned)[0])
        predicted_name = HINT_CLASS_MAPPING.get(predicted_level, "Concept Hint")

        try:
            proba_arr = model.predict_proba(X_aligned)[0]
        except Exception:
            proba_arr = [0.0] * 5
            if predicted_level < len(proba_arr):
                proba_arr[predicted_level] = 1.0

        highest_prob = float(round(max(proba_arr) if len(proba_arr) > 0 else 0.0, 4))
        confidence = compute_confidence(highest_prob)
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return {
            "status": "success",
            "prediction": predicted_name,
            "confidence": confidence,
            "hint_level": predicted_level,
            "highest_probability": highest_prob,
            "timestamp": timestamp_str
        }

    except Exception as exc:
        logger.error("Error during hint prediction: %s", exc, exc_info=True)
        return {
            "status": "error",
            "message": "Hint prediction failed.",
            "details": str(exc)
        }


def predict_hint(
    snapshot: Dict[str, Any],
    models_dir: Optional[Path | str] = None
) -> Dict[str, Any]:
    """Fallback function loading hint model from disk."""
    base_dir = Path(models_dir) if models_dir else Path("models")
    model, feature_columns, metadata, load_error = load_model_artifacts(
        model_name="hint_model",
        models_dir=base_dir,
        cols_filename="hint_feature_columns.json",
        meta_filename="hint_model_metadata.json"
    )
    if load_error or model is None or not feature_columns:
        return {
            "status": "error",
            "message": load_error or "Hint model not loaded."
        }
    return predict_hint_with_preloaded(
        snapshot=snapshot,
        model=model,
        feature_columns=feature_columns,
        metadata=metadata
    )
