/**
 * @file SessionManager.ts
 * Central orchestrator for session lifecycle.
 *
 * Responsibilities:
 * - Start/end sessions with input collection
 * - Wire up TelemetryTracker and EventTimeline
 * - Compute session summary at end
 * - Periodic crash-recovery persistence
 * - Expose state for sidebar UI refresh
 * - Handle "already recording" guard
 */

import * as vscode from 'vscode';
import {
  Session,
  SessionStatus,
  Difficulty,
  HintCounts,
  EventType,
  SidebarState,
  InProgressData,
  RecommendationResult,
  RecommendationStatus,
} from '../types';
import { EventTimeline } from '../telemetry/EventTimeline';
import { TelemetryTracker } from '../telemetry/TelemetryTracker';
import { SessionPersistence } from './SessionPersistence';
import { generateUUID } from '../utils/uuid';
import { SCHEMA_VERSION, PERSIST_INTERVAL_MS } from '../constants';
import { backendClient, BackendError } from '../backendClient';
import { buildRecommendationRequest, buildSnapshot } from '../recommendation';
import { isAutoRecommendEnabled } from '../config';

export class SessionManager {
  private session: Session | null = null;
  private timeline: EventTimeline | null = null;
  private tracker: TelemetryTracker | null = null;
  private trackedDocumentUri?: string;
  private persistTimer: ReturnType<typeof setInterval> | null = null;
  private readonly persistence: SessionPersistence;

  // ── Backend recommendation state ─────────────────────────────────────────
  // Surfaced through getState() so SidebarProvider's existing polling loop
  // picks it up automatically — no separate push channel needed.
  private recommendation: RecommendationResult | null = null;
  private recommendationStatus: RecommendationStatus = 'idle';
  private recommendationError: string | null = null;

  /** Callback fired on status changes — used by SidebarProvider to refresh */
  private statusChangeCallback: ((status: SessionStatus) => void) | null = null;

