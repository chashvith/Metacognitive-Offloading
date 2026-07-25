import os
import json
import random
import uuid
from datetime import datetime, timedelta

# Create dataset directory if it doesn't exist
DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dataset')
os.makedirs(DATASET_DIR, exist_ok=True)

# Problem list
PROBLEMS = [
    {"name": "Two Sum", "difficulty": "Easy"},
    {"name": "Reverse String", "difficulty": "Easy"},
    {"name": "Binary Search", "difficulty": "Easy"},
    {"name": "Valid Parentheses", "difficulty": "Easy"},
    {"name": "Merge Sorted Array", "difficulty": "Easy"},
    {"name": "Add Two Numbers", "difficulty": "Medium"},
    {"name": "Longest Substring Without Repeating Chars", "difficulty": "Medium"},
    {"name": "Container With Most Water", "difficulty": "Medium"},
    {"name": "Three Sum", "difficulty": "Medium"},
    {"name": "LRU Cache", "difficulty": "Medium"},
    {"name": "Merge k Sorted Lists", "difficulty": "Hard"},
    {"name": "Median of Two Sorted Arrays", "difficulty": "Hard"},
    {"name": "Trapping Rain Water", "difficulty": "Hard"}
]

LANGUAGES = ["cpp", "python", "java", "javascript"]

