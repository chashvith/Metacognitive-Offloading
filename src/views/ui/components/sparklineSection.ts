/**
 * @file sparklineSection.ts
 * Animated Struggle Meter & Trend Chart component.
 */

export function renderSparklineSection(): string {
  return /*html*/ `
  <!-- ── 📈 Live Struggle Meter Card ────────────────────────────── -->
  <div class="card" id="sparklineSection" style="display:none;">
    <div class="card-header" onclick="toggleCard(this)">
      <div class="card-title">📈 Live Struggle Meter</div>
      <span class="accordion-icon">▼</span>
    </div>
    <div class="card-body">
      <div class="struggle-container">
        <div class="struggle-header">
          <span>Current Score</span>
          <span class="struggle-score-val" id="struggleScore">0.00</span>
        </div>
        <div class="struggle-bar-bg">
          <div class="struggle-bar-fill struggle-low" id="struggleBarFill"></div>
        </div>
        <canvas id="sparkline" width="280" height="50"></canvas>
      </div>
    </div>
  </div>`;
}
