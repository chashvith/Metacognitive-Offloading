/**
 * @file SessionPersistence.ts
 * File I/O for session JSON files. Handles:
 * - Saving completed sessions to dataset/session_YYYYMMDD_HHMMSS.json
 * - Persisting in-progress state to dataset/.in_progress_session.json
 * - Crash recovery: loading and cleaning up in-progress files
 * - Re-exporting the last saved session
 *
 * Uses vscode.workspace.fs for portability (works on remote workspaces too).
 */

import * as vscode from 'vscode';
import { Session, InProgressData } from '../types';
import { DATASET_FOLDER, IN_PROGRESS_FILE } from '../constants';

export class SessionPersistence {
  /**
   * Get the URI to the dataset/ folder at the workspace root.
   * Returns null if no workspace folder is open.
   */
  private getDatasetUri(): vscode.Uri | null {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
      return null;
    }
    return vscode.Uri.joinPath(folders[0].uri, DATASET_FOLDER);
  }

  /**
   * Ensure the dataset/ folder exists, creating it if needed.
   */
  private async ensureDatasetFolder(): Promise<vscode.Uri | null> {
    const uri = this.getDatasetUri();
    if (!uri) {
      return null;
    }
    try {
      await vscode.workspace.fs.createDirectory(uri);
    } catch {
      // Directory may already exist — that's fine
    }
    return uri;
  }

  /**
   * Save a completed session to dataset/session_YYYYMMDD_HHMMSS.json.
   * @param session - The full session data to save
   * @param forceExport - If true, uses current time for filename (re-export)
   * @returns The URI of the saved file, or null on failure
   */
  async saveSession(session: Session, forceExport: boolean = false): Promise<vscode.Uri | null> {
    const datasetUri = await this.ensureDatasetFolder();
    if (!datasetUri) {
      vscode.window.showErrorMessage(
        'No workspace folder open. Cannot save session data.'
      );
      return null;
    }

    const dateSource = forceExport
      ? new Date()
      : new Date(session.end_time || Date.now());
    const filename = `session_${this.formatDateForFilename(dateSource)}.json`;
    const fileUri = vscode.Uri.joinPath(datasetUri, filename);

    const content = JSON.stringify(session, null, 2);
    await vscode.workspace.fs.writeFile(
      fileUri,
      Buffer.from(content, 'utf-8')
    );

    return fileUri;
  }

  /**
   * Persist in-progress session state for crash recovery.
   * Called every PERSIST_INTERVAL_MS and on each manual event.
   * @param data - Session + tracker state snapshot
   */
  async persistInProgress(data: InProgressData): Promise<void> {
    const datasetUri = await this.ensureDatasetFolder();
    if (!datasetUri) {
      return;
    }

    const fileUri = vscode.Uri.joinPath(datasetUri, IN_PROGRESS_FILE);
    const content = JSON.stringify(data, null, 2);
    await vscode.workspace.fs.writeFile(
      fileUri,
      Buffer.from(content, 'utf-8')
    );
  }

  /**
   * Load the in-progress session file (if it exists).
   * Used during activation to check for crash recovery.
   * @returns The saved in-progress data, or null if none exists
   */
  async loadInProgress(): Promise<InProgressData | null> {
    const datasetUri = this.getDatasetUri();
    if (!datasetUri) {
      return null;
    }

    const fileUri = vscode.Uri.joinPath(datasetUri, IN_PROGRESS_FILE);
    try {
      const rawBytes = await vscode.workspace.fs.readFile(fileUri);
      const text = Buffer.from(rawBytes).toString('utf-8');
      return JSON.parse(text) as InProgressData;
    } catch {
      return null;
    }
  }

  /**
   * Delete the in-progress session file after successful save or discard.
   */
  async deleteInProgress(): Promise<void> {
    const datasetUri = this.getDatasetUri();
    if (!datasetUri) {
      return;
    }

    const fileUri = vscode.Uri.joinPath(datasetUri, IN_PROGRESS_FILE);
    try {
      await vscode.workspace.fs.delete(fileUri);
    } catch {
      // File may not exist — that's fine
    }
  }

  /**
   * Get the most recently saved session (for re-export).
   * Sorts session files by filename (which embeds the timestamp).
   * @returns The last session data, or null if none found
   */
  async getLastSession(): Promise<Session | null> {
    const datasetUri = this.getDatasetUri();
    if (!datasetUri) {
      return null;
    }

    try {
      const entries = await vscode.workspace.fs.readDirectory(datasetUri);
      const sessionFiles = entries
        .filter(
          ([name, type]) =>
            type === vscode.FileType.File &&
            name.startsWith('session_') &&
            name.endsWith('.json')
        )
        .map(([name]) => name)
        .sort()
        .reverse();

      if (sessionFiles.length === 0) {
        return null;
      }

      const fileUri = vscode.Uri.joinPath(datasetUri, sessionFiles[0]);
      const rawBytes = await vscode.workspace.fs.readFile(fileUri);
      const text = Buffer.from(rawBytes).toString('utf-8');
      return JSON.parse(text) as Session;
    } catch {
      return null;
    }
  }

  /**
   * Format a Date as YYYYMMDD_HHMMSS for filenames.
   */
  private formatDateForFilename(date: Date): string {
    const pad = (n: number): string => String(n).padStart(2, '0');
    return (
      `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}` +
      `_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`
    );
  }
}
