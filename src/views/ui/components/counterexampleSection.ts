/**
 * @file counterexampleSection.ts
 * Counterexample placeholder buttons (wired to telemetry; AI drop-in later).
 */

export function renderCounterexampleSection(): string {
  return /*html*/ `
  <!-- ── ⚡ OP Counterexample Card ────────────────────────────── -->
  <div class="card" id="counterexampleSection" style="display:none; border-color: rgba(239, 68, 68, 0.4);">
    <div class="card-header" onclick="toggleCard(this)">
      <div class="card-title" style="color: #ef4444;">⚡ Edge Case Detector</div>
      <span class="accordion-icon">▼</span>
    </div>
    <div class="card-body">
      <div class="button-row" style="display: flex; gap: 8px;">
        <button class="btn btn-danger" style="flex: 1;"
                data-command="cognitiveCoach.showCounterexample">💥 Show Flaw</button>
        <button class="btn btn-secondary" style="flex: 1;"
                data-command="cognitiveCoach.counterexampleResolved">✓ Resolved</button>
      </div>
    </div>
  </div>`;
}
