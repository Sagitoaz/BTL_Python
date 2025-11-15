# Giải thích chi tiết: `src/extension.ts`

## 📋 Mục đích của file

File này là **VS Code Extension Entry Point** - điểm khởi đầu:
1. **Activate extension** khi VS Code khởi động
2. **Register InlineCompletionItemProvider** cho Python/C++
3. **Load configuration** từ settings.json
4. **Register commands** (test, view profile, clear profile)
5. **Setup subscriptions** để cleanup khi deactivate
6. **Initialize provider** với server URL và API key

**Main entry point** - kết nối UI với backend!

---

## 🔍 Phân tích từng phần

### Import statements

```typescript
import * as vscode from "vscode";
import { InlineProvider } from "./inlineProvider";
```

**Giải thích:**

- `vscode`: VS Code Extension API
- `InlineProvider`: Custom completion provider class

---

## 🚀 Function: `activate()`

### Purpose
**Called when extension is activated** - first time user triggers it

### Signature

```typescript
export function activate(context: vscode.ExtensionContext)
```

**Parameter:**
- `context`: Extension context (subscriptions, global state, etc.)

**When activated?**
- Extension installed and VS Code starts
- User opens Python/C++ file (activation event)
- User runs extension command

---

### Step 1: Load Configuration

```typescript
const cfg = vscode.workspace.getConfiguration("btl");
const serverUrl =
  cfg.get<string>("serverUrl") ??
  process.env.SERVER_URL ??
  "https://btl-python-r9kz.onrender.com";
const apiKey = cfg.get<string>("apiKey") ?? process.env.API_KEY ?? "5conmeo";
const enableStreaming = cfg.get<boolean>("enableStreaming") ?? false;
const timeoutMs = cfg.get<number>("timeoutMs") ?? 15000;
```

---

### Phân tích Configuration Loading

#### getConfiguration()

```typescript
const cfg = vscode.workspace.getConfiguration("btl");
```

**Loads settings from:**
```json
// settings.json
{
  "btl.serverUrl": "http://localhost:8000",
  "btl.apiKey": "my-secret-key",
  "btl.enableStreaming": true,
  "btl.timeoutMs": 10000
}
```

**Namespace:** `"btl"` groups all settings together

---

#### Nullish Coalescing (??)

```typescript
cfg.get<string>("serverUrl") ?? 
process.env.SERVER_URL ?? 
"https://btl-python-r9kz.onrender.com"
```

**Priority (first non-null/undefined wins):**

1. **VS Code settings** (`btl.serverUrl`)
2. **Environment variable** (`SERVER_URL`)
3. **Default value** (production server)

**Example scenarios:**

**Scenario 1: User configured in settings**
```json
// settings.json
"btl.serverUrl": "http://localhost:8000"
```
```typescript
serverUrl = "http://localhost:8000" ✅
```

**Scenario 2: Environment variable**
```bash
# .env or shell
export SERVER_URL=http://192.168.1.100:8000
```
```typescript
// settings.json has no btl.serverUrl
serverUrl = "http://192.168.1.100:8000" ✅
```

**Scenario 3: Default (nothing configured)**
```typescript
// No settings, no env var
serverUrl = "https://btl-python-r9kz.onrender.com" ✅
```

---

#### serverUrl

```typescript
const serverUrl =
  cfg.get<string>("serverUrl") ??
  process.env.SERVER_URL ??
  "https://btl-python-r9kz.onrender.com";
```

**Default:** Production Render.com deployment

**Why this default?**
- Extension works out-of-the-box
- No local setup needed
- Can override for development

---

#### apiKey

```typescript
const apiKey = cfg.get<string>("apiKey") ?? process.env.API_KEY ?? "5conmeo";
```

**Default:** `"5conmeo"` (demo key)

**Priority:**
1. `btl.apiKey` setting
2. `API_KEY` environment variable
3. Demo key

---

#### enableStreaming

```typescript
const enableStreaming = cfg.get<boolean>("enableStreaming") ?? false;
```

**Default:** `false` (non-streaming)

**Options:**
- `false`: Get complete response (simpler)
- `true`: Stream tokens as generated (faster UX)

---

#### timeoutMs

```typescript
const timeoutMs = cfg.get<number>("timeoutMs") ?? 15000;
```

**Default:** 15 seconds (15,000 ms)

