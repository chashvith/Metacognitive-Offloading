/**
 * @file commands.ts
 * Registers all Command Palette commands. Every manual event button in the
 * sidebar has a corresponding command here so it can be triggered via
 * Ctrl+Shift+P if the webview misbehaves.
 */

import * as vscode from 'vscode';
import { SessionManager } from '../session/SessionManager';
import { EventType } from '../types';
import { ZipDatasetExporter } from '../export/DatasetExporter';

/**
 * Register all Cognitive Coach commands and return the disposables.
 * @param manager - The singleton SessionManager instance
 * @returns Array of disposables to push into context.subscriptions
 */
export function registerCommands(
  manager: SessionManager
): vscode.Disposable[] {
  const disposables: vscode.Disposable[] = [];

  // ── Session lifecycle ────────────────────────────────────────────────────

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.startProblem', () =>
      manager.startProblem()
    )
  );

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.endProblem', () =>
      manager.endProblem('Ended_incomplete')
    )
  );

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.exportSession', () =>
      manager.exportLastSession()
    )
  );

  const datasetExporter = new ZipDatasetExporter();
  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.exportDataset', () =>
      datasetExporter.exportDataset()
    )
  );

  // ── Compile / Run events (manual) ────────────────────────────────────────

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.compileSuccess', () => {
      if (!manager.isRecording) {
        vscode.window.showWarningMessage('No active session. Start a problem first.');
        return;
      }
      manager.recordCompileSuccess();
      vscode.window.setStatusBarMessage('✓ Compile Success recorded', 2000);
    })
  );

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.compileError', () => {
      if (!manager.isRecording) {
        vscode.window.showWarningMessage('No active session. Start a problem first.');
        return;
      }
      manager.recordCompileError();
      vscode.window.setStatusBarMessage('✗ Compile Error recorded', 2000);
    })
  );

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.successfulRun', () => {
      if (!manager.isRecording) {
        vscode.window.showWarningMessage('No active session. Start a problem first.');
        return;
      }
      manager.recordSuccessfulRun();
      vscode.window.setStatusBarMessage('✓ Successful Run recorded', 2000);
    })
  );

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.runtimeError', () => {
      if (!manager.isRecording) {
        vscode.window.showWarningMessage('No active session. Start a problem first.');
        return;
      }
      manager.recordRuntimeError();
      vscode.window.setStatusBarMessage('✗ Runtime Error recorded', 2000);
    })
  );

  // ── Hint events (manual) ─────────────────────────────────────────────────

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.hint1', () => {
      if (!manager.isRecording) {
        vscode.window.showWarningMessage('No active session. Start a problem first.');
        return;
      }
      manager.recordHint(EventType.Hint1Requested);
      vscode.window.setStatusBarMessage('💡 Hint 1 recorded', 2000);
    })
  );

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.hint2', () => {
      if (!manager.isRecording) {
        vscode.window.showWarningMessage('No active session. Start a problem first.');
        return;
      }
      manager.recordHint(EventType.Hint2Requested);
      vscode.window.setStatusBarMessage('💡 Hint 2 recorded', 2000);
    })
  );

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.conceptHint', () => {
      if (!manager.isRecording) {
        vscode.window.showWarningMessage('No active session. Start a problem first.');
        return;
      }
      manager.recordHint(EventType.ConceptHintRequested);
      vscode.window.setStatusBarMessage('📖 Concept Hint recorded', 2000);
    })
  );

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.pseudocode', () => {
      if (!manager.isRecording) {
        vscode.window.showWarningMessage('No active session. Start a problem first.');
        return;
      }
      manager.recordHint(EventType.PseudocodeRequested);
      vscode.window.setStatusBarMessage('📝 Pseudocode recorded', 2000);
    })
  );

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.solution', () => {
      if (!manager.isRecording) {
        vscode.window.showWarningMessage('No active session. Start a problem first.');
        return;
      }
      manager.recordHint(EventType.SolutionRequested);
      vscode.window.setStatusBarMessage('🔑 Solution recorded', 2000);
    })
  );

  // ── Counterexample events (placeholder buttons) ──────────────────────────

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.showCounterexample', () => {
      if (!manager.isRecording) {
        vscode.window.showWarningMessage('No active session. Start a problem first.');
        return;
      }
      manager.recordCounterexampleShown();
      vscode.window.setStatusBarMessage('⚡ Counterexample shown', 2000);
    })
  );

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.counterexampleResolved', () => {
      if (!manager.isRecording) {
        vscode.window.showWarningMessage('No active session. Start a problem first.');
        return;
      }
      manager.recordCounterexampleResolved();
      vscode.window.setStatusBarMessage('✓ Counterexample resolved', 2000);
    })
  );

  // ── End-state events ─────────────────────────────────────────────────────

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.problemSolved', () =>
      manager.endProblem('Solved')
    )
  );

  disposables.push(
    vscode.commands.registerCommand('cognitiveCoach.problemAbandoned', () =>
      manager.endProblem('Abandoned')
    )
  );

  return disposables;
}
