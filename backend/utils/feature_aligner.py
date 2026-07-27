"""Feature alignment utility for ML model input validation and formatting."""

from typing import Any, Dict, List
import pandas as pd

DIFFICULTY_MAP = {"easy": 0, "medium": 1, "hard": 2}
TOPIC_MAP = {
    "arrays": 0, "strings": 1, "linked lists": 2, "trees": 3,
    "graphs": 4, "dynamic programming": 5, "sorting": 6, "searching": 7
}
LANGUAGE_MAP = {
    "python": 0, "java": 1, "cpp": 2, "c++": 2, "javascript": 3, "typescript": 4
}


def align_features(snapshot: Dict[str, Any], feature_columns: List[str]) -> pd.DataFrame:
    """Aligns input snapshot dictionary to the exact feature columns required by the model.

    Args:
        snapshot: Raw student session snapshot dictionary.
        feature_columns: Target feature column names.

    Returns:
        Pandas DataFrame ready for inference.
    """
    row: Dict[str, Any] = {}
    for col in feature_columns:
        if col in snapshot:
            val = snapshot[col]
            if col == "difficulty" and isinstance(val, str):
                val = DIFFICULTY_MAP.get(val.lower(), 0)
            elif col == "topic" and isinstance(val, str):
                val = TOPIC_MAP.get(val.lower(), 0)
            elif col == "language" and isinstance(val, str):
                val = LANGUAGE_MAP.get(val.lower(), 0)
            row[col] = val
        else:
            row[col] = 0.0

    df = pd.DataFrame([row], columns=feature_columns)
    return df
