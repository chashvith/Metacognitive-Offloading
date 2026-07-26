"""Production-Ready Student Solver Inference Pipeline.

This script acts as the main entry point for predicting whether a student will
eventually solve a programming problem based on their behavioral coding snapshot.

It can be imported directly by backend services (e.g. FastAPI) or executed as a CLI script.
"""

import json
import logging

from typing import Any, Dict
from predict.solver import predict_solver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Demonstrates inference pipeline execution with sample snapshots."""
    sample_snapshot = {
        "difficulty": "Easy",
        "language": "java",
        "topic": "Arrays",
        "subtopic": "Two Pointers",
        "elapsed_time": 92,
        "progress_ratio": 0.56,
        "current_struggle_score": 0.125,
        "chars_typed": 251,
        "chars_deleted": 19,
        "pause_count": 1,
        "pause_duration": 6.705,
        "compile_attempts": 1,
        "compile_errors": 1,
        "successful_runs": 0,
        "runtime_errors": 0,
        "deletion_ratio": 0.075,
        "typing_speed": 163.7,
        "compile_failure_rate": 1.0,
        "average_pause_duration": 6.705
    }

    print("\n--- Running Inference Pipeline Test ---")
    result = predict_solver(sample_snapshot)
    print(json.dumps(result, indent=2))

    invalid_snapshot = {
        "elapsed_time": -10,  # Invalid negative elapsed time
        "progress_ratio": 1.5  # Invalid progress_ratio > 1.0
    }

    print("\n--- Testing Invalid Snapshot Handling ---")
    invalid_result = predict_solver(invalid_snapshot)
    print(json.dumps(invalid_result, indent=2))


if __name__ == "__main__":
    main()
