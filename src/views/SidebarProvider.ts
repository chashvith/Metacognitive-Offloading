/**
 * @file SidebarProvider.ts
 * WebviewViewProvider for the Activity Bar sidebar panel.
 *
 * Renders HTML with:
 * - Status badge (Idle/Recording/Ended) with animated indicator
 * - Live timer (updated via postMessage on UI_REFRESH_INTERVAL_MS)
 * - Metrics grid (chars typed/deleted, pauses, struggle score)
 * - Buttons for all manual events
 * - Struggle score mini sparkline (canvas)
 *
 * Communication pattern:
 * - Webview → Extension: postMessage({ command: 'cognitiveCoach.xxx' })
 * - Extension → Webview: postMessage({ type: 'stateUpdate', state: {...} })
 *
 * The UI refresh is on a timer (rendering only). Data capture happens
 * per-event in TelemetryTracker — two separate loops, never conflated.
 */

import * as vscode from 'vscode';
import { SessionManager } from '../session/SessionManager';
import { UI_REFRESH_INTERVAL_MS } from '../constants';

export class SidebarProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'cognitiveCoach.sidebar';

  private view?: vscode.WebviewView;
  private refreshInterval?: ReturnType<typeof setInterval>;

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly sessionManager: SessionManager
  ) {}

  /**
   * Called by VS Code when the webview view is first shown.
   */
  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.extensionUri],
    };

    webviewView.webview.html = this.getHtml(webviewView.webview);

    // Handle messages from webview → extension
    webviewView.webview.onDidReceiveMessage((message) => {
      if (message.command) {
        vscode.commands.executeCommand(message.command);
      }
    });

    // Start UI refresh timer (rendering only, not data capture)
    this.startRefresh();

    webviewView.onDidDispose(() => {
      this.stopRefresh();
    });
  }

  /** Start the UI refresh timer */
  private startRefresh(): void {
    this.refreshInterval = setInterval(() => {
      this.pushState();
    }, UI_REFRESH_INTERVAL_MS);
  }

  /** Stop the UI refresh timer */
  private stopRefresh(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = undefined;
    }
  }

  /** Push current state to the webview for rendering */
  pushState(): void {
    if (!this.view) {
      return;
    }
    const state = this.sessionManager.getState();
    this.view.webview.postMessage({ type: 'stateUpdate', state });
  }

  /**
   * Generate the full HTML for the webview.
   * Embeds sidebar.css and inline JS for state updates + sparkline rendering.
   */
  private getHtml(webview: vscode.Webview): string {
    const cssUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.extensionUri, 'media', 'sidebar.css')
    );

    const nonce = getNonce();

    return /*html*/ `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';">
  <link rel="stylesheet" href="${cssUri}">
  <title>Cognitive Coach</title>
</head>
<body>

  <!-- ── Status Section ──────────────────────────────────────────── -->
  <div class="status-section">
    <div class="status-badge" id="statusBadge">
      <span class="status-dot"></span>
      <span class="status-text" id="statusText">Idle</span>
    </div>
    <div class="timer" id="timer">00:00:00</div>
    <div class="problem-name" id="problemName"></div>
  </div>

  <!-- ── Session Controls ────────────────────────────────────────── -->
  <div class="section">
    <h3>Session</h3>
    <div class="button-group">
      <button class="btn btn-primary" id="startBtn"
              onclick="send('cognitiveCoach.startProblem')">
        ▶ Start Problem
      </button>
      <button class="btn btn-danger" id="endBtn"
              onclick="send('cognitiveCoach.endProblem')" disabled>
        ■ End Problem
      </button>
      <button class="btn btn-secondary"
              onclick="send('cognitiveCoach.exportSession')">
        ↗ Export Session
      </button>
      <button class="btn btn-secondary"
              onclick="send('cognitiveCoach.exportDataset')">
        📦 Export Dataset
      </button>
    </div>
  </div>

  <!-- ── Live Metrics ────────────────────────────────────────────── -->
  <div class="section" id="metricsSection" style="display:none;">
    <h3>Live Metrics</h3>
    <div class="metrics-grid">
      <div class="metric">
        <span class="metric-value" id="charsTyped">0</span>
        <span class="metric-label">Typed</span>
      </div>
      <div class="metric">
        <span class="metric-value" id="charsDeleted">0</span>
        <span class="metric-label">Deleted</span>
      </div>
      <div class="metric">
        <span class="metric-value" id="pauseCount">0</span>
        <span class="metric-label">Pauses</span>
      </div>
      <div class="metric">
        <span class="metric-value" id="struggleScore">0.00</span>
        <span class="metric-label">Struggle</span>
      </div>
    </div>
  </div>

  <!-- ── Compile / Run ───────────────────────────────────────────── -->
  <div class="section" id="eventsSection" style="display:none;">
    <h3>Compile / Run</h3>
    <div class="button-row">
      <button class="btn btn-success"
              onclick="send('cognitiveCoach.compileSuccess')">✓ Compile OK</button>
      <button class="btn btn-error"
              onclick="send('cognitiveCoach.compileError')">✗ Compile Err</button>
    </div>
    <div class="button-row">
      <button class="btn btn-success"
              onclick="send('cognitiveCoach.successfulRun')">✓ Run OK</button>
      <button class="btn btn-error"
              onclick="send('cognitiveCoach.runtimeError')">✗ Runtime Err</button>
    </div>
    <div class="compile-stats" id="compileStats"></div>
  </div>

  <!-- ── Hints ───────────────────────────────────────────────────── -->
  <div class="section" id="hintsSection" style="display:none;">
    <h3>Hints</h3>
    <div class="button-group">
      <button class="btn btn-hint"
              onclick="send('cognitiveCoach.hint1')">💡 Hint 1</button>
      <button class="btn btn-hint"
              onclick="send('cognitiveCoach.hint2')">💡 Hint 2</button>
      <button class="btn btn-hint"
              onclick="send('cognitiveCoach.conceptHint')">📖 Concept</button>
      <button class="btn btn-hint"
              onclick="send('cognitiveCoach.pseudocode')">📝 Pseudocode</button>
      <button class="btn btn-hint"
              onclick="send('cognitiveCoach.solution')">🔑 Solution</button>
    </div>
  </div>

  <!-- ── Counterexample (placeholder wired Day 1) ────────────────── -->
  <div class="section" id="counterexampleSection" style="display:none;">
    <h3>Counterexample</h3>
    <div class="button-row">
      <button class="btn btn-warning"
              onclick="send('cognitiveCoach.showCounterexample')">⚡ Show</button>
      <button class="btn btn-success"
              onclick="send('cognitiveCoach.counterexampleResolved')">✓ Resolved</button>
    </div>
  </div>

  <!-- ── Struggle Score Sparkline ─────────────────────────────────── -->
  <div class="section" id="sparklineSection" style="display:none;">
    <h3>Struggle Score</h3>
    <canvas id="sparkline" width="280" height="60"></canvas>
  </div>

  <!-- ── Finish ──────────────────────────────────────────────────── -->
  <div class="section" id="endSection" style="display:none;">
    <h3>Finish</h3>
    <div class="button-group">
      <button class="btn btn-solved"
              onclick="send('cognitiveCoach.problemSolved')">🎉 Problem Solved</button>
      <button class="btn btn-abandoned"
              onclick="send('cognitiveCoach.problemAbandoned')">🏳 Abandoned</button>
    </div>
  </div>

  <!-- ── Webview Script ──────────────────────────────────────────── -->
  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();

    /** Send a command to the extension host */
    function send(command) {
      vscode.postMessage({ command });
    }

    /** Format seconds as HH:MM:SS */
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

    /**
     * Draw a mini sparkline of struggle scores on the canvas.
     * Spikes then drops when the student self-corrects — the best demo visual.
     */
    function drawSparkline(scores) {
      const canvas = document.getElementById('sparkline');
      if (!canvas || scores.length < 2) return;

      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;
      const padding = 4;

      ctx.clearRect(0, 0, w, h);

      // Background
      ctx.fillStyle = 'rgba(128, 128, 128, 0.05)';
      ctx.roundRect(0, 0, w, h, 4);
      ctx.fill();

      const maxTime = scores[scores.length - 1].time || 1;
      const drawW = w - padding * 2;
      const drawH = h - padding * 2;

      // Gradient fill under curve
      const gradient = ctx.createLinearGradient(0, padding, 0, h - padding);
      gradient.addColorStop(0, 'rgba(255, 107, 107, 0.3)');
      gradient.addColorStop(1, 'rgba(255, 107, 107, 0.02)');

      // Draw fill
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

      // Draw line
      ctx.beginPath();
      ctx.strokeStyle = '#ff6b6b';
      ctx.lineWidth = 2;
      ctx.lineJoin = 'round';
      scores.forEach(function(entry, i) {
        var x = padding + (entry.time / maxTime) * drawW;
        var y = padding + drawH - (entry.score * drawH);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      // Draw dots on last few points
      var dotsToShow = Math.min(5, scores.length);
      for (var j = scores.length - dotsToShow; j < scores.length; j++) {
        var entry = scores[j];
        var dx = padding + (entry.time / maxTime) * drawW;
        var dy = padding + drawH - (entry.score * drawH);
        ctx.beginPath();
        ctx.arc(dx, dy, 3, 0, Math.PI * 2);
        ctx.fillStyle = '#ff6b6b';
        ctx.fill();
      }
    }

    /** Handle state updates from the extension host */
    window.addEventListener('message', function(event) {
      var data = event.data;
      if (data.type !== 'stateUpdate') return;
      var state = data.state;

      // Status badge
      var badge = document.getElementById('statusBadge');
      var statusText = document.getElementById('statusText');
      statusText.textContent = state.status;
      badge.className = 'status-badge status-' +
        state.status.toLowerCase().replace('_', '-');

      // Timer
      document.getElementById('timer').textContent =
        formatTime(state.elapsedSeconds);

      // Problem name
      document.getElementById('problemName').textContent =
        state.problemName || '';

      // Show/hide sections based on recording state
      var isRecording = state.status === 'Recording';
      document.getElementById('startBtn').disabled = isRecording;
      document.getElementById('endBtn').disabled = !isRecording;

      var sections = [
        'metricsSection', 'eventsSection', 'hintsSection',
        'counterexampleSection', 'sparklineSection', 'endSection'
      ];
      sections.forEach(function(id) {
        document.getElementById(id).style.display =
          isRecording ? 'block' : 'none';
      });

      if (isRecording) {
        // Metrics
        document.getElementById('charsTyped').textContent =
          state.charactersTyped;
        document.getElementById('charsDeleted').textContent =
          state.charactersDeleted;
        document.getElementById('pauseCount').textContent =
          state.pauseCount;
        document.getElementById('struggleScore').textContent =
          state.currentStruggleScore.toFixed(2);

        // Compile/run stats
        document.getElementById('compileStats').textContent =
          'Compiles: ' + state.compileAttempts +
          ' | Errors: ' + state.compileErrors +
          ' | Runs OK: ' + state.successfulRuns +
          ' | RT Errors: ' + state.runtimeErrors;

        // Sparkline
        if (state.struggleScores && state.struggleScores.length >= 2) {
          drawSparkline(state.struggleScores);
        }
      }
    });
  </script>

</body>
</html>`;
  }
}

/** Generate a random nonce for Content Security Policy */
function getNonce(): string {
  let text = '';
  const possible =
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}
