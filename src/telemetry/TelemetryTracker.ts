/**
 * @file TelemetryTracker.ts
 * Attaches VS Code listeners and computes all automatic metrics.
 *
 * Key design decisions:
 * - EVERY raw text-change event is captured for metrics (chars typed/deleted,
 *   pause detection). No debouncing of data capture.
 * - Timeline entries for typing are batched — flushed on pauses and manual events
 *   to keep JSON files manageable.
 * - UI refresh is on a separate timer (UI_REFRESH_INTERVAL_MS) — rendering
 *   optimization only, never conflated with data capture.
 * - Struggle score is computed per-event (compile error, pause end, hint request),
 *   NOT on a timer. This produces responsive spikes at the exact moment things
 *   go wrong — your best demo visual.
 */

import * as vscode from 'vscode';
import { EventType, StruggleScoreEntry, TrackerState } from '../types';
import { EventTimeline } from './EventTimeline';
import { IDLE_THRESHOLD_MS } from '../constants';

export class TelemetryTracker {
  private readonly disposables: vscode.Disposable[] = [];
  private timeline: EventTimeline;

  // ── Text metrics (raw, per-event, no debounce) ───────────────────────────
  private charactersTyped: number = 0;
  private charactersDeleted: number = 0;

  // ── Pause & idle tracking ────────────────────────────────────────────────
  private lastChangeTimestamp: number = 0;
  private pauseCount: number = 0;
  private totalPauseDuration: number = 0; // ms
  private idleTime: number = 0;           // ms — total zero-activity wall-clock time

  // ── File tracking ────────────────────────────────────────────────────────
  private fileSaveCount: number = 0;
  private fileOpenCount: number = 0;
  private trackedDocumentUri: string | undefined;

  // ── Auto-detected compile/run (via VS Code task system) ──────────────────
  private autoCompileAttempts: number = 0;

  // ── Terminal output streaming (Shell Integration, command-scoped) ──────────
  // We stream the output of each command execution using execution.read().
  // This is command-scoped so we know exactly what type of command produced
  // the output (compile vs run). Works whenever shell integration is active.
  private lastTerminalCommandType: 'compile' | 'run' | null = null;
  private lastTerminalCommandTime: number = 0;
  private static readonly TERMINAL_DEDUP_MS = 1500;

  // ── Same-error-repeated tracking ─────────────────────────────────────────
  private lastErrorMessage: string = '';
  private currentErrorStreak: number = 0;
  private sameErrorPeak: number = 0;

  // ── Counterexample tracking ──────────────────────────────────────────────
  private counterexampleShownTime: number | null = null;
  private counterexampleShownCount: number = 0;
  private timeToResolutionAfterCounterexample: number | null = null;

  // ── Hints offered vs. used ───────────────────────────────────────────────
  private hintsAvailable: number = 0;
  private hintsUsed: number = 0;

  // ── Struggle score (computed per-event, NOT on timer) ────────────────────
  private struggleScores: StruggleScoreEntry[] = [];

  // ── Typing batch for timeline (display batching only, NOT data) ──────────
  private pendingTypedChars: number = 0;
  private pendingDeletedChars: number = 0;