  constructor() {
    this.persistence = new SessionPersistence();
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // PUBLIC GETTERS
  // ═══════════════════════════════════════════════════════════════════════════

  /** Current session status */
  get status(): SessionStatus {
    if (this.session?.status === 'Recording') {
      return 'Recording';
    }
    return this.session ? (this.session.status as SessionStatus) : 'Idle';
  }

  /** Whether a session is currently active */
  get isRecording(): boolean {
    return this.status === 'Recording';
  }

  /** Current session (read-only) */
  get currentSession(): Session | null {
    return this.session;
  }

  /** Elapsed seconds in current session */
  get elapsedSeconds(): number {
    return this.timeline?.getElapsedSeconds() ?? 0;
  }

  /** Register a callback for status changes */
  onStatusChange(callback: (status: SessionStatus) => void): void {
    this.statusChangeCallback = callback;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // START PROBLEM
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Start a new problem session. Shows sequential input boxes for:
   * Problem Name → Difficulty → Language → Student ID (optional).
   *
   * If a session is already active, prompts the user to end it first.
   * @returns true if a new session was started successfully
   */
  async startProblem(): Promise<boolean> {
    // Guard: already recording?
    if (this.isRecording) {
      const choice = await vscode.window.showWarningMessage(
        'A session is already active. End it first?',
        'End Current Session',
        'Cancel'
      );
      if (choice === 'End Current Session') {
        await this.endProblem('Ended_incomplete');
      } else {
        return false;
      }
    }

    // ── Collect problem info via sequential input boxes ─────────────────
    const problemName = await vscode.window.showInputBox({
      prompt: 'Problem Name',
      placeHolder: 'e.g. Two Sum, Reverse Linked List',
      ignoreFocusOut: true,
    });
    if (!problemName) {
      return false;
    }

    const difficulty = (await vscode.window.showQuickPick(
      ['Easy', 'Medium', 'Hard'],
      {
        placeHolder: 'Select difficulty',
        ignoreFocusOut: true,
      }
    )) as Difficulty | undefined;
    if (!difficulty) {
      return false;
    }

    const activeEditor = vscode.window.activeTextEditor;
    const defaultLang = activeEditor?.document.languageId ?? '';
    const language = await vscode.window.showInputBox({
      prompt: 'Programming Language',
      value: defaultLang,
      ignoreFocusOut: true,
    });
    if (language === undefined) {
      return false;
    }

    const studentId = await vscode.window.showInputBox({
      prompt: 'Student ID (optional — press Enter to skip)',
      placeHolder: 'Optional',
      ignoreFocusOut: true,
    });
    if (studentId === undefined) {
      return false;
    }

    // ── Initialize session ─────────────────────────────────────────────
    const now = Date.now();
    const trackedUri = activeEditor?.document.uri.toString();
    this.trackedDocumentUri = trackedUri;

    this.timeline = new EventTimeline(now);
    this.tracker = new TelemetryTracker(this.timeline, trackedUri);

    this.session = this.createEmptySession({
      problemName,
      difficulty,
      topic: '',
      subtopic: '',
      estMins: null,
      language: language || defaultLang || 'unknown',
      studentId: studentId || '',
      startTime: new Date(now).toISOString(),
    });

    // Reset any recommendation left over from a previous session
    this.recommendation = null;
    this.recommendationStatus = 'idle';
    this.recommendationError = null;

    // Attach listeners
    this.tracker.attach();

    // Push start event
    this.timeline.push(EventType.ProblemStarted, 'manual');

    // Start periodic crash-recovery persistence
    this.startPersistTimer();

    // Notify
    this.statusChangeCallback?.('Recording');
    vscode.window.showInformationMessage(
      `🎯 Recording started: ${problemName}`
    );

    return true;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // END PROBLEM
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * End the current session with the given status.
   * Computes summary, saves to disk, cleans up listeners and timers.
   *
   * @param forcedStatus - Use to bypass QuickPick (e.g. 'Ended_incomplete' during shutdown)
   * @returns true if a session was ended
   */
  async endProblem(
    forcedStatus?: 'Ended_incomplete'
  ): Promise<boolean> {
    if (!this.session || !this.timeline || !this.tracker) {
      vscode.window.showWarningMessage('No active session to end.');
      return false;
    }

    let finalStatus = forcedStatus as SessionStatus | undefined;
    let minHelp = 0;
    let outcomeReason = '';

    if (!finalStatus) {
      const pick = await vscode.window.showQuickPick([
        'Solved independently',
        'Solved after Hint 1',
        'Solved after Hint 2',
        'Solved after Concept',
        'Solved after Pseudocode',
        'Solved after Full Solution',
        'Couldn\'t solve',
        'Stopped because of time',
        'Other'
      ], { placeHolder: 'How did this session end?', ignoreFocusOut: true });

      if (!pick) {
        return false; // user cancelled ending the problem
      }

      switch(pick) {
        case 'Solved independently': finalStatus = 'Solved'; minHelp = 0; break;
        case 'Solved after Hint 1': finalStatus = 'Solved_With_Hint1'; minHelp = 1; break;
        case 'Solved after Hint 2': finalStatus = 'Solved_With_Hint2'; minHelp = 2; break;
        case 'Solved after Concept': finalStatus = 'Solved_With_Concept'; minHelp = 3; break;
        case 'Solved after Pseudocode': finalStatus = 'Solved_With_Pseudocode'; minHelp = 4; break;
        case 'Solved after Full Solution': finalStatus = 'Solved_With_Solution'; minHelp = 5; break;
        case 'Couldn\'t solve': finalStatus = 'Could_Not_Solve'; minHelp = 6; break;
        case 'Stopped because of time': finalStatus = 'Stopped_Time'; minHelp = 6; break;
        case 'Other': finalStatus = 'Stopped_Other'; minHelp = 6; break;
      }
      outcomeReason = pick;
    }

    this.session.outcome = {
      final_status: finalStatus || 'Ended_incomplete',
      minimum_help_required: minHelp,
      reason: outcomeReason
    };

    // Finalize tracker (accounts for trailing idle time)
    this.tracker.finalize();

    // Push end event
    if (finalStatus?.startsWith('Solved')) {
      this.timeline.push(EventType.ProblemSolved, 'manual');
    } else if (finalStatus === 'Could_Not_Solve' || finalStatus?.startsWith('Stopped')) {
      this.timeline.push(EventType.ProblemAbandoned, 'manual');
    } else {
      this.timeline.push(EventType.ProblemEnded, 'manual');
    }

    // ── Compute session summary ──────────────────────────────────────────
    const metrics = this.tracker.getMetrics();
    const elapsed = this.timeline.getElapsedSeconds();

    this.session.end_time = new Date().toISOString();
    this.session.time_spent = elapsed;
    this.session.idle_time = metrics.idleTime;

    this.session.characters_typed = metrics.charactersTyped;
    this.session.characters_deleted = metrics.charactersDeleted;
    this.session.deletion_ratio = metrics.deletionRatio;
    this.session.typing_speed = metrics.typingSpeed;

    this.session.pause_count = metrics.pauseCount;
    this.session.pause_duration = metrics.totalPauseDuration;

    this.session.file_save_count = metrics.fileSaveCount;
    this.session.file_open_count = metrics.fileOpenCount;

    this.session.compile_attempts =
      this.timeline.getEventCount(EventType.CompileSuccess) +
      this.timeline.getEventCount(EventType.CompileError);
    this.session.compile_errors = this.timeline.getEventCount(
      EventType.CompileError
    );
    this.session.successful_runs = this.timeline.getEventCount(
      EventType.SuccessfulRun
    );
    this.session.runtime_errors = this.timeline.getEventCount(
      EventType.RuntimeError
    );
    this.session.auto_compile_attempts = metrics.autoCompileAttempts;

    this.session.hints_requested = this.computeHintCounts();
    this.session.hints_available = metrics.hintsAvailable;
    this.session.hints_used = metrics.hintsUsed;
    this.session.independent_fix_rate = metrics.independentFixRate;

    this.session.same_error_peak = metrics.sameErrorPeak;
    this.session.struggle_scores = metrics.struggleScores;

    this.session.counterexample_shown_count = metrics.counterexampleShownCount;
    this.session.time_to_resolution_after_counterexample =
      metrics.timeToResolutionAfterCounterexample;

    this.session.status = finalStatus || 'Ended_incomplete';
    
    // ML derived metrics
    const hesitationIndex = elapsed > 0 ? metrics.totalPauseDuration / elapsed : 0;
    const editingIntensity = metrics.charactersTyped > 0 ? metrics.charactersDeleted / metrics.charactersTyped : 0;
    const helpDependencyScore = metrics.hintsAvailable > 0 ? metrics.hintsUsed / metrics.hintsAvailable : 0;
    const compileAttempts = (this.session.compile_attempts || 0);
    const compileFailureRate = compileAttempts > 0 ? (this.session.compile_errors || 0) / compileAttempts : 0;
    const avgPause = metrics.pauseCount > 0 ? metrics.totalPauseDuration / metrics.pauseCount : 0;

    this.session.derived_metrics = {
      hesitation_index: hesitationIndex,
      editing_intensity: editingIntensity,
      help_dependency_score: helpDependencyScore,
      compile_failure_rate: compileFailureRate,
      average_pause_duration: avgPause
    };

    // Sanitize absolute file paths
    this.session.timeline = this.timeline.toJSON().map(e => {
      if (e.meta && typeof e.meta.file === 'string') {
        e.meta.file = e.meta.file.split(/[/\\]/).pop();
      }
      return e;
    });

    // ── Save and clean up ────────────────────────────────────────────────
    const savedUri = await this.persistence.saveSession(this.session);
    await this.persistence.deleteInProgress();

    this.stopPersistTimer();
    this.tracker.dispose();

    const problemName = this.session.problem_name;
    this.session = null;
    this.timeline = null;
    this.tracker = null;

    // Notify
    this.statusChangeCallback?.('Idle');

    if (savedUri) {
      vscode.window.showInformationMessage(
        `Session ended (${finalStatus}): ${problemName} — saved to dataset/`
      );
    }

    return true;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // MANUAL EVENT RECORDING
  // ═══════════════════════════════════════════════════════════════════════════

  /** Record a compile success (manual button / command palette) */
  recordCompileSuccess(): void {
    if (!this.tracker) { return; }
    this.tracker.recordCompileSuccess();
    this.persistInProgressNow();
  }

  /** Record a compile error (manual button / command palette) */
  recordCompileError(): void {
    if (!this.tracker) { return; }
    this.tracker.recordCompileError();
    this.persistInProgressNow();
    this.maybeAutoRequestRecommendation();
  }

  /** Record a successful run (manual button / command palette) */
  recordSuccessfulRun(): void {
    if (!this.tracker) { return; }
    this.tracker.recordSuccessfulRun();
    this.persistInProgressNow();
  }

  /** Record a runtime error (manual button / command palette) */
  recordRuntimeError(): void {
    if (!this.tracker) { return; }
    this.tracker.recordRuntimeError();
    this.persistInProgressNow();
    this.maybeAutoRequestRecommendation();
  }

  /**
   * Record a hint request at the given level.
   * @param type - The specific hint EventType
   */
  recordHint(type: EventType): void {
    if (!this.tracker) { return; }
    this.tracker.recordHint(type);
    this.persistInProgressNow();
    this.maybeAutoRequestRecommendation(type);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // BACKEND RECOMMENDATION (POST /predict/full → POST /recommend)
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Fire-and-forget wrapper used by struggle-signalling events (compile
   * error, runtime error, hint request) to automatically refresh the
   * recommendation, gated by the `cognitiveCoach.autoRecommend` setting.
   * Errors are swallowed here since requestRecommendation() already reports
   * them through recommendationStatus/recommendationError for the UI.
   */
  private maybeAutoRequestRecommendation(explicitHintType?: EventType): void {
    if (!isAutoRecommendEnabled() && !explicitHintType) {
      return;
    }
    void this.requestRecommendation(explicitHintType);
  }

  /**
   * Collect the current telemetry snapshot, send it through the backend's
   * ML pipeline (POST /predict/full) and Recommendation Engine
   * (POST /recommend), and store the result for the sidebar to display.
   *
   * Safe to call repeatedly — each call fully replaces the previous
   * recommendation/error state. Backend failures are caught and surfaced
   * via recommendationStatus/recommendationError rather than thrown, so a
   * down backend never disrupts telemetry collection or session recording.
   */
  async requestRecommendation(explicitHintType?: EventType): Promise<void> {
    if (!this.session || !this.tracker || !this.timeline) {
      vscode.window.showWarningMessage(
        'No active session. Start a problem first.'
      );
      return;
    }

    this.recommendationStatus = 'loading';
    this.recommendationError = null;

    try {
      let studentCode = '';
      if (this.trackedDocumentUri) {
        const doc = vscode.workspace.textDocuments.find(
          (d) => d.uri.toString() === this.trackedDocumentUri
        );
        if (doc) studentCode = doc.getText();
      }
      if (!studentCode) {
        studentCode = vscode.window.activeTextEditor?.document.getText() ?? '';
      }

      const snapshot = buildSnapshot(this.session, this.tracker, this.timeline);
      const fullPrediction = await backendClient.predictFull(snapshot);
      const recommendationRequest = buildRecommendationRequest(
        this.session,
        snapshot,
        studentCode,
        fullPrediction,
        explicitHintType
      );
      const recommendation = await backendClient.recommend(
        recommendationRequest
      );

      this.recommendation = recommendation;
      this.recommendationStatus = 'idle';
      this.recommendationError = null;
    } catch (err) {
      this.recommendationStatus = 'error';
      this.recommendationError =
        err instanceof BackendError
          ? err.message
          : err instanceof Error
          ? err.message
          : 'Unknown error contacting the Cognitive Coach backend.';

      vscode.window.showWarningMessage(
        `Cognitive Coach backend unavailable: ${this.recommendationError}`
      );
    }
  }

  /**
   * Show a counterexample (placeholder — logs event + shows dummy test case).
   * Person B replaces the dummy data with a real Gemini API call on Day 2–3.
   */
  recordCounterexampleShown(): void {
    if (!this.tracker) { return; }
    this.tracker.recordCounterexampleShown();
    this.persistInProgressNow();

    // Placeholder: show a dummy counterexample in an info message
    vscode.window.showInformationMessage(
      '⚡ Counterexample: Input=[2,7,11,15], Target=9 → Expected=[0,1]\n' +
        '(Placeholder — real test case generation coming Day 2–3)'
    );
  }

  /** Record that the student resolved the counterexample */
  recordCounterexampleResolved(): void {
    if (!this.tracker) { return; }
    this.tracker.recordCounterexampleResolved();
    this.persistInProgressNow();
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // CRASH RECOVERY
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Check for an in-progress session file on activation.
   * If found, prompt the user to recover or discard it.
   */
  async checkForRecovery(): Promise<void> {
    const recovered = await this.persistence.loadInProgress();
    if (!recovered) {
      return;
    }

    const choice = await vscode.window.showWarningMessage(
      `Found an unfinished session: "${recovered.session.problem_name}". What would you like to do?`,
      'Recover & Save',
      'Discard'
    );

    if (choice === 'Recover & Save') {
      const session = recovered.session;
      session.status = 'Ended_incomplete';
      session.end_time = new Date().toISOString();
      session.time_spent = session.time_spent || 0;
      session.timeline = session.timeline || [];
      await this.persistence.saveSession(session);
      vscode.window.showInformationMessage(
        `✅ Recovered session "${session.problem_name}" saved to dataset/`
      );
    }

    await this.persistence.deleteInProgress();
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // EXPORT LAST SESSION
  // ═══════════════════════════════════════════════════════════════════════════

  /** Re-export the last saved session as a new JSON file */
  async exportLastSession(): Promise<void> {
    const lastSession = await this.persistence.getLastSession();
    if (lastSession) {
      const uri = await this.persistence.saveSession(lastSession, true);
      if (uri) {
        vscode.window.showInformationMessage('📤 Session re-exported to dataset/');
      }
    } else {
      vscode.window.showWarningMessage('No session found to export.');
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SIDEBAR STATE
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Get a snapshot of the current state for the sidebar UI.
   * Called on a timer (UI_REFRESH_INTERVAL_MS) — rendering optimization only.
   */
  getState(): SidebarState {
    if (!this.session || !this.tracker || !this.timeline) {
      return {
        status: 'Idle',
        elapsedSeconds: 0,
        problemName: '',
        charactersTyped: 0,
        charactersDeleted: 0,
        pauseCount: 0,
        compileAttempts: 0,
        compileErrors: 0,
        successfulRuns: 0,
        runtimeErrors: 0,
        hintsRequested: { hint1: 0, hint2: 0, concept: 0, pseudocode: 0, solution: 0 },
        currentStruggleScore: 0,
        struggleScores: [],
        recommendationStatus: 'idle',
        recommendation: null,
        recommendationError: null,
      };
    }

    const metrics = this.tracker.getMetrics();
    const scores = metrics.struggleScores;

    return {
      status: 'Recording',
      elapsedSeconds: this.timeline.getElapsedSeconds(),
      problemName: this.session.problem_name,
      charactersTyped: metrics.charactersTyped,
      charactersDeleted: metrics.charactersDeleted,
      pauseCount: metrics.pauseCount,
      compileAttempts:
        this.timeline.getEventCount(EventType.CompileSuccess) +
        this.timeline.getEventCount(EventType.CompileError),
      compileErrors: this.timeline.getEventCount(EventType.CompileError),
      successfulRuns: this.timeline.getEventCount(EventType.SuccessfulRun),
      runtimeErrors: this.timeline.getEventCount(EventType.RuntimeError),
      hintsRequested: this.computeHintCounts(),
      currentStruggleScore:
        scores.length > 0 ? scores[scores.length - 1].score : 0,
      struggleScores: scores,
      recommendationStatus: this.recommendationStatus,
      recommendation: this.recommendation,
      recommendationError: this.recommendationError,
    };
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // PERSISTENCE TIMER
  // ═══════════════════════════════════════════════════════════════════════════

  /** Start the periodic crash-recovery persistence timer */
  private startPersistTimer(): void {
    this.persistTimer = setInterval(() => {
      this.persistInProgressNow();
    }, PERSIST_INTERVAL_MS);
  }

  /** Stop the persistence timer */
  private stopPersistTimer(): void {
    if (this.persistTimer) {
      clearInterval(this.persistTimer);
      this.persistTimer = null;
    }
  }

  /** Persist current session state immediately (for crash recovery) */
  private async persistInProgressNow(): Promise<void> {
    if (!this.session || !this.timeline || !this.tracker) {
      return;
    }

    // Snapshot current state
    const metrics = this.tracker.getMetrics();
    this.session.time_spent = this.timeline.getElapsedSeconds();
    this.session.characters_typed = metrics.charactersTyped;
    this.session.characters_deleted = metrics.charactersDeleted;
    this.session.timeline = this.timeline.toJSON();

    const data: InProgressData = {
      session: { ...this.session },
      trackerState: this.tracker.toJSON(),
    };

    await this.persistence.persistInProgress(data);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // HELPERS
  // ═══════════════════════════════════════════════════════════════════════════

  /** Compute hint counts from the timeline */
  private computeHintCounts(): HintCounts {
    if (!this.timeline) {
      return { hint1: 0, hint2: 0, concept: 0, pseudocode: 0, solution: 0 };
    }
    return {
      hint1: this.timeline.getEventCount(EventType.Hint1Requested),
      hint2: this.timeline.getEventCount(EventType.Hint2Requested),
      concept: this.timeline.getEventCount(EventType.ConceptHintRequested),
      pseudocode: this.timeline.getEventCount(EventType.PseudocodeRequested),
      solution: this.timeline.getEventCount(EventType.SolutionRequested),
    };
  }

  private createEmptySession(opts: {
    problemName: string;
    difficulty: Difficulty;
    topic: string;
    subtopic: string;
    estMins: number | null;
    language: string;
    studentId: string;
    startTime: string;
  }): Session {
    return {
      schema_version: SCHEMA_VERSION,
      session_id: generateUUID(),
      problem_name: opts.problemName,
      difficulty: opts.difficulty,
      language: opts.language,
      student_id: opts.studentId,
      start_time: opts.startTime,
      end_time: '',
      problem: {
        topic: opts.topic,
        subtopic: opts.subtopic,
        difficulty: opts.difficulty,
        estimated_minutes: opts.estMins,
      },
      outcome: null,
      derived_metrics: null,
      time_spent: 0,
      idle_time: 0,
      characters_typed: 0,
      characters_deleted: 0,
      deletion_ratio: 0,
      typing_speed: 0,
      pause_count: 0,
      pause_duration: 0,
      file_save_count: 0,
      file_open_count: 0,
      compile_attempts: 0,
      compile_errors: 0,
      successful_runs: 0,
      runtime_errors: 0,
      auto_compile_attempts: 0,
      hints_requested: { hint1: 0, hint2: 0, concept: 0, pseudocode: 0, solution: 0 },
      hints_available: 0,
      hints_used: 0,
      independent_fix_rate: 1.0,
      same_error_peak: 0,
      struggle_scores: [],
      counterexample_shown_count: 0,
      time_to_resolution_after_counterexample: null,
      status: 'Recording',
      timeline: [],
    };
  }

  /**
   * Graceful shutdown: end active session as Ended_incomplete.
   * Called from extension.deactivate().
   */
  async dispose(): Promise<void> {
    if (this.isRecording) {
      await this.endProblem('Ended_incomplete');
    }
  }
}
