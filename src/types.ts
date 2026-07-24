/**
 * @file types.ts
 * All TypeScript interfaces, enums, and type aliases for the Cognitive Coach extension.
 * This is the single source of truth for the data schema.
 */

// ─── Event Type Enum ───────────────────────────────────────────────────────────

/**
 * All possible event types in the unified timeline.
 * Both automatic (text changes, pauses, saves) and manual (compile, hints)
 * events share this single enum — enforced at compile time, not free strings.
 */
export enum EventType {
  // Session lifecycle
  ProblemStarted = 'problem_started',
  ProblemSolved = 'problem_solved',
  ProblemAbandoned = 'problem_abandoned',
  ProblemEnded = 'problem_ended',

  // Automatic text events (batched in timeline, raw for metrics)
  Typed = 'typed',
  Deleted = 'deleted',

  // Automatic file events
  FileSaved = 'file_saved',
  FileSwitched = 'file_switched',

  // Automatic timing events
  PauseDetected = 'pause_detected',

  // Manual compile/run events
  CompileSuccess = 'compile_success',
  CompileError = 'compile_error',
  SuccessfulRun = 'successful_run',
  RuntimeError = 'runtime_error',

  // Auto-detected compile/run via VS Code task system
  TaskStarted = 'task_started',

  // Manual hint events
  Hint1Requested = 'hint1_requested',
  Hint2Requested = 'hint2_requested',
  ConceptHintRequested = 'concept_hint_requested',
  PseudocodeRequested = 'pseudocode_requested',
  SolutionRequested = 'solution_requested',

  // Counterexample events (placeholder buttons wired Day 1, AI drop-in Day 2–3)
  CounterexampleShown = 'counterexample_shown',
  CounterexampleResolved = 'counterexample_resolved',

  // Error pattern tracking
  SameErrorRepeated = 'same_error_repeated',
}

// ─── Timeline ──────────────────────────────────────────────────────────────────

/**
 * A single entry in the unified event timeline.
 * Time is seconds elapsed since session start. Both automatic and manual
 * events share this same structure — one array, one schema.
 */
export interface TimelineEvent {
  /** Seconds elapsed since session start */
  time: number;
  /** The type of event */
  event: EventType;
  /** Optional metadata specific to this event type */
  meta?: Record<string, unknown>;
}

// ─── Session Metadata ──────────────────────────────────────────────────────────

/** Session status states */
export type SessionStatus = 'Idle' | 'Recording' | 'Solved' | 'Abandoned' | 'Ended_incomplete';

/** Difficulty levels for problems */
export type Difficulty = 'Easy' | 'Medium' | 'Hard';

/** Breakdown of hint requests by level */
export interface HintCounts {
  hint1: number;
  hint2: number;
  concept: number;
  pseudocode: number;
  solution: number;
}

// ─── Struggle Score ────────────────────────────────────────────────────────────

/**
 * A single struggle-score data point, computed on every meaningful event
 * (compile error, pause end, hint request) — NOT on a fixed timer.
 * This produces responsive spikes that match the exact moment things go wrong.
 */
export interface StruggleScoreEntry {
  /** Seconds elapsed since session start */
  time: number;
  /** Normalized score (0.0 = no struggle, 1.0 = maximum struggle) */
  score: number;
  /** The event that triggered this computation */
  trigger: EventType;
}

// ─── Session (full output schema) ──────────────────────────────────────────────

/**
 * Full session data matching the output JSON schema.
 * One of these is written per session to dataset/session_YYYYMMDD_HHMMSS.json.
 */
export interface Session {
  schema_version: string;
  session_id: string;
  problem_name: string;
  difficulty: Difficulty;
  language: string;
  student_id: string;
  start_time: string;
  end_time: string;

  // Time metrics
  time_spent: number;
  idle_time: number;

  // Text metrics
  characters_typed: number;
  characters_deleted: number;
  deletion_ratio: number;
  typing_speed: number;

  // Pause metrics
  pause_count: number;
  pause_duration: number;

  // File metrics
  file_save_count: number;
  file_open_count: number;

  // Compile/run metrics (manual)
  compile_attempts: number;
  compile_errors: number;
  successful_runs: number;
  runtime_errors: number;

  // Compile/run metrics (auto-detected via task system, kept separate)
  auto_compile_attempts: number;

  // Hint metrics
  hints_requested: HintCounts;
  hints_available: number;
  hints_used: number;
  independent_fix_rate: number;

  // Error pattern metrics
  same_error_peak: number;

  // Struggle score (array, not just final — your best demo visual)
  struggle_scores: StruggleScoreEntry[];

  // Counterexample metrics
  counterexample_shown_count: number;
  time_to_resolution_after_counterexample: number | null;

  // Status and timeline
  status: SessionStatus;
  timeline: TimelineEvent[];
}

// ─── Webview Communication ─────────────────────────────────────────────────────

/** Message sent FROM the webview TO the extension host */
export interface WebviewMessage {
  command: string;
  payload?: Record<string, unknown>;
}

/**
 * State snapshot sent FROM the extension host TO the webview for UI refresh.
 * Computed on a timer (UI_REFRESH_INTERVAL_MS) — rendering only.
 */
export interface SidebarState {
  status: SessionStatus;
  elapsedSeconds: number;
  problemName: string;
  charactersTyped: number;
  charactersDeleted: number;
  pauseCount: number;
  compileAttempts: number;
  compileErrors: number;
  successfulRuns: number;
  runtimeErrors: number;
  hintsRequested: HintCounts;
  currentStruggleScore: number;
  struggleScores: StruggleScoreEntry[];
}

// ─── Persistence (crash recovery) ──────────────────────────────────────────────

/** Shape of the .in_progress_session.json file for crash recovery */
export interface InProgressData {
  session: Session;
  trackerState: TrackerState;
}

/** Serializable snapshot of TelemetryTracker internal state */
export interface TrackerState {
  charactersTyped: number;
  charactersDeleted: number;
  lastChangeTimestamp: number;
  pauseCount: number;
  totalPauseDuration: number;
  idleTime: number;
  fileSaveCount: number;
  fileOpenCount: number;
  autoCompileAttempts: number;
  trackedDocumentUri: string | undefined;
  lastErrorMessage: string;
  currentErrorStreak: number;
  sameErrorPeak: number;
  counterexampleShownTime: number | null;
  counterexampleShownCount: number;
  timeToResolutionAfterCounterexample: number | null;
  hintsAvailable: number;
  hintsUsed: number;
  struggleScores: StruggleScoreEntry[];
  pendingTypedChars: number;
  pendingDeletedChars: number;
}
