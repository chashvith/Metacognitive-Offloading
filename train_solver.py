"""XGBoost Model Training Pipeline for Student Solver Prediction.

This module imports preprocessed training data from preprocessing.py, validates
dataset sufficiency, builds and trains an XGBoost binary classifier, evaluates
performance, extracts ranked feature importances, and persists the trained model
and feature metadata to disk.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def load_training_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Loads preprocessed training and testing datasets from preprocessing module.

    Returns:
        Tuple of (X_train, X_test, y_train, y_test).

    Raises:
        ImportError: If preprocessing module cannot be imported.
        Exception: If data loading or preprocessing fails.
    """
    try:
        from preprocessing import preprocess_data
        return preprocess_data()
    except ImportError as exc:
        logger.error("Failed to import preprocessing module: %s", exc)
        raise
    except Exception as exc:
        logger.error("Error loading preprocessed data: %s", exc)
        raise


def validate_training_data(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series
) -> bool:
    """Validates training and testing data prior to model training.

    Args:
        X_train: Feature matrix for training.
        X_test: Feature matrix for testing.
        y_train: Target labels for training.
        y_test: Target labels for testing.

    Returns:
        True if datasets are valid and sufficient for training, False otherwise.
    """
    if X_train is None or X_train.empty:
        logger.warning("Validation failed: Training feature matrix (X_train) is empty.")
        return False

    if X_test is None or X_test.empty:
        logger.warning("Validation failed: Testing feature matrix (X_test) is empty.")
        return False

    if list(X_train.columns) != list(X_test.columns):
        logger.warning("Validation failed: Feature columns between X_train and X_test do not match.")
        return False

    unique_train_classes = np.unique(y_train)
    if len(unique_train_classes) < 2:
        logger.warning(
            "Validation failed: Training labels contain only %d class (%s). Minimum 2 classes required.",
            len(unique_train_classes), list(unique_train_classes)
        )
        return False

    return True


def build_model() -> xgb.XGBClassifier:
    """Instantiates XGBoost Classifier with baseline hyperparameters.

    Returns:
        Baseline XGBClassifier model.
    """
    model = xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    return model


def train_model(
    model: xgb.XGBClassifier,
    X_train: pd.DataFrame,
    y_train: pd.Series
) -> xgb.XGBClassifier:
    """Fits XGBoost classifier on training dataset.

    Args:
        model: XGBClassifier baseline model.
        X_train: Training features.
        y_train: Training target labels.

    Returns:
        Fitted XGBClassifier model.
    """
    model.fit(X_train, y_train)
    logger.info("Model training completed successfully.")
    return model


def evaluate_model(
    model: xgb.XGBClassifier,
    X_test: pd.DataFrame,
    y_test: pd.Series
) -> Dict[str, Any]:
    """Evaluates fitted model performance on test set.

    Args:
        model: Fitted XGBClassifier model.
        X_test: Testing features.
        y_test: Testing target labels.

    Returns:
        Dictionary containing evaluation metrics and prediction outputs.
    """
    y_pred = model.predict(X_test)

    try:
        y_prob = model.predict_proba(X_test)[:, 1]
    except Exception:
        y_prob = None

    accuracy = float(accuracy_score(y_test, y_pred))
    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))

    roc_auc: Optional[float] = None
    if y_prob is not None and len(np.unique(y_test)) >= 2:
        try:
            roc_auc = float(roc_auc_score(y_test, y_prob))
        except ValueError as exc:
            logger.warning("ROC-AUC score could not be calculated: %s", exc)
    else:
        logger.warning("ROC-AUC score calculation skipped: test set contains only one class.")

    report = classification_report(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
        "report": report,
        "confusion_matrix": cm,
        "y_pred": y_pred,
        "y_prob": y_prob
    }


def display_feature_importance(
    model: xgb.XGBClassifier,
    feature_names: List[str]
) -> pd.DataFrame:
    """Extracts and displays feature importance ranked from highest to lowest.

    Args:
        model: Trained XGBClassifier.
        feature_names: List of feature column names.

    Returns:
        DataFrame containing sorted feature importances.
    """
    importances = model.feature_importances_
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": importances
    }).sort_values(by="importance", ascending=False).reset_index(drop=True)

    print("\n--- Top Important Features ---")
    for idx, row in importance_df.iterrows():
        print(f"{idx + 1:2d}. {row['feature']:<30} : {row['importance']:.6f}")

    return importance_df


def save_model(
    model: xgb.XGBClassifier,
    output_dir: Path | str = "models",
    model_filename: str = "solver_model.json",
    feature_names: Optional[List[str]] = None
) -> Tuple[Path, Path]:
    """Saves trained XGBoost model and feature column metadata to disk.

    Args:
        model: Trained XGBClassifier.
        output_dir: Directory where model artifacts are saved.
        model_filename: Model file name.
        feature_names: List of feature column names.

    Returns:
        Tuple of (model_path, metadata_path).
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir / model_filename
    model.save_model(str(model_path))
    logger.info("Saved trained model to '%s'.", model_path)

    metadata_path = out_dir / "feature_columns.json"
    if feature_names is not None:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump({"feature_columns": list(feature_names)}, f, indent=2)
        logger.info("Saved feature metadata to '%s'.", metadata_path)

    return model_path, metadata_path


def main() -> None:
    """Main execution function for model training pipeline."""
    try:
        X_train, X_test, y_train, y_test = load_training_data()
    except Exception as exc:
        print("\n----------------------------------------")
        print("Solver Model Training Summary")
        print("----------------------------------------")
        print(f"Error loading training data: {exc}")
        print("Failed to initialize preprocessing pipeline.")
        print("----------------------------------------\n")
        return

    is_valid = validate_training_data(X_train, X_test, y_train, y_test)

    if not is_valid:
        print("\n----------------------------------------")
        print("Solver Model Training Summary")
        print("----------------------------------------")
        print("Insufficient data to train the model.")
        print("Collect more student sessions before training.")
        print("----------------------------------------\n")
        return

    try:
        model = build_model()
        model = train_model(model, X_train, y_train)

        eval_metrics = evaluate_model(model, X_test, y_test)
        feature_importance_df = display_feature_importance(model, list(X_train.columns))
        model_path, meta_path = save_model(model, output_dir="models", feature_names=list(X_train.columns))

        print("\n----------------------------------------")
        print("Solver Model Training Summary")
        print("----------------------------------------")
        print(f"Training Samples   : {len(X_train)}")
        print(f"Testing Samples    : {len(X_test)}")
        print(f"Number of Features : {X_train.shape[1]}")
        print(f"Model              : {model.__class__.__name__}")
        print("Training Completed Successfully")
        print(f"Accuracy           : {eval_metrics['accuracy']:.4f}")
        print(f"Precision          : {eval_metrics['precision']:.4f}")
        print(f"Recall             : {eval_metrics['recall']:.4f}")
        print(f"F1 Score           : {eval_metrics['f1']:.4f}")
        roc_str = f"{eval_metrics['roc_auc']:.4f}" if eval_metrics['roc_auc'] is not None else "N/A (single class in test set)"
        print(f"ROC-AUC            : {roc_str}")
        print(f"Model Saved To     : {model_path.resolve()}")
        print(f"Metadata Saved To  : {meta_path.resolve()}")
        print("----------------------------------------\n")

    except Exception as exc:
        logger.error("Model training failed: %s", exc, exc_info=True)
        print("\n----------------------------------------")
        print("Solver Model Training Summary")
        print("----------------------------------------")
        print(f"Model Training Failed: {exc}")
        print("----------------------------------------\n")


if __name__ == "__main__":
    main()
