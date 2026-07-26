"""Preprocessing Pipeline for Student Solver Prediction Model.

This module loads snapshot CSV data generated from coding sessions, validates the dataset,
handles missing values, performs ordinal and one-hot encoding on categorical features,
splits data by session_id to prevent data leakage, and prepares ready-to-train
feature matrices (X_train, X_test) and target vectors (y_train, y_test) for XGBoost.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "session_id",
    "problem_name",
    "difficulty",
    "language",
    "topic",
    "subtopic",
    "snapshot_time",
    "elapsed_time",
    "progress_ratio",
    "current_struggle_score",
    "chars_typed",
    "chars_deleted",
    "pause_count",
    "pause_duration",
    "compile_attempts",
    "compile_errors",
    "successful_runs",
    "runtime_errors",
    "deletion_ratio",
    "typing_speed",
    "compile_failure_rate",
    "average_pause_duration",
    "solved"
]

NON_FEATURE_COLUMNS = ["session_id", "problem_name", "snapshot_time"]
TARGET_COLUMN = "solved"

DIFFICULTY_MAPPING = {
    "Easy": 0,
    "Medium": 1,
    "Hard": 2
}


def load_dataset(file_path: Path | str = "dataset/processed/snapshots.csv") -> pd.DataFrame:
    """Loads the CSV dataset into a pandas DataFrame.

    Args:
        file_path: Path to the snapshots CSV file.

    Returns:
        Loaded pandas DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If reading the CSV fails.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error("Dataset file not found at '%s'.", path.resolve())
        raise FileNotFoundError(f"Dataset file not found at '{path.resolve()}'.")

    try:
        df = pd.read_csv(path)
        logger.info("Dataset loaded successfully from '%s'.", path)
        return df
    except Exception as exc:
        logger.error("Failed to read dataset CSV from '%s': %s", path, exc)
        raise IOError(f"Failed to read dataset CSV: {exc}") from exc


def validate_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Validates dataset structure, checks required columns, removes duplicates, and logs anomalies.

    Args:
        df: Input pandas DataFrame.

    Returns:
        Validated DataFrame with duplicate rows removed.

    Raises:
        ValueError: If dataset is empty or required columns are missing.
    """
    if df.empty:
        logger.error("Dataset is empty.")
        raise ValueError("Dataset is empty.")

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        logger.error("Dataset is missing required column(s): %s", missing_cols)
        raise ValueError(f"Dataset is missing required column(s): {missing_cols}")

    initial_rows = len(df)
    df_clean = df.drop_duplicates().copy()
    duplicates_removed = initial_rows - len(df_clean)

    if duplicates_removed > 0:
        logger.info("Removed %d duplicate row(s).", duplicates_removed)

    # Check for invalid numeric values (negative values in count/duration metrics)
    numeric_check_cols = [
        "elapsed_time", "progress_ratio", "current_struggle_score",
        "chars_typed", "chars_deleted", "pause_count", "pause_duration",
        "compile_attempts", "compile_errors", "successful_runs", "runtime_errors"
    ]
    for col in numeric_check_cols:
        if col in df_clean.columns:
            negative_count = (df_clean[col] < 0).sum()
            if negative_count > 0:
                logger.warning("Column '%s' contains %d negative value(s).", col, negative_count)

    logger.info("Dataset validation completed. Total rows: %d.", len(df_clean))
    return df_clean


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Handles missing values safely for categorical and numerical features.

    Args:
        df: Input pandas DataFrame.

    Returns:
        DataFrame with missing values imputed.
    """
    df_filled = df.copy()

    # Fill categorical missing values
    df_filled["topic"] = df_filled["topic"].fillna("Unknown").replace("", "Unknown")
    df_filled["subtopic"] = df_filled["subtopic"].fillna("Unknown").replace("", "Unknown")

    # Mode imputation for difficulty
    valid_diffs = df_filled["difficulty"].dropna()
    valid_diffs = valid_diffs[valid_diffs != ""]
    diff_mode = valid_diffs.mode()[0] if not valid_diffs.empty else "Easy"
    df_filled["difficulty"] = df_filled["difficulty"].fillna(diff_mode).replace("", diff_mode)

    # Mode imputation for language
    valid_langs = df_filled["language"].dropna()
    valid_langs = valid_langs[valid_langs != ""]
    lang_mode = valid_langs.mode()[0] if not valid_langs.empty else "Unknown"
    df_filled["language"] = df_filled["language"].fillna(lang_mode).replace("", lang_mode)

    # Fill numerical missing values with column median
    numeric_cols = df_filled.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df_filled[col].isnull().sum() > 0:
            median_val = df_filled[col].median()
            df_filled[col] = df_filled[col].fillna(median_val)
            logger.info("Imputed missing values in column '%s' with median (%s).", col, median_val)

    logger.info("Missing values handled successfully.")
    return df_filled