  /**
   * @param timeline - The shared EventTimeline instance
   * @param trackedDocumentUri - URI of the active editor at session start
   */
  constructor(timeline: EventTimeline, trackedDocumentUri?: string) {
    this.timeline = timeline;
    this.trackedDocumentUri = trackedDocumentUri;
    this.lastChangeTimestamp = Date.now();
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // LISTENER SETUP
  // ═══════════════════════════════════════════════════════════════════════════

  /** Attach all VS Code event listeners. Call once after construction. */
  attach(): void {
    // Text document changes — raw, every single event
    this.disposables.push(
      vscode.workspace.onDidChangeTextDocument((e) => this.onTextChange(e))
    );

    // File saves
    this.disposables.push(
      vscode.workspace.onDidSaveTextDocument((doc) => this.onFileSave(doc))
    );

    // Active editor changes (file switching)
    this.disposables.push(
      vscode.window.onDidChangeActiveTextEditor((editor) =>
        this.onEditorChange(editor)
      )
    );

    // Task/debug process starts (auto-detected compile/run via VS Code tasks panel)
    this.disposables.push(
      vscode.tasks.onDidStartTaskProcess((e) => this.onTaskStart(e))
    );

    // ── Approach 1: Shell Integration (VS Code 1.93+, requires shell to support it)
    // Works automatically when shell integration is injected. Gives us the
    // exact exit code for any command. May silently not fire on some Windows
    // setups — Approach 2 is the fallback.
    if (vscode.window.onDidEndTerminalShellExecution) {
      this.disposables.push(
        vscode.window.onDidEndTerminalShellExecution((e) =>
          this.onTerminalExecutionEnd(e)
        )
      );
    }

    // ── Approach 2: Stream command output via execution.read()
    // When shell integration fires onDidStartTerminalShellExecution, we read
    // the output stream for that specific command and scan it for error patterns.
    if (vscode.window.onDidStartTerminalShellExecution) {
      this.disposables.push(
        vscode.window.onDidStartTerminalShellExecution((e) =>
          this.onTerminalExecutionStart(e)
        )
      );
    }

  }

  // ═══════════════════════════════════════════════════════════════════════════
  // AUTOMATIC EVENT HANDLERS
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Handle every raw text-change event. This is the core telemetry capture —
   * no debouncing, no batching. Each ContentChangeEvent's rangeLength (chars
   * deleted) and text.length (chars inserted) are processed individually.
   */
  private onTextChange(e: vscode.TextDocumentChangeEvent): void {
    // Only track changes in the monitored document
    if (
      this.trackedDocumentUri &&
      e.document.uri.toString() !== this.trackedDocumentUri
    ) {
      return;
    }

    const now = Date.now();

    // ── Pause detection: gap since last change > threshold ────────────────
    if (this.lastChangeTimestamp > 0) {
      const gap = now - this.lastChangeTimestamp;
      if (gap >= IDLE_THRESHOLD_MS) {
        this.pauseCount++;
        this.totalPauseDuration += gap;
        this.idleTime += gap;

        // Flush pending typing to timeline before the pause event
        this.flushTypingEvents();

        this.timeline.push(EventType.PauseDetected, {
          duration_ms: gap,
          pause_number: this.pauseCount,
        });

        // Struggle score on pause end (resume of typing)
        this.computeStruggleScore(EventType.PauseDetected);
      }
    }

    this.lastChangeTimestamp = now;

    // ── Process each content change in the event ─────────────────────────
    for (const change of e.contentChanges) {
      const inserted = change.text.length;
      const deleted = change.rangeLength;

      // Raw metric accumulation (every event, no batching)
      this.charactersTyped += inserted;
      this.charactersDeleted += deleted;

      // Pending batch for timeline entries (display batching only)
      this.pendingTypedChars += inserted;
      this.pendingDeletedChars += deleted;
    }
  }

  /**
   * Flush accumulated typing/deleting as timeline events.
   * Called at natural break points: pauses, manual events, session end.
   */
  private flushTypingEvents(): void {
    if (this.pendingTypedChars > 0) {
      this.timeline.push(EventType.Typed, { chars: this.pendingTypedChars });
      this.pendingTypedChars = 0;
    }
    if (this.pendingDeletedChars > 0) {
      this.timeline.push(EventType.Deleted, {
        chars: this.pendingDeletedChars,
      });
      this.pendingDeletedChars = 0;
    }
  }

  /** Handle file save events */
  private onFileSave(doc: vscode.TextDocument): void {
    if (
      this.trackedDocumentUri &&
      doc.uri.toString() !== this.trackedDocumentUri
    ) {
      return;
    }
    this.fileSaveCount++;
    this.flushTypingEvents();
    this.timeline.push(EventType.FileSaved);
  }

  /** Handle active editor changes (file switching) */
  private onEditorChange(editor: vscode.TextEditor | undefined): void {
    if (!editor) {
      return;
    }
    const newUri = editor.document.uri.toString();
    if (newUri !== this.trackedDocumentUri) {
      this.flushTypingEvents();
      this.trackedDocumentUri = newUri;
      this.fileOpenCount++;
      this.timeline.push(EventType.FileSwitched, {
        file: editor.document.fileName,
      });
    }
  }

  /** Handle auto-detected task/compile starts */
  private onTaskStart(e: vscode.TaskProcessStartEvent): void {
    this.autoCompileAttempts++;
    this.timeline.push(EventType.TaskStarted, {
      task: e.execution.task.name,
    });
  }

