"""Production-Ready Student Hint Prediction Inference Pipeline.

Acts as the main entry point for predicting the minimum effective hint required
by a student based on their behavioral coding snapshot.

Can be imported by backend services (e.g., FastAPI) or executed as a CLI script.
"""

import json
import logging
from typing import Any, Dict

from predict.hint import predict_hint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Demonstrates hint prediction pipeline execution with sample snapshots."""
    sample_snapshot = {
        "elapsed_time": 132,
        "progress_ratio": 0.80,
        "current_struggle_score": 0.183,
        "chars_typed": 252,
        "chars_deleted": 19,
        "pause_count": 3,
        "pause_duration": 49.79,
        "compile_attempts": 3,
        "compile_errors": 2,
        "successful_runs": 1,
        "runtime_errors": 0,
        "deletion_ratio": 0.0754,
        "typing_speed": 114.55,
        "compile_failure_rate": 0.6667,
        "average_pause_duration": 16.60,
        "difficulty": "Easy",
        "language": "java",
        "topic": "Arrays",
        "subtopic": "Traversal"
    }

    print("\n--- Running Hint Prediction Pipeline Test ---")
    result = predict_hint(sample_snapshot)
    print(json.dumps(result, indent=2))

    invalid_snapshot = {
        "elapsed_time": -5,
        "progress_ratio": 1.2
    }

    print("\n--- Testing Invalid Snapshot Handling ---")
    invalid_result = predict_hint(invalid_snapshot)
    print(json.dumps(invalid_result, indent=2))


if __name__ == "__main__":
    main()
