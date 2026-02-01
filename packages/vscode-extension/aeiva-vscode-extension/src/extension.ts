import * as vscode from 'vscode';
import { createAnnotationForSelection, renderAnnotations, removeAnnotationAtSelection } from './annotations';
import { requestPatchForSelection } from './patchPreview';
import { ChatViewProvider } from './chatView';

/** Single terminal instance for Aeiva terminal chat */
let aeivaTerminal: vscode.Terminal | undefined;

/** Open (or reuse) a terminal in an editor tab on the right with Aeiva icon */
function openAeivaTerminalChat(context: vscode.ExtensionContext) {
  const stillOpen =
    aeivaTerminal &&
    (aeivaTerminal as any)?.exitStatus === undefined; // tolerate older typings

  if (stillOpen) {
    aeivaTerminal!.show(true);
    return;
  }

  // Custom tab icon from your extension's media folder
  const iconUri = vscode.Uri.file(context.asAbsolutePath('media/aeiva.svg'));

  const options: vscode.TerminalOptions = {
    name: 'Aeiva',
    location: { viewColumn: vscode.ViewColumn.Two }, // editor area, right column
    iconPath: iconUri
    // cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
    // env: { AEIVA_MODE: 'chat' }
  };

  aeivaTerminal = vscode.window.createTerminal(options);
  aeivaTerminal.show(true);
  aeivaTerminal.sendText('echo "🧠 Aeiva Terminal Chat ready."');
  aeivaTerminal.sendText('echo "Type your commands or start your chat client here."');
  aeivaTerminal.sendText('echo "—"');

  /* ↓  your future startup code goes here  ↓ */

  // example: run a python module or shell script that boots the agent
  // aeivaTerminal.sendText('python -m aeiva.agent --mode vscode --port 8787');

  // or send a shell alias, env, or CLI startup
  // aeivaTerminal.sendText('export AEIVA_MODE=vscode');
  // aeivaTerminal.sendText('aeiva start');

  /* 
  key points
	•	You can send any shell command via aeivaTerminal.sendText("...").
	•	Each call runs exactly as if the user typed it in that terminal.
	•	Keep it non-blocking — avoid loops or long running code in the extension host; the terminal handles it in its own shell.

  When you later need to pass configuration (port, daemon path, env vars, etc.), read them at the top of openAeivaTerminalChat() from vscode.workspace.getConfiguration('aeiva') and interpolate:
  ```
  const cfg = vscode.workspace.getConfiguration('aeiva');
  const port = cfg.get<number>('agent.port', 8787);
  aeivaTerminal.sendText(`python -m aeiva.agent --port ${port}`);
  ```

  */

  /* ↑  stop here; rest of file unchanged  ↑ */
}

export function activate(context: vscode.ExtensionContext) {
  /**
   * COMMANDS
   */

  // 1) Terminal chat (Claude-style) — bound to the editor/title button
  context.subscriptions.push(
    vscode.commands.registerCommand('aeiva.openTerminalChat', async () => {
      vscode.window.setStatusBarMessage('Aeiva: opening terminal chat…', 1200);
      openAeivaTerminalChat(context);
    })
  );

  // 2) (Optional) Keep the right-dock Aeiva webview available via Command Palette
  context.subscriptions.push(
    vscode.commands.registerCommand('aeiva.openChat', async () => {
      await vscode.commands.executeCommand('workbench.action.focusAuxiliaryBar');
      const cmds = await vscode.commands.getCommands(true);
      if (cmds.includes('aeivaChat.focus')) {
        await vscode.commands.executeCommand('aeivaChat.focus');
      } else {
        vscode.window.showWarningMessage('Aeiva chat view not registered yet.');
      }
    })
  );

  // 3) Anchored edit commands
  context.subscriptions.push(
    vscode.commands.registerCommand('aeiva.annotate.selection', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        return;
      }
      await createAnnotationForSelection(editor);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('aeiva.requestPatch', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        return;
      }
      await requestPatchForSelection(editor);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('aeiva.removeAnnotation', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showInformationMessage('Aeiva: no active editor.');
        return;
      }
      await removeAnnotationAtSelection(editor);
    })
  );

  /**
   * EVENTS & INITIAL RENDER
   */
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((ed) => {
      if (ed) {
        renderAnnotations(ed);
      }
    })
  );

  context.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument((ev) => {
      const ed = vscode.window.activeTextEditor;
      if (ed && ev.document === ed.document) {
        renderAnnotations(ed);
      }
    })
  );

  if (vscode.window.activeTextEditor) {
    renderAnnotations(vscode.window.activeTextEditor);
  }

  /**
   * REGISTER WEBVIEW PROVIDER (right dock view, optional)
   * Keeps 'aeivaChat' available for the aeiva.openChat command.
   */
  const provider = new ChatViewProvider(context);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(ChatViewProvider.viewType, provider)
  );
}

export function deactivate() {
  try {
    aeivaTerminal?.dispose();
  } catch {
    // ignore
  }
}