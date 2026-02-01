import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export type Annotation = {
  id: string;
  target: {
    uri: string;
    range: { start: number; end: number };
    version: number;
  };
  intent: 'rewrite' | 'style' | 'explain' | 'verify' | 'cite';
  message: string;
  createdAt: string;
  status: 'open' | 'applied' | 'rejected';
};

const decorationTypes: Record<Annotation['intent'], vscode.TextEditorDecorationType> = {
  rewrite: vscode.window.createTextEditorDecorationType({ backgroundColor: 'rgba(255,200,0,0.2)', border: '1px solid rgba(255,200,0,0.7)' }),
  style:   vscode.window.createTextEditorDecorationType({ backgroundColor: 'rgba(0,200,255,0.2)', border: '1px solid rgba(0,200,255,0.7)' }),
  explain: vscode.window.createTextEditorDecorationType({ backgroundColor: 'rgba(150,255,150,0.2)', border: '1px solid rgba(150,255,150,0.7)' }),
  verify:  vscode.window.createTextEditorDecorationType({ backgroundColor: 'rgba(255,150,150,0.2)', border: '1px solid rgba(255,150,150,0.7)' }),
  cite:    vscode.window.createTextEditorDecorationType({ backgroundColor: 'rgba(200,150,255,0.2)', border: '1px solid rgba(200,150,255,0.7)' })
};

export function sidecarPath(docUri: vscode.Uri) {
  const docFs = docUri.fsPath;
  const base = path.basename(docFs);
  const dir = path.dirname(docFs);
  return path.join(dir, `${base}.aeiva.ann.jsonl`);
}

export function loadAnnotations(doc: vscode.TextDocument): Annotation[] {
  try {
    const p = sidecarPath(doc.uri);
    if (!fs.existsSync(p)) return [];
    const lines = fs.readFileSync(p, 'utf-8').split('\n').filter(Boolean);
    return lines.map((l) => JSON.parse(l));
  } catch {
    return [];
  }
}

export function appendAnnotation(doc: vscode.TextDocument, ann: Annotation) {
  const p = sidecarPath(doc.uri);
  fs.appendFileSync(p, JSON.stringify(ann) + '\n', 'utf-8');
}

export async function createAnnotationForSelection(editor: vscode.TextEditor) {
  const sel = editor.selection;
  if (sel.isEmpty) {
    vscode.window.showWarningMessage('Select some text first.');
    return;
  }
  const intent = await vscode.window.showQuickPick(['rewrite','style','explain','verify','cite'], { placeHolder: 'Annotation intent' });
  if (!intent) return;
  const message = await vscode.window.showInputBox({ prompt: 'Enter your annotation message' });
  if (!message) return;

  const start = editor.document.offsetAt(sel.start);
  const end = editor.document.offsetAt(sel.end);

  const ann: Annotation = {
    id: cryptoRandom(),
    target: { uri: editor.document.uri.toString(), range: { start, end }, version: editor.document.version },
    intent: intent as Annotation['intent'],
    message,
    createdAt: new Date().toISOString(),
    status: 'open'
  };

  appendAnnotation(editor.document, ann);
  renderAnnotations(editor);
  vscode.window.showInformationMessage('Annotation added.');
}

export function renderAnnotations(editor: vscode.TextEditor) {
  const anns = loadAnnotations(editor.document).filter(a => a.status === 'open');
  const perIntentRanges: Record<Annotation['intent'], vscode.DecorationOptions[]> = {
    rewrite: [], style: [], explain: [], verify: [], cite: []
  };

  for (const a of anns) {
    const range = new vscode.Range(
      editor.document.positionAt(a.target.range.start),
      editor.document.positionAt(a.target.range.end)
    );
    perIntentRanges[a.intent].push({
      range,
      hoverMessage: new vscode.MarkdownString(`**${a.intent.toUpperCase()}** — ${a.message}\n\nID: \`${a.id}\``)
    });
  }

  (Object.keys(perIntentRanges) as Annotation['intent'][]).forEach(k => {
    editor.setDecorations(decorationTypes[k], perIntentRanges[k]);
  });
}

function cryptoRandom() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

/** Overwrite the sidecar with the provided list of annotations */
export function writeAllAnnotations(doc: vscode.TextDocument, anns: Annotation[]) {
  const p = sidecarPath(doc.uri);
  const content = anns.map(a => JSON.stringify(a)).join('\n');
  fs.writeFileSync(p, content + (content ? '\n' : ''), 'utf-8');
}

/** Return all annotations that overlap the current selection (or caret if empty) */
function annotationsOverlappingSelection(editor: vscode.TextEditor, anns: Annotation[]) {
  const sel = editor.selection;
  const doc = editor.document;

  // Interpret an empty selection as a 1-char probe at the caret
  const selStart = doc.offsetAt(sel.start);
  const selEnd = sel.isEmpty ? selStart + 1 : doc.offsetAt(sel.end);

  // overlap = !(end <= selStart || start >= selEnd)
  return anns.filter(a => {
    const aStart = a.target.range.start;
    const aEnd = a.target.range.end;
    return !(aEnd <= selStart || aStart >= selEnd);
  });
}

/** Remove one annotation that overlaps the selection (or caret) */
export async function removeAnnotationAtSelection(editor: vscode.TextEditor) {
  const doc = editor.document;
  const anns = loadAnnotations(doc);
  if (anns.length === 0) {
    vscode.window.showInformationMessage('Aeiva: no annotations for this file.');
    return;
  }

  const overlapping = annotationsOverlappingSelection(editor, anns);
  if (overlapping.length === 0) {
    vscode.window.showInformationMessage('Aeiva: no annotation at the selected location.');
    return;
  }

  // If multiple overlap, let user pick which one to remove
  let target: Annotation;
  if (overlapping.length === 1) {
    target = overlapping[0];
  } else {
    const picked = await vscode.window.showQuickPick(
      overlapping.map(a => ({
        label: `${a.intent.toUpperCase()} — ${a.message}`,
        description: `[${a.target.range.start}, ${a.target.range.end})`,
        detail: `ID: ${a.id}`,
        ann: a
      })),
      { placeHolder: 'Select an annotation to remove' }
    );
    if (!picked) return;
    target = picked.ann;
  }

  const remaining = anns.filter(a => a.id !== target.id);
  writeAllAnnotations(doc, remaining);
  renderAnnotations(editor);
  vscode.window.showInformationMessage('Aeiva: annotation removed.');
}