  /**
   * Approach 1: Shell Integration exit-code handler.
   * Only fires when the terminal's shell integration script is injected.
   * On Windows with PowerShell this may not fire — Approach 2 is the fallback.
   */
  private onTerminalExecutionEnd(e: vscode.TerminalShellExecutionEndEvent): void {
    const cmd = e.execution.commandLine.value.toLowerCase().trim();
    const exitCode = e.exitCode;
    if (exitCode === undefined) {
      return;
    }

    const isCompile = this.isCompileCommand(cmd);
    const isRun = this.isRunCommand(cmd);

    if (!isCompile && !isRun) {
      return;
    }

    const now = Date.now();
    if (now - this.lastTerminalCommandTime < TelemetryTracker.TERMINAL_DEDUP_MS) {
      return; // Already recorded via Approach 2
    }
    this.lastTerminalCommandTime = now;

    if (isCompile) {
      exitCode === 0 ? this.recordCompileSuccess() : this.recordCompileError(
        `${e.execution.commandLine.value} (exit ${exitCode})`
      );
    } else {
      exitCode === 0 ? this.recordSuccessfulRun() : this.recordRuntimeError(
        `${e.execution.commandLine.value} (exit ${exitCode})`
      );
    }
  }

  /**
   * Approach 1 (start): Streams command output via execution.read() to detect
   * error/success patterns from compiler/runtime output text.
   */
  private onTerminalExecutionStart(e: vscode.TerminalShellExecutionStartEvent): void {
    const cmd = e.execution.commandLine.value.toLowerCase().trim();
    const isCompile = this.isCompileCommand(cmd);
    const isRun = this.isRunCommand(cmd);

    if (!isCompile && !isRun) {
      return;
    }

    const cmdType: 'compile' | 'run' = isCompile ? 'compile' : 'run';

    // Stream the output of this specific command execution
    void this.streamExecutionOutput(e.execution, cmdType);
  }

  /**
   * Reads the output stream of a command execution and scans for
   * error/success patterns. Fires the appropriate telemetry event.
   */
  private async streamExecutionOutput(
    execution: vscode.TerminalShellExecution,
    cmdType: 'compile' | 'run'
  ): Promise<void> {
    let outputBuffer = '';
    try {
      for await (const chunk of execution.read()) {
        outputBuffer += chunk;
        // Cap buffer size
        if (outputBuffer.length > 4000) {
          outputBuffer = outputBuffer.slice(-4000);
        }
      }
    } catch {
      // Stream ended or terminal closed — use whatever we collected
    }

    const now = Date.now();
    if (now - this.lastTerminalCommandTime < TelemetryTracker.TERMINAL_DEDUP_MS) {
      return; // Already recorded via shell integration end event
    }

    const buf = outputBuffer.toLowerCase();
    const hasError = this.bufferHasError(buf, cmdType);

    this.lastTerminalCommandTime = now;
    if (cmdType === 'compile') {
      hasError ? this.recordCompileError('auto-detected from output') : this.recordCompileSuccess();
    } else {
      hasError ? this.recordRuntimeError('auto-detected from output') : this.recordSuccessfulRun();
    }
  }

  /**
   * Scan a terminal output buffer string for known error patterns.
   * Covers C++, Python, Java, Node.js, Rust, and generic patterns.
   */
  private bufferHasError(buf: string, cmdType: 'compile' | 'run'): boolean {
    if (cmdType === 'compile') {
      return (
        buf.includes('error:') ||
        buf.includes(': error c') ||          // MSVC
        buf.includes('compilation failed') ||
        buf.includes('build failed') ||
        buf.includes('syntaxerror') ||         // Python
        buf.includes('nameerror') ||           // Python
        buf.includes('cannot find symbol') ||  // Java
        buf.includes('^~~~') ||                // clang
        buf.includes('^---')
      );
    } else {
      return (
        buf.includes('traceback (most recent call last)') || // Python
        buf.includes('exception in thread') ||               // Java
        buf.includes('segmentation fault') ||
        buf.includes('segfault') ||
        buf.includes('uncaughtexception') ||                 // Node.js
        buf.includes('error: panicked') ||                   // Rust
        buf.includes('aborted (core dumped)')
      );
    }
  }

  // ── Command classifier helpers ────────────────────────────────────────────

