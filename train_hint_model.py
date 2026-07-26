"""XGBoost Multiclass Training Pipeline for Hint Prediction Model.

Imports hint training dataset with heuristic labels, validates dataset sufficiency,
preprocesses features, trains an XGBoost multiclass classifier (5 classes),
evaluates performance metrics, displays ranked feature importances, and saves model binary,
feature order, and training metadata to disk.
"""

from datetime import datetime, timezone
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

from preprocessing import encode_features, handle_missing_values, split_by_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

IGNORE_COLUMNS = [
    "session_id",
    "problem_name",
    "snapshot_time",
    "hint_name",
    "label_reason",
    "hint_need_score",
    "hint_label",
    "solved"
]

NUM_CLASSES = 5


def load_dataset(file_path: Path | str = "dataset/processed/hint_training_dataset.csv") -> pd.DataFrame:
    """Loads the hint training dataset CSV into a pandas DataFrame.

    Args:
        file_path: Target dataset CSV path.

    Returns:
        Loaded DataFrame.

    Raises:
        FileNotFoundError: If input file is missing.
        IOError: If reading CSV fails.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error("Hint dataset file not found at '%s'.", path.resolve())
        raise FileNotFoundError(f"Hint dataset file not found at '{path.resolve()}'.")

    try:
        df = pd.read_csv(path)
        logger.info("Loaded hint dataset (%d rows) from '%s'.", len(df), path)
        return df
    except Exception as exc:
        logger.error("Failed to read hint dataset CSV: %s", exc)
        raise IOError(f"Failed to read hint dataset: {exc}") from exc


def validate_dataset(df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
    """Validates dataset structure, column presence, and class diversity.

    Args:
        df: Input pandas DataFrame.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if df is None or df.empty:
        msg = "Dataset is empty."
        logger.warning(msg)
        return False, msg

    if "hint_label" not in df.columns:
        msg = "Target column 'hint_label' is missing."
        logger.warning(msg)
        return False, msg

    unique_classes = df["hint_label"].dropna().unique()
    if len(unique_classes) < 2:
        msg = f"Dataset contains only {len(unique_classes)} class in 'hint_label' ({list(unique_classes)}). Minimum 2 classes required."
        logger.warning(msg)
        return False, msg

    return True, None


