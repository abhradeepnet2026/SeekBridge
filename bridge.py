from flask import Flask, request, jsonify
import subprocess, uuid, shutil, json

app = Flask(__name__)
OPENC_PATH = shutil.which("opencode") or shutil.which("opencode.cmd")
sessions = {}

@app.route("/v1/chat/completions", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        model = data.get("model", "opencode/deepseek-v4-flash-free")
        msgs = data.get("messages", [])
        if not msgs:
            return jsonify({"error": "No messages provided"}), 400

        session_id = data.get("session_id") or request.headers.get("X-Session-Id", "")
        sys_prompt = ""
        user_text = ""
        for m in msgs:
            if m["role"] == "system":
                sys_prompt = m["content"]
            elif m["role"] == "user":
                user_text = m["content"]

        if not user_text:
            return jsonify({"error": "No user message"}), 400

        prompt = f"{sys_prompt}\n\n{user_text}" if sys_prompt else user_text

        if not OPENC_PATH:
            return jsonify({"error": "OpenCode CLI not found in PATH"}), 500

        cmd = [OPENC_PATH, "run", "-m", model, "--format", "json", prompt]
        if session_id and session_id in sessions:
            cmd.insert(-1, "-s")
            cmd.insert(-1, sessions[session_id])

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if res.returncode != 0:
            return jsonify({"error": res.stderr.strip() or f"Exit code {res.returncode}"}), 500

        out_text = ""
        oc_session_id = ""
        for line in res.stdout.strip().splitlines():
            if not line.strip():
                continue
            try:
                evt = json.loads(line)
                if evt.get("type") == "text":
                    out_text += evt["part"]["text"]
                if evt.get("type") == "step_start":
                    oc_session_id = evt["part"]["sessionID"]
                elif evt.get("type") == "step_finish" and not oc_session_id:
                    oc_session_id = evt["part"]["sessionID"]
            except json.JSONDecodeError:
                pass

        if oc_session_id:
            session_key = session_id or str(uuid.uuid4())
            sessions[session_key] = oc_session_id
            response_id = session_key
        else:
            response_id = str(uuid.uuid4())

        return jsonify({
            "id": response_id,
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": out_text.strip()}, "finish_reason": "stop"}]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080)