**Why 15s?**
- LLM generation takes 1-5 seconds typically
- Network latency: 1-2 seconds
- Safety margin: 15s prevents false timeouts

---

### Step 2: Create Provider Instance

```typescript
const provider = new InlineProvider(
  serverUrl,
  apiKey,
  enableStreaming,
  timeoutMs
);
```

**Constructor parameters:**
- `serverUrl`: Backend API endpoint
- `apiKey`: Authentication token
- `enableStreaming`: SSE streaming mode
- `timeoutMs`: Request timeout

**See:** `explaincode/src/02_inlineProvider.ts.md` for details

---

### Step 3: Define Language Selector

```typescript
// Register for both Python and C++
const selector: vscode.DocumentSelector = [
  { language: "python", scheme: "file" },
  { language: "python", scheme: "untitled" },
  { language: "cpp", scheme: "file" },
  { language: "cpp", scheme: "untitled" },
  { language: "c", scheme: "file" },
  { language: "c", scheme: "untitled" },
];
```

---

### Phân tích Document Selector

**Purpose:** Tell VS Code which files to activate on

#### Python files

```typescript
{ language: "python", scheme: "file" },
{ language: "python", scheme: "untitled" },
```

**Matches:**
- `file`: Saved Python files (`.py`)
- `untitled`: Unsaved new files with Python language selected

**Examples:**
- `file:///home/user/project/main.py` ✅
- `untitled:Untitled-1` (Python mode) ✅

---

#### C++ files

```typescript
{ language: "cpp", scheme: "file" },
{ language: "cpp", scheme: "untitled" },
```

**Matches:**
- `.cpp`, `.cc`, `.cxx` files
- Unsaved C++ files

---

#### C files

```typescript
{ language: "c", scheme: "file" },
{ language: "c", scheme: "untitled" },
```

**Matches:**
- `.c`, `.h` files
- Unsaved C files

---

**Why separate entries?**
- VS Code requires explicit language + scheme pairs
- Can't use wildcards
- Each combination must be listed

---

### Step 4: Register Provider

```typescript
const disposable = vscode.languages.registerInlineCompletionItemProvider(
  selector,
  provider
);
context.subscriptions.push(disposable);
```

---

### Phân tích Registration

#### registerInlineCompletionItemProvider()

```typescript
vscode.languages.registerInlineCompletionItemProvider(
  selector,  // Which files?
  provider   // Provider instance
)
```

**What happens:**
1. VS Code monitors files matching `selector`
2. When user types → VS Code calls `provider.provideInlineCompletionItems()`
3. Provider returns suggestions
4. VS Code shows inline ghost text

**Similar to:**
- GitHub Copilot
- Tabnine
- IntelliCode

---

#### Disposable Pattern

```typescript
const disposable = vscode.languages.registerInlineCompletionItemProvider(...);
context.subscriptions.push(disposable);
```

**Why disposable?**
- Need to unregister on deactivation
- Prevent memory leaks
- Clean shutdown

**Lifecycle:**
```typescript
// Activation:
disposable = register(...)
context.subscriptions.push(disposable)

// Deactivation (automatic):
for (const sub of context.subscriptions) {
  sub.dispose()  // ← Unregisters provider
}
```

---

### Step 5: Register Acceptance Tracking Command

```typescript
// Track completion acceptance
context.subscriptions.push(
  vscode.commands.registerCommand("btl.trackAcceptance", async (completionId: string) => {
    await (provider as any).handleAcceptance(completionId);
  })
);
```

---

### Phân tích Acceptance Tracking

**Purpose:** Send feedback when user accepts completion

**Flow:**

1. **User accepts completion** (presses Tab/Enter)
2. **VS Code triggers command** with completion ID
3. **Provider sends feedback** to backend `/feedback/completion`
4. **Backend updates user profile**

**Command ID:** `"btl.trackAcceptance"`

**Parameter:** `completionId: string`
- Unique ID generated per completion
- Format: `"1699704225_0.123456"`

**Type cast:** `(provider as any)`
- TypeScript doesn't know about `handleAcceptance` method
- Safe cast to bypass type checking

---

### Step 6: Register Inline Suggest Command

```typescript
// (tùy chọn) lệnh bật/tắt gợi ý nhanh
context.subscriptions.push(
  vscode.commands.registerCommand("btl.inlineSuggest", async () => {
    await vscode.commands.executeCommand(
      "editor.action.inlineSuggest.trigger"
    );
  })
);
```

