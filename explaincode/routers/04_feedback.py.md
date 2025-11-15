# Giải thích chi tiết: `server/app/routers/feedback.py`

## 📋 Mục đích của file

File này implement **User Feedback Endpoints** để:
1. **Record feedback** (accept/reject completions)
2. **Build user profiles** dựa trên feedback patterns
3. **Personalize completions** theo coding style cá nhân
4. **Manage user profiles** (get, delete)
5. **Track acceptance metrics** (accept rate, accept time)

---

## 🔍 Phân tích từng phần

### Import statements

```python
"""
User feedback endpoints for personalization.
Track accept/reject to improve future suggestions.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from app.core.security import require_api_key
from app.services.user_profiling import get_profiler
```

**Giải thích:**

- `logging`: Log feedback operations
- `Optional`: Type hint for optional values
- `APIRouter, Depends, HTTPException, Header`: FastAPI components
- `BaseModel`: Pydantic model for request validation
- `require_api_key`: Authentication
- `get_profiler`: User profiling service singleton

---

## 🛠️ Router Setup

```python
router = APIRouter(prefix="/feedback", tags=["feedback"])
logger = logging.getLogger("feedback")
```

**Configuration:**

#### `prefix="/feedback"`
- All endpoints start with `/feedback`
- URLs: `/feedback/completion`, `/feedback/profile`

#### `tags=["feedback"]`
- OpenAPI/Swagger grouping
- Separate section in docs

#### Logger
- Named logger: `"feedback"`
- Separate from other components

---

## 📝 Pydantic Model: `CompletionFeedback`

### Purpose
**Request model** cho completion feedback

### Code

```python
class CompletionFeedback(BaseModel):
    """Feedback on a completion"""
    request_id: str
    accepted: bool
    completion_text: str = ""
    prefix: str = ""
    accept_time_ms: float = 0.0
```

---

### Fields Explained

#### `request_id: str`
**Purpose:** Correlate feedback với original completion request

**Example:**
```python
request_id = "550e8400-e29b-41d4-a716-446655440000"
```

**Use case:**
- Link feedback to telemetry data
- Debug specific completions
- Track user journey

---

#### `accepted: bool`

**Values:**
- `True`: User accepted completion (pressed Tab/Enter)
- `False`: User rejected completion (pressed Esc/ignored)

**Example:**
```python
accepted = True   # User liked it ✅
accepted = False  # User didn't like it ❌
```

---

#### `completion_text: str = ""`

**Purpose:** The completion that was accepted/rejected

**Default:** Empty string (optional)

**Example:**
```python
completion_text = "return a + b"
```

**Use case:**
- Analyze what patterns user accepts
- Learn coding style preferences
- Build personalized prompts

---

#### `prefix: str = ""`

**Purpose:** Code context before completion

**Default:** Empty string (optional)

**Example:**
```python
prefix = "def add(a, b):\n    "
```

**Use case:**
- Understand context of acceptance
- Pattern matching (e.g., user accepts type hints in function signatures)

---

#### `accept_time_ms: float = 0.0`

**Purpose:** Time from suggestion to acceptance (milliseconds)

**Default:** 0.0 (optional)

**Example:**
```python
accept_time_ms = 1234.5  # 1.23 seconds
```

**Use case:**
- Quick acceptance → high confidence
- Slow acceptance → user thinking/editing
- Metrics: Average time to accept

---

### Example Request

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "accepted": true,
  "completion_text": "return a + b",
  "prefix": "def add(a, b):\n    ",
  "accept_time_ms": 850.5
}
```

---

## ✅ Endpoint: POST `/feedback/completion`

### Purpose
**Record user feedback** on a completion để improve personalization

### Code

```python
@router.post("/completion", dependencies=[Depends(require_api_key)])
def record_completion_feedback(
    feedback: CompletionFeedback,
    x_user_id: Optional[str] = Header(None, description="User identifier")
):
    """
    Record user feedback on a completion (accepted or rejected).
    This helps personalize future suggestions.
    """
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-ID header required for feedback"
        )
