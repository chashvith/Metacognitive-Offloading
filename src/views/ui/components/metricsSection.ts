/**
 * @file metricsSection.ts
 * Session Analytics Dashboard component.
 */

export function renderMetricsSection(): string {
  return /*html*/ `
  <!-- ── 📊 Session Analytics Card ──────────────────────────────── -->
  <div class="card" id="metricsSection" style="display:none;">
    <div class="card-header" onclick="toggleCard(this)">
      <div class="card-title">📊 Session Analytics</div>
      <span class="accordion-icon">▼</span>
    </div>
    <div class="card-body">
      <div class="metrics-grid">
        <div class="metric-box">
          <div class="metric-val" id="compileErrors">0</div>
          <div class="metric-lbl">Compile Errors</div>
        </div>
        <div class="metric-box">
          <div class="metric-val" id="runtimeErrors">0</div>
          <div class="metric-lbl">Runtime Errors</div>
        </div>
        <div class="metric-box">
          <div class="metric-val" id="charsTyped">0</div>
          <div class="metric-lbl">Chars Typed</div>
        </div>
        <div class="metric-box">
          <div class="metric-val" id="pauseCount">0</div>
          <div class="metric-lbl">Pauses</div>
        </div>
      </div>
      <div class="compile-stats" id="compileStats" style="margin-top: 8px; text-align: center; font-size: 11px; opacity: 0.8;">
        Compiles: 0 | Runs OK: 0
      </div>
    </div>
  </div>`;
}
