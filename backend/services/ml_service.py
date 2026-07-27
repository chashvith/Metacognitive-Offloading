"""ML Service for managing and serving pre-loaded machine learning models."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import xgboost as xgb

from predict.engine import PredictionEngine
from predict.hint import predict_hint_with_preloaded, predict_hint
from utils.model_loader import load_model_artifacts

logger = logging.getLogger(__name__)


class MLService:
    """Singleton service for holding pre-loaded models and executing fast inference."""

    def __init__(self, models_dir: Optional[Path | str] = None):
        if models_dir is None:
            # Check local backend/models or fallback to parent models
            local_models = Path(__file__).resolve().parent.parent / "models"
            parent_models = Path(__file__).resolve().parent.parent.parent / "models"
            self.models_dir = local_models if local_models.exists() else parent_models
        else:
            self.models_dir = Path(models_dir)

        self.solver_model: Optional[xgb.XGBClassifier] = None
        self.solver_cols: Optional[list] = None
        self.solver_meta: Optional[dict] = None

        self.hint_model: Optional[xgb.XGBClassifier] = None
        self.hint_cols: Optional[list] = None
        self.hint_meta: Optional[dict] = None

        self.engine: Optional[PredictionEngine] = None
        self.is_loaded: bool = False

    def load(self) -> None:
        """Pre-loads solver_model and hint_model into memory at FastAPI startup."""
        logger.info("Initializing MLService: Loading models into memory from '%s'...", self.models_dir.resolve())
        
        # Load Solver Model
        s_model, s_cols, s_meta, s_err = load_model_artifacts(
            model_name="solver_model",
            models_dir=self.models_dir
        )
        if s_err:
            logger.warning("Solver model loading warning: %s", s_err)
        else:
            self.solver_model = s_model
            self.solver_cols = s_cols
            self.solver_meta = s_meta

        # Load Hint Model
        h_model, h_cols, h_meta, h_err = load_model_artifacts(
            model_name="hint_model",
            models_dir=self.models_dir,
            cols_filename="hint_feature_columns.json",
            meta_filename="hint_model_metadata.json"
        )
        if h_err:
            logger.warning("Hint model loading warning: %s", h_err)
        else:
            self.hint_model = h_model
            self.hint_cols = h_cols
            self.hint_meta = h_meta

        self.engine = PredictionEngine(models_dir=self.models_dir)
        self.is_loaded = True
        logger.info("MLService models loaded successfully into memory!")

    def predict_solver(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Runs solver model inference on a snapshot."""
        if not self.is_loaded or self.solver_model is None or self.solver_cols is None:
            if not self.engine:
                self.engine = PredictionEngine(models_dir=self.models_dir)
            return self.engine.predict(
                snapshot=snapshot,
                model_name="solver_model",
                target_positive_label="Likely to Solve",
                target_negative_label="Unlikely to Solve"
            )

        return self.engine.predict_with_preloaded(
            snapshot=snapshot,
            model=self.solver_model,
            feature_columns=self.solver_cols,
            metadata=self.solver_meta,
            model_name="solver_model",
            target_positive_label="Likely to Solve",
            target_negative_label="Unlikely to Solve"
        )

    def predict_hint(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Runs hint model inference on a snapshot."""
        if not self.is_loaded or self.hint_model is None or self.hint_cols is None:
            return predict_hint(snapshot, models_dir=self.models_dir)

        return predict_hint_with_preloaded(
            snapshot=snapshot,
            model=self.hint_model,
            feature_columns=self.hint_cols,
            metadata=self.hint_meta
        )

    def predict_full(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Runs both solver and hint models and aggregates output."""
        solver_res = self.predict_solver(snapshot)
        hint_res = self.predict_hint(snapshot)
        return {
            "status": "success",
            "solver": solver_res,
            "hint": hint_res
        }


# Global singleton instance
ml_service = MLService()
