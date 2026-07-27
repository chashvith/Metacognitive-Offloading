"""Confidence calculation utility."""

def compute_confidence(probability: float) -> float:
    """Computes a confidence score based on the probability output of the model.

    Args:
        probability: Prediction probability (0.0 to 1.0).

    Returns:
        Float rounded confidence score.
    """
    if probability is None:
        return 0.5
    return float(round(max(0.0, min(1.0, float(probability))), 4))
