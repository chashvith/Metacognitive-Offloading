"""Snapshot Input Validator.

Validates incoming coding session snapshots to ensure required fields exist,
values are numeric where expected, and metrics lie within plausible physical ranges.
"""

import logging
import math
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

NON_NEGATIVE_NUMERIC_FIELDS = [
    "elapsed_time",
    "typing_speed",
    "compile_attempts",
    "compile_errors",
    "pause_duration",
    "chars_typed",
    "chars_deleted",
    "pause_count",
    "successful_runs",
    "runtime_errors",
    "deletion_ratio",
    "compile_failure_rate",
    "average_pause_duration",
    "current_struggle_score"
]


def validate_snapshot(snapshot: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validates an incoming student snapshot dictionary.

    Args:
        snapshot: Snapshot dictionary containing telemetry and behavioral metrics.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not isinstance(snapshot, dict) or not snapshot:
        msg = "Snapshot must be a non-empty dictionary."
        logger.warning("Validation failed: %s", msg)
        return False, msg

    # Check non-negative numerical fields
    for field in NON_NEGATIVE_NUMERIC_FIELDS:
        if field in snapshot:
            val = snapshot[field]
            if val is None or not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                msg = f"Field '{field}' must be a valid non-NaN number."
                logger.warning("Validation failed: %s", msg)
                return False, msg
            if val < 0:
                msg = f"Field '{field}' cannot be negative (got {val})."
                logger.warning("Validation failed: %s", msg)
                return False, msg

    # Check progress_ratio bounds (0 <= progress_ratio <= 1)
    if "progress_ratio" in snapshot:
        val = snapshot["progress_ratio"]
        if val is None or not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
            msg = "Field 'progress_ratio' must be a valid number."
            logger.warning("Validation failed: %s", msg)
            return False, msg
        if not (0.0 <= float(val) <= 1.0):
            msg = f"Field 'progress_ratio' must be between 0.0 and 1.0 (got {val})."
            logger.warning("Validation failed: %s", msg)
            return False, msg

    return True, None