```

---

### Phân tích chi tiết

#### Function Parameters

```python
def record_completion_feedback(
    feedback: CompletionFeedback,
    x_user_id: Optional[str] = Header(None, description="User identifier")
):
```

**`feedback: CompletionFeedback`:**
- Request body (JSON)
- Validated by Pydantic
- Auto-converted to `CompletionFeedback` object

**`x_user_id: Optional[str] = Header(None, ...)`:**
- Extract from HTTP header `X-User-ID`
- Optional (can be `None`)
- Required for feedback (validated below)

---

#### Require User ID

```python
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-ID header required for feedback"
        )
```

**Why required?**
- Feedback is user-specific
- Need to know WHO gave feedback
- Can't personalize without user identification

**Request without header:**
```http
POST /feedback/completion
Authorization: Bearer sk_abc123
Content-Type: application/json

{"request_id": "...", "accepted": true}

Response:
{
  "detail": "X-User-ID header required for feedback"
}
Status: 400 Bad Request
```

**Request with header:**
```http
POST /feedback/completion
Authorization: Bearer sk_abc123
X-User-ID: user-456
Content-Type: application/json

{"request_id": "...", "accepted": true}

→ ✅ Processes feedback
```

---

### Update User Profile

```python
    try:
        profiler = get_profiler()
        profile = profiler.update_profile_from_completion(
            user_id=x_user_id,
            prefix=feedback.prefix,
            completion=feedback.completion_text,
            accepted=feedback.accepted,
            accept_time_ms=feedback.accept_time_ms
        )
```

---

#### Get Profiler Instance

```python
        profiler = get_profiler()
```

**Singleton pattern:**
- Same instance across all requests
- Maintains in-memory cache
- Manages profile persistence

**See:** `app.services.user_profiling.get_profiler()`

---

#### Update Profile

```python
        profile = profiler.update_profile_from_completion(
            user_id=x_user_id,
            prefix=feedback.prefix,
            completion=feedback.completion_text,
            accepted=feedback.accepted,
            accept_time_ms=feedback.accept_time_ms
        )
```

**Method purpose:**
- Load user's existing profile (or create new)
- Update statistics (accept rate, avg time)
- Analyze coding patterns
- Extract style preferences
- Save updated profile

**Returns:** Updated `UserProfile` object

**See:** `app.services.user_profiling.update_profile_from_completion()`

---

### Return Response

```python
        return {
            "status": "ok",
            "user_id": x_user_id,
            "total_samples": profile.coding_style.total_samples,
            "accept_rate": profile.accept_rate
        }
```

**Response fields:**

#### `"status": "ok"`
- Success indicator
- Feedback recorded successfully

#### `"user_id": x_user_id`
- Echo user ID back
- Confirm which user was updated

#### `"total_samples": profile.coding_style.total_samples`
- How many completions tracked
- Indicates data quality (more samples = better personalization)

#### `"accept_rate": profile.accept_rate`
- Percentage of completions accepted
- User satisfaction metric

---

### Example Response

```json
{
  "status": "ok",
  "user_id": "user-456",
  "total_samples": 127,
  "accept_rate": 0.85
}
```

**Interpretation:**
- User `user-456` profile updated
- 127 completions tracked
- 85% acceptance rate (high satisfaction!)

---

### Error Handling

```python
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Catch-all exception:**
- Any error in profiling → 500 error
- Log for debugging
- Return error to client

