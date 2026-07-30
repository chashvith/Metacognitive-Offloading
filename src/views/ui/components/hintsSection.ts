/**
 * @file hintsSection.ts
 * Manual hint-request buttons (hint1/hint2/concept/pseudocode/solution).
 */

export function renderHintsSection(): string {
  return /*html*/ `
  <!-- ── Hints ───────────────────────────────────────────────────── -->
  <div class="section" id="hintsSection" style="display:none;">
    <h3>Hints</h3>
    <div class="button-group">
      <button class="btn btn-hint"
              data-command="cognitiveCoach.hint1">💡 Hint 1</button>
      <button class="btn btn-hint"
              data-command="cognitiveCoach.hint2">💡 Hint 2</button>
      <button class="btn btn-hint"
              data-command="cognitiveCoach.conceptHint">📖 Concept</button>
      <button class="btn btn-hint"
              data-command="cognitiveCoach.pseudocode">📝 Pseudocode</button>
      <button class="btn btn-hint"
              data-command="cognitiveCoach.solution">🔑 Solution</button>
    </div>
  </div>`;
}
