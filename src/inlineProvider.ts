import * as vscode from 'vscode';

const DEFAULT_STOPS_PY = ["\n\n", "\n\n```", "\n\n##", "\n\n# ", "\n\n\"\"\"", "\n\n'''"];
const DEFAULT_TEMPERATURE = 0.2;
const DEFAULT_MAX_TOKENS = 128;
const MAX_SIDE_CHARS = 4000;

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
  signal: AbortSignal
): Promise<string | null> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Accept": "application/json",
  };
  if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

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
  signal: AbortSignal
): Promise<string | null> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
  };
  if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

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

function getLineIndent(doc: vscode.TextDocument, pos: vscode.Position): string {
  const line = doc.lineAt(pos.line).text;
  const m = line.match(/^(\s*)/);
  return m ? m[1] : "";
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

function tidyCompletion(raw: string, prefix: string, suffix: string, baseIndent: string, atEOL: boolean): string {
  let s = raw.replace(/\r\n/g, "\n");
  s = stripMdFence(s);
  s = s.replace(/^\n{3,}/, "\n\n");
  s = dedupeConsecutiveLinesSoft(s);

  // tránh lặp với phần sau con trỏ
  const ol = headOverlapLen(s, suffix);
  if (ol > 0 && ol <= 3) {
    s = s.slice(ol);
  }

  // nếu ngay trước caret là ':', tạo block => bắt buộc newline + indent 4
  if (needsBlockIndent(prefix)) {
    if (s.startsWith("\n")) s = s.replace(/^\n(\s*)?/, "\n" + baseIndent + "    ");
    else s = "\n" + baseIndent + "    " + s;
  } else if (atEOL && !s.startsWith("\n")) {
    // nếu caret ở cuối dòng và completion bắt đầu bằng ký tự nội dung => xuống dòng + giữ indent hiện tại
    s = "\n" + baseIndent + s;
  } else {
    // nếu đang ở dòng chỉ có indent, thêm indent cho dòng đầu
    if (/^[^\s]/.test(s) && /^\s*$/.test(baseIndent)) s = baseIndent + s;
  }

  s = s.replace(/```+$/g, "");
  return s.trimEnd();
}


export class InlineProvider implements vscode.InlineCompletionItemProvider {
  constructor(
    private readonly serverUrl: string,
    private readonly apiKey: string | undefined,
    private readonly enableStreaming: boolean,
    private readonly timeoutMs: number
  ) { }

  async provideInlineCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position,
    context: vscode.InlineCompletionContext,
    token: vscode.CancellationToken
  ): Promise<vscode.InlineCompletionList | null> {
    // Không spam: chỉ gợi ý khi người dùng vừa gõ (typing trigger)

    const { prefix, suffix } = getPrefixSuffix(document, position);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    token.onCancellationRequested(() => controller.abort());

    try {
      const requestBody = {
        prefix,
        suffix,
        language: document.languageId,
        temperature: DEFAULT_TEMPERATURE,
        max_tokens: DEFAULT_MAX_TOKENS,
        stop: document.languageId === 'python' ? DEFAULT_STOPS_PY : [],
      };

      const completion = this.enableStreaming
        ? await fetchStreamCompletion(this.serverUrl, this.apiKey, requestBody, controller.signal)
        : await fetchCompletion(this.serverUrl, this.apiKey, requestBody, controller.signal);

      if (!completion) return null;

      const baseIndent = getLineIndent(document, position);
      const atEOL = isAtLineEnd(document, position);
      const post = tidyCompletion(completion, prefix, suffix, baseIndent, atEOL);
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

      const item = new vscode.InlineCompletionItem(finalText, range);
      return { items: [item] };

    } catch {
      return null;
    } finally {
      clearTimeout(timeout);
    }
  }
}
