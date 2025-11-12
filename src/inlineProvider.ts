import * as vscode from 'vscode';
import * as crypto from 'crypto';

const DEFAULT_STOPS_PY = ["\n\n", "\n\n```", "\n\n##", "\n\n# ", "\n\n\"\"\"", "\n\n'''"];
const DEFAULT_STOPS_CPP = ["\n\n", "\n\n```", "\n\n//", "\n\n/*", "\n\n#endif"];
const DEFAULT_TEMPERATURE = 0.2; // Lower for more deterministic code
const DEFAULT_MAX_TOKENS = 300; // Longer for multi-line completions
const MAX_SIDE_CHARS = 8000; // More context

// Generate anonymous user ID based on machine ID
function getUserId(): string {
  const machineId = vscode.env.machineId;
  const hash = crypto.createHash('sha256').update(machineId).digest('hex');
  return hash.substring(0, 16); // Use first 16 chars for brevity
}

// Get indent character and size from editor config
function detectIndentation(doc: vscode.TextDocument): { char: string, size: number } {
  const config = vscode.workspace.getConfiguration('editor', doc.uri);
  const insertSpaces = config.get<boolean>('insertSpaces', true);
  const tabSize = config.get<number>('tabSize', 4);
  
  if (insertSpaces) {
    return { char: ' ', size: tabSize };
  }
  return { char: '\t', size: 1 };
}

// Get current line's indentation string
function getIndentFromLine(line: string): string {
  const match = line.match(/^(\s*)/);
  return match ? match[1] : '';
}

// Calculate indent level (number of indent units)
function getIndentLevel(indent: string, indentChar: string, indentSize: number): number {
  if (indentChar === '\t') {
    return indent.split('\t').length - 1;
  }
  return Math.floor(indent.length / indentSize);
}

// Create indent string from level
function makeIndent(level: number, indentChar: string, indentSize: number): string {
  if (indentChar === '\t') {
    return '\t'.repeat(level);
  }
  return ' '.repeat(level * indentSize);
}

// Detect if we're completing from a comment (comment-to-code feature)
function detectCommentIntent(prefix: string, language: string): { isComment: boolean, instruction: string } {
  const lines = prefix.split('\n');
  const lastLine = lines[lines.length - 1] || '';
  const prevLine = lines[lines.length - 2] || '';
  
  // Python comments
  if (language === 'python') {
    // Single line: # TODO: implement this function
    if (lastLine.trim().startsWith('#')) {
      return { isComment: true, instruction: lastLine.trim().substring(1).trim() };
    }
    // Docstring: """Calculate sum of numbers"""
    const docMatch = prefix.match(/"""([^"]+)"""\s*$/s) || prefix.match(/'''([^']+)'''\s*$/s);
    if (docMatch) {
      return { isComment: true, instruction: docMatch[1].trim() };
    }
  }
  
  // C++ comments
  if (language === 'cpp' || language === 'c') {
    // Single line: // TODO: implement addition
    if (lastLine.trim().startsWith('//')) {
      return { isComment: true, instruction: lastLine.trim().substring(2).trim() };
    }
    // Multi-line: /* Calculate factorial */
    const multiMatch = prefix.match(/\/\*([^*]+)\*\/\s*$/s);
    if (multiMatch) {
      return { isComment: true, instruction: multiMatch[1].trim() };
    }
  }
  
  return { isComment: false, instruction: '' };
}

// Detect missing imports from completion text
function detectMissingImports(completion: string, prefix: string, language: string): string[] {
  const imports: string[] = [];
  
  if (language === 'python') {
    // Find usage patterns like: pd.DataFrame, np.array, os.path
    const matches = completion.matchAll(/\b([a-z_]+)\.([A-Za-z_][A-Za-z0-9_]*)/g);
    const usedModules = new Set<string>();
    for (const match of matches) {
      usedModules.add(match[1]);
    }
    
    // Common module mappings
    const commonImports: Record<string, string> = {
      'pd': 'import pandas as pd',
      'np': 'import numpy as np',
      'plt': 'import matplotlib.pyplot as plt',
      'os': 'import os',
      'sys': 'import sys',
      'json': 'import json',
      're': 'import re',
      'datetime': 'import datetime',
      'math': 'import math',
    };
    
    // Check which imports are missing
    for (const mod of usedModules) {
      const importStatement = commonImports[mod];
      if (importStatement && !prefix.includes(importStatement)) {
        imports.push(importStatement);
      }
    }
    
    // Check for direct function usage
    if (/\bDataFrame\b/.test(completion) && !prefix.includes('pandas')) {
      if (!imports.some(i => i.includes('pandas'))) {
        imports.push('import pandas as pd');
      }
    }
  }
  
  if (language === 'cpp' || language === 'c') {
    // Detect std:: usage
    if (/std::(vector|string|map|set|cout|cin)/.test(completion)) {
      if (!prefix.includes('#include <iostream>') && /std::(cout|cin|endl)/.test(completion)) {
        imports.push('#include <iostream>');
      }
      if (!prefix.includes('#include <vector>') && /std::vector/.test(completion)) {
        imports.push('#include <vector>');
      }
      if (!prefix.includes('#include <string>') && /std::string/.test(completion)) {
        imports.push('#include <string>');
      }
      if (!prefix.includes('#include <map>') && /std::map/.test(completion)) {
        imports.push('#include <map>');
      }
    }
  }
  
  return imports;
}

