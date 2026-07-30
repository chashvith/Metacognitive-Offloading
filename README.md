<div align="center">
  <h1>🧠 Cognitive Coach</h1>
  <p><b>The Metacognitive AI Tutor for the Next Generation of Developers</b></p>
  <p>
    <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
    <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" />
    <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" />
    <img alt="Gemini" src="https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=googlebard&logoColor=white" />
    <img alt="VS Code" src="https://img.shields.io/badge/VS_Code-0078D4?style=for-the-badge&logo=visual%20studio%20code&logoColor=white" />
  </p>
</div>

<br/>

> **Cognitive Coach** is an AI-powered educational ecosystem that records how a student solves programming problems, detects cognitive overload in real-time, intervenes with pedagogical hints, and provides teachers with a dashboard to analyze the learning process.

---

## Key Features

- **Real-Time Struggle Detection**: The VS Code extension continuously calculates a `struggle_score` based on typing speed, pauses, and compilation errors. It proactively offers a hint when predefined struggle thresholds are reached.
- **Modern Dashboard for Visualizing Student Telemetry**: A web dashboard that visualizes student telemetry data, charting cognitive load over time and providing insights into problem-solving behavior.
- **Interactive Session Replay**: Teachers can watch a chronological timeline of exactly where the student paused, errored out, and succeeded, providing context to the telemetry logs.
- **AI Session Summaries**: The dashboard uses the Google Gemini LLM to analyze the student's telemetry timeline and generate a plain-English summary of their learning journey and core struggles.

---

## Project Architecture

Our solution spans across the following components:

1. **Telemetry Extension (VS Code)**
   - Gathers high-fidelity data (pauses, deletions, errors, hint requests) passively.
   - Generates a live `struggle_score` using a weighted heuristic algorithm.
   - Saves anonymized JSON datasets locally.

2. **Intelligence Backend (Python / FastAPI)**
   - Serves the Teacher Dashboard web application.
   - Interfaces with the **Google Gemini API** to generate context-aware hints and session summaries based on the student's actual code.
   - Exposes RESTful endpoints for telemetry ingestion and querying.

3. **Machine Learning Pipeline (Data Science)**
   - Uses exported JSON datasets to train a Random Forest + XGBoost predictive model.
   - Predicts the minimum level of pedagogical help a student will need based on historical behavior.

---

## Getting Started

### Prerequisites
- **Node.js** (v18+)
- **Python** (v3.10+)
- **Visual Studio Code** (v1.96+)
- **Google Gemini API Key** (Set as `GEMINI_API_KEY` in `backend/.env`)

### 1. Launch the VS Code Extension
```bash
git clone https://github.com/chashvith/Metacognitive-Offloading.git
cd Metacognitive-Offloading
npm install
npm run build
```
1. Open the repository folder in VS Code.
2. Press **F5** to launch the Extension Development Host.
3. In the new window, click the **Cognitive Coach** icon in the Activity Bar.
4. Click **Start Problem** and start coding.

### 2. Launch the Teacher Dashboard
Open a new terminal in the project root:
```bash
pip install -r backend/requirements.txt
python backend/app.py
```
Open your browser to [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html).

---

## Machine Learning Pipeline

We train our models on features derived from the student's raw keystroke timeline to understand student cognition:

| Feature | Description |
|---------|-------------|
| `time_spent` | Total session time in seconds |
| `hesitation_index` | Pause duration divided by total time |
| `compile_failure_rate` | Compilation errors per attempt |
| `typing_speed` | Keystrokes per active minute |
| `struggle_max` | The peak cognitive struggle score |
| `help_dependency` | Ratio of hints used vs hints available |

**Objective:** Predict the `minimum_help_required` (0 = Fully Independent, 6 = Could Not Solve).

To run the pipeline locally:
```bash
python scripts/generate_synthetic_data.py  # Generates 300 sessions
python scripts/train_model.py              # Trains XGBoost model
```

---

<div align="center">
  <i>Built for the Hackathon by a team passionate about AI in Education.</i>
</div>
