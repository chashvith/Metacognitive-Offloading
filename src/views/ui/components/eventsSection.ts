/**
 * @file eventsSection.ts
 * AI Actions Pills component for the AI Tutor Dashboard.
 */

export function renderEventsSection(): string {
  return /*html*/ `
  <!-- ── 🎯 AI Actions Card ──────────────────────────────────────── -->
  <div class="card" id="eventsSection" style="display:none;">
    <div class="card-header" onclick="toggleCard(this)">
      <div class="card-title">🎯 AI Actions</div>
      <span class="accordion-icon">▼</span>
    </div>
    <div class="card-body">
      <div class="ai-actions-grid">
        <button class="ai-action-btn primary" id="btnExplain" data-command="cognitiveCoach.getRecommendation">
          🤖 Get AI Guidance
        </button>
        <button class="ai-action-btn" id="btnCompileError" data-command="cognitiveCoach.compileError">
          ✗ Compile Error
        </button>
        <button class="ai-action-btn" id="btnConcept" data-command="cognitiveCoach.conceptHint">
          📖 Teach Me
        </button>
        <button class="ai-action-btn" id="btnGuided" data-command="cognitiveCoach.hint1">
          💡 Next Step
        </button>
        <button class="ai-action-btn" id="btnPseudocode" data-command="cognitiveCoach.pseudocode">
          📝 Pseudocode
        </button>
        <button class="ai-action-btn" id="btnSolution" data-command="cognitiveCoach.solution">
          🔑 Full Solution
        </button>
      </div>
    </div>
  </div>`;
}