function getPrefixSuffix(doc: vscode.TextDocument, pos: vscode.Position) {
  const start = new vscode.Position(0, 0);
  const end = new vscode.Position(doc.lineCount - 1, doc.lineAt(doc.lineCount - 1).text.length);
  const before = new vscode.Range(start, pos);
  const after = new vscode.Range(pos, end);
  let prefix = doc.getText(before);
  let suffix = doc.getText(after);
  if (prefix.length > MAX_SIDE_CHARS) prefix = prefix.slice(-MAX_SIDE_CHARS);
  if (suffix.length > MAX_SIDE_CHARS) suffix = suffix.slice(0, MAX_SIDE_CHARS);
  return { prefix, suffix };
}

type ApiResp = {
  completion?: string;
  choices?: Array<{ text?: string }>;
};

async function fetchCompletion(
  serverUrl: string,
  apiKey: string | undefined,
  body: any,
  signal: AbortSignal,
  userId: string | null = null
): Promise<string | null> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Accept": "application/json",
  };
  if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;
  if (userId) headers["X-User-ID"] = userId;

  try {
    const url = serverUrl.replace(/\/+$/, "") + "/complete";
    const resp = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal,
    });

    if (!resp.ok) {
      // đọc text để log chi tiết lỗi server
      let errBody = "";
      try { errBody = (await resp.text()).slice(0, 500); } catch { /* noop */ }

      console.error(`[BTL] POST ${url} -> ${resp.status} ${resp.statusText}. Body: ${errBody}`);

      // 401/403 thường do API key sai/thiếu -> không hiển thị popup để tránh làm phiền khi đang gõ
      if (resp.status === 401 || resp.status === 403) {
        // có thể bật popup nếu bạn muốn: vscode.window.showWarningMessage("BTL: 401/403 - Kiểm tra btl.apiKey/btl.serverUrl.");
        return null;
      }
      // các lỗi khác cứ trả null để tắt gợi ý
      return null;
    }

    // cố gắng parse JSON; nếu fail thì log
    let data: ApiResp | null = null;
    try {
      data = (await resp.json()) as ApiResp | null;
    } catch (e) {
      console.error(`[BTL] JSON parse error từ ${url}:`, e);
      return null;
    }

    const raw =
      data?.completion ??
      data?.choices?.[0]?.text ??
      "";

    if (typeof raw !== "string" || !raw) return null;

    const cleaned = stripMdFence(raw).trimEnd();
    return cleaned.length ? cleaned : null;
  } catch (err: any) {
    if (err?.name === "AbortError") return null;
    console.error(`[BTL] fetchCompletion lỗi:`, err);
    return null;
  }
}

async function fetchStreamCompletion(
  serverUrl: string,
  apiKey: string | undefined,
  body: any,
  signal: AbortSignal,
  userId: string | null = null
): Promise<string | null> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
  };
  if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;
  if (userId) headers["X-User-ID"] = userId;

  try {
    const url = serverUrl.replace(/\/+$/, "") + "/complete_stream";
    const resp = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal,
    });

    if (!resp.ok) {
      let errBody = "";
      try { errBody = (await resp.text()).slice(0, 500); } catch { }
      console.error(`[BTL] POST ${url} -> ${resp.status} ${resp.statusText}. Body: ${errBody}`);
      return null;
    }

    const reader = resp.body?.getReader();
    if (!reader) return null;

    const td = new TextDecoder();
    let buf = "";
    let out = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += td.decode(value, { stream: true });

      // SSE phân mảnh theo dòng "data: {...}\n\n"
      let idx: number;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const chunk = buf.slice(0, idx).trim();
        buf = buf.slice(idx + 2);

        // mỗi dòng có thể là: "data: {json}"
        if (chunk.startsWith("data:")) {
          const payload = chunk.slice(5).trim();
          if (payload === "[DONE]") continue;

          try {
            const obj = JSON.parse(payload) as any;
            // Hỗ trợ 2 kiểu: delta tích lũy hoặc completion cuối
            if (typeof obj?.delta === "string") out += obj.delta;
            if (typeof obj?.completion === "string") out = obj.completion; // phòng server gửi snapshot
          } catch (e) {
            console.error("[BTL] SSE JSON parse error:", e);
          }
        }
      }
    }

    const cleaned = stripMdFence(out).trimEnd();
    return cleaned.length ? cleaned : null;
  } catch (err: any) {
    if (err?.name === "AbortError") return null;
    console.error("[BTL] fetchStreamCompletion lỗi:", err);
    return null;
  }
}

