/**
 * @file endSection.ts
 * Final "End Problem" call-to-action shown at the bottom of the panel
 * while recording.
 */

export function renderEndSection(): string {
  return /*html*/ `
  <!-- ── Finish ──────────────────────────────────────────────────── -->
  <div class="section" id="endSection" style="display:none;">
    <h3>Finish</h3>
    <button class="btn btn-abandoned" style="width: 100%;"
            data-command="cognitiveCoach.endProblem">🛑 End Problem</button>
  </div>`;
}
