"""Hint Label Generation Pipeline.

Generates deterministic, explainable training labels for the Hint Prediction Model
by computing a Hint Need Score (HNS) from student behavioral metrics and applying
domain rule-based overrides. Includes human-readable hint names and label decision reason tracking.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Centralized human-readable hint name mapping
HINT_NAME_MAPPING: Dict[int, str] = {
    0: "No Hint",
    1: "Concept Hint",
    2: "Guided Hint",
    3: "Pseudocode",
    4: "Full Solution"
}

# Configurable heuristic parameters and labeling strategy version
DEFAULT_CONFIG: Dict[str, Any] = {
    "labeling_strategy_version": "1.0",
    "hns_weights": {
        "current_struggle_score": 0.35,
        "compile_failure_rate": 0.20,
        "normalized_pause_score": 0.15,
        "normalized_runtime_error_score": 0.15,
        "deletion_ratio": 0.10,
        "progress_ratio": 0.05
    },
    "label_thresholds": [
        (0.00, 0.20, 0),
        (0.20, 0.40, 1),
        (0.40, 0.60, 2),
        (0.60, 0.80, 3),
        (0.80, 1.00, 4)
    ],
    "override_rules": {
        "rule1": {
            "struggle_threshold": 0.20,
            "compile_fail_threshold": 0.20,
            "target_label": 0
        },
        "rule2": {
            "progress_threshold": 0.90,
            "min_label": 3
        },
        "rule3": {
            "min_compile_attempts": 10,
            "compile_fail_threshold": 0.80,
            "min_label": 3
        },
        "rule4": {
            "progress_threshold": 0.95,
            "struggle_threshold": 0.85,
            "target_label": 4
        },
        "rule5": {
            "min_successful_runs": 1,
            "label_reduction": 1
        }
    }
}


def load_dataset(file_path: Path | str = "dataset/processed/snapshots.csv") -> pd.DataFrame:
    """Loads the processed snapshots dataset CSV.

    Args:
        file_path: Path to input snapshots.csv file.

    Returns:
        Loaded pandas DataFrame.

    Raises:
        FileNotFoundError: If input file is missing.
        IOError: If reading fails.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error("Input snapshot file not found at '%s'.", path.resolve())
        raise FileNotFoundError(f"Input snapshot file not found at '{path.resolve()}'.")

    try:
        df = pd.read_csv(path)
        logger.info("Loaded %d rows from '%s'.", len(df), path)
        return df
    except Exception as exc:
        logger.error("Failed to read snapshot dataset: %s", exc)
        raise IOError(f"Failed to read dataset: {exc}") from exc


def min_max_normalize(series: pd.Series) -> pd.Series:
    """Performs Min-Max normalization on a numeric series.

    Args:
        series: Pandas numeric series.

    Returns:
        Normalized series bounded between 0.0 and 1.0.
    """
    s = series.astype(float).fillna(0.0)
    min_val = s.min()
    max_val = s.max()

    if max_val == min_val:
        return pd.Series(0.0, index=series.index)

    return (s - min_val) / (max_val - min_val)