---

### Phân tích Inline Suggest Command

**Purpose:** Manual trigger for completions

**Command ID:** `"btl.inlineSuggest"`

**Executes built-in command:**
```typescript
"editor.action.inlineSuggest.trigger"
```

**Built-in VS Code command:**
- Shows inline suggestion at cursor
- Same as Copilot hotkey (usually Ctrl+Space or Alt+\)

**User can bind to hotkey:**
```json
// keybindings.json
{
  "key": "ctrl+alt+space",
  "command": "btl.inlineSuggest",
  "when": "editorTextFocus"
}
```

---

### Step 7: Register Test Completion Command

```typescript
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
```

---

### Phân tích Test Command

**Purpose:** Debug/test completions

**Command ID:** `"btl.testCompletion"`

**User invocation:**
```
Ctrl+Shift+P → "BTL: Test Completion"
```

---

#### Check Active Editor

```typescript
const editor = vscode.window.activeTextEditor;
if (!editor) {
  vscode.window.showWarningMessage("No active editor");
  return;
}
```

**Validation:**
- User must have a file open
- Cursor must be in editor
- If not → show warning and exit

---

#### Show Info Message

```typescript
vscode.window.showInformationMessage(
  `Testing completion with server: ${serverUrl}`
);
```

**Output:**
```
ℹ Testing completion with server: https://btl-python-r9kz.onrender.com
```

**Benefits:**
- User knows which server is being used
- Helps debug connection issues
- Confirms extension is active

---

#### Trigger Completion

```typescript
await vscode.commands.executeCommand(
  "editor.action.inlineSuggest.trigger"
);
```

**Manually triggers completion** at current cursor position

---

### Step 8: Register View Profile Command

```typescript
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
      // ... webview creation ...
```

---

### Phân tích View Profile

**Command ID:** `"btl.viewProfile"`

**Purpose:** Show user's coding profile in webview

---

#### Check Personalization

```typescript
const userId = (provider as any).userId;
if (!userId) {
  vscode.window.showWarningMessage("Personalization is disabled");
  return;
}
```

**userId = null when:**
- User disabled personalization in settings
- Privacy mode enabled

---

#### Fetch Profile from Backend

```typescript
const headers: Record<string, string> = {
  "X-User-ID": userId,
};
if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

const response = await fetch(`${serverUrl}/feedback/profile`, { headers });
```

**Endpoint:** `GET /feedback/profile`

**Headers:**
- `X-User-ID`: Hashed user identifier
- `Authorization`: Bearer token (if configured)

**Response:**
```json
{
  "user_id": "e3b0c442",
  "coding_style": {
    "indent_size": 4,
    "uses_tabs": false,
    "total_samples": 42,
    ...
  },
  "accept_rate": 0.85,
  "avg_accept_time_ms": 450.0,
  ...
}
```

---

#### Create Webview Panel

```typescript
const panel = vscode.window.createWebviewPanel(
  'btlProfile',              // View type ID
  'My Coding Profile',       // Panel title
  vscode.ViewColumn.One,     // Show in first column
  {}                         // Options (empty)
);
```

**Creates new tab** with HTML content

---

#### Webview HTML

```typescript
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
```

---

### Phân tích Webview HTML

**Profile display:**

**User ID:**
```typescript
${userId}
// → "e3b0c442f8a3b1d9"
```

**Total Samples:**
```typescript
${profile.coding_style?.total_samples || 0}
// → "42"
```

**Indent Style:**
```typescript
${profile.coding_style?.uses_tabs ? 'Tabs' : profile.coding_style?.indent_size + ' spaces'}
// → "4 spaces" or "Tabs"
```

**Quotes:**
```typescript
${profile.coding_style?.prefer_double_quotes ? 'Double' : 'Single'}
// → "Single" or "Double"
```

**Naming Convention:**
```typescript
${profile.coding_style?.snake_case_ratio > 0.5 ? 'snake_case' : 'camelCase'}
// If 60% snake_case → "snake_case"
// If 30% snake_case → "camelCase"
```

**Type Hints:**
```typescript
${(profile.coding_style?.type_hints_ratio * 100).toFixed(0)}%
// 0.75 → "75%"
```

**Docstrings:**
```typescript
${(profile.coding_style?.docstring_ratio * 100).toFixed(0)}%
// 0.42 → "42%"
```