// Get base indentation at cursor position
function getBaseIndent(doc: vscode.TextDocument, pos: vscode.Position): string {
  const line = doc.lineAt(pos.line).text;
  return getIndentFromLine(line);
}
function headOverlapLen(a: string, b: string, cap = 120): number {
  const m = Math.min(a.length, b.length, cap);
  let k = m;
  while (k > 0 && a.slice(0, k) !== b.slice(0, k)) k--;
  return k; // số ký tự trùng ở ĐẦU a và b
}
function needsBlockIndent(prefix: string): boolean {
  const last = prefix.split("\n").pop() ?? "";
  return /:\s*$/.test(last); // dòng trước kết thúc bằng dấu :
}
function stripMdFence(text: string): string {
  const m = text.match(/```(?:\w+)?\n([\s\S]*?)```/);
  return m ? m[1] : text;
}
function isAtLineEnd(doc: vscode.TextDocument, pos: vscode.Position): boolean {
  const line = doc.lineAt(pos.line).text;
  return pos.character >= line.length;
}
function firstNonEmptyLine(s: string): string {
  for (const line of s.split("\n")) {
    const t = line.replace(/\s+$/, "");
    if (t.length) return t;
  }
  return "";
}
function getLastNonEmptyLines(doc: vscode.TextDocument, pos: vscode.Position, k = 3): string[] {
  const out: string[] = [];
  let line = pos.line - 1;
  while (line >= 0 && out.length < k) {
    const t = doc.lineAt(line).text.replace(/\s+$/, "");
    if (t.length) out.push(t);
    line--;
  }
  return out; // thứ tự: gần nhất trước
}
function getTypedStem(prefix: string): string {
  // lấy token Python hợp lệ ngay trước caret, ví dụ "sub" trong "def sub"
  const m = prefix.match(/([A-Za-z_][A-Za-z_0-9]*)$/);
  return m ? m[1] : "";
}
function normalizeLine(s: string): string {
  return s.replace(/\s+/g, " ").trim();
}
function dedupeConsecutiveLinesSoft(s: string): string {
  const lines = s.split("\n");
  const out: string[] = [];
  let prevNorm = "";
  for (const ln of lines) {
    const norm = normalizeLine(ln);
    if (norm.length === 0 || norm !== prevNorm) {
      out.push(ln);
      prevNorm = norm;
    }
  }
  return out.join("\n");
}
function leftOverlapLenOnLine(prefix: string, suggestion: string, limit = 80): number {
  const left = (prefix.split("\n").pop() ?? "");
  // BỎ newline + indent ở đầu gợi ý trước khi so khớp
  const head = suggestion.replace(/^\n+\s*/, "");
  const max = Math.min(left.length, head.length, limit);
  for (let k = max; k > 0; k--) {
    if (left.slice(-k) === head.slice(0, k)) return k;
  }
  return 0;
}

