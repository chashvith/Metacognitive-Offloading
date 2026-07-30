<div align="center">
  <h1>🧠 Cognitive Coach</h1>
  <p><b>The Metacognitive AI Tutor</b></p>
  <p>
    <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
    <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" />
    <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" />
    <img alt="Gemini" src="https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=googlebard&logoColor=white" />
  </p>
</div>

An AI-powered educational ecosystem that silently records how a student solves programming problems, detects cognitive overload in real-time, proactively intervenes with hints, and provides teachers with a stunning dashboard to replay and analyze the learning process.

---

## 🚀 The "Wow" Features (Hackathon Highlights)

1. **"Mind-Reading" Proactive Intervention**: The VS Code extension isn't just passive. It continuously calculates a real-time `struggle_score`. If a student gets stuck, it proactively pops up and offers a hint right when they need it most!
2. **Teacher Analytics Dashboard**: A gorgeous, dark-mode, glassmorphic web dashboard that visualizes student telemetry data, charting their cognitive load over time.
3. **Cinematic Session Replay**: Teachers can hit "Replay" to watch a dramatic chronological timeline of exactly where the student paused, errored out, and succeeded, without having to read a single line of raw logs.
4. **AI Session Summaries**: The dashboard uses the Google Gemini LLM to analyze the student's entire telemetry timeline and instantly generate a 3-sentence plain-English summary of their learning journey.

---

## 🧠 Project Architecture

The project consists of three main components:

1. **The Telemetry Extension (VS Code)**
   - Silently gathers data (pauses, deletions, errors, hint requests).
   - Generates a real-time `struggle_score` using a weighted algorithm.
   - Saves rich JSON datasets locally.
2. **The Backend API (Python / FastAPI)**
   - Serves the Teacher Dashboard web app.
   - Generates AI insights using Google Gemini SDK.
   - Exposes REST APIs for fetching and parsing student session data.
3. **The ML Training Pipeline**
   - Uses the exported JSON datasets to train a Random Forest + XGBoost model.
   - Predicts the *minimum level of help* a student will need in the future.

---

## 🛠️ Getting Started / Live Demo Setup

### Prerequisites
- **Node.js** v18+ 
- **Python 3.10+** 
- **Visual Studio Code** v1.96+
- **Google Gemini API Key** (Set as `GEMINI_API_KEY` in `backend/.env`)

### 1. Start the VS Code Extension
```bash
git clone https://github.com/chashvith/Metacognitive-Offloading.git
cd Metacognitive-Offloading/cognitive-coach
npm install
npm run build
```
Open the folder in VS Code, press **F5** to launch the Extension Host. Click the **Cognitive Coach** icon in the sidebar and start coding!

### 2. Start the Teacher Dashboard (Backend)
Open a new terminal in the project root:
```bash
pip install fastapi uvicorn google-genai
python backend/app.py
```
Open your browser to `http://localhost:8000/static/index.html` to view the Teacher Dashboard.

*(Pro Tip: Search for "PITCH" in the dashboard to see the pre-loaded perfect demo session!)*

---

## 📊 How the ML Pipeline Works

We train on rich features derived from the telemetry timeline:
| Feature | Description |
|---------|-------------|
| `time_spent` | Total session time (seconds) |
| `idle_ratio` | Fraction of time idle |
| `deletion_ratio` | chars deleted / chars typed |
| `typing_speed` | chars per active minute |
| `hesitation_index` | pause_duration / time_spent |
| `compile_failure_rate` | errors / attempts |
| `help_dependency` | hints_used / hints_available |
| `struggle_max` | Peak struggle score |

**Target ML Label:** `minimum_help_required` (0 = Independent, 6 = Could Not Solve).

To run the pipeline yourself:
```bash
python scripts/generate_synthetic_data.py  # Generates 300 sessions
python scripts/train_model.py              # Trains XGBoost model
```

---

*Built with ❤️ for the Hackathon.*
