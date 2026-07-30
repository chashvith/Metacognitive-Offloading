/**
 * @file counterexampleSection.ts
 * Counterexample placeholder buttons (wired to telemetry; AI drop-in later).
 */

export function renderCounterexampleSection(): string {
  return /*html*/ `
  <!-- ── Counterexample (placeholder wired Day 1) ────────────────── -->
  <div class="section" id="counterexampleSection" style="display:none;">
    <h3>Counterexample</h3>
    <div class="button-row">
      <button class="btn btn-warning"
              data-command="cognitiveCoach.showCounterexample">⚡ Show</button>
      <button class="btn btn-success"
              data-command="cognitiveCoach.counterexampleResolved">✓ Resolved</button>
    </div>
  </div>`;
}
