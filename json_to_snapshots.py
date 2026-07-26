"""JSON to Snapshot CSV Generator for ML Training.

This script processes coding session JSON files, replays the event timeline
to compute cumulative metrics at each compile event, and generates a CSV dataset
for training machine learning models (e.g., predicting problem-solving outcome).
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

REQUIRED_SESSION_KEYS = {"session_id", "timeline"}
COMPILE_EVENTS = {"compile_error", "compile_success"}

CSV_COLUMNS = [
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


def load_json_files(folder_path: Path | str) -> Tuple[List[Dict[str, Any]], int]:
    """Reads all .json files from the specified folder.

    Args:
        folder_path: Path to the directory containing session JSON files.

    Returns:
        A tuple of (valid_sessions, skipped_count).
    """
    folder = Path(folder_path)
    sessions: List[Dict[str, Any]] = []
    skipped_count = 0

    if not folder.exists() or not folder.is_dir():
        logger.error("Folder path '%s' does not exist or is not a directory.", folder)
        return sessions, skipped_count

    json_files = list(folder.glob("*.json"))
    logger.info("Found %d JSON file(s) in '%s'.", len(json_files), folder)

    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                logger.warning("Skipping '%s': Root element is not a JSON object.", file_path.name)
                skipped_count += 1
                continue

            # Validate required keys
            missing_keys = REQUIRED_SESSION_KEYS - data.keys()
            if missing_keys:
                logger.warning(
                    "Skipping '%s': Missing required key(s): %s", file_path.name, missing_keys
                )
                skipped_count += 1
                continue

            if not isinstance(data.get("timeline"), list):
                logger.warning("Skipping '%s': 'timeline' key is not a list.", file_path.name)
                skipped_count += 1
                continue

            sessions.append(data)

        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping malformed or unreadable file '%s': %s", file_path.name, exc)
            skipped_count += 1

    return sessions, skipped_count


def get_current_struggle_score(struggle_scores: Optional[List[Dict[str, Any]]], elapsed_time: float) -> float:
    """Finds the latest struggle score whose time is <= elapsed_time.

    Args:
        struggle_scores: List of struggle score entries from session JSON.
        elapsed_time: Current compile snapshot time.

    Returns:
        Most recent struggle score at or before elapsed_time, or 0.0 if none exists.
    """
    if not isinstance(struggle_scores, list):
        return 0.0

    latest_score = 0.0
    latest_time = -1.0

    for item in struggle_scores:
        if isinstance(item, dict):
            t = float(item.get("time", 0) or 0)
            if t <= elapsed_time and t >= latest_time:
                latest_score = float(item.get("score", 0.0) or 0.0)
                latest_time = t

    return latest_score


def compute_snapshot_features(
    chars_typed: int,
    chars_deleted: int,
    pause_count: int,
    pause_duration: float,
    compile_attempts: int,
    compile_errors: int,
    elapsed_time: float
) -> Dict[str, float]:
    """Computes derived snapshot features from cumulative counters.

    Args:
        chars_typed: Cumulative characters typed up to current event.
        chars_deleted: Cumulative characters deleted up to current event.
        pause_count: Cumulative number of pauses detected.
        pause_duration: Cumulative pause duration in seconds.
        compile_attempts: Cumulative compilation attempts.
        compile_errors: Cumulative compilation errors.
        elapsed_time: Elapsed session time in seconds.

    Returns:
        Dict containing deletion_ratio, typing_speed, compile_failure_rate, and average_pause_duration.
    """
    deletion_ratio = (chars_deleted / chars_typed) if chars_typed > 0 else 0.0
    typing_speed = (chars_typed / elapsed_time * 60.0) if elapsed_time > 0 else 0.0
    compile_failure_rate = (compile_errors / compile_attempts) if compile_attempts > 0 else 0.0
    average_pause_duration = (pause_duration / pause_count) if pause_count > 0 else 0.0

    return {
        "deletion_ratio": deletion_ratio,
        "typing_speed": typing_speed,
        "compile_failure_rate": compile_failure_rate,
        "average_pause_duration": average_pause_duration
    }


def create_snapshot(
    session_meta: Dict[str, Any],
    elapsed_time: float,
    progress_ratio: float,
    current_struggle_score: float,
    counters: Dict[str, Any],
    derived_features: Dict[str, float]
) -> Dict[str, Any]:
    """Constructs a single snapshot dictionary adhering to the required schema.

    Args:
        session_meta: Top-level metadata extracted from session JSON.
        elapsed_time: Time of the current compile event.
        progress_ratio: Ratio of elapsed time to total session time.
        current_struggle_score: Latest struggle score at or before snapshot time.
        counters: Dictionary of cumulative event counters.
        derived_features: Dictionary of derived numerical features.

    Returns:
        A dictionary representing one CSV snapshot row.
    """
    snapshot = {
        "session_id": session_meta.get("session_id", ""),
        "problem_name": session_meta.get("problem_name", ""),
        "difficulty": session_meta.get("difficulty", ""),
        "language": session_meta.get("language", ""),
        "topic": session_meta.get("topic", ""),
        "subtopic": session_meta.get("subtopic", ""),
        "snapshot_time": elapsed_time,
        "elapsed_time": elapsed_time,
        "progress_ratio": progress_ratio,
        "current_struggle_score": current_struggle_score,
        "chars_typed": counters["chars_typed"],
        "chars_deleted": counters["chars_deleted"],
        "pause_count": counters["pause_count"],
        "pause_duration": counters["pause_duration"],
        "compile_attempts": counters["compile_attempts"],
        "compile_errors": counters["compile_errors"],
        "successful_runs": counters["successful_runs"],
        "runtime_errors": counters["runtime_errors"],
        "deletion_ratio": derived_features["deletion_ratio"],
        "typing_speed": derived_features["typing_speed"],
        "compile_failure_rate": derived_features["compile_failure_rate"],
        "average_pause_duration": derived_features["average_pause_duration"],
        "solved": session_meta.get("solved", 0)
    }
    return snapshot


def process_session(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Replays the session timeline to generate snapshots at compile events.

    Args:
        session: Parsed session JSON dictionary.

    Returns:
        List of snapshot dictionaries generated for compile events.
    """
    # Extract problem details safely
    problem_info = session.get("problem") if isinstance(session.get("problem"), dict) else {}

    solved_label = 1 if (
        session.get("status") == "Solved" or
        (isinstance(session.get("outcome"), dict) and session.get("outcome", {}).get("final_status") == "Solved")
    ) else 0

    session_meta = {
        "session_id": session.get("session_id", ""),
        "problem_name": session.get("problem_name", ""),
        "difficulty": session.get("difficulty") or problem_info.get("difficulty", ""),
        "language": session.get("language", ""),
        "topic": problem_info.get("topic", ""),
        "subtopic": problem_info.get("subtopic", ""),
        "solved": solved_label
    }

    total_session_time = float(session.get("time_spent", 0) or 0)
    struggle_scores = session.get("struggle_scores", [])

    # Initialize cumulative counters
    chars_typed = 0
    chars_deleted = 0
    pause_count = 0
    pause_duration = 0.0
    compile_attempts = 0
    compile_errors = 0
    successful_runs = 0
    runtime_errors = 0

    snapshots: List[Dict[str, Any]] = []

    timeline = session.get("timeline", [])

    for event in timeline:
        if not isinstance(event, dict):
            continue

        event_name = event.get("event", "")
        meta = event.get("meta") if isinstance(event.get("meta"), dict) else {}

        # Update cumulative counters according to event type
        if event_name == "typed":
            chars_typed += int(meta.get("chars", 0) or 0)
        elif event_name == "deleted":
            chars_deleted += int(meta.get("chars", 0) or 0)
        elif event_name == "pause_detected":
            pause_count += 1
            duration_ms = float(meta.get("duration_ms", 0) or 0)
            pause_duration += duration_ms / 1000.0
        elif event_name == "compile_error":
            compile_attempts += 1
            compile_errors += 1
        elif event_name == "compile_success":
            compile_attempts += 1
        elif event_name == "successful_run":
            successful_runs += 1
        elif event_name == "runtime_error":
            runtime_errors += 1

        # Generate snapshot if compile event occurs
        if event_name in COMPILE_EVENTS:
            elapsed_time = float(event.get("time", 0) or 0)

            # Compute progress_ratio
            progress_ratio = (elapsed_time / total_session_time) if total_session_time > 0 else 0.0

            # Compute current_struggle_score
            current_struggle_score = get_current_struggle_score(struggle_scores, elapsed_time)

            counters = {
                "chars_typed": chars_typed,
                "chars_deleted": chars_deleted,
                "pause_count": pause_count,
                "pause_duration": pause_duration,
                "compile_attempts": compile_attempts,
                "compile_errors": compile_errors,
                "successful_runs": successful_runs,
                "runtime_errors": runtime_errors
            }

            derived = compute_snapshot_features(
                chars_typed=chars_typed,
                chars_deleted=chars_deleted,
                pause_count=pause_count,
                pause_duration=pause_duration,
                compile_attempts=compile_attempts,
                compile_errors=compile_errors,
                elapsed_time=elapsed_time
            )

            snapshot = create_snapshot(
                session_meta=session_meta,
                elapsed_time=elapsed_time,
                progress_ratio=progress_ratio,
                current_struggle_score=current_struggle_score,
                counters=counters,
                derived_features=derived
            )
            snapshots.append(snapshot)

    return snapshots


