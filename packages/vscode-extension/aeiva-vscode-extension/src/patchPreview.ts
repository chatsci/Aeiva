import * as vscode from 'vscode';

type PatchEdit = { op: 'replace'; offsetStart: number; offsetEnd: number; text: string };
type PatchResponse = {
  rationale: string;
  edits: PatchEdit[];
  guards?: Record<string, any>;
  telemetry?: Record<string, any>;
};

export async function requestPatchForSelection(editor: vscode.TextEditor) {
  const config = vscode.workspace.getConfiguration('aeiva');
  const daemonUrl = config.get<string>('daemonUrl') || 'http://127.0.0.1:8787';

  const sel = editor.selection;
  if (sel.isEmpty) { vscode.window.showWarningMessage('Select some text first.'); return; }

  const doc = editor.document;
  const start = doc.offsetAt(sel.start);
  const end = doc.offsetAt(sel.end);
  const selectionText = doc.getText(sel);

  const preContext = doc.getText(new vscode.Range(
    doc.positionAt(Math.max(0, start - 800)),
    doc.positionAt(start)
  ));
  const postContext = doc.getText(new vscode.Range(
    doc.positionAt(end),
    doc.positionAt(Math.min(doc.getText().length, end + 800))
  ));

  const language = langFromFile(doc.fileName);
  const intent = await vscode.window.showQuickPick(['rewrite','style','explain','verify','cite'], { placeHolder: 'Intent for patch' });
  if (!intent) return;

  const body = {
    language, intent, selectionText, offsetStart: start, offsetEnd: end,
    preContext, postContext, constraints: {}, projectRoot: vscode.workspace.rootPath || ''
  };

  try {
    const resp = await fetch(`${daemonUrl}/patch`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    if (!resp.ok) throw new Error(`Daemon returned ${resp.status}`);
    const data = (await resp.json()) as PatchResponse;

    const preview = data.edits.map(e => `REPLACE [${e.offsetStart},${e.offsetEnd}) with:\n${e.text}`).join('\n---\n');
    const action = await vscode.window.showInformationMessage(`AI Patch:\n${preview}`, 'Accept', 'Reject');
    if (action === 'Accept') {
      await applyEdits(doc, data.edits);
      vscode.window.showInformationMessage('Patch applied.');
    }
  } catch (e:any) {
    vscode.window.showErrorMessage(`Patch request failed: ${e.message}`);
  }
}

function langFromFile(fileName: string) {
  if (fileName.endsWith('.tex')) return 'latex';
  if (fileName.endsWith('.md')) return 'markdown';
  if (fileName.endsWith('.py')) return 'python';
  if (fileName.endsWith('.ts')) return 'typescript';
  return 'plaintext';
}

async function applyEdits(doc: vscode.TextDocument, edits: PatchEdit[]) {
  const ws = new vscode.WorkspaceEdit();
  edits.sort((a,b)=>b.offsetStart - a.offsetStart).forEach(e => {
    ws.replace(doc.uri, new vscode.Range(doc.positionAt(e.offsetStart), doc.positionAt(e.offsetEnd)), e.text);
  });
  await vscode.workspace.applyEdit(ws);
}