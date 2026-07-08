import subprocess, sys, os, shutil

def ensure_deps():
    print("--- SeekBridge Setup ---")
    try:
        import fastapi, uvicorn
    except ImportError:
        print("[*] Installing FastAPI + Uvicorn...")
        subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn"], check=True)

def verify_env():
    if not (shutil.which("opencode") or shutil.which("opencode.cmd")):
        print("\n[!] OpenCode CLI not found in system PATH.")
        print("Please install it first: https://opencode.sh")
        sys.exit(1)

if __name__ == "__main__":
    ensure_deps()
    verify_env()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    bridge_path = os.path.join(base_dir, "bridge.py")

    print(f"\n[+] Starting bridge at http://127.0.0.1:8080/v1")
    print(f"[*] Model: opencode/deepseek-v4-flash-free")
    print(f"[*] Streaming: enabled (SSE)\n")

    try:
        subprocess.run([sys.executable, bridge_path], cwd=base_dir, check=True)
    except KeyboardInterrupt:
        print("\nStopping SeekBridge...")
