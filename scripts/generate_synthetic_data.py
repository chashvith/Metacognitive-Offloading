"""
generate_synthetic_data.py
==========================
Generates a BALANCED synthetic dataset for ML training.

5-Level Schema (matches team benchmark):
  Level 0 = No Hint needed
  Level 1 = Concept Hint
  Level 2 = Guided Hint
  Level 3 = Pseudocode
  Level 4 = Full Solution

Generates ~1000 sessions, ~200 per class, with realistic
feature distributions that differ meaningfully across levels.
"""

import os
import json
import random
import uuid
import math
from datetime import datetime, timedelta

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dataset')
os.makedirs(DATASET_DIR, exist_ok=True)

PROBLEMS = [
    {"name": "Two Sum", "difficulty": "Easy"},
    {"name": "Reverse String", "difficulty": "Easy"},
    {"name": "Binary Search", "difficulty": "Easy"},
    {"name": "Valid Parentheses", "difficulty": "Easy"},
    {"name": "Merge Sorted Array", "difficulty": "Easy"},
    {"name": "Palindrome Number", "difficulty": "Easy"},
    {"name": "Remove Duplicates", "difficulty": "Easy"},
    {"name": "Add Two Numbers", "difficulty": "Medium"},
    {"name": "Longest Substring", "difficulty": "Medium"},
    {"name": "Container With Most Water", "difficulty": "Medium"},
    {"name": "Three Sum", "difficulty": "Medium"},
    {"name": "LRU Cache", "difficulty": "Medium"},
    {"name": "Group Anagrams", "difficulty": "Medium"},
    {"name": "Merge Intervals", "difficulty": "Medium"},
    {"name": "Merge k Sorted Lists", "difficulty": "Hard"},
    {"name": "Median of Two Sorted Arrays", "difficulty": "Hard"},
    {"name": "Trapping Rain Water", "difficulty": "Hard"},
    {"name": "N-Queens", "difficulty": "Hard"},
]

LANGUAGES = ["cpp", "python", "java", "javascript", "go", "csharp"]

# ---------------------------------------------------------------
# Profile configs per hint level
# Each profile defines (mean, std) for key features so that
# the model can learn meaningful separating boundaries.
# ---------------------------------------------------------------
PROFILES = {
    # Level 0: Strong student, solves independently
    0: {
        "time_spent":       (240, 150),    # much more variance
        "chars_typed":      (280, 100),
        "chars_deleted":    (25, 25),
        "pause_count":      (2, 2),
        "pause_duration":   (12, 10),
        "compile_attempts": (2, 2),
        "compile_errors":   (0.3, 0.8),
        "successful_runs":  (2, 2),
        "runtime_errors":   (0.2, 0.6),
        "file_saves":       (4, 3),
        "idle_time":        (20, 20),
        "same_error_peak":  (0, 0.5),
    },
    # Level 1: Needs a concept hint (light struggle)
    1: {
        "time_spent":       (420, 200),
        "chars_typed":      (320, 120),
        "chars_deleted":    (65, 40),
        "pause_count":      (5, 4),
        "pause_duration":   (45, 30),
        "compile_attempts": (4, 3),
        "compile_errors":   (1.5, 1.5),
        "successful_runs":  (2, 2),
        "runtime_errors":   (0.8, 1.0),
        "file_saves":       (6, 4),
        "idle_time":        (50, 40),
        "same_error_peak":  (1, 1),
    },
    # Level 2: Needs guided hint (moderate struggle)
    2: {
        "time_spent":       (660, 250),
        "chars_typed":      (380, 150),
        "chars_deleted":    (130, 70),
        "pause_count":      (9, 5),
        "pause_duration":   (100, 60),
        "compile_attempts": (7, 4),
        "compile_errors":   (3, 2.5),
        "successful_runs":  (2, 2),
        "runtime_errors":   (2, 1.5),
        "file_saves":       (9, 5),
        "idle_time":        (90, 50),
        "same_error_peak":  (2, 1.5),
    },
    # Level 3: Needs pseudocode (heavy struggle)
    3: {
        "time_spent":       (960, 300),
        "chars_typed":      (420, 180),
        "chars_deleted":    (210, 100),
        "pause_count":      (14, 6),
        "pause_duration":   (200, 90),
        "compile_attempts": (11, 6),
        "compile_errors":   (5, 3.5),
        "successful_runs":  (1, 1.5),
        "runtime_errors":   (3, 2.5),
        "file_saves":       (13, 7),
        "idle_time":        (150, 70),
        "same_error_peak":  (3, 2),
    },
    # Level 4: Needs full solution (gave up / extreme struggle)
    4: {
        "time_spent":       (1320, 400),
        "chars_typed":      (480, 220),
        "chars_deleted":    (320, 140),
        "pause_count":      (20, 8),
        "pause_duration":   (350, 150),
        "compile_attempts": (15, 8),
        "compile_errors":   (8, 5),
        "successful_runs":  (0.5, 1.0),
        "runtime_errors":   (5, 3.5),
        "file_saves":       (18, 9),
        "idle_time":        (250, 100),
        "same_error_peak":  (4, 2.5),
    },
}

