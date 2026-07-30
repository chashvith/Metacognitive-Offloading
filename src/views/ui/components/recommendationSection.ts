/**
 * @file recommendationSection.ts
 * AI Coach Card component for the AI Tutor Dashboard.
 */

export function renderRecommendationSection(): string {
  return /*html*/ `
  <!-- ── 🤖 AI Coach Card ────────────────────────────────────────── -->
  <div class="card" id="recommendationSection" style="display:none;">
    <div class="card-header" onclick="toggleCard(this)">
      <div class="card-title">🤖 AI Coach</div>
      <span class="accordion-icon">▼</span>
    </div>
    <div class="card-body">
      <!-- Loading Skeleton -->
      <div id="recommendationLoading" class="skeleton-loader" style="display:none;">
        <div class="skeleton-line" style="width: 60%;"></div>
        <div class="skeleton-line" style="width: 90%;"></div>
        <div class="skeleton-line" style="width: 75%;"></div>
      </div>

      <!-- Error State -->
      <div id="recommendationError" class="recommendation-error" style="display:none;"></div>

      <!-- Recommendation Card Content -->
      <div id="recommendationCard" class="recommendation-card-content" style="display:none;">
        <div class="recommendation-badge-row">
          <span id="recommendationTitle" class="recommendation-header-title"></span>
          <span id="recommendationLevel" class="badge"></span>
        </div>

        <div id="recommendationMessage" class="markdown-body"></div>

        <div class="callout-box" id="nextStepBox">
          <div class="callout-title">🎯 Actionable Next Step</div>
          <div id="recommendationNextStep" class="markdown-body"></div>
        </div>

        <div class="callout-box" id="reflectionBox">
          <div class="callout-title">💡 Reflection Question</div>
          <div id="recommendationReflection" class="markdown-body"></div>
        </div>

        <div id="recommendationCodeWrapper" style="display:none;">
          <pre class="code-block"><code id="recommendationCode"></code></pre>
        </div>

        <p id="recommendationEncouragement" style="font-style: italic; font-size: 11px; opacity: 0.8;"></p>

        <!-- User Actions & Feedback Bar -->
        <div class="action-controls-row">
          <button class="ctrl-btn" id="copyBtn" onclick="copyRecommendation()" title="Copy explanation">
            📋 Copy
          </button>
          <button class="ctrl-btn" id="regenBtn" data-command="cognitiveCoach.getRecommendation" title="Regenerate explanation">
            🔄 Regenerate
          </button>
          <button class="ctrl-btn" id="thumbsUpBtn" onclick="rateRecommendation('up')" title="Helpful">
            👍
          </button>
          <button class="ctrl-btn" id="thumbsDownBtn" onclick="rateRecommendation('down')" title="Not helpful">
            👎
          </button>
        </div>
      </div>
    </div>
  </div>`;
}
