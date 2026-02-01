import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export class ChatViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'aeivaChat';
  constructor(private readonly context: vscode.ExtensionContext) {}

  resolveWebviewView(webviewView: vscode.WebviewView) {
    webviewView.webview.options = { enableScripts: true };
    const htmlPath = path.join(this.context.extensionPath, 'media', 'sidebar.html');
    const html = fs.readFileSync(htmlPath, 'utf-8');
    webviewView.webview.html = html;
  }
}