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
  /** Source of the event (automatic vs manual button click) */
  source: 'automatic' | 'manual';
  /** Optional metadata specific to this event type */
  meta?: Record<string, unknown>;
}

// ─── Session Metadata ──────────────────────────────────────────────────────────

/** Session status states */
export type SessionStatus =
  | 'Idle'
  | 'Recording'
  | 'Solved'
  | 'Solved_With_Hint1'
  | 'Solved_With_Hint2'
  | 'Solved_With_Concept'
  | 'Solved_With_Pseudocode'
  | 'Solved_With_Solution'
  | 'Could_Not_Solve'
  | 'Stopped_Time'
  | 'Stopped_Other'
  | 'Ended_incomplete';

/** Problem Metadata */
export interface ProblemMetadata {
  topic: string;
  subtopic: string;
  difficulty: Difficulty;
  estimated_minutes: number | null;
}

/** Session Outcome */
export interface Outcome {
  final_status: SessionStatus;
  minimum_help_required: number; // 0 = independent, 1-5 = hints, 6 = could not solve
  reason: string;
}

/** Derived ML Metrics */
export interface DerivedMetrics {
  hesitation_index: number | null;
  editing_intensity: number | null;
  help_dependency_score: number | null;
  compile_failure_rate: number | null;
  average_pause_duration: number | null;
}

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

  // ─── Backward Compatible Fields ───
  time_spent: number | null;
  idle_time: number | null;

  characters_typed: number | null;
  characters_deleted: number | null;
  deletion_ratio: number | null;
  typing_speed: number | null;

  pause_count: number | null;
  pause_duration: number | null;

  file_save_count: number | null;
  file_open_count: number | null;

  compile_attempts: number | null;
  compile_errors: number | null;
  successful_runs: number | null;
  runtime_errors: number | null;
  auto_compile_attempts: number | null;

  hints_requested: HintCounts;
  hints_available: number | null;
  hints_used: number | null;
  independent_fix_rate: number | null;

  same_error_peak: number | null;
  struggle_scores: StruggleScoreEntry[];

  status: SessionStatus;
  timeline: TimelineEvent[];

  // ─── New ML Dataset Fields ───
  problem: ProblemMetadata;
  outcome: Outcome | null;
  derived_metrics: DerivedMetrics | null;
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

  /** Lifecycle status of the latest backend recommendation request */
  recommendationStatus: RecommendationStatus;
  /** Most recent recommendation returned by POST /recommend, if any */
  recommendation: RecommendationResult | null;
  /** Human-readable error message if the last backend call failed */
  recommendationError: string | null;
}

// ─── Persistence (crash recovery) ──────────────────────────────────────────────

/** Shape of the .in_progress_session.json file for crash recovery */
export interface InProgressData {
  session: Session;
  trackerState: TrackerState;
}

// ─── Backend Integration (FastAPI: /predict/full, /recommend) ─────────────────

/**
 * Telemetry snapshot payload sent to POST /predict/full and embedded inside
 * POST /recommend. Field names/shape match backend/schemas/snapshot.py's
 * `SnapshotSchema` exactly — the backend is the source of truth for this shape.
 */
export interface SnapshotPayload {
  difficulty: Difficulty;
  language: string;
  topic: string;
  subtopic: string;
  elapsed_time: number;
  progress_ratio: number;
  current_struggle_score: number;
  chars_typed: number;
  chars_deleted: number;
  pause_count: number;
  pause_duration: number;
  compile_attempts: number;
  compile_errors: number;
  successful_runs: number;
  runtime_errors: number;
  deletion_ratio: number;
  typing_speed: number;
  compile_failure_rate: number;
  average_pause_duration: number;
}

/** A single model's output within a /predict/full response (solver or hint) */
export interface ModelPrediction {
  prediction: string;
  confidence: number;
  status?: string;
  [key: string]: unknown;
}

/** Response body of POST /predict/full (backend/schemas/snapshot.py FullPredictResponse) */
export interface FullPredictResult {
  status: string;
  solver: ModelPrediction;
  hint: ModelPrediction;
}

/** Request body of POST /recommend (backend/schemas/recommendation.py RecommendationRequest) */
export interface RecommendationRequestPayload {
  problem_name: string;
  difficulty: Difficulty;
  topic: string;
  subtopic: string;
  language: string;
  student_code: string;
  solver_prediction: string;
  solver_confidence: number;
  hint_prediction: string;
  hint_confidence: number;
  snapshot: SnapshotPayload;
}

/** Response body of POST /recommend (backend/schemas/recommendation.py RecommendationResponse) */
export interface RecommendationResult {
  title: string;
  level: string;
  message: string;
  next_step: string;
  reflection_question: string;
  encouragement: string;
  confidence: number;
  code?: string | null;
  complexity?: Record<string, string> | null;
  metadata: Record<string, unknown>;
  status: string;
}

/** Lifecycle status of the current recommendation request, surfaced in the sidebar */
export type RecommendationStatus = 'idle' | 'loading' | 'error';

// ─── Persistence (crash recovery) ──────────────────────────────────────────────

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
  hintsAvailable: number;
  hintsUsed: number;
  struggleScores: StruggleScoreEntry[];
  pendingTypedChars: number;
  pendingDeletedChars: number;
}
