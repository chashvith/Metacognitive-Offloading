/**
 * @file sessionControls.ts
 * Start/End session and export buttons — always visible, regardless of
 * recording state (buttons are enabled/disabled client-side instead).
 */

export function renderSessionControls(): string {
  return /*html*/ `
  <!-- ── Session Controls ────────────────────────────────────────── -->
  <div class="section">
    <h3>Session</h3>
    <div class="button-group">
      <button class="btn btn-primary" id="startBtn"
              data-command="cognitiveCoach.startProblem">
        ▶ Start Problem
      </button>
      <button class="btn btn-danger" id="endBtn"
              data-command="cognitiveCoach.endProblem" disabled>
        ■ End Problem
      </button>
      <button class="btn btn-secondary"
              data-command="cognitiveCoach.exportSession">
        ↗ Export Session
      </button>
      <button class="btn btn-secondary"
              data-command="cognitiveCoach.exportDataset">
        📦 Export Dataset
      </button>
    </div>
  </div>`;
}
