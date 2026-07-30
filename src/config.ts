/**
 * @file config.ts
 * Reads user-configurable extension settings (contributes.configuration in
 * package.json, under the "cognitiveCoach" section). Kept as a tiny, isolated
 * module so backendClient.ts and SessionManager.ts never touch
 * `vscode.workspace.getConfiguration` directly — one place to change the
 * settings shape.
 */

import * as vscode from 'vscode';
import { BACKEND_CONFIG_SECTION, DEFAULT_BACKEND_URL } from './constants';

/**
 * Resolve the FastAPI backend's base URL from the `cognitiveCoach.backendUrl`
 * setting, falling back to http://localhost:8000 if unset.
 * Trailing slashes are stripped so callers can safely do `${baseUrl}/predict/full`.
 */
export function getBackendBaseUrl(): string {
  const configured = vscode.workspace
    .getConfiguration(BACKEND_CONFIG_SECTION)
    .get<string>('backendUrl');

  const url = (configured && configured.trim()) || DEFAULT_BACKEND_URL;
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

/**
 * Whether the extension should automatically request a recommendation after
 * struggle-signalling events (compile error, runtime error, hint requests),
 * per the `cognitiveCoach.autoRecommend` setting. Defaults to true.
 */
export function isAutoRecommendEnabled(): boolean {
  return vscode.workspace
    .getConfiguration(BACKEND_CONFIG_SECTION)
    .get<boolean>('autoRecommend', true);
}
