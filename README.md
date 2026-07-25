# Cognitive Coach — Telemetry Collection Extension

An AI-powered educational coding assistant that records how a student solves a programming problem, session by session, and saves each session as a local JSON file for ML training.

---

## Project Overview

The goal of this extension is to silently gather data about the coding process (pauses, deletions, errors, hint requests). By aggregating these events into a timeline, we train a machine learning model to detect *when* a student is struggling and predict the **minimum level of help** they will need.

**Target label for ML:** `minimum_help_required` (0–6)
| Value | Meaning |
|-------|---------|
| 0 | Solved independently |
| 1 | Needed Hint 1 |
| 2 | Needed Hint 2 |
| 3 | Needed Concept explanation |
| 4 | Needed Pseudocode |
| 5 | Needed Full Solution |
| 6 | Could Not Solve |

---

## Features

- **Automatic Error Detection**: Detects compile errors and runtime errors directly from terminal output — supports C++, Python, Java, JavaScript, Go, C#, Rust, Ruby, PHP, Swift, Kotlin, Dart and more.
- **Local JSON Dataset**: Every session writes directly to the local `dataset/` folder with a standardized ML-ready schema.
- **Outcome QuickPick**: When ending a session, a dialog asks "How did this session end?" — this sets the `minimum_help_required` label automatically.
- **Derived ML Metrics**: Automatically computes `hesitation_index`, `editing_intensity`, `help_dependency_score`, `compile_failure_rate`, and `average_pause_duration` before export.
- **Unified Event Timeline**: Every event is tagged with `"source": "automatic"` or `"source": "manual"` for full traceability.
- **Real-Time Struggle Score**: Computes a struggle score per-event based on deletion ratio, pause frequency, compile error rate, and hint usage.
- **Dataset Export**: One-click "Export Dataset" button that zips all sessions into a single `.zip` file.
- **Crash Recovery**: Periodically saves an in-progress state file. Restores if VS Code crashes.
- **Synthetic Data Generator**: `scripts/generate_synthetic_data.py` generates 300+ realistic sessions for ML bootstrapping.
- **ML Training Pipeline**: `scripts/train_model.py` trains a Random Forest + XGBoost model and saves the best one.

---

## Folder Structure

```
cognitive-coach/
├── dataset/                  <- All JSON session data goes here
│   └── .gitkeep
├── model/                    <- Trained ML model (.pkl) saved here
├── scripts/
│   ├── generate_synthetic_data.py   <- Generate 300 synthetic sessions
│   └── train_model.py               <- Train Random Forest + XGBoost
├── media/                    <- Icons and webview CSS
├── src/
│   ├── commands/             <- VS Code command registrations
│   ├── export/               <- ZIP export logic
│   ├── session/              <- Session lifecycle and file I/O
│   ├── telemetry/            <- VS Code listeners + metrics calculation
│   ├── utils/                <- UUID generator
│   ├── views/                <- Webview UI
│   ├── constants.ts          <- Tunable thresholds
│   ├── extension.ts          <- Entry point
│   └── types.ts              <- TypeScript interfaces & ML schema
├── package.json
├── README.md
└── .gitignore
```

---

## Getting Started

### Prerequisites
- **Node.js** v18+ — [Download](https://nodejs.org/)
- **Visual Studio Code** v1.96+ — [Download](https://code.visualstudio.com/)
- **Python 3.10+** (for ML scripts only) — [Download](https://python.org/)

### Installation

```bash
git clone https://github.com/chashvith/Metacognitive-Offloading.git
cd Metacognitive-Offloading/cognitive-coach
npm install
npm run build
```

### Running the Extension

1. Open the `cognitive-coach` folder in VS Code.
2. Press **F5** to launch the Extension Development Host.
3. In the new window, open any project folder.
4. Click the **Cognitive Coach icon** in the left Activity Bar.
5. Click **Start Problem**, fill in the prompts, and start coding!

---

## How Data Collection Works

```
Student types in editor
        │
        ▼
onDidChangeTextDocument (every keystroke, no debounce)
        │
        ├──> chars_typed / chars_deleted updated
        ├──> Pause detection: gap > 5s → pause event + struggle score
        └──> Typing batched for timeline

Student runs code in terminal
        │
        ▼
Shell Integration / Task hooks detect exit code
        │
        ├──> Exit 0  → compile_success or successful_run
        └──> Exit ≠0 → compile_error or runtime_error

Student clicks "End Problem"
        │
        ▼
QuickPick: "How did this session end?"
        │
        └──> Sets status + minimum_help_required label
             Computes derived_metrics
             Sanitizes file paths
             Saves JSON to dataset/
```

---

## ML Training

### Step 1: Generate Synthetic Data (optional)
```bash
python scripts/generate_synthetic_data.py
# Generates 300 session JSONs in dataset/
```

### Step 2: Train the Model
```bash
pip install scikit-learn xgboost pandas numpy
python scripts/train_model.py
# Trains Random Forest + XGBoost
# Saves best model to model/cognitive_coach_model.pkl
# Prints accuracy, classification report, feature importances
```

### ML Features (X)
| Feature | Description |
|---------|-------------|
| `time_spent` | Total session time (seconds) |
| `idle_ratio` | Fraction of time idle |
| `deletion_ratio` | chars deleted / chars typed |
| `typing_speed` | chars per active minute |
| `pause_count` | Number of detected pauses |
| `hesitation_index` | pause_duration / time_spent |
| `compile_failure_rate` | errors / attempts |
| `runtime_errors` | Total runtime errors |
| `hints_used` | Total hints clicked |
| `help_dependency` | hints_used / hints_available |
| `struggle_max` | Peak struggle score |
| `struggle_trend` | Final score − initial score |
| `editing_intensity` | chars_deleted / chars_typed |
| `difficulty` | Easy=0 / Medium=1 / Hard=2 |

### ML Label (Y)
`minimum_help_required` — integer 0 to 6

---

## Installing the Extension (for testers)

Share the `cognitive-coach-0.0.1.vsix` file. Recipients install it by:
1. Open VS Code → Extensions (`Ctrl+Shift+X`)
2. Click `...` menu → **Install from VSIX...**
3. Select the `.vsix` file
4. Reload VS Code

Their `dataset/` session files can be collected, zipped, and sent back for training.
