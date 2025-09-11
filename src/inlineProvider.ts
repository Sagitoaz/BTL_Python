import * as vscode from 'vscode';

const DEFAULT_STOPS_PY = ["\n\n```", "\n\n##", "\n\n# ", "\n\n\"\"\"", "\n\n'''"];
const DEFAULT_TEMPERATURE = 0.2;
const DEFAULT_MAX_TOKENS = 128;
const MAX_SIDE_CHARS = 4000;

function stripMdFence(text: string): string {
    const m = text.match(/```(?:\w+)?\n([\s\S]*?)```/);
    return m ? m[1] : text;
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

    // 401/403 coi như không gợi ý
    if (!resp.ok) return null;

    const data = (await resp.json()) as ApiResp | null;

    const raw =
      data?.completion ??
      data?.choices?.[0]?.text ??
      "";

    if (typeof raw !== "string" || !raw) return null;

    // Hậu xử lý nhẹ
    const cleaned = stripMdFence(raw).trimEnd();
    return cleaned.length ? cleaned : null;
  } catch (err: any) {
    // Bị hủy do timeout/caret di chuyển
    if (err?.name === "AbortError") return null;
    return null;
  }
}


export class InlineProvider implements vscode.InlineCompletionItemProvider {
    constructor(
        private readonly serverUrl: string,
        private readonly apiKey?: string
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
        const timeout = setTimeout(() => controller.abort(), 2500); // 2.5s timeout
        token.onCancellationRequested(() => controller.abort());

        try {
            const completion = await fetchCompletion(
                this.serverUrl,
                this.apiKey,
                {
                    prefix,
                    suffix,
                    language: document.languageId,
                    temperature: DEFAULT_TEMPERATURE,
                    max_tokens: DEFAULT_MAX_TOKENS,
                    stops: document.languageId === 'python' ? DEFAULT_STOPS_PY : [],
                },
                controller.signal
            );

            if (!completion) return null;

            // Chỉ chèn từ vị trí con trỏ (range rỗng)
            const item = new vscode.InlineCompletionItem(completion, new vscode.Range(position, position));
            return { items: [item] };
        } catch {
            return null;
        } finally {
            clearTimeout(timeout);
        }
    }
}
