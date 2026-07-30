/**
 * @file SidebarProvider.ts
 * WebviewViewProvider for the Activity Bar sidebar panel.
 *
 * Owns webview lifecycle (resolve/dispose) and the two message channels:
 * - Webview → Extension: postMessage({ command: 'cognitiveCoach.xxx' })
 * - Extension → Webview: postMessage({ type: 'stateUpdate', state: {...} })
 *
 * All HTML/CSS/client-script generation lives in sidebarRenderer.ts + the
 * ui/components/ fragments — this class only wires that renderer into the
 * VS Code webview API and forwards commands/state.
 *
 * The UI refresh is on a timer (rendering only). Data capture happens
 * per-event in TelemetryTracker — two separate loops, never conflated.
 */

import * as vscode from 'vscode';
import { SessionManager } from '../session/SessionManager';
import { UI_REFRESH_INTERVAL_MS } from '../constants';
import { renderSidebarHtml } from './sidebarRenderer';

export class SidebarProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'cognitiveCoach.sidebar';

  private view?: vscode.WebviewView;
  private refreshInterval?: ReturnType<typeof setInterval>;

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly sessionManager: SessionManager
  ) {}

  /**
   * Called by VS Code when the webview view is first shown.
   */
  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.extensionUri],
    };

    webviewView.webview.html = renderSidebarHtml(
      webviewView.webview,
      this.extensionUri
    );

    // Handle messages from webview → extension
    webviewView.webview.onDidReceiveMessage((message) => {
      if (message.command) {
        vscode.commands.executeCommand(message.command);
      }
    });

    // Start UI refresh timer (rendering only, not data capture)
    this.startRefresh();

    webviewView.onDidDispose(() => {
      this.stopRefresh();
    });
  }

  /** Start the UI refresh timer */
  private startRefresh(): void {
    this.refreshInterval = setInterval(() => {
      this.pushState();
    }, UI_REFRESH_INTERVAL_MS);
  }

  /** Stop the UI refresh timer */
  private stopRefresh(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = undefined;
    }
  }

  /** Push current state to the webview for rendering */
  pushState(): void {
    if (!this.view) {
      return;
    }
    const state = this.sessionManager.getState();
    this.view.webview.postMessage({ type: 'stateUpdate', state });
  }
}
