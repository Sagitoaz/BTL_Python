import * as vscode from 'vscode';
import { InlineProvider } from './inlineProvider';

export function activate(context: vscode.ExtensionContext) {
  const cfg = vscode.workspace.getConfiguration('btl');
  const serverUrl = cfg.get<string>('serverUrl') ?? process.env.SERVER_URL ?? 'http://localhost:9000';
  const apiKey = cfg.get<string>('apiKey') ?? process.env.API_KEY;


  const provider = new InlineProvider(serverUrl, apiKey);

  // áp cho Python trước; muốn all languages thì dùng: { pattern: "**/*" }
  const selector: vscode.DocumentSelector = [{ language: 'python', scheme: 'file' }, { language: 'python', scheme: 'untitled' }];

  const disposable = vscode.languages.registerInlineCompletionItemProvider(selector, provider);
  context.subscriptions.push(disposable);

  // (tùy chọn) lệnh bật/tắt gợi ý nhanh
  context.subscriptions.push(
    vscode.commands.registerCommand('btl.inlineSuggest', async () => {
      await vscode.commands.executeCommand('editor.action.inlineSuggest.trigger');
    })
  );
}

export function deactivate() { }
