/**
 * @file backendClient.ts
 * Thin HTTP client for the Cognitive Coach FastAPI backend.
 *
 * Owns every fetch/timeout/error-handling detail for the two endpoints the
 * extension needs (POST /predict/full and POST /recommend) so the rest of
 * the extension only ever deals with typed inputs/outputs and a single
 * `BackendError` failure mode. Does not know anything about VS Code UI —
 * callers (SessionManager) decide how to surface failures to the user.
 */

import { getBackendBaseUrl } from './config';
import { BACKEND_REQUEST_TIMEOUT_MS } from './constants';
import {
  FullPredictResult,
  RecommendationRequestPayload,
  RecommendationResult,
  SnapshotPayload,
} from './types';

/** Thrown for any backend communication failure (network, timeout, non-2xx, bad JSON). */
export class BackendError extends Error {
  constructor(message: string, readonly cause?: unknown) {
    super(message);
    this.name = 'BackendError';
  }
}

/**
 * POST JSON to `${backendUrl}${path}` and parse the JSON response, with a
 * request timeout and normalized error handling. Generic over the expected
 * response shape so each endpoint wrapper stays a one-liner.
 */
async function postJson<TResponse>(
  path: string,
  body: unknown
): Promise<TResponse> {
  const url = `${getBackendBaseUrl()}${path}`;
  const controller = new AbortController();
  const timeoutHandle = setTimeout(
    () => controller.abort(),
    BACKEND_REQUEST_TIMEOUT_MS
  );

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (err) {
    const isAbort = err instanceof Error && err.name === 'AbortError';
    throw new BackendError(
      isAbort
        ? `Request to ${url} timed out after ${BACKEND_REQUEST_TIMEOUT_MS}ms. Is the backend running?`
        : `Could not reach backend at ${url}. Is it running? (${
            err instanceof Error ? err.message : String(err)
          })`,
      err
    );
  } finally {
    clearTimeout(timeoutHandle);
  }

  if (!response.ok) {
    // FastAPI/Pydantic errors return a JSON body with a `detail` field —
    // surface it when available, otherwise fall back to the status text.
    let detail = response.statusText;
    try {
      const errorBody = (await response.json()) as { detail?: unknown };
      if (errorBody?.detail) {
        detail =
          typeof errorBody.detail === 'string'
            ? errorBody.detail
            : JSON.stringify(errorBody.detail);
      }
    } catch {
      // Response body wasn't JSON — keep statusText.
    }
    throw new BackendError(
      `Backend returned ${response.status} for ${path}: ${detail}`
    );
  }

  try {
    return (await response.json()) as TResponse;
  } catch (err) {
    throw new BackendError(
      `Backend response for ${path} was not valid JSON.`,
      err
    );
  }
}

/**
 * Backend client — one method per endpoint the extension consumes.
 * Both are POST endpoints on the existing, unmodified FastAPI backend.
 */
export const backendClient = {
  /** POST /predict/full — runs the Solver and Hint XGBoost models. */
  predictFull(snapshot: SnapshotPayload): Promise<FullPredictResult> {
    return postJson<FullPredictResult>('/predict/full', { snapshot });
  },

  /** POST /recommend — runs the Recommendation Engine on prediction + context. */
  recommend(
    payload: RecommendationRequestPayload
  ): Promise<RecommendationResult> {
    return postJson<RecommendationResult>('/recommend', payload);
  },

  /** POST /feedback — submits user feedback for a hint. */
  submitFeedback(
    sessionId: string,
    rating: string
  ): Promise<{ status: string }> {
    return postJson<{ status: string }>('/feedback', { session_id: sessionId, rating });
  },
};
