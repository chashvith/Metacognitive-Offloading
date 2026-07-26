"""Confidence Calculation Module.

Maps numeric prediction probabilities to human-readable confidence levels
(High, Medium, Low) using configurable decision thresholds.
"""

import logging

logger = logging.getLogger(__name__)


def compute_confidence(
    probability: float,
    high_threshold: float = 0.85,
    medium_threshold: float = 0.60
) -> str:
    """Computes confidence level from prediction probability.

    Args:
        probability: Float value between 0.0 and 1.0 representing solve probability.
        high_threshold: Threshold above which confidence is considered High.
        medium_threshold: Threshold above which confidence is considered Medium.

    Returns:
        String confidence category ('High', 'Medium', or 'Low').
    """
    if probability >= high_threshold:
        return "High"
    elif probability >= medium_threshold:
        return "Medium"
    else:
        return "Low"
