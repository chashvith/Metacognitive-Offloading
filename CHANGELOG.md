# Change Log

All notable changes to the "cognitive-coach" extension will be documented in this file.

## [0.0.1] — 2026-07-24

### Added
- **Sidebar panel**: Activity Bar view container with webview showing status, timer, metrics, and all action buttons
- **Session lifecycle**: Start Problem (with input boxes for name, difficulty, language, student ID), End Problem, Export Session
- **Automatic telemetry**: Characters typed/deleted, pause detection, idle time, file saves, file switches, auto-detected task starts
- **Manual events**: Compile Success/Error, Successful Run/Runtime Error, Hints (5 levels), Counterexample (placeholder), Problem Solved/Abandoned
- **Unified timeline**: Single chronological array for all events (automatic + manual), typed EventType enum
- **Struggle score**: Per-event computation (deletion ratio + pause frequency + error rate + hint usage), sparkline visualization
- **Crash recovery**: In-progress session state persisted every 10s, recovery prompt on activation
- **Session JSON output**: Full schema with `schema_version: "1.0"`, saved to `dataset/` folder
- **16 Command Palette commands**: All actions accessible via `Ctrl+Shift+P`