def generate_session(index):
    prob = random.choice(PROBLEMS)
    lang = random.choice(LANGUAGES)
    student_id = f"student_{random.randint(100, 999)}"
    
    # Decide label (minimum help required):
    # 0 = Independent, 1 = Hint1, 2 = Hint2, 3 = Concept, 4 = Pseudocode, 5 = Solution, 6 = Couldn't solve
    min_help = random.choices(
        population=[0, 1, 2, 3, 4, 5, 6],
        weights=[0.30, 0.15, 0.12, 0.10, 0.13, 0.12, 0.08],
        k=1
    )[0]
    
    # Base variables based on help level (to create distinct patterns)
    if min_help == 0:
        time_spent = random.randint(180, 600)  # 3 to 10 mins
        compile_attempts = random.randint(1, 4)
        compile_errors = random.randint(0, 1)
        successful_runs = random.randint(1, 3)
        runtime_errors = random.randint(0, 1)
        chars_typed = random.randint(120, 350)
        chars_deleted = random.randint(10, 50)
        pause_count = random.randint(2, 6)
        total_pause_dur = random.randint(15, 60)
        hints_used = 0
        final_status = "Solved"
        reason = "Solved independently"
    elif min_help in [1, 2]:
        time_spent = random.randint(400, 1000) # 6 to 16 mins
        compile_attempts = random.randint(3, 8)
        compile_errors = random.randint(1, 3)
        successful_runs = random.randint(1, 3)
        runtime_errors = random.randint(0, 2)
        chars_typed = random.randint(150, 450)
        chars_deleted = random.randint(30, 120)
        pause_count = random.randint(5, 12)
        total_pause_dur = random.randint(60, 200)
        hints_used = min_help
        final_status = f"Solved_With_Hint{min_help}"
        reason = f"Solved after Hint {min_help}"
    elif min_help in [3, 4]:
        time_spent = random.randint(600, 1500) # 10 to 25 mins
        compile_attempts = random.randint(6, 12)
        compile_errors = random.randint(2, 6)
        successful_runs = random.randint(1, 4)
        runtime_errors = random.randint(1, 4)
        chars_typed = random.randint(200, 600)
        chars_deleted = random.randint(80, 250)
        pause_count = random.randint(10, 20)
        total_pause_dur = random.randint(150, 400)
        hints_used = min_help
        final_status = "Solved_With_Concept" if min_help == 3 else "Solved_With_Pseudocode"
        reason = f"Solved after {'Concept' if min_help == 3 else 'Pseudocode'}"
    else: # 5 or 6
        time_spent = random.randint(800, 1800) # 13 to 30 mins
        compile_attempts = random.randint(8, 18)
        compile_errors = random.randint(4, 10)
        successful_runs = random.randint(0, 2)
        runtime_errors = random.randint(2, 6)
        chars_typed = random.randint(250, 700)
        chars_deleted = random.randint(150, 450)
        pause_count = random.randint(15, 30)
        total_pause_dur = random.randint(250, 700)
        hints_used = 5 if min_help == 5 else 3
        if min_help == 5:
            final_status = "Solved_With_Solution"
            reason = "Solved after Full Solution"
        else:
            final_status = random.choice(["Could_Not_Solve", "Stopped_Time", "Stopped_Other"])
            reason = "Couldn't solve" if final_status == "Could_Not_Solve" else "Stopped because of time"
            
    # Calculate minor variables
    idle_time = total_pause_dur + random.randint(10, 50)
    deletion_ratio = chars_deleted / chars_typed if chars_typed > 0 else 0.0
    active_mins = max((time_spent - idle_time) / 60, 0.1)
    typing_speed = (chars_typed / active_mins) if active_mins > 0 else 0.0
    file_save_count = compile_attempts + random.randint(1, 5)
    file_open_count = random.randint(1, 3)
    auto_compile_attempts = max(0, compile_attempts - random.randint(1, 3))
    
    # Hints mapping
    hints_req = {
        "hint1": 1 if min_help >= 1 else 0,
        "hint2": 1 if min_help >= 2 else 0,
        "concept": 1 if min_help >= 3 else 0,
        "pseudocode": 1 if min_help >= 4 else 0,
        "solution": 1 if min_help >= 5 else 0
    }
    
    # Timestamps
    end_dt = datetime.utcnow() - timedelta(days=random.randint(0, 30), seconds=random.randint(0, 86400))
    start_dt = end_dt - timedelta(seconds=time_spent)
    
    # Struggle score array simulation
    struggle_scores = []
    current_score = 0.1
    for t in sorted(random.sample(range(5, time_spent - 5), min(10, time_spent // 30))):
        trigger = random.choice(["pause_detected", "compile_error", "runtime_error", "typed", "deleted"])
        if trigger in ["compile_error", "runtime_error"]:
            current_score = min(1.0, current_score + random.uniform(0.15, 0.35))
        elif trigger == "pause_detected":
            current_score = min(1.0, current_score + random.uniform(0.05, 0.15))
        else:
            current_score = max(0.0, current_score - random.uniform(0.05, 0.15))
            
        struggle_scores.append({
            "time": t,
            "score": round(current_score, 3),
            "trigger": trigger
        })
        
    # Generate chronological timeline
    timeline = []
    timeline.append({"time": 0, "event": "problem_started", "source": "manual"})
    
    # Insert typing/deleting/saving/error blocks
    num_events = random.randint(10, 25)
    event_times = sorted(random.sample(range(2, time_spent - 2), num_events))
    
    for et in event_times:
        choice = random.choices(
            ["typed", "deleted", "file_saved", "compile_success", "compile_error", "successful_run", "runtime_error"],
            weights=[0.30, 0.15, 0.20, 0.10, 0.10, 0.08, 0.07],
            k=1
        )[0]
        
        source = "automatic" if choice in ["typed", "deleted", "file_saved", "compile_success", "compile_error", "successful_run", "runtime_error"] else "manual"
        
        meta = None
        if choice == "typed":
            meta = {"chars": random.randint(5, 45)}
        elif choice == "deleted":
            meta = {"chars": random.randint(2, 15)}
        elif choice == "compile_error":
            meta = {"error": "compound compile error detected from output"}
        elif choice == "runtime_error":
            meta = {"error": "floating point exception"}
            
        evt = {"time": et, "event": choice, "source": source}
        if meta:
            evt["meta"] = meta
        timeline.append(evt)
        
    # Add hint events at logical times
    hint_keys = ["hint1", "hint2", "concept", "pseudocode", "solution"]
    for idx, key in enumerate(hint_keys):
        if hints_req[key] == 1:
            hint_time = int(time_spent * (0.3 + (idx * 0.12)))
            timeline.append({
                "time": min(hint_time, time_spent - 2),
                "event": f"{key if key not in ['concept', 'solution'] else key + '_hint' if key == 'concept' else 'solution'}_requested",
                "source": "manual"
            })
            
    # Sort timeline chronologically
    timeline.sort(key=lambda x: x["time"])
    
    # End event
    timeline.append({
        "time": time_spent,
        "event": "problem_solved" if final_status.startswith("Solved") else "problem_abandoned",
        "source": "manual"
    })
    
    # Derived ML metrics
    hesitation_index = total_pause_dur / time_spent if time_spent > 0 else 0.0
    editing_intensity = chars_deleted / chars_typed if chars_typed > 0 else 0.0
    help_dependency_score = hints_used / 5.0
    compile_failure_rate = compile_errors / compile_attempts if compile_attempts > 0 else 0.0
    average_pause_duration = total_pause_dur / pause_count if pause_count > 0 else 0.0

    session_data = {
        "schema_version": "1.0",
        "session_id": str(uuid.uuid4()),
        "problem_name": prob["name"],
        "difficulty": prob["difficulty"],
        "language": lang,
        "student_id": student_id,
        "start_time": start_dt.isoformat() + "Z",
        "end_time": end_dt.isoformat() + "Z",
        "problem": {
            "topic": "",
            "subtopic": "",
            "difficulty": prob["difficulty"],
            "estimated_minutes": None
        },
        "outcome": {
            "final_status": final_status,
            "minimum_help_required": min_help,
            "reason": reason
        },
        "derived_metrics": {
            "hesitation_index": round(hesitation_index, 6),
            "editing_intensity": round(editing_intensity, 6),
            "help_dependency_score": round(help_dependency_score, 6),
            "compile_failure_rate": round(compile_failure_rate, 6),
            "average_pause_duration": round(average_pause_duration, 2)
        },
        "time_spent": time_spent,
        "idle_time": idle_time,
        "characters_typed": chars_typed,
        "characters_deleted": chars_deleted,
        "deletion_ratio": round(deletion_ratio, 4),
        "typing_speed": round(typing_speed, 1),
        "pause_count": pause_count,
        "pause_duration": total_pause_dur,
        "file_save_count": file_save_count,
        "file_open_count": file_open_count,
        "compile_attempts": compile_attempts,
        "compile_errors": compile_errors,
        "successful_runs": successful_runs,
        "runtime_errors": runtime_errors,
        "auto_compile_attempts": auto_compile_attempts,
        "hints_requested": hints_req,
        "hints_available": 5,
        "hints_used": hints_used,
        "independent_fix_rate": round(1 - (hints_used / 5), 2),
        "same_error_peak": random.randint(0, 2),
        "struggle_scores": struggle_scores,
        "counterexample_shown_count": 0,
        "time_to_resolution_after_counterexample": None,
        "status": final_status,
        "timeline": timeline
    }
    
    # Save file
    dt_str = start_dt.strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(DATASET_DIR, f"session_{dt_str}_{index}.json")
    with open(filepath, 'w') as f:
        json.dump(session_data, f, indent=2)

if __name__ == "__main__":
    NUM_SESSIONS = 300
    print(f"Generating {NUM_SESSIONS} synthetic student sessions...")
    for i in range(NUM_SESSIONS):
        generate_session(i)
    print(f"Successfully generated {NUM_SESSIONS} files inside dataset/ folder!")
