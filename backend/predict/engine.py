"""Prediction Engine Module for Backend with preloaded model support."""

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


class PredictionEngine:
    """Generic prediction engine with preloaded model memory support."""

    def __init__(self, models_dir: Path | str = "models"):
        self.models_dir = Path(models_dir)

    def predict_with_preloaded(
        self,
        snapshot: Dict[str, Any],
        model: xgb.XGBClassifier,
        feature_columns: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        model_name: str = "solver_model",
        target_positive_label: str = "Likely to Solve",
        target_negative_label: str = "Unlikely to Solve"
    ) -> Dict[str, Any]:
        """Runs model inference using an ALREADY PRELOADED model instance."""
        try:
            is_valid, validation_error = validate_snapshot(snapshot)
            if not is_valid:
                return {
                    "status": "error",
                    "message": f"Invalid snapshot. {validation_error}"
                }

            if model is None or not feature_columns:
                return {
                    "status": "error",
                    "message": f"Model or feature metadata for '{model_name}' is not loaded."
                }

            X_aligned = align_features(snapshot, feature_columns)
            pred_class_raw = model.predict(X_aligned)[0]
            pred_class = int(pred_class_raw)

            try:
                proba_arr = model.predict_proba(X_aligned)[0]
                solve_prob = float(proba_arr[1]) if len(proba_arr) > 1 else float(proba_arr[0])
            except Exception as exc:
                logger.warning("predict_proba failed: %s", exc)
                solve_prob = 1.0 if pred_class == 1 else 0.0

            solve_prob = float(round(max(0.0, min(1.0, solve_prob)), 4))
            confidence_level = compute_confidence(solve_prob)
            prediction_label = target_positive_label if pred_class == 1 else target_negative_label
            model_version = str(metadata.get("version", "1.0")) if metadata else "1.0"
            timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            return {
                "status": "success",
                "prediction": prediction_label,
                "confidence": confidence_level,
                "solve_probability": solve_prob,
                "model_version": model_version,
                "timestamp": timestamp_str
            }

        except Exception as exc:
            logger.error("Error during prediction execution: %s", exc, exc_info=True)
            return {
                "status": "error",
                "message": "An internal error occurred during prediction."
            }

    def predict(
        self,
        snapshot: Dict[str, Any],
        model_name: str = "solver_model",
        target_positive_label: str = "Likely to Solve",
        target_negative_label: str = "Unlikely to Solve"
    ) -> Dict[str, Any]:
        """Fallback prediction method loading model from disk if not pre-loaded."""
        model, feature_columns, metadata, load_error = load_model_artifacts(
            model_name=model_name,
            models_dir=self.models_dir
        )
        if load_error or model is None or not feature_columns:
            return {
                "status": "error",
                "message": load_error or "Model or feature metadata not found."
            }
        return self.predict_with_preloaded(
            snapshot=snapshot,
            model=model,
            feature_columns=feature_columns,
            metadata=metadata,
            model_name=model_name,
            target_positive_label=target_positive_label,
            target_negative_label=target_negative_label
        )
