"""Snapshot validation utility."""

from typing import Any, Dict, Optional, Tuple


def validate_snapshot(snapshot: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validates student snapshot structure and data bounds.

    Args:
        snapshot: Snapshot dictionary.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not isinstance(snapshot, dict):
        return False, "Snapshot must be a valid JSON dictionary object."

    if not snapshot:
        return False, "Snapshot dictionary cannot be empty."

    # Validate non-negative numeric fields if present
    non_negative_fields = [
        "elapsed_time", "chars_typed", "chars_deleted",
        "pause_count", "pause_duration", "compile_attempts",
        "compile_errors", "successful_runs", "runtime_errors"
    ]

    for field in non_negative_fields:
        if field in snapshot:
            val = snapshot[field]
            if isinstance(val, (int, float)) and val < 0:
                return False, f"Field '{field}' cannot be negative (got {val})."

    # Validate progress ratio (0.0 to 1.0)
    if "progress_ratio" in snapshot:
        pr = snapshot["progress_ratio"]
        if isinstance(pr, (int, float)) and (pr < 0.0 or pr > 1.0):
            return False, f"Field 'progress_ratio' must be between 0.0 and 1.0 (got {pr})."

    return True, None
