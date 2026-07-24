import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
const archiver = require('archiver');
import { DATASET_FOLDER, IN_PROGRESS_FILE } from '../constants';

export interface IDatasetExporter {
  exportDataset(): Promise<void>;
}

export class ZipDatasetExporter implements IDatasetExporter {
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

  async exportDataset(): Promise<void> {
    const datasetUri = await this.ensureDatasetFolder();
    if (!datasetUri) {
      vscode.window.showErrorMessage(
        'No workspace folder open. Cannot export session data.'
      );
      return;
    }

    // Read the directory
    let entries: [string, vscode.FileType][];
    try {
      entries = await vscode.workspace.fs.readDirectory(datasetUri);
    } catch (e) {
      vscode.window.showErrorMessage(`Failed to read dataset directory: ${e}`);
      return;
    }

    // Filter for JSON sessions, excluding .in_progress_session.json
    const sessionFiles = entries
      .filter(
        ([name, type]) =>
          type === vscode.FileType.File &&
          name.endsWith('.json') &&
          name !== IN_PROGRESS_FILE
      )
      .map(([name]) => name);

    if (sessionFiles.length === 0) {
      vscode.window.showWarningMessage(
        'No completed sessions found to export.'
      );
      return;
    }

    // Suggest a filename and location for the ZIP
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const timestamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(
      now.getDate()
    )}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    const suggestedFilename = `dataset_export_${timestamp}.zip`;

    // Default to workspace root (outside dataset/)
    const defaultUri = vscode.workspace.workspaceFolders
      ? vscode.Uri.joinPath(vscode.workspace.workspaceFolders[0].uri, suggestedFilename)
      : undefined;

    const saveUri = await vscode.window.showSaveDialog({
      defaultUri,
      filters: {
        'ZIP Archives': ['zip'],
      },
      title: 'Export Dataset',
    });

    if (!saveUri) {
      // User cancelled
      return;
    }

    // Create the ZIP using archiver
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'Exporting Dataset...',
        cancellable: false,
      },
      async (progress) => {
        return new Promise<void>((resolve, reject) => {
          const output = fs.createWriteStream(saveUri.fsPath);
          const archive = archiver('zip', {
            zlib: { level: 9 }, // Sets the compression level.
          });

          output.on('close', () => {
            vscode.window.showInformationMessage(
              `📦 Dataset exported successfully to: ${saveUri.fsPath}`
            );
            resolve();
          });

          archive.on('error', (err: any) => {
            vscode.window.showErrorMessage(`Error creating ZIP: ${err.message}`);
            reject(err);
          });

          archive.pipe(output);

          // Append each session file
          for (let i = 0; i < sessionFiles.length; i++) {
            const fileName = sessionFiles[i];
            const fileUri = vscode.Uri.joinPath(datasetUri, fileName);
            progress.report({
              message: `Compressing ${fileName} (${i + 1}/${sessionFiles.length})`,
            });
            archive.file(fileUri.fsPath, { name: fileName });
          }

          archive.finalize();
        });
      }
    );
  }
}
