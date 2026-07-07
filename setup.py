import subprocess, sys, os

def install_deps():
    print("Checking dependencies...")
    try:
        import flask
    except ImportError:
        print("Installing Flask...")
        subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True)

def check_opencode():
    import shutil
    if not shutil.which("opencode") and not shutil.which("opencode.cmd"):
        print("\n[!] OpenCode CLI not found!")
        print("Please install OpenCode CLI first before running this bridge.")
        sys.exit(1)

if __name__ == "__main__":
    install_deps()
    check_opencode()
    print("\nStarting SeekBridge...")
    print("API will be available at: http://127.0.0.1:8080/v1")
    print("Model to use: opencode/deepseek-v4-flash-free")
    # Use absolute path to bridge.py
    bridge_path = os.path.join(os.path.dirname(__file__), "bridge.py")
    subprocess.run([sys.executable, bridge_path])