  private isCompileCommand(cmd: string): boolean {
    return (
      cmd.startsWith('g++') ||
      cmd.startsWith('gcc') ||
      cmd.startsWith('clang') ||
      cmd.startsWith('javac') ||
      cmd.includes('cargo build') ||
      cmd.includes('npm run build') ||
      cmd.startsWith('make') ||
      cmd.startsWith('cmake') ||
      cmd.startsWith('msbuild') ||
      cmd.startsWith('cl ')
    );
  }

  private isRunCommand(cmd: string): boolean {
    return (
      cmd.includes('./a.out') ||
      cmd.includes('./a.exe') ||
      cmd.includes('.\\a.exe') ||
      cmd.includes('.\\main.exe') ||
      cmd.includes('.\\main') ||
      cmd.startsWith('python') ||
      cmd.startsWith('python3') ||
      cmd.startsWith('node ') ||
      cmd.startsWith('java ') ||
      cmd.includes('cargo run') ||
      cmd.includes('npm start') ||
      cmd.includes('npm run start')
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // MANUAL EVENT HANDLERS (called from SessionManager)
  // ═══════════════════════════════════════════════════════════════════════════

  /** Record a successful compile (manual button) */
  recordCompileSuccess(): void {
    this.flushTypingEvents();
    this.lastErrorMessage = '';
    this.currentErrorStreak = 0;
    this.timeline.push(EventType.CompileSuccess);
    this.computeStruggleScore(EventType.CompileSuccess);
  }

  /** Record a compile error (manual button) */
  recordCompileError(errorMessage?: string): void {
    this.flushTypingEvents();
    this.trackErrorRepetition(errorMessage);
    this.timeline.push(
      EventType.CompileError,
      errorMessage ? { error: errorMessage } : undefined
    );
    this.computeStruggleScore(EventType.CompileError);
  }

  /** Record a successful run (manual button) */
  recordSuccessfulRun(): void {
    this.flushTypingEvents();
    this.lastErrorMessage = '';
    this.currentErrorStreak = 0;
    this.timeline.push(EventType.SuccessfulRun);
    this.computeStruggleScore(EventType.SuccessfulRun);
  }

  /** Record a runtime error (manual button) */
  recordRuntimeError(errorMessage?: string): void {
    this.flushTypingEvents();
    this.trackErrorRepetition(errorMessage);
    this.timeline.push(
      EventType.RuntimeError,
      errorMessage ? { error: errorMessage } : undefined
    );
    this.computeStruggleScore(EventType.RuntimeError);
  }

  /**
   * Record a hint request (any level). Updates both timeline and metrics.
   * @param type - The specific hint EventType
   */
  recordHint(type: EventType): void {
    this.flushTypingEvents();
    this.hintsUsed++;
    this.timeline.push(type);
    this.computeStruggleScore(type);
  }

  /**
   * Record a counterexample being shown (placeholder — logs event + dummy test case).
   * Person B drops the real Gemini call into this same slot on Day 2–3.
   */
  recordCounterexampleShown(): void {
    this.flushTypingEvents();
    this.counterexampleShownCount++;
    this.counterexampleShownTime = Date.now();
    this.timeline.push(EventType.CounterexampleShown, {
      // Placeholder dummy test case — replaced when AI layer lands
      test_case: {
        input: [2, 7, 11, 15],
        target: 9,
        expected: [0, 1],
      },
    });
    this.computeStruggleScore(EventType.CounterexampleShown);
  }

  /**
   * Record a counterexample being resolved by the student.
   * Computes time-to-resolution — the core hypothesis metric.
   */
  recordCounterexampleResolved(): void {
    this.flushTypingEvents();
    if (this.counterexampleShownTime !== null) {
      this.timeToResolutionAfterCounterexample = Math.round(
        (Date.now() - this.counterexampleShownTime) / 1000
      );
    }
    this.timeline.push(EventType.CounterexampleResolved, {
      resolution_time_seconds: this.timeToResolutionAfterCounterexample,
    });
    this.computeStruggleScore(EventType.CounterexampleResolved);
  }

  /**
   * Record that a hint was made available (offered by system).
   * Used for the "hints offered vs. hints used" metric.
   */
  offerHint(): void {
    this.hintsAvailable++;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SAME-ERROR-REPEATED TRACKING
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Track consecutive identical errors. Fires SameErrorRepeated event when
   * the streak exceeds the previous peak.
   */
  private trackErrorRepetition(errorMessage?: string): void {
    const msg = errorMessage || '(no message)';
    if (msg === this.lastErrorMessage) {
      this.currentErrorStreak++;
      if (this.currentErrorStreak > this.sameErrorPeak) {
        this.sameErrorPeak = this.currentErrorStreak;
      }
      this.timeline.push(EventType.SameErrorRepeated, {
        streak: this.currentErrorStreak,
        error: msg,
      });
    } else {
      this.currentErrorStreak = 1;
      this.lastErrorMessage = msg;
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // STRUGGLE SCORE (computed per-event, NOT on timer)
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Compute struggle score based on recent activity.
   * Components (each normalized 0–1):
   *   - Deletion ratio (weight 0.30): high deletions = rewriting = struggling
   *   - Pause frequency (weight 0.20): frequent pauses = stuck/thinking
   *   - Error rate (weight 0.35): compile + runtime errors per minute
   *   - Hint usage (weight 0.15): using hints = needing help
   */
  private computeStruggleScore(trigger: EventType): void {
    const elapsed = this.timeline.getElapsedSeconds();
    if (elapsed === 0) {
      this.struggleScores.push({ time: 0, score: 0, trigger });
      return;
    }

    const elapsedMinutes = elapsed / 60;

    // Component 1: Deletion ratio (0–1)
    const deletionRatio =
      this.charactersTyped > 0
        ? Math.min(this.charactersDeleted / this.charactersTyped, 1.0)
        : 0;

    // Component 2: Pause frequency (normalized: 5 pauses/min = max)
    const pauseFrequency =
      elapsedMinutes > 0
        ? Math.min(this.pauseCount / elapsedMinutes / 5, 1.0)
        : 0;

    // Component 3: Error rate (normalized: 3 errors/min = max)
    const errorEvents =
      this.timeline.getEventCount(EventType.CompileError) +
      this.timeline.getEventCount(EventType.RuntimeError);
    const errorRate =
      elapsedMinutes > 0
        ? Math.min(errorEvents / elapsedMinutes / 3, 1.0)
        : 0;

    // Component 4: Hint usage (normalized: 5 hints = max)
    const hintUsage = Math.min(this.hintsUsed / 5, 1.0);

    // Weighted average
    const score =
      0.3 * deletionRatio +
      0.2 * pauseFrequency +
      0.35 * errorRate +
      0.15 * hintUsage;

    this.struggleScores.push({
      time: elapsed,
      score: Math.round(score * 1000) / 1000,
      trigger,
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // METRICS SNAPSHOT & FINALIZATION
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Finalize idle-time accounting. Must be called before computing the
   * final session summary (accounts for trailing idle time).
   */
  finalize(): void {
    const now = Date.now();
    if (this.lastChangeTimestamp > 0) {
      const gap = now - this.lastChangeTimestamp;
      if (gap >= IDLE_THRESHOLD_MS) {
        this.idleTime += gap;
      }
    }
    this.flushTypingEvents();
  }

  /**
   * Get a snapshot of all current metrics.
   * Used by SessionManager for summary computation and by SidebarProvider
   * for UI state updates.
   */
  getMetrics() {
    const elapsed = this.timeline.getElapsedSeconds();
    const activeSeconds = Math.max(elapsed - this.idleTime / 1000, 1);
    const activeMinutes = activeSeconds / 60;

    return {
      charactersTyped: this.charactersTyped,
      charactersDeleted: this.charactersDeleted,
      deletionRatio:
        this.charactersTyped > 0
          ? Math.round(
              (this.charactersDeleted / this.charactersTyped) * 100
            ) / 100
          : 0,
      typingSpeed:
        activeMinutes > 0
          ? Math.round((this.charactersTyped / activeMinutes) * 10) / 10
          : 0,
      pauseCount: this.pauseCount,
      totalPauseDuration: Math.round(this.totalPauseDuration / 1000),
      idleTime: Math.round(this.idleTime / 1000),
      fileSaveCount: this.fileSaveCount,
      fileOpenCount: this.fileOpenCount,
      autoCompileAttempts: this.autoCompileAttempts,
      sameErrorPeak: this.sameErrorPeak,
      counterexampleShownCount: this.counterexampleShownCount,
      timeToResolutionAfterCounterexample:
        this.timeToResolutionAfterCounterexample,
      hintsAvailable: this.hintsAvailable,
      hintsUsed: this.hintsUsed,
      independentFixRate: this.computeIndependentFixRate(),
      struggleScores: [...this.struggleScores],
    };
  }

  /**
   * Independent fix rate: did they resolve it themselves after the
   * counterexample, or did they need the full progressive hint ladder?
   * This is the actual success metric for the whole pitch.
   *
   * = 1.0 if no hints were available (solved independently)
   * = 0.0 if all available hints were consumed
   */
  private computeIndependentFixRate(): number {
    if (this.hintsAvailable === 0) {
      return 1.0;
    }
    const rate = 1 - this.hintsUsed / Math.max(this.hintsAvailable, 1);
    return Math.round(rate * 100) / 100;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SERIALIZATION (crash recovery)
  // ═══════════════════════════════════════════════════════════════════════════

  /** Serialize tracker state for in-progress persistence */
  toJSON(): TrackerState {
    return {
      charactersTyped: this.charactersTyped,
      charactersDeleted: this.charactersDeleted,
      lastChangeTimestamp: this.lastChangeTimestamp,
      pauseCount: this.pauseCount,
      totalPauseDuration: this.totalPauseDuration,
      idleTime: this.idleTime,
      fileSaveCount: this.fileSaveCount,
      fileOpenCount: this.fileOpenCount,
      autoCompileAttempts: this.autoCompileAttempts,
      trackedDocumentUri: this.trackedDocumentUri,
      lastErrorMessage: this.lastErrorMessage,
      currentErrorStreak: this.currentErrorStreak,
      sameErrorPeak: this.sameErrorPeak,
      counterexampleShownTime: this.counterexampleShownTime,
      counterexampleShownCount: this.counterexampleShownCount,
      timeToResolutionAfterCounterexample:
        this.timeToResolutionAfterCounterexample,
      hintsAvailable: this.hintsAvailable,
      hintsUsed: this.hintsUsed,
      struggleScores: this.struggleScores,
      pendingTypedChars: this.pendingTypedChars,
      pendingDeletedChars: this.pendingDeletedChars,
    };
  }

  /**
   * Restore tracker state from crash-recovery data.
   * @param data - Previously saved TrackerState
   * @param timeline - The restored EventTimeline
   */
  static fromJSON(data: TrackerState, timeline: EventTimeline): TelemetryTracker {
    const tracker = new TelemetryTracker(timeline, data.trackedDocumentUri);
    tracker.charactersTyped = data.charactersTyped ?? 0;
    tracker.charactersDeleted = data.charactersDeleted ?? 0;
    tracker.lastChangeTimestamp = data.lastChangeTimestamp ?? Date.now();
    tracker.pauseCount = data.pauseCount ?? 0;
    tracker.totalPauseDuration = data.totalPauseDuration ?? 0;
    tracker.idleTime = data.idleTime ?? 0;
    tracker.fileSaveCount = data.fileSaveCount ?? 0;
    tracker.fileOpenCount = data.fileOpenCount ?? 0;
    tracker.autoCompileAttempts = data.autoCompileAttempts ?? 0;
    tracker.lastErrorMessage = data.lastErrorMessage ?? '';
    tracker.currentErrorStreak = data.currentErrorStreak ?? 0;
    tracker.sameErrorPeak = data.sameErrorPeak ?? 0;
    tracker.counterexampleShownTime = data.counterexampleShownTime ?? null;
    tracker.counterexampleShownCount = data.counterexampleShownCount ?? 0;
    tracker.timeToResolutionAfterCounterexample =
      data.timeToResolutionAfterCounterexample ?? null;
    tracker.hintsAvailable = data.hintsAvailable ?? 0;
    tracker.hintsUsed = data.hintsUsed ?? 0;
    tracker.struggleScores = data.struggleScores ?? [];
    tracker.pendingTypedChars = data.pendingTypedChars ?? 0;
    tracker.pendingDeletedChars = data.pendingDeletedChars ?? 0;
    return tracker;
  }

  /** Clean up all listeners */
  dispose(): void {
    this.flushTypingEvents();
    for (const d of this.disposables) {
      d.dispose();
    }
    this.disposables.length = 0;
  }
}