def encode_features(df: pd.DataFrame) -> pd.DataFrame:
    """Encodes categorical variables using ordinal mapping for difficulty and one-hot encoding for others.

    Args:
        df: Input pandas DataFrame.

    Returns:
        Encoded DataFrame with numerical features.
    """
    df_encoded = df.copy()

    # Ordinal Encoding for difficulty
    df_encoded["difficulty"] = df_encoded["difficulty"].map(
        lambda x: DIFFICULTY_MAPPING.get(x, 0)
    ).astype(int)

    # One-Hot Encoding for language, topic, subtopic
    categorical_cols = ["language", "topic", "subtopic"]
    existing_cat_cols = [c for c in categorical_cols if c in df_encoded.columns]

    df_encoded = pd.get_dummies(
        df_encoded,
        columns=existing_cat_cols,
        prefix=existing_cat_cols,
        dtype=int
    )

    logger.info("Categorical columns encoded successfully.")
    return df_encoded


def split_by_session(
    df: pd.DataFrame,
    session_col: str = "session_id",
    test_size: float = 0.20,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Splits dataset into training and testing sets by grouping on session_id to prevent data leakage.

    Args:
        df: Input pandas DataFrame.
        session_col: Column name representing unique session IDs.
        test_size: Proportion of sessions reserved for testing.
        random_state: Random state seed.

    Returns:
        Tuple of (train_df, test_df).
    """
    if session_col not in df.columns:
        raise KeyError(f"Session column '{session_col}' not found in DataFrame.")

    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(gss.split(df, groups=df[session_col]))

    train_df = df.iloc[train_idx].copy()
    test_df = df.iloc[test_idx].copy()

    logger.info(
        "Split dataset using GroupShuffleSplit: %d train rows (%d sessions), %d test rows (%d sessions).",
        len(train_df), train_df[session_col].nunique(),
        len(test_df), test_df[session_col].nunique()
    )
    return train_df, test_df


def prepare_features(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    target_col: str = TARGET_COLUMN,
    drop_cols: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Removes non-feature columns and separates features (X) and target labels (y).

    Args:
        train_df: Training DataFrame.
        test_df: Testing DataFrame.
        target_col: Name of target label column.
        drop_cols: List of non-feature column names to drop.

    Returns:
        Tuple of (X_train, X_test, y_train, y_test).
    """
    if drop_cols is None:
        drop_cols = NON_FEATURE_COLUMNS

    y_train = train_df[target_col].astype(int)
    y_test = test_df[target_col].astype(int)

    cols_to_remove = set(drop_cols + [target_col])

    feature_cols = [col for col in train_df.columns if col not in cols_to_remove]

    X_train = train_df[feature_cols].copy()
    X_test = test_df[feature_cols].copy()

    logger.info("Features prepared. Training features shape: %s, Test features shape: %s.", X_train.shape, X_test.shape)
    return X_train, X_test, y_train, y_test


def preprocess_data(
    file_path: Path | str = "dataset/processed/snapshots.csv",
    test_size: float = 0.20,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Master preprocessing pipeline function.

    Args:
        file_path: Path to snapshots CSV.
        test_size: Ratio of test set split.
        random_state: Seed for random state.

    Returns:
        Tuple of (X_train, X_test, y_train, y_test).
    """
    raw_df = load_dataset(file_path)
    original_row_count = len(raw_df)

    validated_df = validate_dataset(raw_df)
    duplicates_removed_count = original_row_count - len(validated_df)

    imputed_df = handle_missing_values(validated_df)
    encoded_df = encode_features(imputed_df)

    train_df, test_df = split_by_session(
        encoded_df,
        session_col="session_id",
        test_size=test_size,
        random_state=random_state
    )

    X_train, X_test, y_train, y_test = prepare_features(
        train_df,
        test_df,
        target_col=TARGET_COLUMN,
        drop_cols=NON_FEATURE_COLUMNS
    )

    # Print summary
    print("\n--- Preprocessing Summary ---")
    print("Dataset loaded successfully.")
    print(f"Original rows       : {original_row_count}")
    print(f"Duplicates removed  : {duplicates_removed_count}")
    print(f"Training rows       : {len(X_train)}")
    print(f"Testing rows        : {len(X_test)}")
    print(f"Number of features  : {X_train.shape[1]}")
    print("Categorical columns encoded.")
    print("Missing values handled.")
    print("Preprocessing completed successfully.\n")

    return X_train, X_test, y_train, y_test


def main() -> None:
    """Execution entry point for testing preprocessing pipeline."""
    X_train, X_test, y_train, y_test = preprocess_data()
    print("X_train shape:", X_train.shape)
    print("X_test shape :", X_test.shape)
    print("y_train shape:", y_train.shape)
    print("y_test shape :", y_test.shape)


if __name__ == "__main__":
    main()
