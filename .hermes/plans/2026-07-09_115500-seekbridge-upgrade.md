# SeekBridge Upgrade Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Transform SeekBridge from a basic synchronous Flask proxy into a high-performance, streaming-capable API gateway that "directly" connects OpenCode CLI models to Hermes Agent, eliminating the need for paid API fallbacks.

**Architecture:** 
Replace the synchronous Flask server with an asynchronous FastAPI server. Use `asyncio.create_subprocess_exec` to run `opencode` and stream its JSON-L output in real-time as OpenAI-compatible Server-Sent Events (SSE).

**Tech Stack:** 
- Python 3.11+
- FastAPI (Async API framework)
- Uvicorn (ASGI server)
- Asyncio (Process management)

---

## Current Context & Assumptions
- `opencode` CLI is installed and available in the system PATH.
- `opencode run` outputs JSON-L events (e.g., `{"type": "text", "part": {"text": "..."}}`).
- The user wants a "direct" feel, which in API terms means low latency and streaming responses.
- Ponytail Mode (Full) is active: prioritize minimal code, stdlib where possible, and root-cause efficiency.

## Step-by-Step Plan

### Task 1: Infrastructure Update & Dependency Management
**Objective:** Move from Flask to FastAPI/Uvicorn for async support.

**Files:**
- Modify: `requirements.txt`
- Create: `.hermes/plans/2026-07-09_000000-seekbridge-upgrade.md` (this file)

**Step 1: Update requirements**
```bash
# Update requirements.txt
echo "fastapi
uvicorn" > requirements.txt
```

**Step 2: Verify installation**
Run: `uv pip install -r requirements.txt` (or `pip install`)
Expected: Successful installation of fastapi and uvicorn.

**Step 3: Commit**
```bash
git add requirements.txt
git commit -m "chore: switch to fastapi for async streaming support"
```

### Task 2: Implement Async Streaming Core
**Objective:** Replace the synchronous `subprocess.run` with an asynchronous generator that streams `opencode` output.

**Files:**
- Modify: `bridge.py`

**Step 1: Implement the streaming generator**
The core logic should:
1. Spawn `opencode` via `asyncio.create_subprocess_exec`.
2. Read `stdout` line by line.
3. Parse the JSON event.
4. Yield an OpenAI-compatible stream chunk.

**Proposed Code Fragment:**
```python
async def stream_opencode(model, prompt, session_id=None):
    cmd = [OPENC_PATH, "run", "-m", model, "--format", "json", prompt]
    if session_id:
        cmd.extend(["-s", session_id])
    
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    
    async for line in process.stdout:
        try:
            evt = json.loads(line.decode())
            if evt.get("type") == "text":
                content = evt["part"]["text"]
                yield f"data: {json.dumps({'choices': [{'delta': {'content': content}}]})}\n\n"
        except json.JSONDecodeError:
            continue
    
    yield "data: [DONE]\n\n"
    await process.wait()
```

**Step 2: Run a basic test script to verify the generator yields chunks.**
Expected: Correct OpenAI-format chunks.

**Step 3: Commit**
```bash
git add bridge.py
git commit -m "feat: implement async streaming generator for opencode"
```

### Task 3: Build the FastAPI Endpoint
**Objective:** Expose the generator via a `/v1/chat/completions` endpoint using `StreamingResponse`.

**Files:**
- Modify: `bridge.py`

**Step 1: Implement the endpoint**
```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/v1/chat/completions")
async def chat(request: Request):
    data = await request.json()
    model = data.get("model", "opencode/deepseek-v4-flash-free")
    # ... prompt extraction logic from old bridge.py ...
    
    return StreamingResponse(
        stream_opencode(model, prompt, session_id), 
        media_type="text/event-stream"
    )
```

**Step 2: Verify with `curl`**
Run: `curl -X POST http://127.0.0.1:8080/v1/chat/completions -d '{"messages": [{"role": "user", "content": "Hello"}]}'`
Expected: Streamed `data: {...}` blocks.

**Step 3: Commit**
```bash
git add bridge.py
git commit -m "feat: expose streaming chat endpoint via FastAPI"
```

### Task 4: Session Management & Robustness
**Objective:** Improve session ID handling to ensure conversations stay contiguous.

**Files:**
- Modify: `bridge.py`

**Step 1: Refine session mapping**
Ensure `oc_session_id` is captured from `step_start` events and persisted in the `sessions` dict for subsequent calls.

**Step 2: Add basic error handling**
Wrap the process spawn in a try-except and return a 500 JSON response if the process fails to start.

**Step 3: Commit**
```bash
git add bridge.py
git commit -m "refactor: improve session persistence and error handling"
```

### Task 5: Validation & Final Handoff
**Objective:** End-to-end verification with Hermes Agent.

**Step 1: Launch server**
Run: `uvicorn bridge:app --host 127.0.0.1 --port 8080`

**Step 2: Configure Hermes**
- Base URL: `http://127.0.0.1:8080/v1`
- Model: `opencode/deepseek-v4-flash-free`
- API Key: `any`

**Step 3: Test a complex multi-turn conversation**
Verify that the agent streams the response and remembers context via the bridge's session management.

**Step 4: Final Commit & Cleanup**
```bash
git add .
git commit -m "perf: complete transition to streaming async bridge"
```

---

## Risks & Tradeoffs
- **CLI Overhead:** Spawning a process per request is heavier than a native API call, but is the only way to use `opencode` CLI. Using `asyncio` minimizes the blocking impact.
- **JSON-L Stability:** If `opencode` changes its output format, the bridge will break. Added `try-except` on `json.loads` to prevent crashes.
- **Memory:** The `sessions` dict is in-memory. For a local bridge, this is sufficient (YAGNI).

## Verification Steps
- [ ] `curl` test returns `text/event-stream`.
- [ ] Response content matches `opencode` CLI output.
- [ ] Multi-turn conversation maintains state (Session ID is passed and reused).
- [ ] No 404/500 errors on standard OpenAI payload.