**Possible errors:**
- File I/O error (can't save profile)
- JSON parsing error (corrupt profile file)
- Unexpected data format

---

## 👤 Endpoint: GET `/feedback/profile`

### Purpose
**Retrieve user's coding profile** and personalization data

### Code

```python
@router.get("/profile", dependencies=[Depends(require_api_key)])
def get_user_profile(
    x_user_id: Optional[str] = Header(None, description="User identifier")
):
    """Get user's coding profile and personalization data"""
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-ID header required"
        )
```

---

### Phân tích chi tiết

#### Require User ID

```python
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-ID header required"
        )
```

**Same as POST endpoint:**
- Must specify which user's profile
- Can't return profile without user ID

---

### Load Profile

```python
    try:
        profiler = get_profiler()
        profile = profiler.load_profile(x_user_id)
```

**`load_profile()` method:**
- Read profile from disk (JSON file)
- Parse into `UserProfile` object
- If doesn't exist → create default profile

**File location:**
```
data/profiles/user-456.json
```

---

### Return Profile Data

```python
        return {
            "user_id": profile.user_id,
            "coding_style": profile.coding_style.model_dump(),
            "accept_rate": profile.accept_rate,
            "avg_accept_time_ms": profile.avg_accept_time_ms,
            "preferred_completion_length": profile.preferred_completion_length,
            "total_samples": profile.coding_style.total_samples,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at
        }
```

---

### Response Fields Explained

#### `"user_id"`
```python
"user_id": "user-456"
```

**User identifier**

---

#### `"coding_style"`
```python
"coding_style": {
    "uses_type_hints": true,
    "prefers_single_quotes": false,
    "uses_semicolons": false,
    "indentation": "4_spaces",
    "naming_convention": "snake_case",
    "total_samples": 127
}
```

**Detected coding patterns:**
- Type hints preference (Python)
- Quote style (' vs ")
- Semicolon usage (JavaScript)
- Indentation (tabs vs spaces)
- Naming convention (snake_case vs camelCase)

---

#### `"accept_rate"`
```python
"accept_rate": 0.85
```

**Calculation:**
```python
accept_rate = accepted_count / total_completions
# 108 accepted / 127 total = 0.85 (85%)
```

---

#### `"avg_accept_time_ms"`
```python
"avg_accept_time_ms": 1234.5
```

**Average time to accept completions (milliseconds)**

**Interpretation:**
- < 500ms: Instant acceptance (high confidence)
- 500-2000ms: Normal (user reads before accepting)
- > 2000ms: Slow (user editing/thinking)

---

#### `"preferred_completion_length"`
```python
"preferred_completion_length": 45
```

**Average length of accepted completions (characters)**

**Use case:**
- User prefers short snippets → generate 1-line completions
- User accepts long blocks → generate multi-line completions

---

#### `"total_samples"`
```python
"total_samples": 127
```

**Number of completions tracked**

**Data quality indicator:**
- < 10 samples: Not enough data (use defaults)
- 10-50 samples: Some patterns emerging
- > 50 samples: Good personalization possible

---

#### `"created_at"` / `"updated_at"`
```python
"created_at": "2025-11-01T10:30:00",
"updated_at": "2025-11-11T14:23:45"
```

**Timestamps:**
- Profile creation date
- Last update date

---

### Example Response

```json
{
  "user_id": "user-456",
  "coding_style": {
    "uses_type_hints": true,
    "prefers_single_quotes": false,
    "uses_semicolons": false,
    "indentation": "4_spaces",
    "naming_convention": "snake_case",
    "total_samples": 127
  },
  "accept_rate": 0.85,
  "avg_accept_time_ms": 1234.5,
  "preferred_completion_length": 45,
  "total_samples": 127,
  "created_at": "2025-11-01T10:30:00.000Z",
  "updated_at": "2025-11-11T14:23:45.123Z"
}
```

---

### Error Handling

```python
    except Exception as e:
        logger.error(f"Failed to get profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Possible errors:**
- Profile file not found (though should create default)
- JSON parse error (corrupt file)
- File permission issues

---

## 🗑️ Endpoint: DELETE `/feedback/profile`

### Purpose
**Delete user's profile** and all personalization data (GDPR compliance)

### Code

```python
@router.delete("/profile", dependencies=[Depends(require_api_key)])
def delete_user_profile(
    x_user_id: Optional[str] = Header(None, description="User identifier")
):
    """Delete user's profile and all personalization data"""
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-ID header required"
        )
```

---

### Phân tích chi tiết

#### Require User ID

```python
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-ID header required"
        )