def save_dataframe(snapshots: List[Dict[str, Any]], output_path: Path | str) -> Path:
    """Converts snapshot list to DataFrame and saves as CSV.

    Args:
        snapshots: List of snapshot dictionaries.
        output_path: Target path for the output CSV file.

    Returns:
        Path object of saved CSV.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(snapshots, columns=CSV_COLUMNS)
    df.to_csv(out_file, index=False)
    logger.info("Saved %d snapshots to '%s'.", len(df), out_file)
    return out_file


def main() -> None:
    """Main execution entry point."""
    input_folder = Path("dataset/dataset")
    output_file = Path("dataset/processed/snapshots.csv")

    valid_sessions, skipped_count = load_json_files(input_folder)

    all_snapshots: List[Dict[str, Any]] = []
    for session in valid_sessions:
        session_snapshots = process_session(session)
        all_snapshots.extend(session_snapshots)

    saved_path = save_dataframe(all_snapshots, output_file)

    # Print requested output summary
    print("\n--- Processing Summary ---")
    print(f"Number of JSON files processed : {len(valid_sessions)}")
    print(f"Number skipped                : {skipped_count}")
    print(f"Number of snapshots generated : {len(all_snapshots)}")
    print(f"CSV save location             : {saved_path.resolve()}")


if __name__ == "__main__":
    main()