function tidyCompletion(
  raw: string, 
  prefix: string, 
  suffix: string, 
  baseIndent: string,
  indentInfo: { char: string, size: number },
  atEOL: boolean
): string {
  // Step 1: Basic cleaning
  let s = raw.replace(/\r\n/g, "\n");
  s = stripMdFence(s);
  s = s.trim();
  
  if (!s) return '';
  
  // Step 2: Remove overlap with suffix
  const ol = headOverlapLen(s, suffix);
  if (ol > 0 && ol <= 5) {
    s = s.slice(ol);
  }
  
  // Step 3: Deduplicate consecutive similar lines
  s = dedupeConsecutiveLinesSoft(s);
  
  // Step 4: Determine if we need block indent (Python ':')
  const needsBlock = needsBlockIndent(prefix);
  const currentLine = prefix.split('\n').pop() || '';
  const cursorAtLineStart = currentLine.trim().length === 0;
  
  // Step 5: Smart indentation line by line
  const lines = s.split('\n');
  const result: string[] = [];
  
  // Calculate base indent level
  const baseLevel = getIndentLevel(baseIndent, indentInfo.char, indentInfo.size);
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trimStart();
    
    if (!trimmed) {
      // Empty line - keep it
      if (i > 0) result.push('\n');
      continue;
    }
    
    // Detect original indent of this line
    const originalIndent = getIndentFromLine(line);
    let originalLevel = getIndentLevel(originalIndent, ' ', 4); // Assume model uses 4 spaces
    
    if (i === 0) {
      // First line special handling
      if (needsBlock) {
        // After ':' - add one indent level
        const newLevel = baseLevel + 1;
        const newIndent = makeIndent(newLevel, indentInfo.char, indentInfo.size);
        result.push('\n' + newIndent + trimmed);
      } else if (atEOL) {
        // At end of line
        if (cursorAtLineStart) {
          // Cursor at line start - use base indent
          result.push(baseIndent + trimmed);
        } else {
          // Cursor mid-line - check if inline makes sense
          const isOperatorOrKeyword = /^(return|if|else|for|while|class|def|int|void|public|private|=|\+|-|\*|\/|&&|\|\|)/.test(trimmed);
          if (isOperatorOrKeyword && currentLine.length < 80) {
            // Keep inline with space
            result.push(' ' + trimmed);
          } else {
            // Go to new line with base indent
            result.push('\n' + baseIndent + trimmed);
          }
        }
      } else {
        // Middle of line - inline without space
        result.push(trimmed);
      }
    } else {
      // Subsequent lines - preserve relative indentation
      // Calculate relative indent from first line
      const firstLineIndent = lines[0].length - lines[0].trimStart().length;
      const relativeIndent = Math.max(0, (line.length - trimmed.length) - firstLineIndent);
      const relativeLevel = Math.floor(relativeIndent / 4);
      
      // Apply to current base
      const targetLevel = (needsBlock ? baseLevel + 1 : baseLevel) + relativeLevel;
      const newIndent = makeIndent(targetLevel, indentInfo.char, indentInfo.size);
      
      result.push('\n' + newIndent + trimmed);
    }
  }
  
  let final = result.join('');
  
  // Step 6: Final cleanup
  final = final.replace(/```+$/g, "");
  final = final.replace(/\n{3,}/g, "\n\n"); // Max 2 newlines
  
  return final;
}


export class InlineProvider implements vscode.InlineCompletionItemProvider {
  private userId: string | null = null;
  private enablePersonalization: boolean = true;
  private sendFeedback: boolean = true;
  private pendingCompletions: Map<string, { text: string, prefix: string, timestamp: number }> = new Map();

  constructor(
    private readonly serverUrl: string,
    private readonly apiKey: string | undefined,
    private readonly enableStreaming: boolean,
    private readonly timeoutMs: number
  ) {
    // Get user ID and personalization settings
    const config = vscode.workspace.getConfiguration('btl');
    this.enablePersonalization = config.get('enablePersonalization', true);
    this.sendFeedback = config.get('sendFeedback', true);
    
    if (this.enablePersonalization) {
      this.userId = getUserId();
      console.log(`[BTL] User ID for personalization: ${this.userId}`);
    }
  }

  private async sendCompletionFeedback(
    completionText: string,
    prefix: string,
    accepted: boolean,
    acceptTimeMs: number | null = null
  ): Promise<void> {
    if (!this.sendFeedback || !this.userId) return;

    try {
      const url = this.serverUrl.replace(/\/+$/, "") + "/feedback/completion";
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        "X-User-ID": this.userId,
      };
      if (this.apiKey) headers["Authorization"] = `Bearer ${this.apiKey}`;

      const body = {
        request_id: "", // Not tracking request IDs for now
        accepted,
        completion_text: completionText,
        prefix,
        accept_time_ms: acceptTimeMs,
      };

      await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });
      
      console.log(`[BTL] Feedback sent: ${accepted ? 'accepted' : 'rejected'}`);
    } catch (err) {
      console.error('[BTL] Failed to send feedback:', err);
    }
  }

  public async handleAcceptance(completionId: string): Promise<void> {
    const completion = this.pendingCompletions.get(completionId);
    if (!completion) return;

    const acceptTime = Date.now() - completion.timestamp;
    await this.sendCompletionFeedback(
      completion.text,
      completion.prefix,
      true,
      acceptTime
    );

    this.pendingCompletions.delete(completionId);
    
    // Clean up old pending completions (older than 5 minutes)
    const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
    for (const [id, comp] of this.pendingCompletions.entries()) {
      if (comp.timestamp < fiveMinutesAgo) {
        this.pendingCompletions.delete(id);
      }
    }
  }

  async provideInlineCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position,
    context: vscode.InlineCompletionContext,
    token: vscode.CancellationToken
  ): Promise<vscode.InlineCompletionList | null> {
    // Always provide suggestions when requested (like GitHub Copilot)
    // No filtering by trigger kind - let VS Code decide when to show

    const { prefix, suffix } = getPrefixSuffix(document, position);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    token.onCancellationRequested(() => controller.abort());

    try {
      // Map VS Code language IDs to backend language names
      let langId = document.languageId;
      if (langId === 'cpp' || langId === 'c') {
        langId = 'cpp';
      }
      
      // Detect comment-to-code intent
      const commentIntent = detectCommentIntent(prefix, langId);
      
      // Choose appropriate stop sequences
      const stopSeqs = (langId === 'cpp' || langId === 'c') ? DEFAULT_STOPS_CPP : DEFAULT_STOPS_PY;
      
      // Adjust max_tokens if generating from comment (need more space)
      const maxTokens = commentIntent.isComment ? 500 : DEFAULT_MAX_TOKENS;
      
      const requestBody = {
        prefix,
        suffix,
        language: langId,
        temperature: DEFAULT_TEMPERATURE,
        max_tokens: maxTokens,
        stop: stopSeqs,
        comment_instruction: commentIntent.isComment ? commentIntent.instruction : undefined,
      };

      const completion = this.enableStreaming
        ? await fetchStreamCompletion(this.serverUrl, this.apiKey, requestBody, controller.signal, this.userId)
        : await fetchCompletion(this.serverUrl, this.apiKey, requestBody, controller.signal, this.userId);

      if (!completion) return null;

      const baseIndent = getBaseIndent(document, position);
      const indentInfo = detectIndentation(document);
      const atEOL = isAtLineEnd(document, position);
      const post = tidyCompletion(completion, prefix, suffix, baseIndent, indentInfo, atEOL);
      if (!post) return null;

      let finalText = post;

      // Chống lặp: nếu dòng đầu của gợi ý trùng với 1 trong 3 dòng trước caret -> bỏ gợi ý
      const recent = getLastNonEmptyLines(document, position, 3);
      const head = firstNonEmptyLine(finalText);
      if (head && recent.some(l => l === head)) return null;

      // Nếu gợi ý bắt đầu bằng “<một dòng trước>\n…”, cắt phần trùng ấy đi
      for (const l of recent) {
        if (l && finalText.startsWith(l + "\n")) {
          finalText = finalText.slice((l + "\n").length);
          break;
        }
      }
      if (!finalText.trim()) return null;

      const backReplace = leftOverlapLenOnLine(prefix, finalText);

      // 2) ghi đè THUẬN: phần đầu của suffix trùng với gợi ý
      let forwardReplace = 0;
      while (
        forwardReplace < suffix.length &&
        forwardReplace < finalText.length &&
        suffix[forwardReplace] === finalText[forwardReplace]
      ) forwardReplace++;

      // Tạo range thay thế hai phía: [caret - backReplace, caret + forwardReplace]
      const start = new vscode.Position(position.line, Math.max(0, position.character - backReplace));
      const end = position.translate(0, forwardReplace);
      const range = new vscode.Range(start, end);

      // Detect missing imports
      const missingImports = detectMissingImports(finalText, prefix, langId);
      
      // If we have missing imports, prepend them with a comment
      let textWithImports = finalText;
      if (missingImports.length > 0 && commentIntent.isComment) {
        // Show import suggestions as a comment in the completion
        const importComment = langId === 'python' 
          ? `# Add imports: ${missingImports.join(', ')}\n`
          : `// Add imports: ${missingImports.join(', ')}\n`;
        textWithImports = importComment + finalText;
      }

      const item = new vscode.InlineCompletionItem(textWithImports, range);
      
      // Track this completion for feedback
      const completionId = `${Date.now()}_${Math.random()}`;
      if (this.sendFeedback) {
        this.pendingCompletions.set(completionId, {
          text: textWithImports,
          prefix,
          timestamp: Date.now()
        });
        
        // Setup acceptance tracking via command
        (item as any).command = {
          command: 'btl.trackAcceptance',
          title: '',
          arguments: [completionId]
        };
      }
      
      return { items: [item] };

    } catch {
      return null;
    } finally {
      clearTimeout(timeout);
    }
  }
}
