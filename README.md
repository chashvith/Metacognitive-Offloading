# Cognitive Coach — Telemetry Collection Extension

An AI-powered educational coding assistant that records how a student solves a programming problem, session by session, and saves each session as a local JSON file for future ML training.

**This repository covers ONLY the telemetry/data collection phase.** Everything runs fully offline — no AI, no LLM, no backend, no network requests.

---

## Project Overview

The goal of this extension is to silently gather data about the coding process (pauses, deletions, errors, hint requests). By aggregating these events into a timeline, we can later train a machine learning model to detect *when* a student is struggling and proactively offer assistance.

## Features
- **Local JSON Dataset**: Every session writes directly to the local `dataset/` folder.
- **Dataset Export**: One-click "Export Dataset" button that zips all completed sessions into a single `.zip` file for sharing or training.
- **Unified Event Timeline**: All automatic events (typing, file saves) and manual events (compile success, hint requests) share a single chronological timeline.
- **Real-Time Struggle Score**: Computes a struggle score per-event based on deletion ratio, pause frequency, compile error rate, and hint usage.
- **Crash Recovery**: Periodically saves an in-progress state file. Restores if VS Code crashes.
- **Theme-Aware Webview UI**: A responsive Activity Bar panel showing live metrics, timers, and action buttons.

## Folder Structure

```
cognitive-coach-telemetry/
├── dataset/                  ← All JSON session data goes here
│   └── .gitkeep              ← Ensures dataset/ is tracked while contents are ignored
├── media/                    ← Icons and webview CSS
├── src/                      
│   ├── commands/             ← VS Code command registrations
│   ├── export/               ← ZIP export logic (DatasetExporter)
│   ├── session/              ← Session lifecycle and file I/O
│   ├── telemetry/            ← VS Code listeners + metrics calculation
│   ├── utils/                ← UUID generators
│   ├── views/                ← Webview UI providers
│   ├── constants.ts          ← Tunable thresholds
│   ├── extension.ts          ← Entry point
│   └── types.ts              ← Shared TypeScript interfaces
├── .vscode/                  ← Debug configurations (F5 support)
├── package.json              
├── README.md
└── .gitignore                ← Excludes dataset/*.json, *.zip, node_modules/
```

---

## How to Run

### Prerequisites
- Node.js v18+ (includes npm)
- VS Code v1.96.0+

### Setup
```bash
npm install
npm run build
```

1. Open the project folder in VS Code.
2. Press **F5** (or run `Run > Start Debugging`).
3. An **Extension Development Host** window will open.
4. Click the **brain icon** in the left Activity Bar to open the Cognitive Coach panel.
5. Click **Start Problem** and begin coding.

## How to Debug

- **Breakpoints**: You can set breakpoints inside the `src/` folder. Execution will pause when the code path is hit in the Development Host window.
- **Logs**: Use `console.log()`. Output will appear in the **Debug Console** of your *main* VS Code window (not the Development Host).
- **Webview UI Inspection**: Press `Ctrl+Shift+P` (or `Cmd+Shift+P`) in the Development Host and run `Developer: Open Webview Developer Tools` to inspect the HTML/CSS/JS of the sidebar panel.

---

## How Data Collection Works

### Telemetry Capture (end to end)

```
Student types in editor
        │
        ▼
onDidChangeTextDocument fires (EVERY event, no debounce)
        │
        ├──▶ Raw metrics updated: chars_typed, chars_deleted
        ├──▶ Pause detection: gap > 5s → pause event + struggle score recompute
        └──▶ Typing batched for timeline (flushed on pauses / manual events)

Student clicks "Compile Error" button (or Ctrl+Shift+P → command)
        │
        ▼
Manual event pushed to unified timeline
        │
        ├──▶ Same-error-repeated tracker updated
        ├──▶ Struggle score recomputed (per-event, NOT on timer)
        └──▶ In-progress state persisted to disk

Session ends (Solved / Abandoned / VS Code closes)
        │
        ▼
Summary computed → JSON written to dataset/session_YYYYMMDD_HHMMSS.json
```

### Two Separate Loops

| Loop | Interval | Purpose |
|------|----------|---------|
| **Data capture** | Per-event (every keystroke, every button click) | Raw metric accumulation, pause detection, struggle score |
| **UI refresh** | 500ms timer | Render timer, metrics, sparkline in sidebar |

These are never conflated. Data capture is raw and precise. UI refresh is a rendering optimization.

---

## How Export Dataset Works

1. You click **Export Dataset** in the sidebar.
2. The `ZipDatasetExporter` reads the `dataset/` folder for completed `.json` files (excluding any `.in_progress_session.json`).
3. VS Code prompts you to choose where to save the ZIP file (defaults to outside the `dataset/` directory so it isn't gitignored).
4. The `archiver` library compresses the sessions into the `.zip` file on disk.

---

## Future Roadmap

### Phase 2: AI Hint Layer
- Integrate local or API-driven LLM (e.g., Gemini/OpenAI).
- Replace the placeholder "Counterexample" buttons with real generated counterexamples based on the active editor code.
- Progressive hint generation (concept → pseudocode → solution).

### Phase 3: ML Training Pipeline
- Scripts to parse exported ZIP datasets.
- Feature extraction and struggle prediction modeling.

### Phase 4: Real-time Coaching
- Live struggle detection → proactive nudges.
- Adaptive hint difficulty based on student profile.
