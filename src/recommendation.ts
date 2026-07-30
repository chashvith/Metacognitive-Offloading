/**
 * @file recommendation.ts
 * Pure mapping logic between the extension's internal telemetry shapes
 * (Session, TelemetryTracker metrics, EventTimeline) and the payloads the
 * FastAPI backend expects (SnapshotPayload, RecommendationRequestPayload).
 *
 * Deliberately has no VS Code or network dependencies — it's a set of pure
 * functions, which keeps SessionManager focused on orchestration and makes
 * this mapping independently testable.
 */

import { EventTimeline } from './telemetry/EventTimeline';
import { TelemetryTracker } from './telemetry/TelemetryTracker';
import {
  EventType,
  FullPredictResult,
  RecommendationRequestPayload,
  Session,
  SnapshotPayload,
} from './types';

/**
 * Build the telemetry snapshot sent to POST /predict/full, matching
 * backend/schemas/snapshot.py's SnapshotSchema field-for-field.
 *
 * @param session - Current session metadata (problem/difficulty/language)
 * @param tracker - Live TelemetryTracker for the current session
 * @param timeline - Live EventTimeline for the current session
 */
export function buildSnapshot(
  session: Session,
  tracker: TelemetryTracker,
  timeline: EventTimeline
): SnapshotPayload {
  const metrics = tracker.getMetrics();

  const compileAttempts =
    timeline.getEventCount(EventType.CompileSuccess) +
    timeline.getEventCount(EventType.CompileError);
  const compileErrors = timeline.getEventCount(EventType.CompileError);
  const successfulRuns = timeline.getEventCount(EventType.SuccessfulRun);
  const runtimeErrors = timeline.getEventCount(EventType.RuntimeError);

  const compileFailureRate =
    compileAttempts > 0 ? compileErrors / compileAttempts : 0;
  const averagePauseDuration =
    metrics.pauseCount > 0
      ? metrics.totalPauseDuration / metrics.pauseCount
      : 0;

  // No explicit "problem completion" signal is tracked yet, so we use a
  // simple, conservative heuristic: a successful run implies real progress,
  // an error-free compile implies partial progress, otherwise none. This is
  // an approximation for the ML features — it does not affect grading logic,
  // which lives entirely in the (unmodified) backend/ML models.
  const progressRatio =
    successfulRuns > 0 ? 1.0 : compileAttempts > 0 && compileErrors === 0 ? 0.5 : 0.0;

  const currentStruggleScore =
    metrics.struggleScores.length > 0
      ? metrics.struggleScores[metrics.struggleScores.length - 1].score
      : 0;

  return {
    difficulty: session.difficulty,
    language: session.language || 'unknown',
    topic: session.problem.topic || 'General',
    subtopic: session.problem.subtopic || 'General',
    elapsed_time: timeline.getElapsedSeconds(),
    progress_ratio: progressRatio,
    current_struggle_score: currentStruggleScore,
    chars_typed: metrics.charactersTyped,
    chars_deleted: metrics.charactersDeleted,
    pause_count: metrics.pauseCount,
    pause_duration: metrics.totalPauseDuration,
    compile_attempts: compileAttempts,
    compile_errors: compileErrors,
    successful_runs: successfulRuns,
    runtime_errors: runtimeErrors,
    deletion_ratio: metrics.deletionRatio,
    typing_speed: metrics.typingSpeed,
    compile_failure_rate: compileFailureRate,
    average_pause_duration: averagePauseDuration,
  };
}

/**
 * Build the POST /recommend request body from the session, the snapshot
 * already sent to /predict/full, the student's current code, and the
 * prediction result returned by /predict/full.
 */
export function buildRecommendationRequest(
  session: Session,
  snapshot: SnapshotPayload,
  studentCode: string,
  fullPrediction: FullPredictResult
): RecommendationRequestPayload {
  return {
    problem_name: session.problem_name || 'Unknown Problem',
    difficulty: session.difficulty,
    topic: snapshot.topic,
    subtopic: snapshot.subtopic,
    language: snapshot.language,
    student_code: studentCode,
    solver_prediction: fullPrediction.solver.prediction ?? 'Likely to Solve',
    solver_confidence: fullPrediction.solver.confidence ?? 0.5,
    hint_prediction: fullPrediction.hint.prediction ?? 'No Hint',
    hint_confidence: fullPrediction.hint.confidence ?? 0.5,
    snapshot,
  };
}
