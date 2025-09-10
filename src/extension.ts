// src/extension.ts
import * as vscode from 'vscode';

/**
 * VS Code sẽ gọi hàm này khi extension được kích hoạt.
 * Kích hoạt xảy ra theo "activationEvents" trong package.json
 * (vd: mở file Python, hoặc sau khi VS Code khởi động xong).
 */
export function activate(context: vscode.ExtensionContext) {
  // Tạo kênh log để bạn xem nhật ký ở View → Output → AI Coder
  const log = vscode.window.createOutputChannel('AI Coder');
  log.appendLine('AI Coder activated');
  context.subscriptions.push(log);

  // Ví dụ 1: lệnh mở trang Settings của extension (tiện để cấu hình)
  const openSettings = vscode.commands.registerCommand('aiCoder.openSettings', async () => {
    await vscode.commands.executeCommand('workbench.action.openSettings', '@ext:your-name.ai-coder');
  });
  context.subscriptions.push(openSettings);

  // Ví dụ 2: lệnh ping để test extension sống
  const ping = vscode.commands.registerCommand('aiCoder.ping', () => {
    vscode.window.showInformationMessage('AI Coder is alive!');
  });
  context.subscriptions.push(ping);
}

/**
 * Được gọi khi extension bị unload (đóng VS Code…).
 * Nếu bạn mở socket/process thì dọn ở đây.
 */
export function deactivate() {}