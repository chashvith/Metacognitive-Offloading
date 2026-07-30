/**
 * @file sidebarRenderer.ts
 * Composes the full AI Tutor Dashboard HTML document (head, CSP, stylesheet link,
 * bundled local JS libraries, body sections, client script) from ./ui/components.
 */

import * as vscode from 'vscode';
import {
  renderStatusSection,
  renderSessionControls,
  renderMetricsSection,
  renderEventsSection,
  renderHintsSection,
  renderCounterexampleSection,
  renderSparklineSection,
  renderRecommendationSection,
  renderEndSection,
  getClientScript,
} from './ui/components';

/**
 * Build the full HTML document for the AI Tutor Dashboard webview.
 *
 * @param webview - The webview instance
 * @param extensionUri - Root URI of the extension
 */
export function renderSidebarHtml(
  webview: vscode.Webview,
  extensionUri: vscode.Uri
): string {
  const cssUri = webview.asWebviewUri(
    vscode.Uri.joinPath(extensionUri, 'media', 'sidebar.css')
  );
  const markedJsUri = webview.asWebviewUri(
    vscode.Uri.joinPath(extensionUri, 'media', 'marked.min.js')
  );
  const highlightJsUri = webview.asWebviewUri(
    vscode.Uri.joinPath(extensionUri, 'media', 'highlight.min.js')
  );

  const nonce = getNonce();

  const body = [
    renderStatusSection(),
    renderSparklineSection(),
    renderRecommendationSection(),
    renderEventsSection(),
    renderMetricsSection(),
    renderSessionControls(),
    renderHintsSection(),
    renderCounterexampleSection(),
    renderEndSection(),
  ].join('\n');

  return /*html*/ `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src ${webview.cspSource} 'nonce-${nonce}';">
  <link rel="stylesheet" href="${cssUri}">
  <title>Cognitive Coach</title>
</head>
<body>
${body}

  <!-- ── Bundled Local Frontend Libraries ────────────────────────── -->
  <script nonce="${nonce}" src="${markedJsUri}"></script>
  <script nonce="${nonce}" src="${highlightJsUri}"></script>

  <!-- ── Webview Script ──────────────────────────────────────────── -->
  <script nonce="${nonce}">
${getClientScript()}
  </script>

</body>
</html>`;
}

/** Generate a random nonce for Content Security Policy. */
function getNonce(): string {
  let text = '';
  const possible =
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}
