/**
 * @file extension.ts
 * Entry point for the Cognitive Coach VS Code extension.
 *
 * activate() wires up:
 * - SessionManager (singleton orchestrator)
 * - SidebarProvider (webview for Activity Bar)
 * - All 16 Command Palette commands
 * - Crash recovery check
 *
 * deactivate() gracefully ends any active session as Ended_incomplete.
 */

import * as vscode from 'vscode';
import { SessionManager } from './session/SessionManager';
import { SidebarProvider } from './views/SidebarProvider';
import { registerCommands } from './commands/commands';

/** The singleton SessionManager — lives for the lifetime of the extension */
let sessionManager: SessionManager;

/**
 * Called when the extension is activated (on startup, per activationEvents).
 */
export function activate(context: vscode.ExtensionContext): void {
  // ── Create the SessionManager ──────────────────────────────────────────
  sessionManager = new SessionManager();

  // ── Register the sidebar webview provider ──────────────────────────────
  const sidebarProvider = new SidebarProvider(
    context.extensionUri,
    sessionManager
  );
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      SidebarProvider.viewType,
      sidebarProvider
    )
  );

  // ── Register all commands ──────────────────────────────────────────────
  const commandDisposables = registerCommands(sessionManager);
  for (const disposable of commandDisposables) {
    context.subscriptions.push(disposable);
  }

  // ── Check for crash recovery ───────────────────────────────────────────
  // Runs asynchronously — doesn't block activation
  sessionManager.checkForRecovery();

  console.log('Cognitive Coach extension activated');
}

/**
 * Called when the extension is deactivated (VS Code closing, extension disabled).
 * Gracefully ends any active session so data isn't lost.
 */
export async function deactivate(): Promise<void> {
  if (sessionManager) {
    await sessionManager.dispose();
  }
}