def prepare_training_data(
    df: pd.DataFrame,
    test_size: float = 0.20,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Preprocesses snapshot dataset and performs group-aware train/test split by session_id.

    Args:
        df: Input snapshot DataFrame.
        test_size: Ratio of sessions reserved for test set.
        random_state: Seed for random state.

    Returns:
        Tuple of (X_train, X_test, y_train, y_test).
    """
    imputed_df = handle_missing_values(df)
    encoded_df = encode_features(imputed_df)

    train_df, test_df = split_by_session(
        encoded_df,
        session_col="session_id",
        test_size=test_size,
        random_state=random_state
    )

    y_train = train_df["hint_label"].astype(int)
    y_test = test_df["hint_label"].astype(int)

    feature_cols = [col for col in train_df.columns if col not in IGNORE_COLUMNS]

    X_train = train_df[feature_cols].copy()
    X_test = test_df[feature_cols].copy()

    logger.info("Features prepared. X_train shape: %s, X_test shape: %s.", X_train.shape, X_test.shape)
    return X_train, X_test, y_train, y_test


def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> xgb.XGBClassifier:
    """Trains baseline XGBoost multiclass classifier (5 classes).

    Args:
        X_train: Feature matrix.
        y_train: Multiclass target labels.

    Returns:
        Fitted XGBClassifier model.
    """
    model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=NUM_CLASSES,
        eval_metric="mlogloss",
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )

    model.fit(X_train, y_train)
    logger.info("Multiclass XGBoost model training completed successfully.")
    return model


def evaluate_model(
    model: xgb.XGBClassifier,
    X_test: pd.DataFrame,
    y_test: pd.Series
) -> Dict[str, Any]:
    """Evaluates fitted multiclass model performance on test set.

    Args:
        model: Fitted XGBClassifier model.
        X_test: Testing feature matrix.
        y_test: Testing target series.

    Returns:
        Dictionary of multiclass evaluation metrics and reports.
    """
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    macro_prec = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
    weighted_prec = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
    macro_rec = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
    weighted_rec = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

    report = classification_report(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)

    roc_auc: Optional[float] = None
    if len(np.unique(y_test)) >= 2:
        try:
            roc_auc = float(roc_auc_score(y_test, y_prob, multi_class="ovr", average="macro"))
        except Exception as exc:
            logger.warning("Multiclass OvR ROC-AUC score calculation skipped: %s", exc)
    else:
        logger.warning("Multiclass ROC-AUC score calculation skipped: Test set contains only one class.")

    return {
        "accuracy": acc,
        "macro_precision": macro_prec,
        "weighted_precision": weighted_prec,
        "macro_recall": macro_rec,
        "weighted_recall": weighted_rec,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "roc_auc": roc_auc,
        "report": report,
        "confusion_matrix": cm,
        "y_pred": y_pred,
        "y_prob": y_prob
    }


def display_feature_importance(
    model: xgb.XGBClassifier,
    feature_names: List[str],
    top_n: int = 15
) -> pd.DataFrame:
    """Extracts and displays feature importance ranked from highest to lowest.

    Args:
        model: Trained XGBClassifier.
        feature_names: List of feature column names.
        top_n: Number of top features to display in console output.

    Returns:
        DataFrame containing sorted feature importances.
    """
    importances = model.feature_importances_
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": importances
    }).sort_values(by="importance", ascending=False).reset_index(drop=True)

    print(f"\n--- Top {min(top_n, len(importance_df))} Important Features ---")
    for idx, row in importance_df.head(top_n).iterrows():
        print(f"{idx + 1:2d}. {row['feature']:<30} : {row['importance']:.6f}")

    return importance_df


def save_model(
    model: xgb.XGBClassifier,
    output_dir: Path | str = "models",
    filename: str = "hint_model.json"
) -> Path:
    """Saves trained model binary using XGBoost native save_model.

    Args:
        model: Trained XGBClassifier.
        output_dir: Target directory.
        filename: Model output filename.

    Returns:
        Path of saved model file.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / filename
    model.save_model(str(out_file))
    logger.info("Saved trained hint model to '%s'.", out_file)
    return out_file


def save_feature_columns(
    feature_names: List[str],
    output_dir: Path | str = "models",
    filename: str = "hint_feature_columns.json"
) -> Path:
    """Saves training feature order to JSON metadata file.

    Args:
        feature_names: List of feature column names.
        output_dir: Target directory.
        filename: Output JSON filename.

    Returns:
        Path of saved feature columns file.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / filename
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"feature_columns": list(feature_names)}, f, indent=2)
    logger.info("Saved hint feature columns to '%s'.", out_file)
    return out_file


def save_metadata(
    metadata: Dict[str, Any],
    output_dir: Path | str = "models",
    filename: str = "hint_model_metadata.json"
) -> Path:
    """Saves model training metadata to JSON file.

    Args:
        metadata: Metadata dictionary.
        output_dir: Target directory.
        filename: Output JSON filename.

    Returns:
        Path of saved metadata file.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / filename
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved hint model metadata to '%s'.", out_file)
    return out_file


def apply_smote(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int = 42,
    k_neighbors: int = 3
) -> Tuple[pd.DataFrame, pd.Series]:
    """Applies SMOTE oversampling to training set only, dynamically handling small class counts.

    Args:
        X_train: Feature matrix for training set.
        y_train: Target series for training set.
        random_state: Random state seed.
        k_neighbors: Preferred number of nearest neighbors.

    Returns:
        Tuple of (X_train_resampled, y_train_resampled).
    """
    from imblearn.over_sampling import SMOTE

    counts = pd.Series(y_train).value_counts()
    min_samples = counts.min()

    effective_k = k_neighbors
    if min_samples <= k_neighbors:
        effective_k = max(1, min_samples - 1)
        logger.warning(
            "Minimum class count in training split is %d <= %d. Adjusting SMOTE k_neighbors to %d.",
            min_samples, k_neighbors, effective_k
        )

    logger.info("Applying SMOTE oversampling (k_neighbors=%d)...", effective_k)
    smote = SMOTE(random_state=random_state, k_neighbors=effective_k)
    X_res, y_res = smote.fit_resample(X_train, y_train)

    X_train_resampled = pd.DataFrame(X_res, columns=X_train.columns)
    y_train_resampled = pd.Series(y_res, name=y_train.name)

    return X_train_resampled, y_train_resampled


def train_hint_model(
    input_path: Path | str = "dataset/processed/hint_training_dataset.csv",
    output_dir: Path | str = "models",
    use_smote: bool = True
) -> Optional[Dict[str, Any]]:
    """Master pipeline function for training Hint Prediction Model.

    Args:
        input_path: Path to dataset CSV.
        output_dir: Path to models directory.
        use_smote: Whether to apply SMOTE to the training split.

    Returns:
        Dictionary of evaluation metrics if training succeeded, None otherwise.
    """
    out_dir = Path(output_dir)

    try:
        raw_df = load_dataset(input_path)
    except Exception as exc:
        msg = f"Dataset load error: {exc}"
        save_metadata({
            "model_name": "Hint Prediction Model",
            "status": "failed",
            "failure_reason": msg,
            "training_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }, output_dir=out_dir)
        print("\n----------------------------------------")
        print("Hint Model Training Summary")
        print("----------------------------------------")
        print("Dataset load failed.")
        print(f"Reason: {msg}")
        print("----------------------------------------\n")
        return None

    is_valid, validation_msg = validate_dataset(raw_df)
    if not is_valid:
        save_metadata({
            "model_name": "Hint Prediction Model",
            "status": "failed",
            "failure_reason": validation_msg,
            "training_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }, output_dir=out_dir)
        print("\n----------------------------------------")
        print("Hint Model Training Summary")
        print("----------------------------------------")
        print("Validation failed. Insufficient data to train Hint Model.")
        print(f"Message: {validation_msg}")
        print("----------------------------------------\n")
        return None

    try:
        X_train, X_test, y_train, y_test = prepare_training_data(raw_df)

        if len(np.unique(y_train)) < 2:
            msg = f"Training split contains only 1 class ({list(np.unique(y_train))}). Minimum 2 classes required in training set."
            save_metadata({
                "model_name": "Hint Prediction Model",
                "status": "failed",
                "failure_reason": msg,
                "training_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
            }, output_dir=out_dir)
            print("\n----------------------------------------")
            print("Hint Model Training Summary")
            print("----------------------------------------")
            print(f"Validation failed: {msg}")
            print("Collect more student sessions before training.")
            print("----------------------------------------\n")
            return None

        orig_dist = pd.Series(y_train).value_counts().sort_index().to_dict()

        if use_smote:
            X_train_fit, y_train_fit = apply_smote(X_train, y_train, random_state=42, k_neighbors=3)
            balanced_dist = pd.Series(y_train_fit).value_counts().sort_index().to_dict()
        else:
            X_train_fit, y_train_fit = X_train, y_train
            balanced_dist = orig_dist

        model = train_model(X_train_fit, y_train_fit)
        eval_metrics = evaluate_model(model, X_test, y_test)
        display_feature_importance(model, list(X_train_fit.columns), top_n=15)

        model_file = save_model(model, output_dir=out_dir)
        cols_file = save_feature_columns(list(X_train_fit.columns), output_dir=out_dir)

        roc_str = f"{eval_metrics['roc_auc']:.4f}" if eval_metrics['roc_auc'] is not None else "N/A"

        metadata = {
            "model_name": "Hint Prediction Model",
            "version": "1.0",
            "algorithm": "XGBoost",
            "objective": "multi:softprob",
            "num_classes": NUM_CLASSES,
            "smote_applied": use_smote,
            "trained_samples": len(X_train_fit) + len(X_test),
            "train_samples": len(X_train_fit),
            "test_samples": len(X_test),
            "accuracy": f"{eval_metrics['accuracy']:.4f}",
            "macro_precision": f"{eval_metrics['macro_precision']:.4f}",
            "macro_recall": f"{eval_metrics['macro_recall']:.4f}",
            "macro_f1": f"{eval_metrics['macro_f1']:.4f}",
            "weighted_f1": f"{eval_metrics['weighted_f1']:.4f}",
            "roc_auc": roc_str,
            "feature_count": X_train_fit.shape[1],
            "training_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "status": "ready"
        }
        meta_file = save_metadata(metadata, output_dir=out_dir)

        classes_detected = list(sorted(np.unique(np.concatenate([y_train_fit.values, y_test.values]))))

        print("\n----------------------------------------")
        print("Hint Model Training Summary")
        print("----------------------------------------")
        print(f"SMOTE Applied         : {use_smote}")
        print(f"Original Train Dist   : {orig_dist}")
        print(f"Balanced Train Dist   : {balanced_dist}")
        print(f"Training Samples      : {len(X_train_fit)} (resampled)")
        print(f"Testing Samples       : {len(X_test)}")
        print(f"Classes Detected      : {classes_detected}")
        print(f"Accuracy              : {eval_metrics['accuracy']:.4f}")
        print(f"Macro Precision       : {eval_metrics['macro_precision']:.4f}")
        print(f"Macro Recall          : {eval_metrics['macro_recall']:.4f}")
        print(f"Macro F1              : {eval_metrics['macro_f1']:.4f}")
        print(f"Weighted F1           : {eval_metrics['weighted_f1']:.4f}")
        print(f"ROC-AUC               : {roc_str}")
        print("\n--- Confusion Matrix (Untouched Test Set) ---")
        print(eval_metrics['confusion_matrix'])
        print("\n--- Classification Report ---")
        print(eval_metrics['report'])
        print(f"Model Saved           : {model_file.resolve()}")
        print(f"Feature Columns Saved : {cols_file.resolve()}")
        print(f"Metadata Saved        : {meta_file.resolve()}")
        print("Training Completed Successfully.")
        print("----------------------------------------\n")

        return eval_metrics

    except Exception as exc:
        logger.error("Hint model training pipeline failed: %s", exc, exc_info=True)
        save_metadata({
            "model_name": "Hint Prediction Model",
            "status": "failed",
            "failure_reason": str(exc),
            "training_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }, output_dir=out_dir)
        print("\n----------------------------------------")
        print("Hint Model Training Summary")
        print("----------------------------------------")
        print(f"Training Failed: {exc}")
        print("----------------------------------------\n")
        return None


def main() -> None:
    """Execution entry point."""
    train_hint_model()


if __name__ == "__main__":
    main()