**Accept Rate:**
```typescript
${(profile.accept_rate * 100).toFixed(1)}%
// 0.854 → "85.4%"
```

**Avg Accept Time:**
```typescript
${profile.avg_accept_time_ms?.toFixed(0) || 'N/A'} ms
// 450.5 → "451 ms"
// null → "N/A"
```

---

#### Error Handling

```typescript
} catch (err) {
  vscode.window.showErrorMessage(`Failed to load profile: ${err}`);
}
```

**Shows popup** if fetch fails

---

### Step 9: Register Clear Profile Command

```typescript
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
```

---

### Phân tích Clear Profile

**Command ID:** `"btl.clearProfile"`

**Purpose:** Delete user profile (GDPR compliance!)

---

#### Confirmation Dialog

```typescript
const confirm = await vscode.window.showWarningMessage(
  "Delete your coding profile? This cannot be undone.",
  { modal: true },
  "Delete"
);

if (confirm !== "Delete") return;
```

**Modal dialog:**
```
⚠ Delete your coding profile? This cannot be undone.
   [Cancel]  [Delete]
```

**`modal: true`:**
- Blocks VS Code UI
- User must respond
- Prevents accidental deletion

**Return value:**
- User clicks "Delete" → `confirm = "Delete"`
- User clicks "Cancel" or ESC → `confirm = undefined`

---

#### Send DELETE Request

```typescript
const response = await fetch(`${serverUrl}/feedback/profile`, {
  method: "DELETE",
  headers
});
```

**Endpoint:** `DELETE /feedback/profile`

**Backend action:**
- Deletes `data/user_profiles/{user_id}.json`
- Returns 200 OK

---

#### Success Message

```typescript
vscode.window.showInformationMessage("Coding profile deleted successfully");
```

**Notification:**
```
ℹ Coding profile deleted successfully
```

---

## 🔚 Function: `deactivate()`

### Purpose
**Called when extension is deactivated**

### Code

```typescript
export function deactivate() {}
```

**Currently empty** - cleanup handled automatically by `context.subscriptions`

**Could add:**
- Save pending data
- Close connections
- Log deactivation

---

## 💡 Key Points cho thuyết trình

### 1. Extension Activation Flow

```
VS Code starts
    ↓
Reads package.json
    ↓
Checks activationEvents: ["onLanguage:python", "onLanguage:cpp"]
    ↓
User opens Python/C++ file
    ↓
activate() called
    ↓
Load config → Create provider → Register commands
    ↓
Extension ready! 🎉
```

---

### 2. Configuration Priority System

**Three-tier fallback:**

```typescript
value = userSetting ?? envVariable ?? defaultValue
```

**Example:**

| Source | Priority | Use Case |
|--------|----------|----------|
| VS Code Settings | 1 (highest) | User preference |
| Environment Variable | 2 | CI/CD, Docker |
| Default Value | 3 (fallback) | Out-of-box |

**Benefits:**
- ✅ Flexible deployment
- ✅ User control
- ✅ Works without config

---

### 3. Document Selector Design

**Why explicit selectors?**

```typescript
[
  { language: "python", scheme: "file" },
  { language: "python", scheme: "untitled" },
  ...
]
```

**Alternatives (not used):**

**Option 1: Wildcard (not supported)**
```typescript
{ language: "*", scheme: "*" }  ❌
```

**Option 2: Array of languages (not supported)**
```typescript
{ language: ["python", "cpp"], scheme: "file" }  ❌
```

**Current approach (correct):**
```typescript
[
  { language: "python", scheme: "file" },
  { language: "cpp", scheme: "file" },
]  ✅
```

---

### 4. Command Registration Pattern

**Standard pattern:**

```typescript
context.subscriptions.push(
  vscode.commands.registerCommand("command.id", async (...args) => {
    // Command logic
  })
);
```

**Benefits:**
- Auto-cleanup on deactivation
- Memory leak prevention
- Proper lifecycle management

**Our commands:**
- `btl.trackAcceptance` - Feedback tracking
- `btl.inlineSuggest` - Manual trigger
- `btl.testCompletion` - Debug/test
- `btl.viewProfile` - Show profile UI
- `btl.clearProfile` - Delete data (GDPR)

---

### 5. Webview for Profile Display

**Why webview?**

**Alternatives:**

