from flask import Flask, request, jsonify
import subprocess, uuid, shutil

app = Flask(__name__)
OPENC_PATH = shutil.which("opencode") or shutil.which("opencode.cmd")

@app.route("/v1/chat/completions", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        model = data.get("model", "opencode/deepseek-v4-flash-free")
        msgs = data.get("messages", [])
        if not msgs: return jsonify({"error": "No messages provided"}), 400
        
        user_msgs = [m["content"] for m in msgs if m["role"] == "user"]
        if not user_msgs: return jsonify({"error": "No user message found"}), 400
        user_query = user_msgs[-1]
        
        if not OPENC_PATH:
            return jsonify({"error": "OpenCode CLI not found in PATH"}), 500
        res = subprocess.run(
            [OPENC_PATH, "run", "-m", model, user_query],
            capture_output=True, text=True, timeout=120
        )
        
        # Ponytail parsing: Extract content after the first double-newline (header separator)
        # or take the whole output if no separator exists.
        out = res.stdout.strip()
        if "\n\n" in out:
            out = out.split("\n\n", 1)[-1].strip()

        return jsonify({
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": out}, "finish_reason": "stop"}]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080)
