<div align="center">
  <h1>🧠 Cognitive Coach</h1>
  <p><b>The Proactive, ML-Driven Pedagogy Engine for Developers</b></p>
  <p>
    <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
    <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" />
    <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" />
    <img alt="Groq" src="https://img.shields.io/badge/Groq-f55036?style=for-the-badge&logo=groq&logoColor=white" />
    <img alt="VS Code" src="https://img.shields.io/badge/VS_Code-0078D4?style=for-the-badge&logo=visual%20studio%20code&logoColor=white" />
  </p>
</div>

<br/>

> Most AI coding assistants just write the code for you. **Cognitive Coach** teaches you how to write it. It is an advanced AI-powered pedagogical ecosystem that tracks keystroke dynamics, predicts cognitive overload using real-time machine learning, and intervenes with context-aware Socratic hints via the ultra-fast Groq API.

---

## 🌟 What Makes Cognitive Coach Special?

- **🔮 Predictive "Struggle" ML Engine**: The VS Code extension silently monitors psychometrics (hesitation index, editing intensity, compile failures). If your calculated `struggle_score` crosses a critical threshold, the AI proactively intervenes before you even ask for help.
- **⚡ Lightning-Fast Llama 3 on Groq**: We migrated our entire backend to Groq for sub-second, structured JSON LLM generations, allowing real-time Socratic tutoring without disrupting the developer's flow.
- **🛡️ Multi-modal Context Building**: The AI doesn't just see your code; it sees your exact timeline. We feed the LLM a structured snapshot of your behavioral telemetry, recent errors, and hesitation patterns so it acts like a world-class teacher, not an auto-completer.
- **🎨 Glassmorphism VS Code Native UI**: We built a stunning, custom sidebar right inside VS Code featuring translucent glassmorphism, animated gradients, and interactive components like the **Edge Case Detector (Counterexamples)**.
- **📊 Teacher Telemetry Dashboard**: A full React/FastAPI local dashboard that visualizes student psychometrics and learning journeys for educators.

---

## 🏗️ Project Architecture

Our solution is a robust, multi-tier ecosystem:

1. **Telemetry Engine (VS Code Extension)**
   - Passively tracks high-fidelity data (pauses, deletions, compile errors).
   - Renders a native, dynamic React-style webview UI inside the editor.
   - Calculates real-time ML heuristics to gauge cognitive load.

2. **Pedagogy Backend (Python / FastAPI)**
   - Interfaces directly with the **Groq API (Llama-3.3-70b-versatile)** to generate structured, pedagogical interventions.
   - Handles LLM orchestration, structured JSON parsing, and graceful fallbacks.
   - Serves the Teacher Dashboard and exposes RESTful endpoints for telemetry ingestion.

3. **Data Science Pipeline**
   - Uses exported JSON telemetry datasets to train XGBoost predictive models.
   - Predicts the exact minimum level of help a student needs (e.g., *Hint 1*, *Concept Explanation*, or *Pseudocode*).

---

## 🚀 Getting Started

### Prerequisites
- **Node.js** (v18+)
- **Python** (v3.10+)
- **Visual Studio Code** (v1.96+)
- **Groq API Key** (Set as `GROQ_API_KEY` in `backend/.env`)

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
4. Click **▶ Start Problem** to begin the telemetry engine and unlock the AI hint features!

### 2. Launch the Pedagogy Backend
Open a new terminal in the project root:
```bash
cd backend
pip install -r requirements.txt
python app.py
```
*(The backend will run on `http://localhost:8000`)*

---

## 📈 The Machine Learning Model

We train our models on features derived from the student's raw keystroke timeline to understand human cognition:

| Feature | Description |
|---------|-------------|
| `time_spent` | Total session time in seconds |
| `hesitation_index` | Pause duration divided by total time |
| `compile_failure_rate` | Compilation errors per attempt |
| `typing_speed` | Keystrokes per active minute |
| `struggle_max` | The peak cognitive struggle score |
| `help_dependency` | Ratio of hints used vs hints available |

To run the pipeline locally:
```bash
python scripts/generate_synthetic_data.py  # Generates 300 sessions
python scripts/train_model.py              # Trains XGBoost model
```

---

<div align="center">
  <i>Built for the Hackathon by a team passionate about AI in Education.</i>
</div>
