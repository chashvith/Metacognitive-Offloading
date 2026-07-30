/**
 * @file clientScript.ts
 * AI Tutor Dashboard Client Script.
 * Owns webview client-side logic: Markdown rendering, Syntax Highlighting,
 * Struggle Meter gauge animations, Accordion toggles, Copy & Feedback actions.
 */

export function getClientScript(): string {
  return /*js*/ `
    const vscode = acquireVsCodeApi();

    function send(command) {
      vscode.postMessage({ command });
    }

    // Event delegation for all data-command buttons
    document.addEventListener('click', function(e) {
      const btn = e.target.closest('button[data-command]');
      if (btn && !btn.disabled) {
        send(btn.getAttribute('data-command'));
      }
    });

    /** Accordion Card Toggle */
    window.toggleCard = function(headerEl) {
      const card = headerEl.closest('.card');
      if (card) {
        card.classList.toggle('collapsed');
      }
    };

    /** Format seconds to HH:MM:SS */
    function formatTime(totalSeconds) {
      const h = Math.floor(totalSeconds / 3600);
      const m = Math.floor((totalSeconds % 3600) / 60);
      const s = totalSeconds % 60;
      return (
        String(h).padStart(2, '0') + ':' +
        String(m).padStart(2, '0') + ':' +
        String(s).padStart(2, '0')
      );
    }

    /** Copy Recommendation Text to Clipboard */
    window.copyRecommendation = function() {
      const msg = document.getElementById('recommendationMessage').innerText || '';
      const nextStep = document.getElementById('recommendationNextStep').innerText || '';
      const code = document.getElementById('recommendationCode').innerText || '';
      const textToCopy = msg + '\\n\\nNext Step:\\n' + nextStep + (code ? '\\n\\nCode:\\n' + code : '');

      navigator.clipboard.writeText(textToCopy).then(function() {
        const btn = document.getElementById('copyBtn');
        const orig = btn.innerHTML;
        btn.innerHTML = '✓ Copied!';
        setTimeout(function() { btn.innerHTML = orig; }, 2000);
      });
    };

    /** Feedback Buttons */
    window.rateRecommendation = function(type) {
      const upBtn = document.getElementById('thumbsUpBtn');
      const downBtn = document.getElementById('thumbsDownBtn');
      if (type === 'up') {
        upBtn.classList.toggle('active');
        downBtn.classList.remove('active');
      } else {
        downBtn.classList.toggle('active');
        upBtn.classList.remove('active');
      }
    };

    /** Draw Canvas Sparkline */
    function drawSparkline(scores) {
      const canvas = document.getElementById('sparkline');
      if (!canvas || scores.length < 2) return;

      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;
      const padding = 4;

      ctx.clearRect(0, 0, w, h);

      const maxTime = scores[scores.length - 1].time || 1;
      const drawW = w - padding * 2;
      const drawH = h - padding * 2;

      const gradient = ctx.createLinearGradient(0, padding, 0, h - padding);
      gradient.addColorStop(0, 'rgba(78, 201, 176, 0.4)');
      gradient.addColorStop(1, 'rgba(78, 201, 176, 0.02)');

      ctx.beginPath();
      scores.forEach(function(entry, i) {
        var x = padding + (entry.time / maxTime) * drawW;
        var y = padding + drawH - (entry.score * drawH);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      var lastX = padding + (scores[scores.length - 1].time / maxTime) * drawW;
      ctx.lineTo(lastX, h - padding);
      ctx.lineTo(padding, h - padding);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();

      ctx.beginPath();
      ctx.strokeStyle = '#4ec9b0';
      ctx.lineWidth = 2;
      ctx.lineJoin = 'round';
      scores.forEach(function(entry, i) {
        var x = padding + (entry.time / maxTime) * drawW;
        var y = padding + drawH - (entry.score * drawH);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }

    /** Update Animated Struggle Gauge Bar */
    function updateStruggleGauge(score) {
      const bar = document.getElementById('struggleBarFill');
      const scoreTxt = document.getElementById('struggleScore');
      if (!bar || !scoreTxt) return;

      const clamped = Math.max(0, Math.min(1, score));
      const pct = (clamped * 100).toFixed(1) + '%';
      bar.style.width = pct;
      scoreTxt.textContent = clamped.toFixed(2);

      bar.className = 'struggle-bar-fill ';
      if (clamped < 0.3) bar.className += 'struggle-low';
      else if (clamped < 0.5) bar.className += 'struggle-medium';
      else if (clamped < 0.7) bar.className += 'struggle-high';
      else bar.className += 'struggle-critical';
    }

    /** Handle State Updates from Extension Host */
    window.addEventListener('message', function(event) {
      const data = event.data;
      if (data.type !== 'stateUpdate') return;
      const state = data.state;

      // Status Badge
      const statusText = document.getElementById('statusText');
      const statusBadge = document.getElementById('statusBadge');
      statusText.textContent = state.status;
      statusBadge.className = 'badge ' + (state.status === 'Recording' ? 'badge-recording' : '');

      // Session Timer & Problem Info
      document.getElementById('timer').textContent = formatTime(state.elapsedSeconds);
      document.getElementById('problemName').textContent = state.problemName || 'No active problem';
      
      const pillsContainer = document.querySelector('.status-pills');
      if (pillsContainer) {
        pillsContainer.style.display = (state.status === 'Recording') ? 'flex' : 'none';
      }

      const isRecording = state.status === 'Recording';
      const sections = [
        'sparklineSection', 'recommendationSection', 'eventsSection',
        'metricsSection', 'hintsSection',
        'counterexampleSection', 'endSection'
      ];
      sections.forEach(function(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = isRecording ? 'block' : 'none';
      });

      // Toggle Start/End button states
      const startBtn = document.getElementById('startBtn');
      const endBtn = document.getElementById('endBtn');
      if (startBtn) startBtn.disabled = isRecording;
      if (endBtn) endBtn.disabled = !isRecording;

      if (isRecording) {
        // Analytics
        document.getElementById('charsTyped').textContent = state.charactersTyped;
        document.getElementById('pauseCount').textContent = state.pauseCount;
        document.getElementById('compileErrors').textContent = state.compileErrors;
        document.getElementById('runtimeErrors').textContent = state.runtimeErrors;

        document.getElementById('compileStats').textContent =
          'Compiles: ' + state.compileAttempts + ' | Runs OK: ' + state.successfulRuns;

        // Struggle Meter & Sparkline
        updateStruggleGauge(state.currentStruggleScore);
        if (state.struggleScores && state.struggleScores.length >= 2) {
          drawSparkline(state.struggleScores);
        }

        // Render Recommendation Card
        renderRecommendationCard(state);
      }
    });

    /** Render AI Coach Card */
    function renderRecommendationCard(state) {
      const loadingEl = document.getElementById('recommendationLoading');
      const errorEl = document.getElementById('recommendationError');
      const cardEl = document.getElementById('recommendationCard');

      loadingEl.style.display = state.recommendationStatus === 'loading' ? 'flex' : 'none';

      if (state.recommendationStatus === 'error' && state.recommendationError) {
        errorEl.style.display = 'block';
        errorEl.textContent = '⚠ ' + state.recommendationError;
      } else {
        errorEl.style.display = 'none';
      }

      const rec = state.recommendation;
      if (!rec) {
        cardEl.style.display = 'none';
        return;
      }

      cardEl.style.display = 'flex';
      document.getElementById('recommendationTitle').textContent = rec.title || 'AI Coach Guidance';

      const levelBadge = document.getElementById('recommendationLevel');
      levelBadge.textContent = rec.level || 'concept';

      // Parse Markdown if marked library is available
      const parseMd = (typeof window.marked !== 'undefined' && window.marked.parse)
        ? window.marked.parse
        : function(t) { return t; };

      document.getElementById('recommendationMessage').innerHTML = parseMd(rec.message || '');
      document.getElementById('recommendationNextStep').innerHTML = parseMd(rec.next_step || '');
      document.getElementById('recommendationReflection').innerHTML = parseMd(rec.reflection_question || '');
      document.getElementById('recommendationEncouragement').textContent = rec.encouragement || '';

      const codeWrapper = document.getElementById('recommendationCodeWrapper');
      const codeEl = document.getElementById('recommendationCode');

      if (rec.code) {
        codeWrapper.style.display = 'block';
        codeEl.textContent = rec.code;
        if (typeof window.hljs !== 'undefined' && window.hljs.highlightElement) {
          window.hljs.highlightElement(codeEl);
        }
      } else {
        codeWrapper.style.display = 'none';
      }

      // Update AI Action buttons based on ML hint level policy
      updateAiActionButtons(rec.level);
    }

    /** Enable/Disable AI Action Pills based on ML hint level */
    function updateAiActionButtons(currentLevel) {
      const levels = ['no_hint', 'concept', 'guided', 'pseudocode', 'full_solution'];
      const currentIdx = levels.indexOf(currentLevel || 'concept');

      const btnConcept = document.getElementById('btnConcept');
      const btnGuided = document.getElementById('btnGuided');
      const btnPseudocode = document.getElementById('btnPseudocode');
      const btnSolution = document.getElementById('btnSolution');

      if (btnConcept) btnConcept.disabled = currentIdx < 1;
      if (btnGuided) btnGuided.disabled = currentIdx < 2;
      if (btnPseudocode) btnPseudocode.disabled = currentIdx < 3;
      if (btnSolution) btnSolution.disabled = currentIdx < 4;
    }
  `;
}
