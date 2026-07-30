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

  // ── Hints offered vs. used ───────────────────────────────────────────────
  private hintsAvailable: number = 0;
  private hintsUsed: number = 0;

  // ── Struggle score (computed per-event, NOT on timer) ────────────────────
  private struggleScores: StruggleScoreEntry[] = [];

  // ── Typing batch for timeline (display batching only, NOT data) ──────────
  private pendingTypedChars: number = 0;
  private pendingDeletedChars: number = 0;
  
  // ── Proactive Intervention (Mind-Reading) ────────────────────────────────
  private lastProactiveHintTime: number = 0;

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

    if (vscode.window.onDidStartTerminalShellExecution) {
      this.disposables.push(
        vscode.window.onDidStartTerminalShellExecution((e) =>
          this.onTerminalExecutionStart(e)
        )
      );
    }

    // ── Diagnostics (Compile Errors) ──────────────────────────────────────────
    this.disposables.push(
      vscode.languages.onDidChangeDiagnostics((e) => this.onDiagnosticsChange(e))
    );

    // ── Debug Sessions (Runtime Errors) ───────────────────────────────────────
    this.disposables.push(
      vscode.debug.onDidTerminateDebugSession((session) => this.onDebugSessionEnd(session))
    );

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

        this.timeline.push(EventType.PauseDetected, 'automatic', {
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
      this.timeline.push(EventType.Typed, 'automatic', { chars: this.pendingTypedChars });
      this.pendingTypedChars = 0;
    }
    if (this.pendingDeletedChars > 0) {
      this.timeline.push(EventType.Deleted, 'automatic', {
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
    this.timeline.push(EventType.FileSaved, 'automatic');
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
      this.timeline.push(EventType.FileSwitched, 'automatic', {
        file: editor.document.fileName,
      });
    }
  }

  /** Handle auto-detected task/compile starts */
  private onTaskStart(e: vscode.TaskProcessStartEvent): void {
    this.autoCompileAttempts++;
    this.timeline.push(EventType.TaskStarted, 'automatic', {
      task: e.execution.task.name,
    });
  }

  /** Handle task process endings (independent of terminal shell integration) */
  private onTaskEnd(e: vscode.TaskProcessEndEvent): void {
    const taskName = e.execution.task.name.toLowerCase();
    const exitCode = e.exitCode;
    if (exitCode === undefined) {
      return;
    }

    const isCompile = taskName.includes('compile') || taskName.includes('build') || taskName.includes('g++') || taskName.includes('gcc') || taskName.includes('clang');
    const isRun = taskName.includes('run') || taskName.includes('execute') || taskName.includes('play');

    const now = Date.now();
    if (now - this.lastTerminalCommandTime < TelemetryTracker.TERMINAL_DEDUP_MS) {
      return; // Already recorded via terminal execution event
    }
    this.lastTerminalCommandTime = now;

    if (isCompile) {
      if (exitCode === 0) {
        this.recordCompileSuccess('automatic');
      } else {
        this.recordCompileError(`Task ${e.execution.task.name} failed (exit ${exitCode})`, 'automatic');
      }
    } else if (isRun) {
      if (exitCode === 0) {
        this.recordSuccessfulRun('automatic');
      } else {
        this.recordRuntimeError(`Task ${e.execution.task.name} failed (exit ${exitCode})`, 'automatic');
      }
    }
  }

  /**
   * Approach 1: Shell Integration exit-code handler.
   * Only fires when the terminal's shell integration script is injected.
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
      return; // Already recorded via Approach 2 (streaming)
    }
    this.lastTerminalCommandTime = now;

    // Handle compound commands (e.g. compile && run)
    if (isCompile && isRun) {
      if (exitCode === 0) {
        this.recordCompileSuccess('automatic');
        this.recordSuccessfulRun('automatic');
      } else {
        // If it failed, check if it was a compile error or runtime error
        // We'll default to runtime error if we don't detect compiler errors
        this.recordRuntimeError(
          `Compound command failed: ${e.execution.commandLine.value} (exit ${exitCode})`, 'automatic'
        );
      }
      return;
    }

    if (isCompile) {
      exitCode === 0 ? this.recordCompileSuccess('automatic') : this.recordCompileError(
        `${e.execution.commandLine.value} (exit ${exitCode})`, 'automatic'
      );
    } else {
      exitCode === 0 ? this.recordSuccessfulRun('automatic') : this.recordRuntimeError(
        `${e.execution.commandLine.value} (exit ${exitCode})`, 'automatic'
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
      // Stream ended or terminal closed
    }

    const now = Date.now();
    if (now - this.lastTerminalCommandTime < TelemetryTracker.TERMINAL_DEDUP_MS) {
      return; // Already recorded
    }

    const buf = outputBuffer.toLowerCase();
    
    // Check if the command line was a compound compile-and-run command
    const cmd = execution.commandLine.value.toLowerCase();
    const isCompound = this.isCompileCommand(cmd) && this.isRunCommand(cmd);

    this.lastTerminalCommandTime = now;

    if (isCompound) {
      const hasCompileError = this.bufferHasError(buf, 'compile');
      const hasRuntimeError = this.bufferHasError(buf, 'run');
      
      if (hasCompileError) {
        this.recordCompileError('compound compile error detected from output', 'automatic');
      } else if (hasRuntimeError) {
        this.recordCompileSuccess('automatic');
        this.recordRuntimeError('compound runtime error detected from output', 'automatic');
      } else {
        this.recordCompileSuccess('automatic');
        this.recordSuccessfulRun('automatic');
      }
      return;
    }

    const hasError = this.bufferHasError(buf, cmdType);

    if (cmdType === 'compile') {
      hasError ? this.recordCompileError('auto-detected from output', 'automatic') : this.recordCompileSuccess('automatic');
    } else {
      hasError ? this.recordRuntimeError('auto-detected from output', 'automatic') : this.recordSuccessfulRun('automatic');
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
        buf.includes('syntaxerror') ||         // Python/JS
        buf.includes('nameerror') ||           // Python
        buf.includes('cannot find symbol') ||  // Java
        buf.includes('fatal error:') ||        // PHP / Swift / C++
        buf.includes('^~~~') ||                // clang
        buf.includes('^---')
      );
    } else {
      return (
        buf.includes('traceback (most recent call last)') || // Python
        buf.includes('exception in thread') ||               // Java
        buf.includes('unhandled exception') ||               // C# / .NET
        buf.includes('segmentation fault') ||
        buf.includes('segfault') ||
        buf.includes('uncaughtexception') ||                 // Node.js
        buf.includes('error: panicked') ||                   // Rust
        buf.includes('panic:') ||                            // Go
        buf.includes('fatal error:') ||                      // PHP / Swift / Go
        buf.includes('aborted (core dumped)') ||
        buf.includes('division by zero') ||                  // C++ / generic division error
        buf.includes('zero division') ||
        buf.includes('arithmetic exception') ||
        buf.includes('floating point exception')             // C++ division by zero signal
      );
    }
  }

  // ── Command classifier helpers ────────────────────────────────────────────

  private isCompileCommand(cmd: string): boolean {
    return (
      cmd.includes('g++') ||
      cmd.includes('gcc ') ||
      cmd.includes('clang ') ||
      cmd.includes('javac ') ||
      cmd.includes('cargo build') ||
      cmd.includes('rustc ') ||
      cmd.includes('go build') ||
      cmd.includes('dotnet build') ||
      cmd.includes('csc ') ||
      cmd.includes('tsc ') ||
      cmd.includes('kotlinc ') ||
      cmd.includes('swiftc ') ||
      cmd.includes('npm run build') ||
      cmd.includes('make') ||
      cmd.includes('cmake') ||
      cmd.includes('msbuild') ||
      cmd.includes(' cl ')
    );
  }

  private isRunCommand(cmd: string): boolean {
    return (
      cmd.includes('./a.out') ||
      cmd.includes('./a.exe') ||
      cmd.includes('.\\a.exe') ||
      cmd.includes('.\\main.exe') ||
      cmd.includes('.\\main') ||
      cmd.includes('\\test') ||           // covers .\test, .\test.exe
      cmd.includes('./test') ||
      cmd.includes('python ') ||
      cmd.includes('python3 ') ||
      cmd.includes('node ') ||
      cmd.includes('java ') ||
      cmd.includes('cargo run') ||
      cmd.includes('go run') ||
      cmd.includes('dotnet run') ||
      cmd.includes('ruby ') ||
      cmd.includes('php ') ||
      cmd.includes('perl ') ||
      cmd.includes('swift ') ||
      cmd.includes('kotlin ') ||
      cmd.includes('dart ') ||
      cmd.includes('npm start') ||
      cmd.includes('npm run start')
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // MANUAL EVENT HANDLERS (called from SessionManager)
  // ═══════════════════════════════════════════════════════════════════════════

  /** Record a successful compile (manual button) */
  recordCompileSuccess(source: 'automatic' | 'manual' = 'manual'): void {
    this.flushTypingEvents();
    this.lastErrorMessage = '';
    this.currentErrorStreak = 0;
    this.timeline.push(EventType.CompileSuccess, source);
    this.computeStruggleScore(EventType.CompileSuccess);
  }

  /** Record a compile error (manual button) */
  recordCompileError(errorMessage?: string, source: 'automatic' | 'manual' = 'manual'): void {
    this.flushTypingEvents();
    this.trackErrorRepetition(errorMessage);
    this.timeline.push(
      EventType.CompileError,
      source,
      errorMessage ? { error: errorMessage } : undefined
    );
    this.computeStruggleScore(EventType.CompileError);
  }

  /** Record a successful run (manual button) */
  recordSuccessfulRun(source: 'automatic' | 'manual' = 'manual'): void {
    this.flushTypingEvents();
    this.lastErrorMessage = '';
    this.currentErrorStreak = 0;
    this.timeline.push(EventType.SuccessfulRun, source);
    this.computeStruggleScore(EventType.SuccessfulRun);
  }

  /** Record a runtime error (manual button) */
  recordRuntimeError(errorMessage?: string, source: 'automatic' | 'manual' = 'manual'): void {
    this.flushTypingEvents();
    this.trackErrorRepetition(errorMessage);
    this.timeline.push(
      EventType.RuntimeError,
      source,
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
    this.timeline.push(type, 'manual');
    this.computeStruggleScore(type);
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
      this.timeline.push(EventType.SameErrorRepeated, 'automatic', {
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

    // Proactive "Mind-Reading" Intervention
    const now = Date.now();
    // Trigger if score > 0.65, we have passed 60s, and haven't prompted in the last 2 mins
    if (score > 0.65 && elapsed > 60 && (now - this.lastProactiveHintTime > 120000)) {
        this.lastProactiveHintTime = now;
        vscode.window.showInformationMessage(
            "Cognitive Coach: It looks like you might be stuck. Would you like a hint?", 
            "Yes, please", "No, thanks"
        ).then(selection => {
            if (selection === "Yes, please") {
                vscode.commands.executeCommand('cognitiveCoach.getRecommendation');
            }
        });
    }
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
      hintsAvailable: this.hintsAvailable,
      hintsUsed: this.hintsUsed,
      independentFixRate: this.computeIndependentFixRate(),
      struggleScores: [...this.struggleScores],
    };
  }

  // ── Diagnostics & Debug Runtime Errors ─────────────────────────────────────
  
  private onDiagnosticsChange(e: vscode.DiagnosticChangeEvent): void {
    if (!this.trackedDocumentUri) return;
    
    // Check if the change affected our tracked document
    const uri = vscode.Uri.parse(this.trackedDocumentUri);
    if (e.uris.some(u => u.toString() === uri.toString())) {
      const diagnostics = vscode.languages.getDiagnostics(uri);
      // Filter for errors (Severity 0 is Error in VS Code)
      const errors = diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Error);
      
      if (errors.length > 0) {
        this.recordCompileError(errors[0].message, 'automatic');
      }
    }
  }

  private onDebugSessionEnd(session: vscode.DebugSession): void {
    this.recordRuntimeError(`Debug session ended: ${session.name}`, 'automatic');
  }

  /**
  * Independent fix rate: did they solve it without relying on hints, or did
  * they need the full progressive hint ladder?
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