**Option 1: QuickPick (limited)**
```typescript
vscode.window.showQuickPick([
  "Indent: 4 spaces",
  "Accept rate: 85%"
])
```
❌ No styling, no layout

**Option 2: Output Channel (ugly)**
```typescript
outputChannel.appendLine("Indent: 4 spaces")
```
❌ Plain text only

**Option 3: Webview (chosen) ✅**
```typescript
panel.webview.html = `<html>...</html>`
```
✅ Full HTML/CSS
✅ Rich formatting
✅ Interactive (could add buttons)

---

### 6. Privacy & GDPR Compliance

**Features:**

**Anonymous User ID:**
```typescript
machineId → SHA256 → "e3b0c442..."
```
- Can't identify user
- Persistent per machine
- No personal data stored

**Clear Profile Command:**
```typescript
vscode.commands.registerCommand("btl.clearProfile", ...)
```
- User can delete all data
- Confirmation dialog
- Complies with GDPR "right to erasure"

**Opt-out Option:**
```json
// settings.json
"btl.enablePersonalization": false
```
- Disables user tracking
- No profile created
- Privacy-first design

---

## 🧪 Test Cases

### Test 1: Extension activates

```typescript
import * as vscode from 'vscode';
import * as myExtension from '../extension';

suite('Extension Test Suite', () => {
  test('Extension should activate', async () => {
    const ext = vscode.extensions.getExtension('your-publisher.btl-python');
    assert.ok(ext);
    await ext?.activate();
    assert.strictEqual(ext?.isActive, true);
  });
});
```

---

### Test 2: Configuration loading

```typescript
test('Should load configuration with defaults', () => {
  const config = vscode.workspace.getConfiguration('btl');
  
  // Should have default serverUrl if not configured
  const serverUrl = config.get<string>('serverUrl') ?? 'https://btl-python-r9kz.onrender.com';
  assert.ok(serverUrl.startsWith('http'));
  
  // Should have default timeout
  const timeout = config.get<number>('timeoutMs') ?? 15000;
  assert.strictEqual(timeout >= 1000, true);
});
```

---

### Test 3: Commands registered

```typescript
test('Commands should be registered', async () => {
  const commands = await vscode.commands.getCommands();
  
  assert.ok(commands.includes('btl.trackAcceptance'));
  assert.ok(commands.includes('btl.inlineSuggest'));
  assert.ok(commands.includes('btl.testCompletion'));
  assert.ok(commands.includes('btl.viewProfile'));
  assert.ok(commands.includes('btl.clearProfile'));
});
```

---

### Test 4: Provider registration

```typescript
test('Inline completion provider should be registered', async () => {
  const doc = await vscode.workspace.openTextDocument({
    language: 'python',
    content: 'def add('
  });
  
  const editor = await vscode.window.showTextDocument(doc);
  const position = new vscode.Position(0, 8);
  
  // Trigger completion
  await vscode.commands.executeCommand('editor.action.inlineSuggest.trigger');
  
  // Should have completions available (if server is running)
  // Note: Hard to test without mocking server
});
```

---

### Test 5: View profile command

```typescript
test('View profile command should open webview', async () => {
  // This test requires mocking fetch and provider
  const originalFetch = global.fetch;
  
  global.fetch = async () => ({
    ok: true,
    json: async () => ({
      coding_style: {
        indent_size: 4,
        total_samples: 10
      },
      accept_rate: 0.8
    })
  }) as any;
  
  try {
    await vscode.commands.executeCommand('btl.viewProfile');
    // Webview should be created
    // Hard to assert without access to webview internals
  } finally {
    global.fetch = originalFetch;
  }
});
```

---

### Test 6: Deactivation cleanup

```typescript
test('Extension should cleanup on deactivate', async () => {
  const ext = vscode.extensions.getExtension('your-publisher.btl-python');
  await ext?.activate();
  
  const commandsBefore = await vscode.commands.getCommands();
  assert.ok(commandsBefore.includes('btl.testCompletion'));
  
  // Deactivate
  if (ext?.exports?.deactivate) {
    await ext.exports.deactivate();
  }
  
  // Commands should still be there (VS Code handles cleanup)
  // But provider should be disposed
});
```

---

**File extension.ts hoàn tất!** ✅

**Tiếp theo:** `inlineProvider.ts` - The CORE logic file (684 lines!) 🚀

Tiếp tục không?

