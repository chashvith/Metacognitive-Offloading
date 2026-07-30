/**
 * @file hintsSection.ts
 * Manual hint-request buttons (hint1/hint2/concept/pseudocode/solution).
 */

export function renderHintsSection(): string {
  return /*html*/ `
  <!-- ── 💡 OP Hints Card ────────────────────────────────────────── -->
  <div class="card" id="hintsSection" style="display:none;">
    <div class="card-header" onclick="toggleCard(this)">
      <div class="card-title">💡 Deep Dive Hints</div>
      <span class="accordion-icon">▼</span>
    </div>
    <div class="card-body">
      <div class="button-group">
        <button class="btn btn-primary"
                data-command="cognitiveCoach.hint1" style="font-size: 14px; padding: 12px; margin-bottom: 8px;">
          🚀 GIVE ME A HINT
        </button>
        <button class="btn btn-secondary"
                data-command="cognitiveCoach.hint2">💡 Hint 2 (Deeper)</button>
        <button class="btn btn-secondary"
                data-command="cognitiveCoach.conceptHint">📖 Explain Concept</button>
      </div>
    </div>
  </div>`;
}
