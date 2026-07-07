from flask import Flask, request, jsonify
import subprocess, uuid, shutil

app = Flask(__name__)

def get_opencode_path():
    # Search for opencode in PATH, otherwise return a default guess or handle error
    path = shutil.which("opencode") or shutil.which("opencode.cmd")
    if not path:
        raise RuntimeError("OpenCode CLI not found in system PATH. Please install it first.")
    return path

@app.route("/v1/chat/completions", methods=["POST"])
def chat():
    try:
        body = request.get_json(force=True)
        model = body.get("model", "opencode/deepseek-v4-flash-free")
        messages = body.get("messages", [])
        if not messages: return jsonify({"error": "No messages"}), 400
        
        last_user = [m["content"] for m in messages if m["role"] == "user"][-1]
        
        # Use the dynamic path found by get_opencode_path()
        res = subprocess.run([get_opencode_path(), "run", "-m", model, last_user], capture_output=True, text=True, timeout=120)
        content = res.stdout.strip().split('\n\n')[-1] if '\n\n' in res.stdout else res.stdout.strip()
        
        return jsonify({
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
