"""Feature Aligner Module.

Converts raw student coding session snapshots into the exact feature vector
structure and column sequence used during model training.
"""

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DIFFICULTY_MAPPING = {
    "Easy": 0,
    "Medium": 1,
    "Hard": 2
}


def align_features(snapshot: Dict[str, Any], feature_columns: List[str]) -> pd.DataFrame:
    """Transforms raw snapshot dictionary into aligned pandas DataFrame matching model schema.

    Args:
        snapshot: Raw snapshot dictionary input.
        feature_columns: List of feature column names expected by the trained model.

    Returns:
        1-row pandas DataFrame containing aligned numerical feature values.
    """
    df = pd.DataFrame([snapshot])

    # Ordinal Encoding for difficulty
    if "difficulty" in df.columns:
        df["difficulty"] = df["difficulty"].map(
            lambda x: DIFFICULTY_MAPPING.get(str(x), 0)
        ).astype(int)
    else:
        df["difficulty"] = 0

    # Categorical One-Hot Encoding for language, topic, subtopic
    categorical_cols = [c for c in ["language", "topic", "subtopic"] if c in df.columns]
    if categorical_cols:
        df = pd.get_dummies(df, columns=categorical_cols, prefix=categorical_cols, dtype=int)

    # Align columns with feature_columns metadata
    aligned_df = pd.DataFrame(index=df.index)

    for col in feature_columns:
        if col in df.columns:
            aligned_df[col] = df[col]
        else:
            aligned_df[col] = 0

    # Ensure correct column ordering and numerical dtype
    aligned_df = aligned_df[feature_columns].astype(float)
    return aligned_df
