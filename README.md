<div align="center">
  <img src="https://raw.githubusercontent.com/chashvith/Metacognitive-Offloading/main/media/logo.png" alt="Cognitive Coach Logo" width="120" />
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

> **Cognitive Coach** is an AI-powered educational ecosystem that silently records how a student solves programming problems, detects cognitive overload in real-time, proactively intervenes with pedagogical hints, and provides teachers with a stunning dashboard to replay and analyze the learning process.

---

## ✨ The "Wow" Features (Hackathon Highlights)

💡 **"Mind-Reading" Proactive Intervention**  
The VS Code extension isn't just a passive tracker. It continuously calculates a real-time `struggle_score` based on typing speed, pauses, and compilation errors. If a student gets stuck, it proactively offers a hint *right when they need it most*.

📊 **Teacher Analytics Dashboard**  
A gorgeous, dark-mode, glassmorphic web dashboard that visualizes student telemetry data, charting their cognitive load over time and providing deep insights into their problem-solving behavior.

🎬 **Cinematic Session Replay**  
Teachers can hit "Replay" to watch a chronological timeline of exactly where the student paused, errored out, and succeeded, without having to read a single line of raw logs.

🤖 **AI Session Summaries**  
The dashboard uses the Google Gemini LLM to analyze the student's entire telemetry timeline and instantly generate a 3-sentence plain-English summary of their learning journey and core struggles.

---

## 🏗️ Project Architecture

Our solution spans across the entire educational stack:

1. **The Telemetry Extension (VS Code)**
   - Silently gathers rich, high-fidelity data (pauses, deletions, errors, hint requests) without interrupting the student.
   - Generates a live `struggle_score` using a weighted heuristic algorithm.
   - Saves anonymized JSON datasets locally.

2. **The Intelligence Backend (Python / FastAPI)**
   - Serves the Teacher Dashboard web application.
   - Interfaces directly with the **Google Gemini API** to generate context-aware hints and session summaries based on the student's actual code.
   - Exposes RESTful endpoints for telemetry ingestion and querying.

3. **The ML Training Pipeline (Data Science)**
   - Uses exported JSON datasets to train a Random Forest + XGBoost predictive model.
   - Predicts the *minimum level of pedagogical help* a student will need based on their historical behavior.

---

## 🚀 Getting Started / Live Demo Setup

### Prerequisites
- **Node.js** (v18+)
- **Python** (v3.10+)
- **Visual Studio Code** (v1.96+)
- **Google Gemini API Key** (Set as `GEMINI_API_KEY` in `backend/.env`)

### 1. Launch the VS Code Extension (The Student Environment)
```bash
git clone https://github.com/chashvith/Metacognitive-Offloading.git
cd Metacognitive-Offloading
npm install
npm run build
```
1. Open the repository folder in VS Code.
2. Press **F5** to launch the Extension Development Host.
3. In the new window, click the **Cognitive Coach (Brain)** icon in the Activity Bar.
4. Click **Start Problem** and start coding!

### 2. Launch the Teacher Dashboard (The Instructor Environment)
Open a new terminal in the project root:
```bash
pip install -r backend/requirements.txt  # Or install fastapi, uvicorn, google-genai manually
python backend/app.py
```
Open your browser to [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html).

*(Pro Tip: Search for "PITCH" in the dashboard to see our pre-loaded perfect demo session!)*

---

## 📈 Machine Learning Pipeline Deep Dive

We believe data is the key to understanding student cognition. We train our models on rich features derived from the student's raw keystroke timeline:

| Feature | Description |
|---------|-------------|
| `time_spent` | Total session time in seconds |
| `hesitation_index` | Pause duration divided by total time |
| `compile_failure_rate` | Compilation errors per attempt |
| `typing_speed` | Keystrokes per active minute |
| `struggle_max` | The peak cognitive struggle score |
| `help_dependency` | Ratio of hints used vs hints available |

**The Goal:** Predict the `minimum_help_required` (0 = Fully Independent, 6 = Could Not Solve).

To reproduce our training:
```bash
python scripts/generate_synthetic_data.py  # Generates 300 sessions
python scripts/train_model.py              # Trains XGBoost model
```

---

<div align="center">
  <i>Built with ❤️ for the Hackathon by a team passionate about AI in Education.</i>
</div>