```

**Must specify which user to delete**

---

### Delete Profile File

```python
    try:
        profiler = get_profiler()
        profile_path = profiler.get_profile_path(x_user_id)
        
        if profile_path.exists():
            profile_path.unlink()
            return {"status": "deleted", "user_id": x_user_id}
        else:
            return {"status": "not_found", "user_id": x_user_id}
```

---

#### Get Profile Path

```python
        profile_path = profiler.get_profile_path(x_user_id)
```

**Returns:** `Path` object to profile file

**Example:**
```python
profile_path = Path("data/profiles/user-456.json")
```

---

#### Check Exists and Delete

```python
        if profile_path.exists():
            profile_path.unlink()
            return {"status": "deleted", "user_id": x_user_id}
```

**`profile_path.exists()`:**
- Check if file exists on disk

**`profile_path.unlink()`:**
- Delete file
- Equivalent to `os.remove()`

**Response:**
```json
{
  "status": "deleted",
  "user_id": "user-456"
}
```

---

#### Profile Not Found

```python
        else:
            return {"status": "not_found", "user_id": x_user_id}
```

**If no profile exists:**
- Return "not_found" status
- Still 200 OK (idempotent operation)

**Response:**
```json
{
  "status": "not_found",
  "user_id": "user-456"
}
```

---

### Error Handling

```python
    except Exception as e:
        logger.error(f"Failed to delete profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Possible errors:**
- Permission denied (can't delete file)
- File system error

---

## 📊 Diagram: Feedback Flow

```
┌─────────────────────────────────────────────────────┐
│           VS Code Extension (Client)                 │
│                                                     │
│  User types: def add(a, b):                         │
│              ▯                                      │
│                                                     │
│  Extension requests completion                       │
│  POST /complete                                     │
│  X-User-ID: user-456                                │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│                  Server                              │
│  Returns completion: "return a + b"                 │
│  request_id: "abc-123"                              │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│           VS Code Extension (Client)                 │
│                                                     │
│  Shows ghost text:                                  │
│  def add(a, b):                                     │
│      return a + b  ← Ghost text                     │
│                                                     │
│  User presses Tab → Accept! ✅                      │
│  (Or Esc → Reject ❌)                               │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓ Send feedback
┌─────────────────────────────────────────────────────┐
│              POST /feedback/completion               │
│  X-User-ID: user-456                                │
│  {                                                  │
│    "request_id": "abc-123",                         │
│    "accepted": true,                                │
│    "completion_text": "return a + b",              │
│    "prefix": "def add(a, b):\n    ",               │
│    "accept_time_ms": 850.5                          │
│  }                                                  │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│         update_profile_from_completion()             │
│                                                     │
│  1. Load profile: data/profiles/user-456.json       │
│                                                     │
│  2. Analyze completion:                             │
│     - No type hints → uses_type_hints = false      │
│     - return statement → function completion        │
│     - Length: 12 chars                              │
│                                                     │
│  3. Update statistics:                              │
│     - total_completions++                           │
│     - accepted_count++ (if accepted)                │
│     - accept_rate = accepted / total                │
│     - avg_accept_time = ...                         │
│                                                     │
│  4. Save profile                                    │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│              Response                                │
│  {                                                  │
│    "status": "ok",                                  │
│    "user_id": "user-456",                           │
│    "total_samples": 128,                            │
│    "accept_rate": 0.86                              │
│  }                                                  │
└─────────────────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│         Next Completion Request                      │
│                                                     │
│  POST /complete                                     │
│  X-User-ID: user-456                                │
│                                                     │
│  → Server loads profile                             │
│  → Generates style hints:                           │
│     "Based on your history: Don't use type hints"   │
│  → Includes in prompt                               │
│  → Better personalized completion! 🎯               │
└─────────────────────────────────────────────────────┘
```

---

## 💡 Key Points cho thuyết trình

### 1. Feedback Loop for Personalization

**How it works:**
```
User accepts completion
    ↓
Record feedback
    ↓
Update profile
    ↓
Extract style patterns
    ↓
Next completion uses patterns
    ↓
Better suggestions! 🎯
```

---

### 2. Privacy Considerations

**What we store:**
- ✅ Statistical patterns (type hints: yes/no)
- ✅ Aggregated metrics (accept rate, avg time)
- ✅ Style preferences (indentation, naming)

**What we DON'T store:**
- ❌ Full code content (privacy!)
- ❌ Project names
- ❌ Sensitive data

**GDPR compliance:**
- Users can view profile: `GET /feedback/profile`
- Users can delete profile: `DELETE /feedback/profile`
- Data minimization (only necessary data)

---

### 3. Accept Time Metrics

**Why track accept time?**

**Fast acceptance (< 500ms):**
- User confident → completion matches intent
- High-quality suggestion

**Slow acceptance (> 2s):**
- User hesitating → maybe not perfect
- User might edit before accepting

**Use cases:**
- Filter training data (only quick accepts = high confidence)
- Measure suggestion quality
- A/B testing different models

---

### 4. Coding Style Detection

**Patterns detected:**

**Python:**
```python
# Type hints
def add(a: int, b: int) -> int:  # uses_type_hints = true

# No type hints
def add(a, b):  # uses_type_hints = false
```

**Indentation:**
```python
# 4 spaces
def foo():
    pass  # indentation = "4_spaces"

# Tabs
def foo():
	pass  # indentation = "tabs"
```

**Naming:**
```python
my_variable = 1  # naming_convention = "snake_case"
myVariable = 1   # naming_convention = "camelCase"
```

---

### 5. Profile Lifecycle

**Creation:**
```
First completion accepted
    ↓
POST /feedback/completion
    ↓
Profile created: data/profiles/user-456.json
```

**Updates:**
```
Each feedback
    ↓
Load profile
    ↓
Update statistics
    ↓
Save profile
```

**Deletion:**
```
User request or GDPR
    ↓
DELETE /feedback/profile
    ↓
File deleted: data/profiles/user-456.json
```

---

## 🧪 Test Cases

### Test 1: Record feedback (accept)

```python
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, Mock

client = TestClient(app)

mock_profile = Mock()
mock_profile.coding_style.total_samples = 10
mock_profile.accept_rate = 0.8

with patch('app.services.user_profiling.get_profiler') as mock_profiler:
    mock_profiler.return_value.update_profile_from_completion.return_value = mock_profile
    
    response = client.post(
        "/feedback/completion",
        headers={
            "Authorization": "Bearer test-key",
            "X-User-ID": "user-123"
        },
        json={
            "request_id": "abc-123",
            "accepted": True,
            "completion_text": "return a + b",
            "prefix": "def add(a, b):\n    ",
            "accept_time_ms": 850.5
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["user_id"] == "user-123"
    assert data["total_samples"] == 10
    assert data["accept_rate"] == 0.8
```

---

### Test 2: Record feedback without user ID

```python
response = client.post(
    "/feedback/completion",
    headers={"Authorization": "Bearer test-key"},
    json={
        "request_id": "abc-123",
        "accepted": True
    }
)

assert response.status_code == 400
assert "X-User-ID" in response.json()["detail"]
```

---

### Test 3: Get user profile

```python
mock_profile = Mock()
mock_profile.user_id = "user-123"
mock_profile.coding_style.model_dump.return_value = {
    "uses_type_hints": True,
    "total_samples": 50
}
mock_profile.accept_rate = 0.85
mock_profile.avg_accept_time_ms = 1200.0
mock_profile.preferred_completion_length = 45
mock_profile.created_at = "2025-11-01T10:00:00"
mock_profile.updated_at = "2025-11-11T14:00:00"

with patch('app.services.user_profiling.get_profiler') as mock_profiler:
    mock_profiler.return_value.load_profile.return_value = mock_profile
    
    response = client.get(
        "/feedback/profile",
        headers={
            "Authorization": "Bearer test-key",
            "X-User-ID": "user-123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user-123"
    assert data["accept_rate"] == 0.85
    assert data["coding_style"]["uses_type_hints"] == True
```

---

### Test 4: Delete profile (exists)

```python
from pathlib import Path

mock_path = Mock(spec=Path)
mock_path.exists.return_value = True

with patch('app.services.user_profiling.get_profiler') as mock_profiler:
    mock_profiler.return_value.get_profile_path.return_value = mock_path
    
    response = client.delete(
        "/feedback/profile",
        headers={
            "Authorization": "Bearer test-key",
            "X-User-ID": "user-123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"
    assert data["user_id"] == "user-123"
    mock_path.unlink.assert_called_once()
```

---

### Test 5: Delete profile (not found)

```python
mock_path = Mock(spec=Path)
mock_path.exists.return_value = False

with patch('app.services.user_profiling.get_profiler') as mock_profiler:
    mock_profiler.return_value.get_profile_path.return_value = mock_path
    
    response = client.delete(
        "/feedback/profile",
        headers={
            "Authorization": "Bearer test-key",
            "X-User-ID": "user-123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_found"
    mock_path.unlink.assert_not_called()
```

---

## 🔧 Client Implementation Example

### VS Code Extension (TypeScript)

```typescript
import * as vscode from 'vscode';

class FeedbackService {
    private apiUrl = 'http://localhost:8000';
    private apiKey = 'sk_abc123...';
    private userId: string;
    
    constructor() {
        // Get or generate user ID
        this.userId = vscode.workspace.getConfiguration('aiCoder').get('userId') 
                      || this.generateUserId();
    }
    
    async recordAcceptance(
        requestId: string,
        completion: string,
        prefix: string,
        acceptTimeMs: number
    ) {
        try {
            const response = await fetch(`${this.apiUrl}/feedback/completion`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.apiKey}`,
                    'X-User-ID': this.userId
                },
                body: JSON.stringify({
                    request_id: requestId,
                    accepted: true,
                    completion_text: completion,
                    prefix: prefix,
                    accept_time_ms: acceptTimeMs
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log(`Profile updated: ${data.total_samples} samples, ${data.accept_rate * 100}% accept rate`);
            }
        } catch (error) {
            console.error('Failed to record feedback:', error);
            // Don't block user - feedback is non-critical
        }
    }
    
    async recordRejection(requestId: string) {
        await fetch(`${this.apiUrl}/feedback/completion`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.apiKey}`,
                'X-User-ID': this.userId
            },
            body: JSON.stringify({
                request_id: requestId,
                accepted: false
            })
        });
    }
    
    async getUserProfile() {
        const response = await fetch(`${this.apiUrl}/feedback/profile`, {
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'X-User-ID': this.userId
            }
        });
        return await response.json();
    }
    
    async deleteProfile() {
        const response = await fetch(`${this.apiUrl}/feedback/profile`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'X-User-ID': this.userId
            }
        });
        return await response.json();
    }
    
    private generateUserId(): string {
        // Generate random user ID
        return `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
}

