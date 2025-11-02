import * as vscode from "vscode";
import { InlineProvider } from "./inlineProvider";

export function activate(context: vscode.ExtensionContext) {
  const cfg = vscode.workspace.getConfiguration("btl");
  const serverUrl =
    cfg.get<string>("serverUrl") ??
    process.env.SERVER_URL ??
    "https://btl-python-r9kz.onrender.com";
  const apiKey = cfg.get<string>("apiKey") ?? process.env.API_KEY ?? "5conmeo";
  const enableStreaming = cfg.get<boolean>("enableStreaming") ?? false;
  const timeoutMs = cfg.get<number>("timeoutMs") ?? 15000;

  const provider = new InlineProvider(
    serverUrl,
    apiKey,
    enableStreaming,
    timeoutMs
  );

  // áp cho Python trước; muốn all languages thì dùng: { pattern: "**/*" }
  const selector: vscode.DocumentSelector = [
    { language: "python", scheme: "file" },
    { language: "python", scheme: "untitled" },
  ];

  const disposable = vscode.languages.registerInlineCompletionItemProvider(
    selector,
    provider
  );
  context.subscriptions.push(disposable);

  // Track completion acceptance
  context.subscriptions.push(
    vscode.commands.registerCommand("btl.trackAcceptance", async (completionId: string) => {
      await (provider as any).handleAcceptance(completionId);
    })
  );

  // (tùy chọn) lệnh bật/tắt gợi ý nhanh
  context.subscriptions.push(
    vscode.commands.registerCommand("btl.inlineSuggest", async () => {
      await vscode.commands.executeCommand(
        "editor.action.inlineSuggest.trigger"
      );
    })
  );

  // Command test completion
  context.subscriptions.push(
    vscode.commands.registerCommand("btl.testCompletion", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage("No active editor");
        return;
      }

      vscode.window.showInformationMessage(
        `Testing completion with server: ${serverUrl}`
      );
      await vscode.commands.executeCommand(
        "editor.action.inlineSuggest.trigger"
      );
    })
  );

  // View coding profile
  context.subscriptions.push(
    vscode.commands.registerCommand("btl.viewProfile", async () => {
      const userId = (provider as any).userId;
      if (!userId) {
        vscode.window.showWarningMessage("Personalization is disabled");
        return;
      }

      try {
        const headers: Record<string, string> = {
          "X-User-ID": userId,
        };
        if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

        const response = await fetch(`${serverUrl}/feedback/profile`, { headers });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const profile = await response.json();
        const panel = vscode.window.createWebviewPanel(
          'btlProfile',
          'My Coding Profile',
          vscode.ViewColumn.One,
          {}
        );

        panel.webview.html = `
          <!DOCTYPE html>
          <html>
          <head>
            <style>
              body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; }
              h1 { color: #3776ab; }
              .metric { margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 5px; }
              .label { font-weight: bold; }
            </style>
          </head>
          <body>
            <h1>🤖 Your Coding Profile</h1>
            <div class="metric"><span class="label">User ID:</span> ${userId}</div>
            <div class="metric"><span class="label">Total Samples:</span> ${profile.coding_style?.total_samples || 0}</div>
            <div class="metric"><span class="label">Indent:</span> ${profile.coding_style?.uses_tabs ? 'Tabs' : profile.coding_style?.indent_size + ' spaces'}</div>
            <div class="metric"><span class="label">Quotes:</span> ${profile.coding_style?.prefer_double_quotes ? 'Double' : 'Single'}</div>
            <div class="metric"><span class="label">Naming:</span> ${profile.coding_style?.snake_case_ratio > 0.5 ? 'snake_case' : 'camelCase'}</div>
            <div class="metric"><span class="label">Type Hints:</span> ${(profile.coding_style?.type_hints_ratio * 100).toFixed(0)}%</div>
            <div class="metric"><span class="label">Docstrings:</span> ${(profile.coding_style?.docstring_ratio * 100).toFixed(0)}%</div>
            <div class="metric"><span class="label">Accept Rate:</span> ${(profile.accept_rate * 100).toFixed(1)}%</div>
            <div class="metric"><span class="label">Avg Accept Time:</span> ${profile.avg_accept_time_ms?.toFixed(0) || 'N/A'} ms</div>
          </body>
          </html>
        `;
      } catch (err) {
        vscode.window.showErrorMessage(`Failed to load profile: ${err}`);
      }
    })
  );

  // Clear coding profile
  context.subscriptions.push(
    vscode.commands.registerCommand("btl.clearProfile", async () => {
      const userId = (provider as any).userId;
      if (!userId) {
        vscode.window.showWarningMessage("Personalization is disabled");
        return;
      }

      const confirm = await vscode.window.showWarningMessage(
        "Delete your coding profile? This cannot be undone.",
        { modal: true },
        "Delete"
      );

      if (confirm !== "Delete") return;

      try {
        const headers: Record<string, string> = {
          "X-User-ID": userId,
        };
        if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

        const response = await fetch(`${serverUrl}/feedback/profile`, {
          method: "DELETE",
          headers
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        vscode.window.showInformationMessage("Coding profile deleted successfully");
      } catch (err) {
        vscode.window.showErrorMessage(`Failed to delete profile: ${err}`);
      }
    })
  );
}

export function deactivate() {}