STATUS_MAP = {
    0: "Solved",
    1: "Solved_With_Concept",
    2: "Solved_With_Guided",
    3: "Solved_With_Pseudocode",
    4: "Solved_With_Solution",
}

REASON_MAP = {
    0: "Solved independently",
    1: "Needed concept hint",
    2: "Needed guided hint",
    3: "Needed pseudocode",
    4: "Needed full solution",
}


def sample_positive(mean, std):
    """Sample from normal distribution, clamp to >= 0."""
    return max(0, random.gauss(mean, std))


def sample_int(mean, std):
    """Sample integer from normal distribution, clamp to >= 0."""
    return max(0, round(random.gauss(mean, std)))


def generate_struggle_scores(time_spent, level):
    """Generate realistic struggle score timeline based on hint level."""
    scores = []
    n_points = min(15, max(3, time_spent // 40))
    current = 0.05 + level * 0.08  # higher levels start with higher baseline

    triggers = ["typed", "deleted", "pause_detected", "compile_error",
                "compile_success", "runtime_error", "successful_run"]

    for t in sorted(random.sample(range(5, max(6, time_spent - 5)), min(n_points, max(1, time_spent - 10)))):
        trigger = random.choice(triggers)

        if trigger in ("compile_error", "runtime_error"):
            current = min(1.0, current + random.uniform(0.08, 0.25))
        elif trigger == "pause_detected":
            current = min(1.0, current + random.uniform(0.03, 0.12))
        elif trigger in ("compile_success", "successful_run"):
            current = max(0.0, current - random.uniform(0.02, 0.10))
        else:
            delta = random.uniform(-0.05, 0.05)
            current = max(0.0, min(1.0, current + delta))

        # Higher levels trend upward
        current += level * 0.005

        scores.append({
            "time": t,
            "score": round(min(1.0, max(0.0, current)), 3),
            "trigger": trigger,
        })

    return scores


def generate_timeline(time_spent, level, compile_errors, runtime_errors,
                      successful_runs, hints_req):
    """Generate a realistic chronological event timeline."""
    timeline = [{"time": 0, "event": "problem_started", "source": "manual"}]

    num_events = random.randint(8, 25)
    event_times = sorted(random.sample(
        range(2, max(3, time_spent - 2)),
        min(num_events, max(1, time_spent - 4))
    ))

    for et in event_times:
        choice = random.choices(
            ["typed", "deleted", "file_saved", "compile_success",
             "compile_error", "successful_run", "runtime_error", "pause_detected"],
            weights=[0.28, 0.12, 0.18, 0.10, 0.10, 0.07, 0.06, 0.09],
            k=1
        )[0]

        meta = None
        if choice == "typed":
            meta = {"chars": random.randint(3, 50)}
        elif choice == "deleted":
            meta = {"chars": random.randint(1, 20)}
        elif choice == "compile_error":
            meta = {"error": random.choice([
                "expected ';' before '}' token",
                "undefined reference to 'main'",
                "cannot find symbol",
                "SyntaxError: unexpected token",
                "indentation error",
            ])}
        elif choice == "runtime_error":
            meta = {"error": random.choice([
                "segmentation fault",
                "floating point exception",
                "ArrayIndexOutOfBoundsException",
                "TypeError: cannot read property",
                "stack overflow",
            ])}
        elif choice == "pause_detected":
            meta = {"duration_ms": random.randint(5000, 25000),
                    "pause_number": random.randint(1, 20)}

        evt = {"time": et, "event": choice, "source": "automatic"}
        if meta:
            evt["meta"] = meta
        timeline.append(evt)

    # Add hint events at logical progression points
    hint_names = ["concept_hint", "guided_hint", "pseudocode", "solution"]
    for i in range(min(level, 4)):
        frac = 0.25 + i * 0.15  # hints appear progressively later
        ht = int(time_spent * frac) + random.randint(-10, 10)
        ht = max(5, min(time_spent - 3, ht))
        timeline.append({
            "time": ht,
            "event": f"{hint_names[i]}_requested",
            "source": "manual",
        })

    timeline.sort(key=lambda x: x["time"])

    # End event
    end_event = "problem_solved" if level <= 3 else "problem_abandoned"
    timeline.append({"time": time_spent, "event": end_event, "source": "manual"})

    return timeline


def generate_session(index, level):
    """Generate one synthetic session for the given hint level."""
    p = PROFILES[level]
    prob = random.choice(PROBLEMS)
    lang = random.choice(LANGUAGES)

    # Sample features from level-specific distributions
    time_spent      = sample_int(*p["time_spent"])
    time_spent      = max(30, time_spent)  # minimum 30 seconds
    chars_typed     = sample_int(*p["chars_typed"])
    chars_deleted   = sample_int(*p["chars_deleted"])
    pause_count     = sample_int(*p["pause_count"])
    pause_duration  = sample_int(*p["pause_duration"])
    compile_attempts = sample_int(*p["compile_attempts"])
    compile_errors  = min(sample_int(*p["compile_errors"]), compile_attempts)
    successful_runs = sample_int(*p["successful_runs"])
    runtime_errors  = sample_int(*p["runtime_errors"])
    file_saves      = sample_int(*p["file_saves"])
    idle_time       = sample_int(*p["idle_time"])
    same_error_peak = sample_int(*p["same_error_peak"])

    # Derived
    deletion_ratio = round(chars_deleted / max(chars_typed, 1), 4)
    active_secs = max(time_spent - idle_time, 1)
    typing_speed = round(chars_typed / (active_secs / 60), 1)
    idle_ratio = round(idle_time / max(time_spent, 1), 4)
    hesitation_index = round(pause_duration / max(time_spent, 1), 6)
    editing_intensity = round(chars_deleted / max(chars_typed, 1), 6)
    compile_failure_rate = round(compile_errors / max(compile_attempts, 1), 6)
    avg_pause = round(pause_duration / max(pause_count, 1), 2)

    # Hints requested mapping
    hints_req = {
        "concept": 1 if level >= 1 else 0,
        "guided":  1 if level >= 2 else 0,
        "pseudocode": 1 if level >= 3 else 0,
        "solution": 1 if level >= 4 else 0,
    }
    hints_used = sum(hints_req.values())
    hints_available = 4
    help_dependency = round(hints_used / hints_available, 6)
    independent_fix_rate = round(1 - (hints_used / hints_available), 2)

    # Timestamps
    end_dt = datetime.utcnow() - timedelta(
        days=random.randint(0, 60),
        seconds=random.randint(0, 86400)
    )
    start_dt = end_dt - timedelta(seconds=time_spent)

    # Struggle scores
    struggle_scores = generate_struggle_scores(time_spent, level)

    # Timeline
    timeline = generate_timeline(
        time_spent, level, compile_errors, runtime_errors,
        successful_runs, hints_req
    )

    session = {
        "schema_version": "1.0",
        "session_id": str(uuid.uuid4()),
        "problem_name": prob["name"],
        "difficulty": prob["difficulty"],
        "language": lang,
        "student_id": f"student_{random.randint(100, 999)}",
        "start_time": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "end_time": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "problem": {
            "topic": "",
            "subtopic": "",
            "difficulty": prob["difficulty"],
            "estimated_minutes": None,
        },
        "outcome": {
            "final_status": STATUS_MAP[level],
            "minimum_help_required": level,
            "reason": REASON_MAP[level],
        },
        "derived_metrics": {
            "hesitation_index": hesitation_index,
            "editing_intensity": editing_intensity,
            "help_dependency_score": help_dependency,
            "compile_failure_rate": compile_failure_rate,
            "average_pause_duration": avg_pause,
        },
        "time_spent": time_spent,
        "idle_time": idle_time,
        "idle_ratio": idle_ratio,
        "characters_typed": chars_typed,
        "characters_deleted": chars_deleted,
        "deletion_ratio": deletion_ratio,
        "typing_speed": typing_speed,
        "pause_count": pause_count,
        "pause_duration": pause_duration,
        "file_save_count": file_saves,
        "file_open_count": random.randint(1, 3),
        "compile_attempts": compile_attempts,
        "compile_errors": compile_errors,
        "successful_runs": successful_runs,
        "runtime_errors": runtime_errors,
        "auto_compile_attempts": max(0, compile_attempts - random.randint(0, 2)),
        "hints_requested": hints_req,
        "hints_available": hints_available,
        "hints_used": hints_used,
        "independent_fix_rate": independent_fix_rate,
        "same_error_peak": same_error_peak,
        "struggle_scores": struggle_scores,
        "counterexample_shown_count": 0,
        "time_to_resolution_after_counterexample": None,
        "status": STATUS_MAP[level],
        "timeline": timeline,
    }

    dt_str = start_dt.strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(DATASET_DIR, f"session_{dt_str}_{index}.json")
    with open(filepath, "w") as f:
        json.dump(session, f, indent=2)


if __name__ == "__main__":
    TOTAL = 10000
    
    # Realistic distribution matching the screenshot
    DISTRIBUTION = {
        0: 0.42,  # 42% No Hint
        1: 0.37,  # 37% Concept Hint
        2: 0.17,  # 17% Guided Hint
        3: 0.03,  # 3% Pseudocode
        4: 0.01,  # 1% Full Solution
    }

    print(f"Generating {TOTAL} synthetic sessions with a REALISTIC distribution...")

    idx = 0
    counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    
    # Generate based on weights
    levels_to_generate = random.choices(
        list(DISTRIBUTION.keys()),
        weights=list(DISTRIBUTION.values()),
        k=TOTAL
    )

    for level in levels_to_generate:
        generate_session(idx, level)
        counts[level] += 1
        idx += 1

    print(f"Done! {TOTAL} files saved to dataset/")
    print()
    print("Hint Label Distribution:")
    names = ["No Hint", "Concept Hint", "Guided Hint", "Pseudocode", "Full Solution"]
    for lvl in range(5):
        pct = (counts[lvl] / TOTAL) * 100
        print(f"  Level {lvl} ({names[lvl]}): {counts[lvl]} sessions ({pct:.1f}%)")
