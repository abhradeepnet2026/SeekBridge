import asyncio
import json
import shutil
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()
OPENC = shutil.which("opencode") or shutil.which("opencode.cmd")
sessions: dict[str, str] = {}  # ponytail: in-mem, fine for a local bridge


def _extract(messages: list[dict]) -> tuple[str, str]:
    sys_p = usr_t = ""
    for m in messages:
        if m.get("role") == "system":
            sys_p = m.get("content", "")
        elif m.get("role") == "user":
            usr_t = m.get("content", "")
    return sys_p, usr_t


async def _stream(model: str, prompt: str, skey: str | None):
    oc_sid = sessions.get(skey) if skey else None
    cmd = [OPENC, "run", "-m", model, "--format", "json"]
    if oc_sid:
        cmd += ["-s", oc_sid]
    cmd += [prompt]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    final_sid = ""
    try:
        assert proc.stdout
        while True:
            raw = await proc.stdout.readline()
            if not raw:
                break
            line = raw.decode(errors="replace").strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue

            et = evt.get("type")
            if et == "error":
                err = evt.get("error", {})
                yield f"data: {json.dumps({'error': err.get('message', 'opencode error')})}\n\n"
                break
            if et == "step_start" and not final_sid:
                final_sid = evt.get("sessionID", "")
            elif et == "text":
                chunk = evt.get("part", {}).get("text", "")
                if chunk:
                    yield "data: " + json.dumps({
                        "id": skey or "chatcmpl-seekbridge",
                        "object": "chat.completion.chunk",
                        "model": model,
                        "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}],
                    }) + "\n\n"
            elif et == "step_finish":
                if not final_sid:
                    final_sid = evt.get("sessionID", "")
                yield "data: " + json.dumps({
                    "id": skey or "chatcmpl-seekbridge",
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": evt.get("part", {}).get("reason", "stop")}],
                }) + "\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        if proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        if final_sid and skey:
            sessions[skey] = final_sid
        yield "data: [DONE]\n\n"
        err_bytes = await proc.stderr.read() if proc.stderr else b""
        if err_bytes:
            err_text = err_bytes.decode(errors="replace").strip()
            if err_text and proc.returncode != 0:
                yield f"data: {json.dumps({'error': err_text})}\n\n"


@app.post("/v1/chat/completions")
async def chat(req: Request):
    if not OPENC:
        return JSONResponse({"error": "OpenCode CLI not found in PATH"}, status_code=500)

    data = await req.json()
    model = data.get("model", "opencode/deepseek-v4-flash-free")
    msgs = data.get("messages", [])
    if not msgs:
        return JSONResponse({"error": "No messages provided"}, status_code=400)

    sys_p, usr_t = _extract(msgs)
    if not usr_t:
        return JSONResponse({"error": "No user message"}, status_code=400)

    prompt = f"{sys_p}\n\n{usr_t}" if sys_p else usr_t
    skey = data.get("session_id") or req.headers.get("X-Session-Id", "") or str(uuid.uuid4())

    stream = data.get("stream", False)
    if stream:
        gen = _stream(model, prompt, skey)
        return StreamingResponse(gen, media_type="text/event-stream",
                                 headers={"X-Session-Id": skey, "Cache-Control": "no-cache"})

    # Non-streaming fallback: buffer the whole stream and return a single JSON blob.
    content = []
    finish = "stop"
    async for chunk_str in _stream(model, prompt, skey):
        for raw in chunk_str.splitlines():
            if not raw.startswith("data: "):
                continue
            payload = raw[6:]
            if payload == "[DONE]":
                continue
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if "error" in obj:
                return JSONResponse({"error": obj["error"]}, status_code=500)
            for choice in obj.get("choices", []):
                content.append(choice.get("delta", {}).get("content", ""))
                if choice.get("finish_reason"):
                    finish = choice["finish_reason"]

    return JSONResponse({
        "id": skey,
        "object": "chat.completion",
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "".join(content).strip()}, "finish_reason": finish}],
    })


@app.get("/v1/models")
async def list_models():
    return {"object": "list", "data": [{"id": "opencode/deepseek-v4-flash-free", "object": "model"}]}


@app.get("/health")
async def health():
    return {"status": "ok", "opencode": bool(OPENC), "sessions": len(sessions)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
