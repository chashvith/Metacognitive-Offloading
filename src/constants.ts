/**
 * @file constants.ts
 * Named constants for tunable thresholds and configuration values.
 * All magic numbers live here — easy to tune without digging through logic.
 */

/** Minimum gap (ms) between text-change events to count as a pause */
export const IDLE_THRESHOLD_MS = 5_000;

/** How often (ms) to auto-persist in-progress session state for crash recovery */
export const PERSIST_INTERVAL_MS = 10_000;

/** Folder name (relative to workspace root) for session data files */
export const DATASET_FOLDER = 'dataset';

/** Filename for crash-recovery in-progress session state */
export const IN_PROGRESS_FILE = '.in_progress_session.json';

/** Schema version stamped into every output JSON for forward compatibility */
export const SCHEMA_VERSION = '1.0';

/** UI refresh interval (ms) — rendering only, telemetry capture is per-event */
export const UI_REFRESH_INTERVAL_MS = 500;

// ─── Backend Integration ────────────────────────────────────────────────────

/** VS Code settings section under which backend integration settings live */
export const BACKEND_CONFIG_SECTION = 'cognitiveCoach';

/** Fallback backend URL used if the user hasn't configured cognitiveCoach.backendUrl */
export const DEFAULT_BACKEND_URL = 'http://localhost:8000';

/** Max time (ms) to wait for a backend HTTP response before aborting */
export const BACKEND_REQUEST_TIMEOUT_MS = 10_000;
