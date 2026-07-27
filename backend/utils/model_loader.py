"""Model Loader Module for Backend."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import xgboost as xgb

logger = logging.getLogger(__name__)


def load_model_artifacts(
    model_name: str = "solver_model",
    models_dir: Path | str = "models",
    cols_filename: Optional[str] = None,
    meta_filename: Optional[str] = None
) -> Tuple[Optional[xgb.XGBClassifier], Optional[List[str]], Optional[Dict[str, Any]], Optional[str]]:
    """Loads XGBoost model binary, feature columns, and metadata safely from disk."""
    base_dir = Path(models_dir)
    clean_name = model_name.replace(".json", "")
    model_file_name = f"{clean_name}.json"
    model_path = base_dir / model_file_name

    # Fallback to root models folder if not found in local backend/models
    if not model_path.exists():
        fallback_dir = Path(__file__).resolve().parent.parent.parent / "models"
        if (fallback_dir / model_file_name).exists():
            base_dir = fallback_dir
            model_path = base_dir / model_file_name

    if cols_filename:
        cols_path = base_dir / cols_filename
    else:
        model_cols = base_dir / f"{clean_name}_feature_columns.json"
        cols_path = model_cols if model_cols.exists() else (base_dir / "feature_columns.json")

    if meta_filename:
        meta_path = base_dir / meta_filename
    else:
        model_meta = base_dir / f"{clean_name}_metadata.json"
        meta_path = model_meta if model_meta.exists() else (base_dir / "model_metadata.json")

    if not model_path.exists():
        msg = f"Model file '{model_path.name}' not found at '{model_path.resolve()}'."
        logger.warning(msg)
        return None, None, None, msg

    if not cols_path.exists():
        msg = f"Feature metadata file '{cols_path.name}' not found at '{cols_path.resolve()}'."
        logger.warning(msg)
        return None, None, None, msg

    try:
        model = xgb.XGBClassifier()
        model.load_model(str(model_path))
    except Exception as exc:
        msg = f"Failed to load XGBoost model from '{model_path}': {exc}"
        logger.error(msg)
        return None, None, None, msg

    try:
        with open(cols_path, "r", encoding="utf-8") as f:
            cols_data = json.load(f)

        if isinstance(cols_data, dict) and "feature_columns" in cols_data:
            feature_columns = cols_data["feature_columns"]
        elif isinstance(cols_data, list):
            feature_columns = cols_data
        else:
            msg = f"Invalid format in '{cols_path.name}'."
            logger.error(msg)
            return None, None, None, msg
    except Exception as exc:
        msg = f"Failed to load feature columns metadata from '{cols_path}': {exc}"
        logger.error(msg)
        return None, None, None, msg

    metadata: Dict[str, Any] = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                all_meta = json.load(f)
            if isinstance(all_meta, dict):
                metadata = all_meta.get(clean_name, all_meta)
        except Exception as exc:
            logger.warning("Could not read model metadata from '%s': %s", meta_path, exc)

    logger.info("Successfully loaded model '%s' with %d feature columns.", model_name, len(feature_columns))
    return model, feature_columns, metadata, None