def normalize_features(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """Normalizes unscaled pause and runtime error metrics.

    Args:
        df: Input snapshot DataFrame.

    Returns:
        Tuple of (normalized_pause_score, normalized_runtime_error_score).
    """
    pause_series = df.get("pause_duration", df.get("average_pause_duration", pd.Series(0.0, index=df.index)))
    norm_pause = min_max_normalize(pause_series)

    runtime_series = df.get("runtime_errors", pd.Series(0.0, index=df.index))
    norm_runtime = min_max_normalize(runtime_series)

    return norm_pause, norm_runtime


def compute_hint_need_score(
    df: pd.DataFrame,
    norm_pause: pd.Series,
    norm_runtime: pd.Series,
    weights: Dict[str, float]
) -> pd.Series:
    """Computes the composite Hint Need Score (HNS) bounded between 0.0 and 1.0.

    Args:
        df: Input snapshot DataFrame.
        norm_pause: Normalized pause score series.
        norm_runtime: Normalized runtime error score series.
        weights: Dictionary of feature weights.

    Returns:
        Series of computed Hint Need Scores.
    """
    struggle = df.get("current_struggle_score", 0.0).astype(float).fillna(0.0)
    compile_fail = df.get("compile_failure_rate", 0.0).astype(float).fillna(0.0)
    deletion = df.get("deletion_ratio", 0.0).astype(float).fillna(0.0)
    progress = df.get("progress_ratio", 0.0).astype(float).fillna(0.0)

    w_struggle = weights.get("current_struggle_score", 0.35)
    w_compile_fail = weights.get("compile_failure_rate", 0.20)
    w_pause = weights.get("normalized_pause_score", 0.15)
    w_runtime = weights.get("normalized_runtime_error_score", 0.15)
    w_deletion = weights.get("deletion_ratio", 0.10)
    w_progress = weights.get("progress_ratio", 0.05)

    hns = (
        w_struggle * struggle +
        w_compile_fail * compile_fail +
        w_pause * norm_pause +
        w_runtime * norm_runtime +
        w_deletion * deletion +
        w_progress * progress
    )

    return hns.clip(lower=0.0, upper=1.0)


def assign_initial_labels(hns_series: pd.Series, thresholds: List[Tuple[float, float, int]]) -> pd.Series:
    """Maps Hint Need Score (HNS) to initial numeric hint labels (0 to 4).

    Args:
        hns_series: Series of computed Hint Need Scores.
        thresholds: List of (lower_bound, upper_bound, label) tuples.

    Returns:
        Series of initial integer hint labels.
    """
    labels = pd.Series(0, index=hns_series.index, dtype=int)

    for idx, hns in hns_series.items():
        val = float(hns)
        if val <= 0.20:
            labels[idx] = 0
        elif val <= 0.40:
            labels[idx] = 1
        elif val <= 0.60:
            labels[idx] = 2
        elif val <= 0.80:
            labels[idx] = 3
        else:
            labels[idx] = 4

    return labels


def apply_override_rules(
    df: pd.DataFrame,
    initial_labels: pd.Series,
    config: Dict[str, Any]
) -> Tuple[pd.Series, pd.Series]:
    """Applies domain rule-based overrides to refine initial hint labels and tracks decision reasons.

    Args:
        df: Input snapshot DataFrame.
        initial_labels: Series of initial numeric hint labels.
        config: Configuration dictionary containing rule parameters.

    Returns:
        Tuple of (final_labels_series, label_reasons_series).
    """
    final_labels = initial_labels.copy()
    label_reasons = pd.Series("HNS Mapping", index=df.index, dtype=str)

    rules = config.get("override_rules", {})

    r1_cfg = rules.get("rule1", {})
    r2_cfg = rules.get("rule2", {})
    r3_cfg = rules.get("rule3", {})
    r4_cfg = rules.get("rule4", {})
    r5_cfg = rules.get("rule5", {})

    for idx, row in df.iterrows():
        label = int(final_labels[idx])
        reason = "HNS Mapping"

        solved = int(row.get("solved", 0))
        struggle = float(row.get("current_struggle_score", 0.0) or 0.0)
        compile_fail = float(row.get("compile_failure_rate", 0.0) or 0.0)
        progress = float(row.get("progress_ratio", 0.0) or 0.0)
        compile_attempts = int(row.get("compile_attempts", 0) or 0)
        successful_runs = int(row.get("successful_runs", 0) or 0)

        # Rule 1: Solved with low struggle & low compile failure -> No Hint (0)
        if solved == 1 and struggle < r1_cfg.get("struggle_threshold", 0.20) and compile_fail < r1_cfg.get("compile_fail_threshold", 0.20):
            label = r1_cfg.get("target_label", 0)
            reason = "Rule 1: Solved with Low Struggle"

        # Rule 2: Near end (progress > 0.90) & unsolved -> At least Pseudocode (3)
        if progress > r2_cfg.get("progress_threshold", 0.90) and solved == 0:
            target = r2_cfg.get("min_label", 3)
            if target > label:
                label = target
                reason = "Rule 2: High Progress but Unsolved"

        # Rule 3: High compile attempts (>= 10) & high compile failure rate (>= 0.80) -> At least Pseudocode (3)
        if compile_attempts >= r3_cfg.get("min_compile_attempts", 10) and compile_fail >= r3_cfg.get("compile_fail_threshold", 0.80):
            target = r3_cfg.get("min_label", 3)
            if target > label:
                label = target
                reason = "Rule 3: Frequent Compile Failures"

        # Rule 4: Critical struggle near deadline (progress > 0.95, unsolved, struggle >= 0.85) -> Full Solution (4)
        if progress > r4_cfg.get("progress_threshold", 0.95) and solved == 0 and struggle >= r4_cfg.get("struggle_threshold", 0.85):
            label = r4_cfg.get("target_label", 4)
            reason = "Rule 4: High Struggle Near Session End"

        # Rule 5: Successful run (successful_runs >= 1) -> Reduce label by 1 level (min 0)
        if successful_runs >= r5_cfg.get("min_successful_runs", 1):
            new_label = max(0, label - r5_cfg.get("label_reduction", 1))
            if new_label != label:
                label = new_label
                reason = "Rule 5: Successful Run Adjustment"

        final_labels[idx] = label
        label_reasons[idx] = reason

    return final_labels.astype(int), label_reasons


def save_dataset(df: pd.DataFrame, output_path: Path | str = "dataset/processed/hint_training_dataset.csv") -> Path:
    """Saves the output dataset containing features, HNS, hint_label, hint_name, and label_reason to CSV.

    Args:
        df: DataFrame to save.
        output_path: Target file path.

    Returns:
        Path of saved CSV.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_file, index=False)
    logger.info("Saved dataset with hint labels to '%s'.", out_file)
    return out_file


def generate_hint_labels(
    input_path: Path | str = "dataset/processed/snapshots.csv",
    output_path: Path | str = "dataset/processed/hint_training_dataset.csv",
    config: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """Master function orchestrating the hint label generation pipeline.

    Args:
        input_path: Input snapshot dataset CSV path.
        output_path: Output dataset CSV path.
        config: Optional configuration dictionary.

    Returns:
        Processed pandas DataFrame containing hint_need_score, hint_label, hint_name, and label_reason.
    """
    cfg = config if config is not None else DEFAULT_CONFIG
    logger.info("Running Hint Label Generation Pipeline (Strategy Version %s)...", cfg.get("labeling_strategy_version", "1.0"))

    df = load_dataset(input_path)

    if df.empty:
        logger.error("Input snapshot dataset is empty.")
        raise ValueError("Input snapshot dataset is empty.")

    norm_pause, norm_runtime = normalize_features(df)
    hns = compute_hint_need_score(df, norm_pause, norm_runtime, cfg["hns_weights"])

    df["hint_need_score"] = hns.round(4)
    initial_labels = assign_initial_labels(df["hint_need_score"], cfg["label_thresholds"])
    final_labels, label_reasons = apply_override_rules(df, initial_labels, cfg)

    df["hint_label"] = final_labels
    df["hint_name"] = df["hint_label"].map(HINT_NAME_MAPPING)
    df["label_reason"] = label_reasons

    saved_file = save_dataset(df, output_path)

    # Class distribution count
    counts = df["hint_label"].value_counts().to_dict()

    print("\n----------------------------------------")
    print("Hint Label Generation Summary")
    print("----------------------------------------")
    print(f"Labeling Strategy Version : {cfg.get('labeling_strategy_version', '1.0')}")
    print(f"Snapshots Processed       : {len(df)}")
    print(f"Labels Generated          : {len(df)}")
    print(f"No Hint (0)               : {counts.get(0, 0)}")
    print(f"Concept Hint (1)          : {counts.get(1, 0)}")
    print(f"Guided Hint (2)           : {counts.get(2, 0)}")
    print(f"Pseudocode (3)            : {counts.get(3, 0)}")
    print(f"Full Solution (4)         : {counts.get(4, 0)}")
    print(f"Dataset Saved             : {saved_file.resolve()}")
    print("Completed Successfully.")
    print("----------------------------------------\n")

    return df


def main() -> None:
    """Execution entry point."""
    try:
        generate_hint_labels()
    except Exception as exc:
        logger.error("Hint label generation failed: %s", exc, exc_info=True)


if __name__ == "__main__":
    main()