// Usage in completion provider
class CompletionProvider implements vscode.InlineCompletionItemProvider {
    private feedbackService = new FeedbackService();
    private startTime: number = 0;
    
    async provideInlineCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position
    ) {
        this.startTime = Date.now();
        
        // Get completion from server...
        const completion = await this.getCompletion(...);
        
        return [{
            insertText: completion.text,
            range: new vscode.Range(position, position),
            command: {
                command: 'aiCoder.completionAccepted',
                title: 'Record Acceptance',
                arguments: [completion.requestId, completion.text, prefix]
            }
        }];
    }
}

// Register command for acceptance
vscode.commands.registerCommand('aiCoder.completionAccepted', 
    (requestId, completion, prefix) => {
        const acceptTime = Date.now() - startTime;
        feedbackService.recordAcceptance(requestId, completion, prefix, acceptTime);
    }
);
```

---

**File này hoàn tất!** 🎉

**Routers directory hoàn tất! 4/4 files:**
- ✅ health.py (health checks, models list)
- ✅ completions.py (main completion endpoints)
- ✅ admin.py (telemetry stats, export, download)
- ✅ feedback.py (user feedback, profiles, personalization)

**Tiếp theo:** `services/` directory (groq.py, user_profiling.py, ollama.py). Tiếp tục không? 🚀

