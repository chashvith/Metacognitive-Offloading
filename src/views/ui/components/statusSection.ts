/**
 * @file statusSection.ts
 * Student Status Card component for the AI Tutor Dashboard.
 */

export function renderStatusSection(): string {
  return /*html*/ `
  <!-- ── 🧠 Student Status Card ──────────────────────────────────── -->
  <div class="card" id="statusCard">
    <div class="status-card-header">
      <div class="card-title">🧠 Cognitive Coach</div>
      <span id="statusBadge" class="badge">
        <span class="status-dot"></span>
        <span id="statusText">IDLE</span>
      </span>
    </div>
    <div class="problem-title" id="problemName">No active problem</div>
    <div class="status-pills">
      <span class="badge" id="problemLanguage">Python</span>
      <span class="badge" id="problemDifficulty">Easy</span>
    </div>
    <div class="session-timer" id="timer">00:00:00</div>
  </div>`;
}
